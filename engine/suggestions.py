"""
Signal Lost — Suggested Actions

Generates 1-3 short, simple, spoiler-free next-action suggestions for the player.
Suggestions are grounded ONLY in what the player can currently see and has
already discovered — never in hidden knowledge, undiscovered NPCs/places, or
deeper-layer lore.

Two entry points:
- ``read_features(session_dir)`` — merged feature flags (global settings overlaid
  by per-session ``session_settings.json``). Used by the engine and GUI.
- ``generate_suggested_actions(...)`` — a standalone LLM call that produces the
  suggestions. The claude-code/codex bypass engine produces them inline as part
  of its single turn call (see ``claude_code_engine``); this helper is the
  fallback used by the LangGraph path, which has no inline suggestion field.

``normalize_actions`` turns a raw list of strings (from either source) into the
``[{"id": "sa-1", "text": "..."}, ...]`` shape the GUI consumes.
"""

from __future__ import annotations

import json
import logging
import os
import re

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------

DEFAULT_FEATURES = {
    "suggested_actions": True,
    "suggested_actions_count": 3,
    "predict_outcome": False,
}


def _read_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def read_features(session_dir: str | None = None) -> dict:
    """Return merged feature flags: defaults < global settings < per-session.

    Always returns the full set of keys with sane fallbacks, so callers can
    index without guarding for missing keys.
    """
    feats = dict(DEFAULT_FEATURES)

    try:
        from engine.llm_factory import load_settings
        glob = load_settings().get("features", {})
        if isinstance(glob, dict):
            feats.update(glob)
    except Exception:
        pass

    if session_dir:
        ss = _read_json(os.path.join(session_dir, "session_settings.json"))
        sf = ss.get("features", {})
        if isinstance(sf, dict):
            feats.update(sf)

    # Coerce / clamp
    feats["suggested_actions"] = bool(feats.get("suggested_actions", True))
    feats["predict_outcome"] = bool(feats.get("predict_outcome", False))
    try:
        feats["suggested_actions_count"] = max(1, min(3, int(feats.get("suggested_actions_count", 3))))
    except (TypeError, ValueError):
        feats["suggested_actions_count"] = 3

    return feats


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_actions(raw, count: int = 3) -> list[dict]:
    """Turn a raw list (of strings, or {text:..} dicts) into GUI action dicts.

    De-duplicates (case-insensitive), drops empties, trims overly long text,
    and caps to ``count`` items. Returns ``[{"id": "sa-1", "text": "..."}, ...]``.
    """
    if not isinstance(raw, list):
        return []

    out: list[dict] = []
    seen: set[str] = set()
    for item in raw:
        if isinstance(item, dict):
            text = item.get("text") or item.get("action") or ""
        else:
            text = str(item)
        text = " ".join(str(text).split()).strip()
        # Strip a leading list marker the model sometimes adds ("1. ", "- ").
        text = re.sub(r"^\s*(?:\d+[.)]|[-*•])\s*", "", text)
        if not text:
            continue
        if len(text) > 120:
            text = text[:117].rstrip() + "…"
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({"id": f"sa-{len(out) + 1}", "text": text})
        if len(out) >= max(1, count):
            break
    return out


# ---------------------------------------------------------------------------
# Recent-suggestion memory (cross-turn de-dupe)
# ---------------------------------------------------------------------------
# Playtest wave 12, friction #3: the 中文 run surfaced the identical "buy a
# decoder tool" teaching nudge on 5 turns (T9-T15). Neither generation path
# could see what it had already offered, so it re-derived the same nudge every
# turn. A tiny per-session file (recent_suggestions.json) remembers the last
# few turns' suggestion lists; both paths inject the recent window into their
# prompt (with a no-repeat directive) and append to it after generating.

_RECENT_FILE = "recent_suggestions.json"
_RECENT_KEEP = 6   # entries kept on disk
RECENT_WINDOW = 3  # turns injected into the prompt


def read_recent_suggestions(session_dir: str | None,
                            last_n: int = RECENT_WINDOW) -> list[str]:
    """Flat, de-duplicated list of suggestion texts offered in the last *last_n* turns."""
    if not session_dir:
        return []
    data = _read_json(os.path.join(session_dir, _RECENT_FILE))
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        return []
    texts: list[str] = []
    seen: set[str] = set()
    for entry in entries[-last_n:]:
        actions = entry.get("actions", []) if isinstance(entry, dict) else []
        for t in actions if isinstance(actions, list) else []:
            t = " ".join(str(t).split()).strip()
            if t and t.lower() not in seen:
                seen.add(t.lower())
                texts.append(t)
    return texts


def record_suggestions(session_dir: str | None, turn: int, actions: list) -> None:
    """Append this turn's suggestion texts to the session memory (non-fatal)."""
    if not session_dir or not actions:
        return
    texts = [a.get("text", "") if isinstance(a, dict) else str(a) for a in actions]
    texts = [" ".join(str(t).split()).strip() for t in texts]
    texts = [t for t in texts if t]
    if not texts:
        return
    path = os.path.join(session_dir, _RECENT_FILE)
    data = _read_json(path)
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        entries = []
    entries.append({"turn": turn, "actions": texts})
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"entries": entries[-_RECENT_KEEP:]}, f,
                      ensure_ascii=False, indent=2)
    except OSError as e:
        logger.warning("could not persist recent suggestions: %s", e)


def format_recent_suggestions(texts: list[str]) -> str:
    """Compact prompt block listing recently offered suggestions (or '')."""
    if not texts:
        return ""
    lines = "\n".join(f"- {t}" for t in texts)
    return f"[Recently offered suggestions — do NOT repeat any of these]\n{lines}"


# ---------------------------------------------------------------------------
# Standalone generation (LangGraph fallback path)
# ---------------------------------------------------------------------------

_SUGGEST_SYS = """You propose the player's next moves in a cyberpunk-noir text RPG.

Given the scene that just happened and what the player can currently SEE and has \
ALREADY discovered, output {count} SHORT, simple, obvious next actions the player \
could take.

STRICT RULES:
- Output ONLY a JSON object: {{"actions": ["...", "..."]}} — no prose, no markdown.
- Give {count} actions (fewer only if the scene genuinely allows fewer). Each MUST \
be clearly DISTINCT from the others.
- Each action is at most 12 words, phrased as a direct command the player would \
type (e.g. "Ask the noodle vendor about the alley", "Head north toward the market").
- Keep most of them mundane and grounded — things any player would naturally try \
next. Do NOT be dramatic or surprising. But exactly ONE action MAY surface an \
available game verb the player might not realize they can use — decrypt an \
encrypted item with the cipher tool, analyze a signal artifact, present what they \
know to an NPC, hack a terminal, or rest to recover integrity — ONLY when the \
inventory/knowledge/scene in the context below actually affords it (they hold the \
tool, have the evidence, or face the encrypted thing). Phrase it in-world as a \
direct command, never as UI-speak or a tutorial hint.
- If the context lists recently offered suggestions, NEVER repeat one of them \
(even reworded) — especially the game-verb teaching option: teach a DIFFERENT \
verb this turn, or offer no teaching option at all.
- Use ONLY the people, places, exits, items, and facts listed in the context below. \
NEVER invent new NPCs, locations, items, or lore.
- NEVER reference anything the player has not yet discovered. No spoilers, no hidden \
secrets, no foreshadowing of undiscovered truths.
- Write the actions in {lang_name}.
"""


def _visible_context(state: dict) -> str:
    """Compact, player-visible scene summary (no hidden/undiscovered content).

    Mirrors the spoiler-safe fields shown to the player in the GUI panels.
    """
    location = state.get("location", {}) or {}
    inventory = state.get("inventory", {}) or {}
    npcs = state.get("npcs", {}) or {}
    knowledge = state.get("knowledge", {}) or {}
    world_state = state.get("world_state", {}) or {}

    exits = location.get("exits", {}) or {}
    pois = location.get("points_of_interest", []) or []
    poi_names = [p.get("name", str(p)) if isinstance(p, dict) else str(p) for p in pois]
    npcs_here = location.get("npcs_present", []) or []
    npc_here_names = [n.get("name", str(n)) if isinstance(n, dict) else str(n) for n in npcs_here]
    items = inventory.get("items", []) or []
    item_names = [i.get("name", i.get("item", "?")) if isinstance(i, dict) else str(i) for i in items]
    encountered = npcs.get("npcs", []) or []
    enc_names = [n.get("name", "?") for n in encountered if isinstance(n, dict)]
    accessible = [e.get("name", "?") for e in world_state.get("district_access", []) if isinstance(e, dict)]

    lines = [
        f"Current location: {location.get('district', '?')} — {location.get('area', '?')}",
        f"Exits: {', '.join(f'{k}: {v}' for k, v in exits.items()) if exits else 'unknown'}",
        f"Points of interest: {', '.join(poi_names) if poi_names else 'none'}",
        f"NPCs here: {', '.join(npc_here_names) if npc_here_names else 'none'}",
        f"Known NPCs: {', '.join(enc_names) if enc_names else 'none yet'}",
        f"Inventory: {', '.join(item_names) if item_names else 'empty'}",
        f"Accessible districts: {', '.join(accessible) if accessible else 'current area only'}",
    ]

    # Discovered knowledge (facts/rumors/evidence the player has actually learned)
    try:
        from engine.prompts import build_knowledge_context
        know = build_knowledge_context(knowledge)
        if know:
            lines.append("")
            lines.append(know)
    except Exception:
        pass

    return "\n".join(lines)


def _llm_text(llm, system: str, user: str) -> str:
    """Call the LLM and return plain text, supporting both the CLI-bypass
    duck-typed interface (``_call_claude``) and LangChain chat models."""
    if hasattr(llm, "_call_claude"):
        return llm._call_claude(system, user)
    from langchain_core.messages import SystemMessage, HumanMessage
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    content = getattr(resp, "content", resp)
    return content if isinstance(content, str) else str(content)


def parse_actions(raw: str) -> list[str]:
    """Extract the action list from a raw LLM reply (tolerant of fences/prose)."""
    if not raw:
        return []
    text = raw.strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    text = re.sub(r"```(?:json)?\s*\n?", "", text).replace("```", "").strip()

    # Try whole-string, then the outermost {...} block.
    candidates = [text]
    depth, start = 0, -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                candidates.append(text[start:i + 1])
                start = -1

    for cand in candidates:
        try:
            data = json.loads(cand)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, dict) and isinstance(data.get("actions"), list):
            return [str(a) for a in data["actions"]]
        if isinstance(data, list):
            return [str(a) for a in data]

    return []


def generate_suggested_actions(state: dict, narrative: str, language: str,
                               llm, count: int = 3,
                               session_dir: str | None = None) -> list[dict]:
    """Generate 1-3 spoiler-safe next-action suggestions via a standalone LLM call.

    Non-fatal: returns ``[]`` on any failure (parse error, LLM error, etc.).
    Used by the LangGraph path; the bypass engine produces suggestions inline.
    When *session_dir* is given, recently offered suggestions are injected into
    the prompt (no-repeat directive) and this turn's output is recorded.
    """
    if not narrative:
        return []
    count = max(1, min(3, int(count)))
    lang_name = "Chinese (简体中文)" if language == "zh" else "English"
    system = _SUGGEST_SYS.format(count=count, lang_name=lang_name)
    recent_block = format_recent_suggestions(read_recent_suggestions(session_dir))
    user = (
        f"[Scene that just happened]\n{narrative}\n\n"
        f"[What the player can see and already knows]\n{_visible_context(state)}\n\n"
        + (f"{recent_block}\n\n" if recent_block else "")
        + "Return the JSON now."
    )
    try:
        raw = _llm_text(llm, system, user)
    except Exception as e:
        logger.warning("suggested-actions generation failed: %s", e)
        return []
    actions = normalize_actions(parse_actions(raw), count)
    if actions and session_dir:
        turn = (state.get("player", {}) or {}).get("turn", 0)
        record_suggestions(session_dir, turn, actions)
    return actions
