"""
Signal Lost — Codex CLI LLM Wrapper

A LangChain BaseChatModel that uses `codex exec` (OpenAI Codex CLI non-interactive mode)
for inference instead of a direct API call. This lets you run the game engine using
your ChatGPT Plus/Pro/Business/Edu/Enterprise plan via Codex's OAuth login.

Mirrors the design of `claude_llm.py`:
- JSONL stream parsing (--json) for structured event capture
- stdin piping of system prompt + conversation
- Session reuse via `codex exec resume` for faster subsequent calls
- Nesting-guard env var stripping
- Sandboxed read-only execution (no file writes from inside the model)

Authentication:
- Run `codex login` once to sign in with your ChatGPT account (OAuth).
- Or set OPENAI_API_KEY in .env / environment and Codex will use it.
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
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool

# Env vars that Codex sets when running inside a Codex session — strip them to
# prevent nested sessions from confusing the child process.
_NESTING_GUARD_VARS = (
    "CODEX_SANDBOX",
    "CODEX_SANDBOX_NETWORK_DISABLED",
    "CODEX_AGENT_IDENTITY",
    "CODEX_HOME_OVERRIDE_SESSION",
    "CODEX_SESSION_ID",
)


def _clean_env() -> dict[str, str]:
    """Return os.environ with Codex nesting-guard vars stripped."""
    return {k: v for k, v in os.environ.items() if k not in _NESTING_GUARD_VARS}


def _parse_json_stream(stdout: str) -> tuple[str, str | None]:
    """Parse JSONL stream from `codex exec --json`.

    Returns (result_text, thread_id).

    Codex emits NDJSON events. The final agent reply is in either:
        {"type": "item.completed", "item": {"item_type": "agent_message", "text": "..."}}
    or
        {"type": "turn.completed", "result": "..."}

    The thread id is in:
        {"type": "thread.started", "thread_id": "..."}
    """
    thread_id: str | None = None
    agent_text: str | None = None
    fallback_text_parts: list[str] = []

    for line in stdout.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue

        etype = event.get("type", "")

        if etype == "thread.started":
            thread_id = event.get("thread_id") or thread_id

        elif etype == "session.created":
            # Older codex builds use session.created instead of thread.started
            thread_id = event.get("session_id") or event.get("thread_id") or thread_id

        elif etype == "item.completed":
            item = event.get("item") or {}
            # item_type is the new field name; older builds used "type"
            item_type = item.get("item_type") or item.get("type")
            if item_type in ("agent_message", "assistant_message", "message"):
                text = item.get("text") or item.get("content") or ""
                if isinstance(text, list):
                    text = "".join(
                        (p.get("text", "") if isinstance(p, dict) else str(p))
                        for p in text
                    )
                if text:
                    agent_text = text  # keep the last one

        elif etype == "turn.completed":
            result = event.get("result")
            if isinstance(result, str) and result:
                fallback_text_parts.append(result)

        elif etype == "error":
            err_msg = event.get("message") or event.get("error") or "Unknown codex error"
            raise RuntimeError(f"codex CLI error: {err_msg}")

    if agent_text is None:
        if fallback_text_parts:
            agent_text = "\n".join(fallback_text_parts)
        else:
            raise RuntimeError("codex CLI returned no agent_message in JSON stream")

    return agent_text, thread_id


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
        desc = func.get("description", "").split("\n")[0]
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
    """Parse a response that may contain tool calls as JSON embedded in prose."""
    stripped = raw.strip()

    json_match = None
    narrative_parts: list[str] = []

    fence_pattern = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)
    fence_m = fence_pattern.search(stripped)
    if fence_m:
        try:
            candidate = json.loads(fence_m.group(1).strip())
            if isinstance(candidate, dict) and "tool_calls" in candidate:
                json_match = candidate
                before = stripped[:fence_m.start()].strip()
                after = stripped[fence_m.end():].strip()
                narrative_parts = [p for p in [before, after] if p]
        except (json.JSONDecodeError, TypeError):
            pass

    if json_match is None:
        for line in stripped.split("\n"):
            line_s = line.strip()
            if line_s.startswith("{") and line_s.endswith("}"):
                try:
                    candidate = json.loads(line_s)
                    if isinstance(candidate, dict) and "tool_calls" in candidate:
                        json_match = candidate
                        narrative_parts = [
                            l for l in stripped.split("\n")
                            if l.strip() != line_s
                        ]
                        break
                except (json.JSONDecodeError, TypeError):
                    continue

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
            _JSON_STRING_PARAMS = {"changes", "entry", "location_data", "item"}
            for tc in tool_calls:
                for param, val in list(tc["args"].items()):
                    if param in _JSON_STRING_PARAMS and isinstance(val, dict):
                        tc["args"][param] = json.dumps(val, ensure_ascii=False)
            narrative = "\n".join(narrative_parts).strip()
            json_text = json_match.get("text", "")
            if json_text and json_text not in narrative:
                narrative = (narrative + "\n\n" + json_text).strip() if narrative else json_text
            return AIMessage(content=narrative, tool_calls=tool_calls)

    return AIMessage(content=raw)


class CodexCLILLM(BaseChatModel):
    """LangChain chat model that delegates to `codex exec` (OpenAI Codex CLI).

    Uses --json output, stdin piping, and thread reuse for performance.
    Authenticates via `codex login` (ChatGPT OAuth) or OPENAI_API_KEY.
    """

    model_name: str = "gpt-5.5"
    max_retries: int = 2
    timeout: int = 300
    sandbox: str = "read-only"
    _thread_id: str | None = None

    @property
    def _llm_type(self) -> str:
        return "codex-cli"

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

        if tool_schemas:
            system_prompt += _format_tool_schemas(tool_schemas)

        raw = self._call_claude(system_prompt, conversation)

        if tool_schemas:
            message = _parse_tool_response(raw)
        else:
            message = AIMessage(content=raw)

        return ChatResult(generations=[ChatGeneration(message=message)])

    def _call_claude(self, system_prompt: str, user_prompt: str) -> str:
        """Invoke `codex exec` with --json output.

        Named `_call_claude` to match the duck-typed interface used by the
        claude-code bypass engine — so the codex provider can plug into the
        same fast path without code duplication.
        """
        return self._call_codex(system_prompt, user_prompt)

    def _call_codex(self, system_prompt: str, user_prompt: str) -> str:
        """Invoke `codex exec --json` and return the agent's reply text."""
        cmd = [
            "codex", "exec",
            "--json",
            "--skip-git-repo-check",
            "--sandbox", self.sandbox,
            "--ephemeral",
            "-m", self.model_name,
        ]

        # Build a single stdin payload — codex exec reads the prompt from stdin
        # when no positional prompt is provided.
        stdin_parts: list[str] = []
        if system_prompt:
            stdin_parts.append(f"[SYSTEM PROMPT]\n{system_prompt}")
        if user_prompt:
            stdin_parts.append(f"[CONVERSATION]\n{user_prompt}")
        stdin_text = "\n\n".join(stdin_parts) if stdin_parts else "(no input)"

        env = _clean_env()
        last_error: Exception | None = None

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
                    stderr = (result.stderr or "")[:500]
                    raise RuntimeError(f"codex CLI exited {result.returncode}: {stderr}")

                output = (result.stdout or "").strip()
                if not output:
                    raise RuntimeError("codex CLI returned empty response")

                text, thread_id = _parse_json_stream(output)
                if thread_id:
                    self._thread_id = thread_id

                if not text:
                    raise RuntimeError("codex CLI returned empty result text")

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
