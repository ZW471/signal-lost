"""
Signal Lost — Message Reducer

Smart context management that collapses tool-call noise while preserving
narrative continuity. This is the key improvement over the CLI-based approach.
"""

from __future__ import annotations

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)


def summarize_tool_calls(messages: list[BaseMessage]) -> str:
    """Summarize a sequence of tool calls into a compact one-line description."""
    summaries = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            # Extract the tool name and a brief result summary
            name = msg.name or "tool"
            content = str(msg.content)
            if len(content) > 80:
                content = content[:77] + "..."
            summaries.append(f"{name}: {content}")
        elif isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.get("name", "tool")
                args = tc.get("args", {})
                # Compact representation of key args
                arg_str = ", ".join(f"{k}={v}" for k, v in list(args.items())[:2])
                summaries.append(f"called {name}({arg_str})")

    return " | ".join(summaries) if summaries else ""


def reduce_turn_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Collapse a completed turn's messages into a compact form.

    Keeps:
    - The player's input (HumanMessage)
    - The final narrative (last AIMessage with text content, no tool_calls)
    - A compact SystemMessage summarizing tool calls and state changes

    Removes:
    - All intermediate AIMessage with tool_calls (the LLM's internal reasoning)
    - All ToolMessage objects (raw tool results)
    """
    human_msgs = []
    tool_msgs = []
    final_narrative = None

    for msg in messages:
        if isinstance(msg, HumanMessage):
            human_msgs.append(msg)
        elif isinstance(msg, ToolMessage):
            tool_msgs.append(msg)
        elif isinstance(msg, AIMessage):
            if msg.tool_calls:
                tool_msgs.append(msg)
            elif msg.content:
                final_narrative = msg

    result = list(human_msgs)

    # Add compact tool summary if there were tool calls
    tool_summary = summarize_tool_calls(tool_msgs)
    if tool_summary:
        result.append(SystemMessage(content=f"[Turn mechanics: {tool_summary}]"))

    if final_narrative:
        result.append(final_narrative)

    return result


def trim_to_window(
    messages: list[BaseMessage],
    max_turns: int = 5,
) -> tuple[list[BaseMessage], list[BaseMessage]]:
    """Identify which conversation messages fall outside the active window.

    Returns (to_keep, to_remove):
      - to_keep: messages within the last `max_turns` turns
      - to_remove: messages older than the window (caller emits RemoveMessage for these)

    SystemMessages are excluded from the window count — they are managed separately
    by input_gate. The caller is responsible for removing/replacing system messages.

    A "turn" begins with each HumanMessage. Inline [Turn mechanics: ...] SystemMessages
    that appear between HumanMessages are counted as part of the preceding turn.
    """
    # Strip system messages — managed externally
    conversation = [m for m in messages if not isinstance(m, SystemMessage)]

    # Group into turns (each turn starts with a HumanMessage)
    turns: list[list[BaseMessage]] = []
    current_turn: list[BaseMessage] = []
    for msg in conversation:
        if isinstance(msg, HumanMessage) and current_turn:
            turns.append(current_turn)
            current_turn = [msg]
        else:
            current_turn.append(msg)
    if current_turn:
        turns.append(current_turn)

    if len(turns) <= max_turns:
        return conversation, []

    old_turns = turns[:-max_turns]
    recent_turns = turns[-max_turns:]

    to_remove = [msg for turn in old_turns for msg in turn]
    to_keep = [msg for turn in recent_turns for msg in turn]
    return to_keep, to_remove
