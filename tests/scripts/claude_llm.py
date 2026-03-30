"""
Signal Lost — Claude Code CLI LLM Wrapper

A LangChain BaseChatModel that uses `claude -p` (Claude Code print mode)
for inference instead of a direct API call. This lets you run the game
engine using your Claude Code subscription with no extra API costs.

Optimizations (inspired by Paperclip's claude-local adapter):
- stream-json output for structured NDJSON parsing
- stdin piping instead of --system-prompt CLI arg
- session reuse via --resume for faster subsequent calls
- nesting-guard env var stripping
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from typing import Any, Sequence
from uuid import uuid4

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable, RunnableBinding
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool

# Env vars that prevent nested Claude Code sessions from starting
_NESTING_GUARD_VARS = (
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "CLAUDE_CODE_SESSION",
    "CLAUDE_CODE_PARENT_SESSION",
)


def _clean_env() -> dict[str, str]:
    """Return os.environ with Claude Code nesting-guard vars stripped."""
    return {k: v for k, v in os.environ.items() if k not in _NESTING_GUARD_VARS}


def _parse_stream_json(stdout: str) -> tuple[str, str | None]:
    """Parse NDJSON stream from `claude -p --output-format stream-json --verbose`.

    Returns (result_text, session_id).
    Raises RuntimeError if the stream indicates an error or contains no result.
    """
    session_id: str | None = None
    result_text: str | None = None

    for line in stdout.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        event_type = event.get("type")

        if event_type == "system":
            session_id = event.get("session_id") or session_id

        elif event_type == "result":
            session_id = event.get("session_id") or session_id
            if event.get("is_error"):
                error_msg = event.get("result", "Unknown error from Claude CLI")
                raise RuntimeError(f"claude CLI error: {error_msg}")
            result_text = event.get("result", "")

    if result_text is None:
        raise RuntimeError("claude CLI returned no result event in stream-json output")

    return result_text, session_id


def _serialize_messages(messages: list[BaseMessage]) -> tuple[str, str]:
    """Split messages into (system_prompt, conversation_text).

    All SystemMessages are concatenated into the system prompt.
    HumanMessage, AIMessage, and ToolMessage become the conversation.
    """
    system_parts: list[str] = []
    conversation_parts: list[str] = []

    for msg in messages:
        if isinstance(msg, SystemMessage):
            system_parts.append(str(msg.content))
        elif isinstance(msg, HumanMessage):
            conversation_parts.append(f"[HUMAN]\n{msg.content}")
        elif isinstance(msg, AIMessage):
            text = str(msg.content) if msg.content else ""
            if msg.tool_calls:
                calls = ", ".join(
                    f"{tc['name']}({json.dumps(tc['args'], ensure_ascii=False)})"
                    for tc in msg.tool_calls
                )
                text += f"\n[Called tools: {calls}]"
            if text.strip():
                conversation_parts.append(f"[ASSISTANT]\n{text}")
        elif isinstance(msg, ToolMessage):
            conversation_parts.append(
                f"[TOOL RESULT: {msg.name}]\n{msg.content}"
            )

    system_prompt = "\n\n".join(system_parts)
    conversation = "\n\n".join(conversation_parts)
    return system_prompt, conversation


def _format_tool_schemas(tools: list[dict]) -> str:
    """Build a compact tool description block for the system prompt."""
    lines = [
        "\n\n## TOOL CALLING",
        "You have game tools. When you need to call tools:",
        "",
        "1. Call ALL tools you need in ONE JSON response — do NOT spread tool calls across multiple responses.",
        '   Format: {"tool_calls": [{"name": "tool_name", "args": {"param": "value"}}, ...]}',
        "",
        "2. After you see [TOOL RESULT] messages, write your narrative response.",
        "   Write rich, vivid, atmospheric cyberpunk prose (at least 3-4 paragraphs).",
        "",
        "3. If no tools are needed, just write your narrative directly.",
        "",
        "IMPORTANT:",
        "- Bundle ALL tool calls into a SINGLE JSON object — one response, all tools at once.",
        "- For tool args that expect JSON (like 'changes'), pass the value directly as an object, NOT as a string.",
        '  Correct: {"name": "update_player", "args": {"changes": {"credits": 40}}}',
        '  Wrong:   {"name": "update_player", "args": {"changes": "{\\"credits\\": 40}"}}',
        "",
        "### Available Tools:",
    ]
    for t in tools:
        func = t.get("function", t)
        name = func.get("name", "?")
        desc = func.get("description", "").split("\n")[0]  # first line only
        params = func.get("parameters", {})
        required = params.get("required", [])
        props = params.get("properties", {})
        param_strs = []
        for pname, pinfo in props.items():
            ptype = pinfo.get("type", "any")
            if "anyOf" in pinfo:
                ptype = "|".join(a.get("type", "?") for a in pinfo["anyOf"])
            req = " (required)" if pname in required else ""
            param_strs.append(f"  - {pname}: {ptype}{req}")
        lines.append(f"\n**{name}** — {desc}")
        if param_strs:
            lines.extend(param_strs)

    return "\n".join(lines)


def _parse_tool_response(raw: str) -> AIMessage:
    """Parse a response that may contain tool calls as JSON embedded in prose.

    The model may output:
    1. Pure prose (no tools needed) — return as narrative
    2. A JSON object with tool_calls (possibly surrounded by narrative text)
    3. A JSON block in markdown fences
    """
    stripped = raw.strip()

    # Try to find a JSON object with tool_calls anywhere in the response
    # Strategy: look for lines that parse as JSON with a tool_calls key
    json_match = None
    narrative_parts = []

    # Check for markdown-fenced JSON
    fence_pattern = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)
    fence_m = fence_pattern.search(stripped)
    if fence_m:
        try:
            candidate = json.loads(fence_m.group(1).strip())
            if isinstance(candidate, dict) and "tool_calls" in candidate:
                json_match = candidate
                # Narrative is everything outside the fence
                before = stripped[:fence_m.start()].strip()
                after = stripped[fence_m.end():].strip()
                narrative_parts = [p for p in [before, after] if p]
        except (json.JSONDecodeError, TypeError):
            pass

    # If no fenced JSON, try to find a JSON line
    if json_match is None:
        for line in stripped.split("\n"):
            line_s = line.strip()
            if line_s.startswith("{") and line_s.endswith("}"):
                try:
                    candidate = json.loads(line_s)
                    if isinstance(candidate, dict) and "tool_calls" in candidate:
                        json_match = candidate
                        # Narrative is everything except this line
                        narrative_parts = [
                            l for l in stripped.split("\n")
                            if l.strip() != line_s
                        ]
                        break
                except (json.JSONDecodeError, TypeError):
                    continue

    # If no inline JSON, try parsing the entire response as JSON
    if json_match is None:
        try:
            candidate = json.loads(stripped)
            if isinstance(candidate, dict) and "tool_calls" in candidate:
                json_match = candidate
                narrative_parts = [candidate.get("text", "")]
        except (json.JSONDecodeError, TypeError):
            pass

    if json_match is not None:
        tool_calls_raw = json_match.get("tool_calls", [])
        if tool_calls_raw:
            tool_calls = [
                {
                    "name": tc["name"],
                    "args": tc.get("args", {}),
                    "id": f"call_{uuid4().hex[:12]}",
                    "type": "tool_call",
                }
                for tc in tool_calls_raw
                if isinstance(tc, dict) and "name" in tc
            ]
            # Normalize: tools that expect JSON string params may receive
            # dicts from the model.  Serialize them so the tool gets valid JSON.
            _JSON_STRING_PARAMS = {"changes", "entry", "location_data", "item"}
            for tc in tool_calls:
                for param, val in list(tc["args"].items()):
                    if param in _JSON_STRING_PARAMS and isinstance(val, dict):
                        tc["args"][param] = json.dumps(val, ensure_ascii=False)
            narrative = "\n".join(narrative_parts).strip()
            # Also include any "text" from the JSON itself
            json_text = json_match.get("text", "")
            if json_text and json_text not in narrative:
                narrative = (narrative + "\n\n" + json_text).strip() if narrative else json_text
            return AIMessage(content=narrative, tool_calls=tool_calls)

    # No tool calls found — entire response is narrative
    return AIMessage(content=raw)


class ClaudeCodeLLM(BaseChatModel):
    """LangChain chat model that delegates to `claude -p` (Claude Code CLI).

    Uses stream-json output, stdin piping, and session reuse for performance.
    """

    model_name: str = "sonnet"
    max_retries: int = 2
    timeout: int = 180
    _session_id: str | None = None

    @property
    def _llm_type(self) -> str:
        return "claude-code-cli"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        tools = kwargs.get("tools")
        tool_schemas: list[dict] | None = None

        if tools:
            tool_schemas = [
                convert_to_openai_tool(t) if not isinstance(t, dict) else t
                for t in tools
            ]

        system_prompt, conversation = _serialize_messages(messages)

        # Append tool schemas to system prompt when tools are bound
        if tool_schemas:
            system_prompt += _format_tool_schemas(tool_schemas)

        raw = self._call_claude(system_prompt, conversation)

        if tool_schemas:
            message = _parse_tool_response(raw)
        else:
            message = AIMessage(content=raw)

        return ChatResult(generations=[ChatGeneration(message=message)])

    def _call_claude(self, system_prompt: str, user_prompt: str) -> str:
        """Invoke `claude -p` with stream-json output and session reuse."""
        cmd = [
            "claude", "-p",
            "--model", self.model_name,
            "--output-format", "stream-json",
            "--verbose",
            "--tools", "",
            "--effort", "low",
        ]

        if self._session_id:
            cmd.extend(["--resume", self._session_id])

        # Pipe system prompt + conversation via stdin instead of --system-prompt arg
        stdin_parts = []
        if system_prompt:
            stdin_parts.append(f"[SYSTEM PROMPT]\n{system_prompt}")
        if user_prompt:
            stdin_parts.append(f"[CONVERSATION]\n{user_prompt}")
        stdin_text = "\n\n".join(stdin_parts)

        env = _clean_env()
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                result = subprocess.run(
                    cmd,
                    input=stdin_text,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    env=env,
                )

                if result.returncode != 0:
                    stderr = result.stderr[:500] if result.stderr else ""
                    # If session resume failed (stale/unknown), retry without it
                    if self._session_id and ("unknown session" in stderr.lower()
                                              or "session" in stderr.lower()):
                        self._session_id = None
                        cmd = [c for c in cmd if c != "--resume" and c != self._session_id]
                        # Rebuild cmd without --resume
                        cmd = [
                            "claude", "-p",
                            "--model", self.model_name,
                            "--output-format", "stream-json",
                            "--verbose",
                            "--tools", "",
                            "--effort", "low",
                        ]
                        continue
                    raise RuntimeError(f"claude CLI exited {result.returncode}: {stderr}")

                output = result.stdout.strip()
                if not output:
                    raise RuntimeError("claude CLI returned empty response")

                # Parse NDJSON stream for result text and session_id
                text, session_id = _parse_stream_json(output)
                if session_id:
                    self._session_id = session_id

                if not text:
                    raise RuntimeError("claude CLI returned empty result text")

                return text

            except (subprocess.TimeoutExpired, RuntimeError) as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)

        raise last_error  # type: ignore[misc]

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | BaseTool | Any],
        **kwargs: Any,
    ) -> Runnable:
        """Bind tools so they're passed to _generate via kwargs."""
        tool_schemas = [
            convert_to_openai_tool(t) if not isinstance(t, dict) else t
            for t in tools
        ]
        return self.bind(tools=tool_schemas, **kwargs)
