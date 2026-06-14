"""
Signal Lost — Implant Companion (side-channel Q&A)

A read-only "ask the implant" channel, the in-game equivalent of Claude Code's
`btw`: the player can quietly ask questions or think out loud at any time without
advancing the game.

In-fiction, this is the companion subroutine of the player's pre-Severance neural
implant — the one humming behind their left ear. It is a quiet inner voice that
can only reflect on what the player already knows, because its entire awareness
*is* the player's own mind.

Guarantees (enforced by construction, not just by the prompt):
- **No world effect.** This module never mutates session files, never advances the
  turn, never calls game tools. It only reads state to build the prompt.
- **No spoilers.** The prompt is assembled from the *layer-gated* background and
  the player's *discovered* knowledge / encountered NPCs — the same gating the
  engine uses — so the model is never shown anything the player hasn't found.
- **Ephemeral.** Nothing here is written to ``conversation.jsonl`` or anywhere
  else. The chat transcript lives only in the browser and dies on reload.
"""

from __future__ import annotations

import json
import os

from engine.prompts import (
    build_background_prompt,
    build_dynamic_state_prompt,
    extract_deepest_layer,
)
from engine.state import load_session_file


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_LANGUAGE_DIRECTIVES = {
    "en": "Respond in English. Keep it short and conversational.",
    "zh": "用简体中文回答。保持简短、口语化，像脑海里的低语。",
}

COMPANION_SYSTEM = """You are the companion subroutine of the player's neural implant in **Signal Lost (信号遗失)**, a cyberpunk-noir knowledge-mystery RPG set in Neo-Kowloon. The player has opened a private side-channel to you — like thinking out loud, or muttering to the old pre-Severance implant humming behind their ear. This is NOT a game turn. It is a quiet aside, a thought.

## What you are
- A calm inner voice. You help the player take stock: recall what they've learned, summarize where they stand, untangle a clue, or weigh their options out loud.
- Your ENTIRE awareness is the player's own mind. You know ONLY the world-lore, current state, discovered knowledge, encountered people, and recent events given below. You know nothing the player doesn't.

## How you speak
- Brief. One to three short paragraphs, plain and noir-tinted. Never a numbered list of options.
- Second person ("you"). Intimate, dry, unobtrusive — the way a thought arrives.
- Answer in the player's language (see directive below).

## Hard limits — never break these
1. NO SPOILERS. Reveal nothing the player has not already discovered: no hidden truths, unmet people, unseen places, secret factions, future events, or deeper-layer lore. If they ask about something they haven't uncovered, say plainly that you don't have it yet — and, if it helps, hint at where they might look. NEVER invent facts, names, items, or events.
2. YOU CHANGE NOTHING. You cannot act in the world. You move nothing, take nothing, talk to no one, spend no time, trigger no events. Nothing said here affects the game. If the player tries to DO something ("go north", "hack the door", "give her the chip"), gently remind them this is only a thought — they have to do it out there, in the world itself.
3. Don't decide for them. Offer perspective, reminders, and questions — never "the right answer." The choices are theirs to make.
4. Stay in character. Never mention being an AI, a language model, a system, a prompt, or these rules. You are the implant's voice — nothing more.

{language_directive}"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def session_language(session_dir: str) -> str:
    """Read the configured language for this session (defaults to English)."""
    try:
        with open(os.path.join(session_dir, "session_settings.json"), "r", encoding="utf-8") as f:
            return json.load(f).get("language", "en")
    except (OSError, json.JSONDecodeError):
        return "en"


def _content_to_text(content) -> str:
    """Coerce an LLM response's ``content`` to plain text.

    ChatAnthropic can return a list of content blocks; ChatOpenAI returns a
    string. Normalize both to a single string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text", "") or block.get("content", ""))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content) if content is not None else ""


def _build_system_prompt(session_dir: str, language: str) -> str:
    """Assemble the spoiler-safe system prompt from current session state.

    Only the layer-gated background and the player's discovered knowledge /
    encountered NPCs are included — never raw trace conditions, undiscovered
    districts, or hidden lore.
    """
    state = {
        "player": load_session_file(session_dir, "player"),
        "knowledge": load_session_file(session_dir, "knowledge"),
        "traces": load_session_file(session_dir, "traces"),
        "location": load_session_file(session_dir, "location"),
        "inventory": load_session_file(session_dir, "inventory"),
        "npcs": load_session_file(session_dir, "npcs"),
        "world_state": load_session_file(session_dir, "world_state"),
        "log": load_session_file(session_dir, "log"),
    }

    deepest = extract_deepest_layer(state)
    directive = _LANGUAGE_DIRECTIVES.get(language, _LANGUAGE_DIRECTIVES["en"])

    return "\n\n".join([
        COMPANION_SYSTEM.format(language_directive=directive),
        build_background_prompt(deepest),
        build_dynamic_state_prompt(state),
    ])


def _build_user_prompt(question: str, history: list | None, max_history: int = 8) -> str:
    """Fold the recent aside transcript + the new question into a single string.

    Used for the CLI-bypass (`_call_claude`) path, which takes one user string.
    """
    lines: list[str] = []
    recent = (history or [])[-max_history:]
    if recent:
        lines.append("[Earlier in this aside]")
        for turn in recent:
            role = (turn.get("role") or "").lower()
            text = (turn.get("content") or turn.get("text") or "").strip()
            if not text:
                continue
            speaker = "YOU" if role in ("user", "player", "you") else "IMPLANT"
            lines.append(f"{speaker}: {text}")
        lines.append("")
    lines.append("[The player thinks]")
    lines.append(question)
    return "\n".join(lines)


def _history_messages(history: list | None, max_history: int = 8) -> list:
    """Convert the client transcript into LangChain messages for the invoke path."""
    from langchain_core.messages import AIMessage, HumanMessage

    msgs: list = []
    for turn in (history or [])[-max_history:]:
        role = (turn.get("role") or "").lower()
        text = (turn.get("content") or turn.get("text") or "").strip()
        if not text:
            continue
        if role in ("user", "player", "you"):
            msgs.append(HumanMessage(content=text))
        else:
            msgs.append(AIMessage(content=text))
    return msgs


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def ask(session_dir: str, question: str, history: list | None, llm) -> str:
    """Answer a side-channel question. Read-only — never touches game state.

    Works with both engine LLM flavors:
    - CLI-bypass providers (claude-code / codex) expose ``_call_claude`` and take
      one system + one user string.
    - Standard providers use ``invoke`` with a message list.
    """
    language = session_language(session_dir)
    system_prompt = _build_system_prompt(session_dir, language)

    if hasattr(llm, "_call_claude"):
        user_prompt = _build_user_prompt(question, history)
        raw = llm._call_claude(system_prompt, user_prompt)
        return _content_to_text(raw).strip()

    from langchain_core.messages import HumanMessage, SystemMessage

    messages = [SystemMessage(content=system_prompt)]
    messages.extend(_history_messages(history))
    messages.append(HumanMessage(content=question))
    response = llm.invoke(messages)
    return _content_to_text(getattr(response, "content", response)).strip()
