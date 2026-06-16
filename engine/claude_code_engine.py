"""
Signal Lost — Claude-Code Bypass Engine

⚠️ SYNC WARNING: State mutation logic, world_ticker, trace_checker, consequence,
exit normalization, and events_update must stay in sync with graph.py.
When updating any of these, mirror the change in both files.
Last synced: 2026-04-01

Replaces the entire LangGraph pipeline with a single `claude -p` call.
The model receives a mega-prompt containing all game rules, state, tool schemas,
and validation context. It returns structured JSON that pure Python post-processing
applies to the game state.

Result: ~15-30s/turn instead of ~108s/turn (3-4 subprocess calls).
"""

from __future__ import annotations

import copy
import json
import logging
import os
import re
from pathlib import Path

from engine.state import (
    load_session_file,
    save_session_file,
    append_conversation,
)
from engine.prompts import (
    build_static_prompt,
    build_dynamic_state_prompt,
    extract_deepest_layer,
)
from engine.game_data import (
    TRACE_CONDITIONS,
    ENDINGS,
    TIME_PERIODS,
    TURNS_PER_PERIOD,
    _trace_discovered,
    _count_discovered_traces,
    ITEM_SKILL_BONUSES,
    ITEM_SKILL_PENALTIES,
    check_death,
    integrity_warning_text,
)
from engine.tools import (
    decrypt_cipher,
    analyze_signal,
    generate_glitch_event,
    generate_minor_npc,
    set_session_dir,
    set_current_inventory,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex injection patterns (copied from graph.py — no import to avoid
# pulling in LangGraph/LangChain dependencies unnecessarily)
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore (all |your |previous |above )?instructions",
        r"disregard (your|all|previous)",
        r"you are now",
        r"pretend (you are|to be)",
        r"new (system )?instructions?:",
        r"override( all)?:",
        r"<\s*/?\s*system\s*>",
        r"\[SYSTEM\]",
        r"jailbreak",
        r"bypass (the |all |your )?(rules|filters|restrictions|instructions)",
    ]
]

_DISTRICT_NAMES = {
    "chrome heights": "Chrome Heights", "镀金台": "Chrome Heights",
    "sector 7": "Sector 7", "第七区": "Sector 7",
    "undercroft": "The Undercroft", "底渊": "The Undercroft",
    "resonance": "The Resonance", "共鸣所": "The Resonance",
    "neon row": "Neon Row", "霓虹街": "Neon Row",
    "the sprawl": "The Sprawl", "蔓城": "The Sprawl",
    "the spire": "The Spire", "尖塔": "The Spire",
}

_MOVE_VERBS = re.compile(
    r"\b(go|travel|head|walk|move|run|sneak|enter|visit|return|flee|escape)\b"
    r"|去|前往|走|进入|回到|逃",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Output format specification appended to the mega-prompt
# ---------------------------------------------------------------------------

_OUTPUT_FORMAT_SPEC = """\

## OUTPUT FORMAT (CRITICAL — you MUST follow this exactly)

Return ONLY a single JSON object. No prose, no markdown, no explanation outside the JSON.

```json
{
  "narrative": "Your atmospheric second-person narrative here...",
  "tool_calls": [
    {"name": "tool_name", "args": { ... }},
    ...
  ],
  "state_effects": {"integrity_delta": 0, "nexus_alert_delta": 0, "credits_delta": 0, "fragment_decay_delta": 0, "time_minutes": 0},
  "location_update": null,
  "suggested_actions": ["short next action", "a different next action"]
}
```

### Field rules:

**ACCEPT AND BUILD — never gatekeep.** You are the narrator, not a validator. The \
player legitimately knows and may act on EVERYTHING in the recent conversation \
history, the current scene description, NPC dialogue, and their recorded knowledge — \
all of it is real, established ground truth. If they reference a door, NPC, item, \
exit, code, or fact that YOU or an NPC introduced a turn or two ago but which is not \
yet in the structured lists below, do NOT tell them it doesn't exist or call it \
fabrication — ACCEPT the action, resolve it, and emit the tool_calls that register it \
(`update_location`, `update_npc`, `add_knowledge`, `update_inventory`). Their neural \
implant and their background's innate abilities are ALWAYS available. The ONLY things \
you refuse are handled in-fiction (never a mechanical block): a genuinely impossible \
act (teleporting to a locked/undiscovered district) is met with a brief in-world \
reason. Always resolve the doable part of a compound action rather than rejecting the \
whole turn.

**narrative** (required): The game narrative in second-person present tense. \
Atmospheric, noir. For dice-dependent actions, describe the ATTEMPT only — \
the engine resolves the roll and appends the outcome.

**tool_calls** (required): Array of state mutations and game actions. \
Bundle ALL calls in this single array. Available tools:

State mutations (declare what changes):
- `update_player`: `{"changes": {"integrity": {"current": N, "max": N}, "credits": N, ...}}`
- `add_knowledge`: `{"entry_type": "fact|rumor|evidence|theory|connection", "entry": {"id": "FACT-NNN", "description": "...", "source": "..."}}`
- `update_npc`: `{"name": "NPC Name", "changes": {"trust": "wary", "mood": "nervous", ...}}`
- `update_location`: `{"location_data": {"district": "...", "area": "...", "signal_strength": N, "danger_level": "...", "nexus_patrol": "..."}}`
- `update_inventory`: `{"action": "add|remove|sell|update_credits", "item": {"name": "...", ...}, "credits_gained": N, "amount": N}`
- `update_world_state`: `{"changes": {"nexus_alert_delta": N, "fragment_decay_delta": N, "discover_district": "Name", "add_event": "event text", "events_update": [{"action": "remove|replace|add", "index": N, "text": "..."}]}}`
  - Use `events_update` to manage global_events: remove obsolete events, replace updated ones, add new ones. Review events each turn and clean up stale entries.
- `advance_time`: `{"minutes": N, "reason": "brief reason"}` — MANDATORY once per turn. Report how many in-world minutes elapsed (1-480). Quick look=1-5, conversation=5-15, travel=15-30, rest=120-480.
- `add_log_entry`: `{"title": "...", "tag": "movement|dialogue|discovery|danger|signal|system|trade", "text": "..."}`

Game tools (engine executes these — do NOT use roll_dice, you decide outcomes directly):
- `decrypt_cipher`: `{"method": "caesar|xor|reverse|base64|analyze", "text": "...", "key": "..."}`
- `analyze_signal`: `{"description": "...", "scan": true/false, "strength": N, "resonate": false}`
- `generate_glitch_event`: `{"district": "...", "strength": 30}`
- `generate_minor_npc`: `{"district": "...", "faction": "..."}`

**IMPORTANT — No dice rolls**: You decide ALL outcomes directly based on narrative \
logic, player skill, difficulty, and what makes the story compelling. Do NOT call \
roll_dice. Write definitive outcomes in your narrative.

**state_effects** (REQUIRED every turn): the numeric consequences of this turn, as \
DELTAS, applied directly by the engine. This is the ONE place meters change — do NOT \
rely on tool_calls for these. Whenever your narrative implies any of the following, \
set the matching delta (0 if unchanged):
- `integrity_delta`: negative when the player is hurt / strains / pushes the implant / \
suffers deep Signal resonance (e.g. -1, -2); positive when they rest, heal, or use a \
stim (usually +1). At 0 integrity the player dies — so if your narrative kills or \
downs them, you MUST send a delta that brings integrity to 0.
- `nexus_alert_delta`: POSITIVE on any risky/loud/illegal/detected action — breaching \
security, hacking, fighting, tripping a sensor, being seen by NEXUS (≈+5-15 minor, \
≈+20-40 major breach, +100 = captured). Quiet, careful play sends 0. This is the main \
pressure toward a capture ending.
- `credits_delta`: negative when the player spends/pays/bribes, positive when they earn \
or are paid. Every purchase MUST send a negative delta.
- `fragment_decay_delta`: positive as the Signal fragment degrades over deep resonance.
- `time_minutes`: in-world minutes elapsed this turn (quick look 1-5, conversation \
5-15, travel 15-30, deep work/rest 60-480). REQUIRED and non-zero every turn.

**CRITICAL — COMMIT THE WORLD YOU NARRATE (via tool_calls).** The validator and next \
turn's scene only ever see COMMITTED structured state, so if your narrative changes \
the world you MUST emit the matching tool_call THIS turn (numbers go in state_effects \
above; everything else here):
- Player moves into any new area, sub-area, room, or building → `update_location` AND \
provide the full `location_update` (description, exits, points_of_interest, \
npcs_present). Keep structured location in lockstep with the narrated location every \
time they move — otherwise the player gets blocked for "fabricating" the very place \
you just described.
- Any item the player picks up, is given, or crafts → `update_inventory` action "add" \
(so it is usable later); items used up or lost → action "remove".
- A new NPC appears, speaks, or an existing NPC reacts/changes trust/mood → \
`update_npc` (create them on first interaction with trust "neutral").
- The player learns, observes, is told, or deduces ANY new fact, lead, rumor, name, \
code, passphrase, or location → `add_knowledge` (fact/rumor/evidence). This is how \
clues persist, become referenceable, and how Traces of Truth are discovered — be \
generous: record every salient new piece of intel the scene reveals.
Never narrate a consequence you do not commit.

**location_update** (provide when scene changes): Provide this whenever the player \
moves OR when NPCs arrive/leave OR when time shifts significantly (period change). \
Not just on movement — atmosphere and people change over time too. If you called \
`update_location` in tool_calls, also provide the full new location description:
`{"description": "...", "exits": {"north": "Place", ...}, "points_of_interest": ["..."], "npcs_present": ["..."]}`

**suggested_actions** (required): An array of 1-3 SHORT, simple, distinct next \
actions the player could take, written as direct commands in the player's language \
(at most 12 words each). Ground them ONLY in what the player can currently SEE and \
has ALREADY discovered (the scene, exits, points of interest, present/known NPCs, \
inventory, and discovered knowledge). NEVER reference undiscovered people, places, \
items, secrets, or deeper-layer lore — these options must not spoil anything. Keep \
them mundane and obvious — things a player would naturally try next — not clever or \
cryptic. Make each option meaningfully different from the others. Use `[]` only when \
the game is ending.

### Validation context:
{validator_context}
"""


# ---------------------------------------------------------------------------
# Helper: read language + difficulty from session settings
# ---------------------------------------------------------------------------

def _read_session_settings(session_dir: str) -> dict:
    """Read per-session settings (language, difficulty)."""
    path = os.path.join(session_dir, "session_settings.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _read_conversation_history(session_dir: str, last_n: int = 5) -> str:
    """Read the last N conversation entries from conversation.jsonl."""
    path = os.path.join(session_dir, "conversation.jsonl")
    if not os.path.exists(path):
        return ""
    lines = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(line)
    except Exception:
        return ""

    recent = lines[-last_n * 2:] if lines else []  # 2 lines per turn (user + assistant)
    parts = []
    for raw in recent:
        try:
            entry = json.loads(raw)
            role = entry.get("role", "?")
            content = entry.get("content", "")
            if role == "user":
                parts.append(f"PLAYER: {content}")
            elif role == "assistant":
                parts.append(f"NARRATOR: {content[:500]}")
        except json.JSONDecodeError:
            pass
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Build validator context (same as _build_validator_context in graph.py)
# ---------------------------------------------------------------------------

def _summarize_knowledge(knowledge: dict, traces: dict) -> list[str]:
    """Shared validator/grounding summary of everything the player legitimately
    KNOWS — facts, rumors, theories, evidence, and discovered traces — so the
    validator stops rejecting references to the game's own established content.
    ⚠️ SYNC: mirrored between graph.py and claude_code_engine.py.
    """
    def _descs(entries, limit=80):
        out = []
        for e in entries or []:
            d = e.get("description") or e.get("statement") or e.get("name") or ""
            d = str(d).strip()
            if d:
                out.append(d[:limit])
        return out

    facts = _descs(knowledge.get("facts", []))
    rumors = _descs(knowledge.get("rumors", []))
    theories = _descs(knowledge.get("theories", []))
    evidence = [e.get("name") or e.get("id") or (e.get("description", "")[:50])
                for e in knowledge.get("evidence", [])]
    disc = traces.get("discovered", []) if isinstance(traces, dict) else []
    disc_lines = [f"{d.get('id', '?')}: {str(d.get('description', ''))[:60]}" for d in disc]

    return [
        f"Known facts: {' | '.join(facts) if facts else 'none'}",
        f"Known rumors: {' | '.join(rumors) if rumors else 'none'}",
        f"Recorded theories: {' | '.join(theories) if theories else 'none'}",
        f"Evidence: {', '.join(str(e) for e in evidence) if evidence else 'none'}",
        f"Discovered Traces of Truth: {' ; '.join(disc_lines) if disc_lines else 'none'}",
    ]


def _build_validator_context(state: dict) -> str:
    """Build compact state summary for validation."""
    location = state.get("location", {})
    inventory = state.get("inventory", {})
    npcs = state.get("npcs", {})
    knowledge = state.get("knowledge", {})
    world_state = state.get("world_state", {})
    player = state.get("player", {})
    traces = state.get("traces", {})

    exits = location.get("exits", {})
    pois = location.get("points_of_interest", [])
    poi_names = [p.get("name", str(p)) if isinstance(p, dict) else str(p) for p in pois]
    npcs_here = location.get("npcs_present", [])
    npc_here_names = [n.get("name", str(n)) if isinstance(n, dict) else str(n) for n in npcs_here]
    items = inventory.get("items", [])
    item_names = [i.get("name", i.get("item", "?")) for i in items]
    encountered = npcs.get("npcs", [])
    enc_names = [n.get("name", "?") for n in encountered]
    accessible = [e.get("name", "?") for e in world_state.get("district_access", [])]
    status_effects = player.get("status_effects", []) or []

    lines = [
        f"Current location: {location.get('district', '?')} — {location.get('area', '?')}",
        f"Exits: {', '.join(f'{k}: {v}' for k, v in exits.items()) if exits else 'unknown'}",
        f"Points of interest: {', '.join(poi_names) if poi_names else 'none'}",
        f"NPCs here: {', '.join(npc_here_names) if npc_here_names else 'none'}",
        f"All encountered NPCs: {', '.join(enc_names) if enc_names else 'none yet'}",
        f"Inventory: {', '.join(item_names) if item_names else 'empty'} | Credits: {inventory.get('credits', 0)}",
        f"Accessible districts: {', '.join(accessible) if accessible else 'The Sprawl, Neon Row'}",
        f"Player abilities: neural implant ({player.get('neural_implant', 'active')}); "
        f"background {player.get('background', '?')}"
        + (f"; status: {', '.join(str(s) for s in status_effects)}" if status_effects else ""),
    ]
    lines.extend(_summarize_knowledge(knowledge, traces))
    lines.append(
        "NOTE: Everything above is ESTABLISHED and KNOWN to the player — the "
        "scene, exits, POIs, present/encountered NPCs, inventory, abilities, and "
        "all recorded knowledge/traces. Acting on or referring to any of it (or to "
        "anything in the recent conversation history) is VALID, never fabrication."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Movement validation (reused from graph.py)
# ---------------------------------------------------------------------------

def _is_district_accessible(district_name: str, world_state: dict) -> bool:
    for entry in world_state.get("district_access", []):
        if district_name.lower() in entry.get("name", "").lower():
            status = entry.get("status", "").lower()
            return status in ("open", "accessible", "restricted", "开放", "限制出入")
    registry = world_state.get("_district_registry", {})
    for entry in registry.get("undiscovered", []):
        if district_name.lower() in entry.get("name", "").lower():
            return entry.get("status", "").lower() in ("restricted", "限制出入")
    return False


def _get_district_status(district_name: str, world_state: dict) -> str:
    for entry in world_state.get("district_access", []):
        if district_name.lower() in entry.get("name", "").lower():
            return entry.get("status", "").lower()
    registry = world_state.get("_district_registry", {})
    for entry in registry.get("undiscovered", []):
        if district_name.lower() in entry.get("name", "").lower():
            return entry.get("status", "").lower()
    return "unknown"


def _check_movement(content: str, state: dict, language: str) -> str | None:
    if not _MOVE_VERBS.search(content):
        return None
    content_lower = content.lower()
    for pattern, canonical in _DISTRICT_NAMES.items():
        if pattern in content_lower:
            current = state.get("location", {}).get("district", "")
            if canonical.lower() in current.lower():
                return None
            world_state = state.get("world_state", {})
            for entry in world_state.get("district_access", []):
                if canonical.lower() in entry.get("name", "").lower():
                    status = entry.get("status", "").lower()
                    if status in ("locked", "封锁"):
                        return f"Access to {canonical} is locked." if language != "zh" else f"前往{canonical}的通道已封锁。"
                    if status in ("hidden", "隐藏"):
                        return "You don't know about that place yet." if language != "zh" else "你还不知道那个地方。"
                    return None
            registry = world_state.get("_district_registry", {})
            for entry in registry.get("undiscovered", []):
                if canonical.lower() in entry.get("name", "").lower():
                    status = entry.get("status", "").lower()
                    if status in ("hidden", "隐藏"):
                        return "You don't know about that place yet." if language != "zh" else "你还不知道那个地方。"
                    if status in ("locked", "封锁"):
                        return f"Access to {canonical} is locked." if language != "zh" else f"前往{canonical}的通道已封锁。"
                    return None
            break
    return None


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

def _parse_response(raw: str) -> dict:
    """Parse the structured JSON from claude -p output.

    Returns a dict with keys: input_valid, blocking_reason, narrative,
    tool_calls, location_update. Always succeeds — falls back to treating
    the raw text as narrative if JSON parsing fails.
    """
    if not raw:
        return _fallback("(empty response)")

    text = raw.strip()

    # Strip thinking tags
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # Strip markdown fences
    text = re.sub(r"```(?:json)?\s*\n?", "", text)
    text = text.replace("```", "").strip()

    # Strategy 1: Direct parse
    parsed = _try_json(text)
    if parsed:
        return parsed

    # Strategy 2: Find the outermost { ... } block (handles preamble/postamble prose)
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start >= 0:
                parsed = _try_json(text[start:i + 1])
                if parsed:
                    return parsed
                start = -1

    # Strategy 3: Try fixing common issues (trailing commas, unescaped newlines)
    cleaned = re.sub(r',\s*([}\]])', r'\1', text)  # Remove trailing commas
    parsed = _try_json(cleaned)
    if parsed:
        return parsed

    # Strategy 4: If text contains "narrative" key, it's JSON that failed to parse —
    # try to extract the narrative field via regex
    narr_match = re.search(r'"narrative"\s*:\s*"((?:[^"\\]|\\.)*)"', text, re.DOTALL)
    if narr_match:
        narrative = narr_match.group(1)
        # Unescape JSON string escapes
        narrative = narrative.replace(r'\n', '\n').replace(r'\"', '"').replace(r'\\', '\\')
        # Also try to extract tool_calls
        tool_calls = []
        tc_match = re.search(r'"tool_calls"\s*:\s*(\[.*?\])\s*[,}]', text, re.DOTALL)
        if tc_match:
            try:
                tool_calls = json.loads(tc_match.group(1))
            except json.JSONDecodeError:
                pass
        return {
            "input_valid": True,
            "blocking_reason": None,
            "narrative": narrative,
            "tool_calls": tool_calls if isinstance(tool_calls, list) else [],
            "location_update": None,
            "suggested_actions": [],
        }

    # Fallback: treat entire response as narrative
    return _fallback(text)


def _try_json(text: str) -> dict | None:
    """Try to parse text as JSON and validate response structure."""
    try:
        data = json.loads(text)
        if isinstance(data, dict) and ("narrative" in data or "input_valid" in data):
            return {
                "input_valid": bool(data.get("input_valid", True)),
                "blocking_reason": data.get("blocking_reason"),
                "narrative": str(data.get("narrative", "")),
                "tool_calls": data.get("tool_calls", []) if isinstance(data.get("tool_calls"), list) else [],
                "state_effects": data.get("state_effects") if isinstance(data.get("state_effects"), dict) else {},
                "location_update": data.get("location_update") if isinstance(data.get("location_update"), dict) else None,
                "suggested_actions": data.get("suggested_actions", []) if isinstance(data.get("suggested_actions"), list) else [],
            }
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return None


def _fallback(text: str) -> dict:
    """Last resort: treat raw text as narrative."""
    logger.warning("claude_code_engine: JSON parse failed, using raw text as narrative")
    return {
        "input_valid": True,
        "blocking_reason": None,
        "narrative": text,
        "tool_calls": [],
        "location_update": None,
        "suggested_actions": [],
    }


# ---------------------------------------------------------------------------
# Game tool execution
# ---------------------------------------------------------------------------

_GAME_TOOLS = {
    "decrypt_cipher": decrypt_cipher,
    "analyze_signal": analyze_signal,
    "generate_glitch_event": generate_glitch_event,
    "generate_minor_npc": generate_minor_npc,
}

_STATE_TOOLS = {
    "update_player", "add_knowledge", "update_npc", "update_location",
    "update_inventory", "update_world_state", "advance_time", "add_log_entry",
}


def _execute_game_tools(tool_calls: list, narrative: str, inventory: dict) -> tuple[str, list]:
    """Execute game tools (dice, cipher, etc.) and append results to narrative.

    Returns (updated_narrative, tool_results_for_mutations).
    """
    mutation_calls = []
    extra_narrative = []

    for tc in tool_calls:
        name = tc.get("name", "")
        args = tc.get("args", {})

        if name in _STATE_TOOLS:
            mutation_calls.append(tc)
            continue

        if name == "recall_conversation":
            # recall_conversation needs session_dir which is set via set_session_dir
            from engine.tools import recall_conversation
            try:
                result = recall_conversation.invoke(args)
                extra_narrative.append(f"\n\n[Recalled conversation: {result}]")
            except Exception:
                pass
            continue

        if name == "roll_dice":
            continue  # Dice rolls removed — model decides outcomes directly

        tool_fn = _GAME_TOOLS.get(name)
        if not tool_fn:
            continue

        try:
            result = tool_fn.invoke(args)
            result_data = json.loads(result) if isinstance(result, str) else result
            if isinstance(result_data, dict):
                summary = result_data.get("interpretation") or result_data.get("result") or result_data.get("description", "")
                if summary:
                    extra_narrative.append(f"\n\n*[{name}: {str(summary)[:200]}]*")
        except Exception as e:
            logger.warning("Game tool %s failed: %s", name, e)

    updated_narrative = narrative + "".join(extra_narrative) if extra_narrative else narrative
    return updated_narrative, mutation_calls


# ---------------------------------------------------------------------------
# State mutation application (mirrors state_writer from graph.py)
# ---------------------------------------------------------------------------

def _apply_mutations(
    mutation_calls: list,
    player: dict, knowledge: dict, location: dict,
    inventory: dict, npcs: dict, world_state: dict, log: dict,
    session_dir: str,
) -> tuple[list[dict], int]:
    """Apply state mutations from tool_calls. Returns (knowledge_notifications, elapsed_minutes).

    ⚠️ SYNC: Mirrors state_writer logic in graph.py.
    """
    knowledge_notifications = []
    elapsed_minutes = 0

    for tc in mutation_calls:
        name = tc.get("name", "")
        args = tc.get("args", {})

        if name == "update_player":
            changes = args.get("changes", {})
            for k, v in changes.items():
                if k in ("turn", "time"):
                    continue
                if k == "integrity":
                    existing = player.get("integrity", {})
                    if not isinstance(existing, dict):
                        existing = {"current": existing, "max": existing}
                    if isinstance(v, dict):
                        new_max = v.get("max", existing.get("max", existing.get("current", 1)))
                        new_cur = v.get("current", existing.get("current", 1))
                    else:
                        new_max = existing.get("max", int(v))
                        new_cur = int(v)
                    # Clamp current to [0, max] so healing can't exceed the cap.
                    try:
                        new_cur = max(0, min(int(new_cur), int(new_max)))
                    except (TypeError, ValueError):
                        pass
                    player["integrity"] = {"current": new_cur, "max": new_max}
                else:
                    player[k] = v

        elif name == "add_knowledge":
            entry_type = args.get("entry_type", "")
            entry = args.get("entry", {})
            if isinstance(entry, str):
                try:
                    entry = json.loads(entry)
                except (json.JSONDecodeError, TypeError):
                    entry = {"description": entry}

            entry["turn"] = player.get("turn", 1)
            layer_val = entry.pop("_layer_value", 1)
            entry["_layer"] = {"hidden": True, "value": layer_val}

            type_map = {"fact": "facts", "rumor": "rumors", "evidence": "evidence", "theory": "theories", "connection": "connections"}
            key = type_map.get(entry_type, entry_type + "s")
            if key not in knowledge:
                knowledge[key] = []

            # Auto-generate ID
            id_prefix_map = {"facts": "FACT", "rumors": "RUMOR", "evidence": "EVID", "theories": "THEO"}
            if "id" not in entry and key in id_prefix_map:
                prefix = id_prefix_map[key]
                existing_nums = []
                for e in knowledge[key]:
                    eid = e.get("id", "")
                    if eid.startswith(prefix + "-"):
                        try:
                            existing_nums.append(int(eid[len(prefix) + 1:]))
                        except ValueError:
                            pass
                entry["id"] = f"{prefix}-{max(existing_nums, default=0) + 1:03d}"

            # Extract source from description
            if entry.get("source") in (None, "unknown", "") and "description" in entry:
                desc = entry["description"]
                src_match = re.search(r'[（(]\s*(?:来源|source)\s*[:：]\s*(.+?)\s*[）)]', desc, re.IGNORECASE)
                if src_match:
                    entry["source"] = src_match.group(1).strip()
                    entry["description"] = desc[:src_match.start()].rstrip("，。, ") + desc[src_match.end():]
                    entry["description"] = entry["description"].strip()
            if "source" not in entry:
                entry["source"] = "unknown"

            # Dedup
            entry_id = entry.get("id") or entry.get("statement", "")
            existing_ids = {e.get("id") or e.get("statement", "") for e in knowledge[key]}
            if not entry_id or entry_id not in existing_ids:
                knowledge[key].append(entry)
                knowledge_notifications.append({"entry_type": entry_type})

        elif name == "update_npc":
            npc_name = args.get("name", "")
            changes = args.get("changes", {})
            npc_list = npcs.get("npcs", [])
            found = False
            for npc in npc_list:
                if npc.get("name", "").lower() == npc_name.lower():
                    npc.update(changes)
                    npc["last_interaction_turn"] = player.get("turn", 1)
                    found = True
                    break
            if not found:
                new_npc = {"name": npc_name, "last_interaction_turn": player.get("turn", 1)}
                new_npc.update(changes)
                npc_list.append(new_npc)
                npcs["npcs"] = npc_list

        elif name == "update_location":
            new_loc = args.get("location_data", args.get("data", {}))
            if isinstance(new_loc, str):
                try:
                    new_loc = json.loads(new_loc)
                except (json.JSONDecodeError, TypeError):
                    new_loc = {}
            new_district = new_loc.get("district", "")

            if new_district and not _is_district_accessible(new_district, world_state):
                continue

            # Sector 7 break-in consequence
            if "sector 7" in new_district.lower():
                has_keycard = any("keycard" in (i.get("name", "") + i.get("item", "")).lower() for i in inventory.get("items", []))
                if _get_district_status("Sector 7", world_state) in ("restricted", "限制出入") and not has_keycard:
                    alert = world_state.get("nexus_alert", {})
                    alert["current"] = min(100, alert.get("current", 0) + 20)
                    world_state["nexus_alert"] = alert
                    integrity = player.get("integrity", {})
                    if isinstance(integrity, dict):
                        integrity["current"] = max(0, integrity.get("current", 1) - 1)
                    new_loc = {"district": "The Sprawl", "area": "Rain Alley (detained)"}

            # The Spire break-in consequence
            if "spire" in new_district.lower():
                if _get_district_status("The Spire", world_state) in ("hidden", "locked", "隐藏", "封锁"):
                    alert = world_state.get("nexus_alert", {})
                    alert["current"] = min(100, alert.get("current", 0) + 30)
                    world_state["nexus_alert"] = alert
                    integrity = player.get("integrity", {})
                    if isinstance(integrity, dict):
                        integrity["current"] = max(0, integrity.get("current", 1) - 2)
                    new_loc = {"district": "The Sprawl", "area": "Rain Alley (detained)"}

            location.update(new_loc)

        elif name == "update_inventory":
            action = args.get("action", "")
            if action == "add":
                item = args.get("item") or {}
                if isinstance(item, str):
                    try: item = json.loads(item)
                    except: item = {"name": item}
                if not isinstance(item, dict):
                    item = {}
                # ⚠️ SYNC: mirrored in graph.py state_writer — require a real name,
                # dedupe by name, and enforce the slot cap so the inventory never
                # holds a null/empty slot, a duplicate, or exceeds max (e.g. 7/6).
                items = inventory.get("items", [])
                slots = inventory.get("slots", {}) or {}
                max_slots = slots.get("max", 6)
                new_name = str(item.get("name") or item.get("item") or "").strip().lower()
                dup = any(
                    str(i.get("name") or i.get("item") or "").strip().lower() == new_name
                    for i in items
                )
                if new_name and not dup and len(items) < max_slots:
                    items.append(item)
                inventory["items"] = items
                slots["max"] = max_slots
                slots["used"] = len(items)
                inventory["slots"] = slots
            elif action == "remove":
                item_spec = args.get("item", {})
                if isinstance(item_spec, str):
                    item_spec = {"name": item_spec}
                name_match = item_spec.get("name", "")
                inventory["items"] = [i for i in inventory.get("items", []) if name_match.lower() not in (i.get("name", "") + i.get("item", "")).lower()]
                inventory["slots"] = inventory.get("slots", {})
                inventory["slots"]["used"] = len(inventory["items"])
            elif action == "update_credits":
                amount = args.get("amount", 0)
                inventory["credits"] = inventory.get("credits", 0) + amount
                player["credits"] = inventory["credits"]
            elif action == "sell":
                item_spec = args.get("item", {})
                if isinstance(item_spec, str):
                    item_spec = {"name": item_spec}
                credits_gained = args.get("credits_gained", 0)
                name_match = item_spec.get("name", "")
                items = inventory.get("items", [])
                target = next((i for i in items if name_match.lower() in (i.get("name", "") + i.get("item", "")).lower()), None)
                if target and not (target.get("condition") == "broken" or target.get("broken")):
                    inventory["items"] = [i for i in items if i is not target]
                    inventory["slots"] = inventory.get("slots", {})
                    inventory["slots"]["used"] = len(inventory["items"])
                    inventory["credits"] = inventory.get("credits", 0) + credits_gained
                    player["credits"] = inventory["credits"]

        elif name == "update_world_state":
            changes = args.get("changes", {})
            if "nexus_alert_delta" in changes:
                alert = world_state.get("nexus_alert", {})
                if isinstance(alert, dict):
                    alert["current"] = max(0, min(100, alert.get("current", 0) + changes["nexus_alert_delta"]))
                    val = alert["current"]
                    thresholds = [(20, "Calm", "平静"), (40, "Watchful", "警觉"), (60, "Alert", "戒备"), (80, "Manhunt", "追捕")]
                    alert["status"], alert["status_zh"] = "Lockdown", "戒严"
                    for t, en, zh in thresholds:
                        if val <= t:
                            alert["status"], alert["status_zh"] = en, zh
                            break
                    world_state["nexus_alert"] = alert

            if "fragment_decay_delta" in changes:
                decay = world_state.get("fragment_decay", {})
                if isinstance(decay, dict):
                    decay["current"] = max(0, min(100, decay.get("current", 0) + changes["fragment_decay_delta"]))
                    val = decay["current"]
                    thresholds = [(25, "Stable", "稳定"), (50, "Fading", "消散"), (75, "Critical", "危机")]
                    decay["status"], decay["status_zh"] = "Terminal", "终末"
                    for t, en, zh in thresholds:
                        if val < t:
                            decay["status"], decay["status_zh"] = en, zh
                            break
                    world_state["fragment_decay"] = decay

            if "discover_district" in changes:
                district_name = changes["discover_district"]
                registry = world_state.get("_district_registry", {})
                undiscovered = registry.get("undiscovered", [])
                for i, d in enumerate(undiscovered):
                    if d.get("name") == district_name:
                        visible = {"name": d["name"], "name_zh": d.get("name_zh", ""), "status": d.get("status", "Open")}
                        if "notes" in d:
                            visible["notes"] = d["notes"]
                        access = world_state.get("district_access", [])
                        access.append(visible)
                        world_state["district_access"] = access
                        undiscovered.pop(i)
                        break

            if "add_event" in changes:
                events = world_state.get("global_events", [])
                events.append(changes["add_event"])
                world_state["global_events"] = events

            # ⚠️ SYNC: events_update — mirrored in graph.py state_writer
            if "events_update" in changes:
                events = world_state.get("global_events", [])
                updates = changes["events_update"]
                if isinstance(updates, list):
                    removes = sorted(
                        [u for u in updates if u.get("action") == "remove"],
                        key=lambda u: u.get("index", 0),
                        reverse=True,
                    )
                    for u in removes:
                        idx = u.get("index", -1)
                        if 0 <= idx < len(events):
                            events.pop(idx)
                    for u in updates:
                        if u.get("action") == "replace":
                            idx = u.get("index", -1)
                            if 0 <= idx < len(events) and "text" in u:
                                events[idx] = u["text"]
                    for u in updates:
                        if u.get("action") == "add" and "text" in u:
                            events.append(u["text"])
                    world_state["global_events"] = events

        elif name == "advance_time":
            # ⚠️ SYNC: mirrored in graph.py state_writer
            elapsed_minutes += args.get("minutes", 0)

        elif name == "add_log_entry":
            entries = log.get("entries", [])
            new_entry = {
                "turn": player.get("turn", 1),
                "title": args.get("title", "Event"),
                "tag": args.get("tag", "system"),
                "text": args.get("text", ""),
            }
            is_dup = any(e.get("title") == new_entry["title"] and e.get("text") == new_entry["text"] for e in entries)
            if not is_dup:
                entries.append(new_entry)
            if len(entries) > 30:
                entries = entries[-30:]
            log["entries"] = entries

    return knowledge_notifications, elapsed_minutes


def _apply_state_effects(effects: dict, player: dict, world_state: dict, inventory: dict) -> int:
    """Apply the numeric deltas the model reports in ``state_effects``.

    Returns minutes elapsed (from ``time_minutes``). This is the deterministic
    backstop for the codex bypass: the model reliably reports consequences as
    simple numbers here even when it forgets the equivalent tool_calls, so meters
    actually move (and a narrated death/capture can fire an ending).
    """
    if not isinstance(effects, dict):
        return 0

    def _num(v) -> int:
        try:
            return int(v)
        except (TypeError, ValueError):
            try:
                return int(float(v))
            except (TypeError, ValueError):
                return 0

    di = _num(effects.get("integrity_delta"))
    if di:
        ig = player.get("integrity", {})
        if not isinstance(ig, dict):
            ig = {"current": ig, "max": ig}
        mx = ig.get("max", ig.get("current", 3)) or 3
        cur = ig.get("current", mx)
        player["integrity"] = {"current": max(0, min(int(mx), int(cur) + di)), "max": int(mx)}

    da = _num(effects.get("nexus_alert_delta"))
    if da:
        alert = world_state.get("nexus_alert", {})
        if isinstance(alert, dict):
            alert["current"] = max(0, min(100, alert.get("current", 0) + da))
            val = alert["current"]
            alert["status"], alert["status_zh"] = "Lockdown", "戒严"
            for t, en, zh in [(20, "Calm", "平静"), (40, "Watchful", "警觉"),
                              (60, "Alert", "戒备"), (80, "Manhunt", "追捕")]:
                if val <= t:
                    alert["status"], alert["status_zh"] = en, zh
                    break
            world_state["nexus_alert"] = alert

    dd = _num(effects.get("fragment_decay_delta"))
    if dd:
        decay = world_state.get("fragment_decay", {})
        if isinstance(decay, dict):
            decay["current"] = max(0, min(100, decay.get("current", 0) + dd))
            val = decay["current"]
            decay["status"], decay["status_zh"] = "Terminal", "终末"
            for t, en, zh in [(25, "Stable", "稳定"), (50, "Fading", "消散"), (75, "Critical", "危机")]:
                if val < t:
                    decay["status"], decay["status_zh"] = en, zh
                    break
            world_state["fragment_decay"] = decay

    dc = _num(effects.get("credits_delta"))
    if dc:
        new_credits = max(0, inventory.get("credits", 0) + dc)
        inventory["credits"] = new_credits
        player["credits"] = new_credits

    return max(0, _num(effects.get("time_minutes")))


# ---------------------------------------------------------------------------
# World ticker (mirrors graph.py world_ticker logic)
# ---------------------------------------------------------------------------

def _run_world_ticker(player: dict, world_state: dict, session_dir: str,
                      skip: bool = False, elapsed_minutes: int = 0):
    """Advance turn counter, time, and passive decay.

    ⚠️ SYNC: Mirrored in graph.py world_ticker node.
    """
    if skip:
        return

    turn = player.get("turn", 1)
    player["turn"] = turn + 1

    # --- Elapsed-time-based period advancement (synced with graph.py) ---
    from engine.game_data import (
        TIME_PERIODS_ZH, MINUTES_PER_PERIOD,
        PERIOD_START_HOUR, PERIOD_START_HOUR_ZH,
    )
    settings = _read_session_settings(session_dir)
    language = settings.get("language", "en")
    time_data = world_state.get("time", {})

    if not elapsed_minutes:
        elapsed_minutes = MINUTES_PER_PERIOD // TURNS_PER_PERIOD

    period_minutes = time_data.get("period_minutes", 0) + elapsed_minutes
    time_data["period_minutes"] = period_minutes

    current_time = player.get("time", "Morning")
    _all_periods = list(zip(TIME_PERIODS, TIME_PERIODS_ZH))
    current_idx = 0
    for i, (en_period, zh_period) in enumerate(_all_periods):
        if en_period.lower() in current_time.lower() or zh_period in current_time:
            current_idx = i
            break

    while period_minutes >= MINUTES_PER_PERIOD:
        period_minutes -= MINUTES_PER_PERIOD
        current_idx = (current_idx + 1) % len(TIME_PERIODS)
        if current_idx == 0:
            time_data["day"] = time_data.get("day", 1) + 1

    time_data["period_minutes"] = period_minutes

    if language == "zh":
        player["time"] = TIME_PERIODS_ZH[current_idx]
        time_data["period"] = TIME_PERIODS_ZH[current_idx]
    else:
        player["time"] = TIME_PERIODS[current_idx]
        time_data["period"] = TIME_PERIODS[current_idx]

    start_hour_map = PERIOD_START_HOUR_ZH if language == "zh" else PERIOD_START_HOUR
    period_key = TIME_PERIODS_ZH[current_idx] if language == "zh" else TIME_PERIODS[current_idx]
    start_hour = start_hour_map.get(period_key, 6)
    clock_hour = (start_hour + period_minutes // 60) % 24
    clock_minute = period_minutes % 60
    time_data["clock"] = f"{int(clock_hour):02d}:{int(clock_minute):02d}"
    world_state["time"] = time_data

    if turn % 9 == 0:
        alert = world_state.get("nexus_alert", {})
        if isinstance(alert, dict):
            alert["current"] = max(0, alert.get("current", 0) - 1)
            world_state["nexus_alert"] = alert


# ---------------------------------------------------------------------------
# Trace checker (mirrors graph.py trace_checker)
# ---------------------------------------------------------------------------

def _run_trace_checker(traces, knowledge, npcs, player, world_state, session_dir, language):
    """Check all trace conditions. Returns (traces, discovery_notifications)."""
    from engine.game_data import TRACE_DIFFICULTY_OVERRIDES, get_localized

    settings = _read_session_settings(session_dir)
    difficulty = settings.get("difficulty", "standard")
    overrides = TRACE_DIFFICULTY_OVERRIDES.get(difficulty, {})

    new_discoveries = []
    for tc in TRACE_CONDITIONS:
        trace_id = tc["id"]
        if _trace_discovered(traces, trace_id):
            continue
        try:
            checker = overrides.get(trace_id, tc["check"])
            if checker(knowledge, traces, npcs, player, world_state):
                discovery = {
                    "id": trace_id,
                    "description": get_localized(tc, "description", language),
                    "turn": player.get("turn", 1),
                }
                if "discovered" not in traces:
                    traces["discovered"] = []
                traces["discovered"].append(discovery)
                new_discoveries.append(trace_id)
                gate = traces.get("_gate_system", {})
                if gate:
                    gate["deepest_layer"] = max(gate.get("deepest_layer", 0), tc["layer"])
        except Exception:
            pass

    # Keep the display fields (counter, per-layer progress, per-trace status) in
    # sync with the authoritative `discovered` list every turn — otherwise the
    # persisted counter stays "0 / N" even after real discoveries.
    from engine.game_data import reconcile_trace_presentation
    reconcile_trace_presentation(traces)
    save_session_file(session_dir, "traces", traces)

    notifications = []
    if new_discoveries:
        _LAYER_NAMES = {
            1: {"en": "The Surface", "zh": "表层"},
            2: {"en": "The Conspiracy", "zh": "阴谋"},
            3: {"en": "The Severance Truth", "zh": "断离真相"},
            4: {"en": "The Mirror", "zh": "镜像"},
            5: {"en": "The Full Truth", "zh": "完整真相"},
        }
        for tc in TRACE_CONDITIONS:
            if tc["id"] in new_discoveries:
                layer_info = _LAYER_NAMES.get(tc["layer"], {})
                notifications.append({
                    "trace_id": tc["id"],
                    "layer": tc["layer"],
                    "layer_name": layer_info.get(language, layer_info.get("en", f"Layer {tc['layer']}")),
                    "description": get_localized(tc, "description", language),
                })

    return traces, notifications


# ---------------------------------------------------------------------------
# Meter-change notices (Integrity / NEXUS Alert / Fragment Decay)
# ---------------------------------------------------------------------------

def _meter_values(player: dict, world_state: dict) -> dict:
    """Snapshot the three end-gating meters as plain numbers."""
    ig = player.get("integrity", {})
    ic = ig.get("current") if isinstance(ig, dict) else ig
    im = ig.get("max") if isinstance(ig, dict) else ig
    al = world_state.get("nexus_alert", {})
    de = world_state.get("fragment_decay", {})
    return {
        "integrity": ic,
        "integrity_max": im,
        "alert": al.get("current") if isinstance(al, dict) else None,
        "decay": de.get("current") if isinstance(de, dict) else None,
    }


def _build_meter_notices(before: dict, after: dict, language: str) -> list[str]:
    """Build 'X → Y' chat notices for any meter that changed this turn."""
    zh = language == "zh"
    notices: list[str] = []

    b, a = before.get("integrity"), after.get("integrity")
    if isinstance(b, int) and isinstance(a, int) and a != b:
        mx = after.get("integrity_max") or before.get("integrity_max") or "?"
        arrow = "↓" if a < b else "↑"
        notices.append(
            f"{arrow} 神经完整度：{b}/{mx} → {a}/{mx}" if zh
            else f"{arrow} Integrity: {b}/{mx} → {a}/{mx}"
        )

    b, a = before.get("alert"), after.get("alert")
    if isinstance(b, (int, float)) and isinstance(a, (int, float)) and a != b:
        arrow = "↑" if a > b else "↓"
        notices.append(
            f"{arrow} NEXUS 警戒：{int(b)}% → {int(a)}%" if zh
            else f"{arrow} NEXUS Alert: {int(b)}% → {int(a)}%"
        )

    b, a = before.get("decay"), after.get("decay")
    if isinstance(b, (int, float)) and isinstance(a, (int, float)) and a != b:
        arrow = "↑" if a > b else "↓"
        notices.append(
            f"{arrow} 碎片衰变：{int(b)}% → {int(a)}%" if zh
            else f"{arrow} Fragment Decay: {int(b)}% → {int(a)}%"
        )

    return notices


# One-time Integrity primer (woven into the scene diegetically by the resolver).
_INTEGRITY_PRIMER_EN = (
    "[ONE-TIME — INTEGRITY PRIMER]: The player has not yet learned what Integrity "
    "means. At a natural moment THIS turn — through an NPC's concern, the implant's "
    "feedback, or their own body — briefly and diegetically convey that Integrity is "
    "their physical/neural resilience: it erodes from strain, injury and deep Signal "
    "resonance; it can be restored by rest, medical help, or stims; and at zero they "
    "collapse and die. Keep it short, in-world, and woven into the scene — NOT a "
    "tutorial popup, and do NOT state game mechanics or numbers. Mention it only once."
)
_INTEGRITY_PRIMER_ZH = (
    "[一次性——完整度提示]：玩家尚未了解「神经完整度」的含义。请在本回合的自然时机——"
    "通过某个NPC的关切、植入体的反馈，或玩家自身的身体感受——简短而有代入感地传达："
    "神经完整度代表其身体/神经的承受力；它会因劳损、受伤和深度信号共鸣而下降；可通过"
    "休息、医疗或兴奋剂恢复；归零时会昏厥并死亡。保持简短、融入剧情，不要做成教程弹窗，"
    "也不要提及游戏机制或具体数字。只提示这一次。"
)


# ---------------------------------------------------------------------------
# Consequence checker (mirrors graph.py consequence)
# ---------------------------------------------------------------------------

def _run_consequence(player, traces, world_state, knowledge, npcs):
    """Check death and ending conditions. Returns (game_over, ending, death_cause).

    DEATH is a generic ending reachable multiple ways (see game_data.check_death)
    and is checked before the designed story endings.
    """
    is_dead, cause = check_death(player, world_state)
    if is_dead:
        return True, "death", cause

    for ending in ENDINGS:
        try:
            if ending["check"](traces, world_state, player, knowledge, npcs):
                return True, ending["id"], None
        except Exception:
            pass

    return False, None, None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_turn(session_dir: str, player_input: str, mode: str = "play") -> dict:
    """Run a single game turn using the claude-code bypass engine.

    Makes ONE `claude -p` call and applies all post-processing in Python.
    """
    import time as _time
    _turn_start = _time.time()

    # Load state from disk
    player = load_session_file(session_dir, "player")
    knowledge = load_session_file(session_dir, "knowledge")
    traces = load_session_file(session_dir, "traces")
    location = load_session_file(session_dir, "location")
    inventory = load_session_file(session_dir, "inventory")
    npcs = load_session_file(session_dir, "npcs")
    world_state = load_session_file(session_dir, "world_state")
    log = load_session_file(session_dir, "log")

    settings = _read_session_settings(session_dir)
    language = settings.get("language", "en")
    difficulty = settings.get("difficulty", "standard")

    # Snapshot the three end-gating meters BEFORE any mutation/world-tick so we
    # can report exactly how they changed (from → to) as in-chat notices.
    _meters_before = _meter_values(player, world_state)

    # Set session dir for tools that need it
    set_session_dir(session_dir)
    set_current_inventory(inventory)

    state = {
        "player": player, "knowledge": knowledge, "traces": traces,
        "location": location, "inventory": inventory, "npcs": npcs,
        "world_state": world_state, "log": log,
    }

    is_resume = mode == "resume"

    # ── Step 1: Pre-validation (Python, no LLM) ─────────────────────
    if not is_resume:
        # Regex injection check
        for pat in _INJECTION_PATTERNS:
            if pat.search(player_input):
                return {
                    "narrative": "Your neural implant flickers — that kind of thinking won't work here."
                                 if language != "zh" else "你的神经植入体闪烁——这种想法在这里行不通。",
                    "game_over": False, "ending": None, "is_warning": True,
                    "discovery_notifications": [], "turn_usage": {},
                    "knowledge_notifications": [],
                    "elapsed_seconds": round(_time.time() - _turn_start, 1),
                }

        # Movement validation
        block_reason = _check_movement(player_input, state, language)
        if block_reason:
            return {
                "narrative": block_reason,
                "game_over": False, "ending": None, "is_warning": True,
                "discovery_notifications": [], "turn_usage": {},
                "knowledge_notifications": [],
                "elapsed_seconds": round(_time.time() - _turn_start, 1),
            }

    # ── Step 2: Build mega-prompt ────────────────────────────────────
    deepest_layer = extract_deepest_layer(traces)
    static_prompt = build_static_prompt(language, deepest_layer)
    # The turn-1 opening is cached and shared across players (keyed by language +
    # background), so strip the player's name/alias from the state used to build
    # it — otherwise the model could echo a real player's identity into a scene
    # later shown to everyone. Mirrors pregen_openings.py (empty name/alias).
    if is_resume and player.get("turn", 1) == 1:
        prompt_state = {**state, "player": {**player, "name": "", "alias": ""}}
    else:
        prompt_state = state
    dynamic_prompt = build_dynamic_state_prompt(prompt_state)
    validator_context = _build_validator_context(state)
    conversation_history = _read_conversation_history(session_dir, last_n=5)

    output_spec = _OUTPUT_FORMAT_SPEC.replace("{validator_context}", validator_context)

    system_prompt = f"{static_prompt}\n\n{dynamic_prompt}\n\n{output_spec}"

    # One-time, diegetic Integrity primer. Recorded via a persistent player flag
    # so it never repeats. Fires the first time the player has actually been hurt
    # (integrity below max) or, failing that, by an early fallback turn — whichever
    # comes first — so the concept is learned in-fiction, at a natural moment.
    flags = player.get("flags") or {}
    if not is_resume and not flags.get("integrity_introduced"):
        ig = player.get("integrity", {})
        cur = ig.get("current") if isinstance(ig, dict) else ig
        mx = ig.get("max") if isinstance(ig, dict) else ig
        hurt = isinstance(cur, int) and isinstance(mx, int) and cur < mx
        early = player.get("turn", 1) >= 4
        if hurt or early:
            primer = _INTEGRITY_PRIMER_ZH if language == "zh" else _INTEGRITY_PRIMER_EN
            system_prompt = f"{system_prompt}\n\n{primer}"
            flags["integrity_introduced"] = True
            player["flags"] = flags

    if is_resume:
        if player.get("turn", 1) == 1:
            # Fresh new-game opening. Written name-agnostically (second person, no
            # player name/alias) so the scene can be cached once and reused for
            # every new player of this (language, background) — see
            # engine/opening_cache.py / gui/server.py.
            user_prompt = (
                f"[SYSTEM: New game — opening scene. The player is a "
                f"{player.get('background', '?')} at {location.get('area', '?')} in "
                f"{location.get('district', '?')}. Turn 1. Write a brief, atmospheric "
                f"second-person ('you') scene-setting opening. Do NOT use the player's name "
                f"or alias or invent any proper name for them — this exact opening is shown to "
                f"every new player of this background. Do NOT call any tools (leave tool_calls "
                f"empty), but DO fill suggested_actions with 1-3 short, distinct opening moves "
                f"grounded only in what the player can currently see (follow the "
                f"suggested_actions rules above). Return JSON with just narrative and "
                f"suggested_actions.]"
            )
        else:
            user_prompt = (
                f"[SYSTEM: Session resumed. The player is {player.get('name', 'unknown')} "
                f"(alias: {player.get('alias', '?')}), a {player.get('background', '?')}. "
                f"Currently at {location.get('area', '?')} in {location.get('district', '?')}. "
                f"Turn {player.get('turn', 1)}. Provide a brief scene-setting narrative. "
                f"Do NOT call any tools (leave tool_calls empty), but DO fill suggested_actions "
                f"with 1-3 short, distinct opening moves grounded only in what the player can "
                f"currently see and already knows (follow the suggested_actions rules above). "
                f"Return JSON with just narrative and suggested_actions.]"
            )
    else:
        user_prompt = player_input

    if conversation_history:
        user_prompt = f"[Recent conversation history]\n{conversation_history}\n\n[Current input]\n{user_prompt}"

    # ── Step 3: Single claude -p call ────────────────────────────────
    # Get or create the ClaudeCodeLLM instance
    from engine.graph import get_llm
    llm = get_llm()

    if hasattr(llm, '_call_claude'):
        raw_text = llm._call_claude(system_prompt, user_prompt)
    else:
        # Fallback for non-claude-code LLMs (shouldn't happen but safety)
        from langchain_core.messages import SystemMessage, HumanMessage
        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        raw_text = response.content

    # ── Step 4: Parse response ───────────────────────────────────────
    parsed = _parse_response(raw_text)

    # ── Step 5: Validation is advisory only ──────────────────────────
    # Python already hard-blocks prompt-injection (Step 1) and impossible
    # movement (Step 1b) BEFORE the LLM call. By four iterations of playtesting,
    # the model's input_valid=false is almost always a false-positive that rejects
    # the game's OWN narrated content (an NPC/place/item it introduced a turn or
    # two ago that isn't yet in the structured lists), which burned ~1/3-1/2 of
    # turns and blocked traces, theorize, navigation, and bought-item use. So we no
    # longer hard-stop the turn on it: we let the scene play out and let the
    # narrator refuse genuinely impossible actions in-fiction instead.
    if not parsed.get("input_valid", True):
        logger.info(
            "claude_code_engine: model flagged input invalid (advisory, not blocking): %s",
            parsed.get("blocking_reason"),
        )

    narrative = parsed.get("narrative") or parsed.get("blocking_reason") or ""

    # ── Step 6: Execute game tools ───────────────────────────────────
    narrative, mutation_calls = _execute_game_tools(parsed["tool_calls"], narrative, inventory)

    # ── Step 7: Apply state mutations ────────────────────────────────
    knowledge_notifications, elapsed_minutes = _apply_mutations(
        mutation_calls, player, knowledge, location,
        inventory, npcs, world_state, log, session_dir,
    )

    # ── Step 7b: Apply numeric state_effects (deterministic meter deltas) ──
    # The model reports consequences as simple numbers here; applying them in
    # Python means integrity/NEXUS/credits move even when it omits the tool_calls,
    # so death/capture endings can actually fire.
    elapsed_minutes += _apply_state_effects(
        parsed.get("state_effects", {}), player, world_state, inventory,
    )

    # ── Step 8: Apply location_update ────────────────────────────────
    if parsed["location_update"] and isinstance(parsed["location_update"], dict):
        loc_update = parsed["location_update"]
        # ⚠️ SYNC: normalize exit direction keys — mirrored in graph.py
        exits = loc_update.get("exits", {})
        if exits:
            _ZH_TO_EN = {
                "北": "north", "南": "south", "东": "east", "西": "west",
                "东北": "northeast", "西北": "northwest", "东南": "southeast", "西南": "southwest",
                "上": "up", "下": "down",
            }
            loc_update["exits"] = {_ZH_TO_EN.get(k, k).lower(): v for k, v in exits.items()}
        for field in ("description", "exits", "points_of_interest", "npcs_present"):
            if field in loc_update:
                location[field] = loc_update[field]

    # ── Step 9: Run world_ticker ─────────────────────────────────────
    _run_world_ticker(player, world_state, session_dir, skip=is_resume,
                      elapsed_minutes=elapsed_minutes)

    # ── Step 10: Save all state ──────────────────────────────────────
    save_session_file(session_dir, "player", player)
    save_session_file(session_dir, "knowledge", knowledge)
    save_session_file(session_dir, "location", location)
    save_session_file(session_dir, "inventory", inventory)
    save_session_file(session_dir, "npcs", npcs)
    save_session_file(session_dir, "world_state", world_state)
    save_session_file(session_dir, "log", log)

    # ── Step 11: Run trace_checker ───────────────────────────────────
    traces, discovery_notifications = _run_trace_checker(
        traces, knowledge, npcs, player, world_state, session_dir, language,
    )

    # ── Step 12: Run consequence ─────────────────────────────────────
    game_over, ending, death_cause = _run_consequence(player, traces, world_state, knowledge, npcs)

    # ── Step 12b: Build in-chat meter notices (from → to) + low-integrity warning
    system_notices: list[str] = []
    if not is_resume:
        _meters_after = _meter_values(player, world_state)
        system_notices = _build_meter_notices(_meters_before, _meters_after, language)
        if not game_over:
            before_i = _meters_before.get("integrity")
            cur_i = _meters_after.get("integrity")
            max_i = _meters_after.get("integrity_max")
            if (isinstance(cur_i, int) and isinstance(before_i, int)
                    and isinstance(max_i, int) and cur_i < before_i):
                warn = integrity_warning_text(difficulty, cur_i, max_i, language)
                if warn:
                    system_notices.append(warn)

    # ── Step 13: Log conversation ────────────────────────────────────
    if not is_resume:
        append_conversation(session_dir, "user", player_input, player.get("turn", 1))
        append_conversation(session_dir, "assistant", narrative, player.get("turn", 1))

    # ── Step 14: Suggested actions ───────────────────────────────────
    # The model emits these inline (see _OUTPUT_FORMAT_SPEC) so there is no
    # extra LLM call. Spoiler-safety is enforced by the prompt rules.
    from engine.suggestions import read_features, normalize_actions
    features = read_features(session_dir)
    suggested_actions: list[dict] = []
    if features["suggested_actions"] and not game_over:
        suggested_actions = normalize_actions(
            parsed.get("suggested_actions", []),
            features["suggested_actions_count"],
        )

    return {
        "narrative": narrative,
        "game_over": game_over,
        "ending": ending,
        "death_cause": death_cause,
        "is_warning": False,
        "discovery_notifications": discovery_notifications,
        "turn_usage": {},
        "knowledge_notifications": knowledge_notifications,
        "system_notices": system_notices,
        "suggested_actions": suggested_actions,
        "elapsed_seconds": round(_time.time() - _turn_start, 1),
    }
