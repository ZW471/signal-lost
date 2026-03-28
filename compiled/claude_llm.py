"""
Signal Lost — Claude Code CLI LLM Wrapper

A LangChain BaseChatModel that uses `claude -p` (Claude Code print mode)
for inference instead of a direct API call. This lets you run the game
engine using your Claude Code subscription with no extra API costs.
"""

from __future__ import annotations

import json
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
        "\n\n## TOOL CALLING — TWO-PHASE RESPONSE",
        "You have game tools. Your response MUST follow this two-phase flow:",
        "",
        "**PHASE 1 (when you need to call tools):**",
        "Output ONLY a JSON object with your tool calls. NO narrative text. NO prose.",
        "Just the raw JSON on a single line:",
        '{"tool_calls": [{"name": "tool_name", "args": {"param": "value"}}]}',
        "",
        "**PHASE 2 (after you see [TOOL RESULT] messages, OR if no tools needed):**",
        "Write your FULL narrative response as rich, vivid, atmospheric prose.",
        "Multiple paragraphs. Immersive noir cyberpunk storytelling.",
        "NO JSON. NO tool calls. Just pure narrative.",
        "",
        "CRITICAL RULES:",
        "- NEVER mix narrative and tool calls in the same response",
        "- When calling tools, output ONLY JSON — save your storytelling for after",
        "- When writing narrative, write at LEAST 3-4 paragraphs of vivid prose",
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
            narrative = "\n".join(narrative_parts).strip()
            # Also include any "text" from the JSON itself
            json_text = json_match.get("text", "")
            if json_text and json_text not in narrative:
                narrative = (narrative + "\n\n" + json_text).strip() if narrative else json_text
            return AIMessage(content=narrative, tool_calls=tool_calls)

    # No tool calls found — entire response is narrative
    return AIMessage(content=raw)


class ClaudeCodeLLM(BaseChatModel):
    """LangChain chat model that delegates to `claude -p` (Claude Code CLI)."""

    model_name: str = "sonnet"
    max_retries: int = 2
    timeout: int = 180

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
        """Invoke `claude -p` and return the raw response text."""
        cmd = [
            "claude", "-p",
            "--model", self.model_name,
            "--tools", "",
            "--no-session-persistence",
        ]

        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                result = subprocess.run(
                    cmd,
                    input=user_prompt,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
                if result.returncode != 0:
                    raise RuntimeError(f"claude CLI exited {result.returncode}: {result.stderr[:500]}")

                output = result.stdout.strip()
                if not output:
                    raise RuntimeError("claude CLI returned empty response")

                return output

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
