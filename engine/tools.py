"""
Signal Lost — LangGraph Tool Definitions

Wraps the existing CLI tools (dice, cipher, signal, glitch, profile, map)
as @tool-decorated functions for use in the LangGraph resolver node.
Also defines state mutation tools that the LLM uses to express game state changes.
"""

from __future__ import annotations

import json
import os
import random
import sys

import importlib.util

from langchain_core.tools import tool

# ---------------------------------------------------------------------------
# Session directory (set by input_gate each turn for file-access tools)
# ---------------------------------------------------------------------------

_current_session_dir: str | None = None


def set_session_dir(session_dir: str) -> None:
    """Set the active session directory. Called by input_gate at the start of each turn."""
    global _current_session_dir
    _current_session_dir = session_dir


_current_inventory: list[dict] = []


def set_current_inventory(items: list[dict]) -> None:
    """Set the current inventory for tool-level item checks."""
    global _current_inventory
    _current_inventory = items


def _has_item(keyword: str) -> bool:
    """Check if the current inventory contains an item matching the keyword."""
    for item in _current_inventory:
        name = (item.get("name", "") + " " + item.get("item", "")).lower()
        if keyword.lower() in name:
            return True
    return False


# Add the game's tools/ directory to path so we can import directly
_GAME_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_TOOLS_DIR = os.path.join(_GAME_ROOT, "tools")
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)


def _import_from_file(module_name: str, file_name: str):
    """Import a module by file path, avoiding stdlib name collisions."""
    path = os.path.join(_TOOLS_DIR, file_name)
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Import core functions from existing tools
# Use _import_from_file for modules that collide with stdlib names
# (signal, profile → stdlib signal, profile)
_dice = _import_from_file("game_dice", "dice.py")
_cipher = _import_from_file("game_cipher", "cipher.py")
_signal = _import_from_file("game_signal", "signal.py")
_glitch = _import_from_file("game_glitch", "glitch.py")
_profile = _import_from_file("game_profile", "profile.py")

parse_dice, roll, check = _dice.parse_dice, _dice.roll, _dice.check
caesar_decrypt = _cipher.caesar_decrypt
xor_decrypt = _cipher.xor_decrypt
substitute_decrypt = _cipher.substitute_decrypt
reverse_decrypt = _cipher.reverse_decrypt
base64_decrypt = _cipher.base64_decrypt
frequency_analysis = _cipher.frequency_analysis
analyze_evidence = _signal.analyze_evidence
signal_scan = _signal.signal_scan
deep_resonance = _signal.deep_resonance
generate_glitch = _glitch.generate_glitch
generate_npc = _profile.generate_npc


# ═══════════════════════════════════════════════════════════════════════════
# Game tools (wrapped from tools/*.py)
# ═══════════════════════════════════════════════════════════════════════════


@tool
def roll_dice(expression: str, target: int | None = None, modifier: int = 0,
              skill_type: str | None = None) -> dict:
    """Roll dice for probability checks.

    Use d100 for skill checks (success if roll <= target).
    Difficulty targets: Easy=80, Normal=60, Hard=40, Very Hard=20, Near Impossible=10.
    Modifiers: relevant background +10, relevant item +10-20, NPC trust +5/level.

    Args:
        expression: Dice expression like 'd100', '2d6+3', 'd20'
        target: Target number for success check (roll <= target = success). None for plain roll.
        modifier: Additional modifier to add to the roll
        skill_type: Type of skill check (e.g. 'lockpick', 'hack', 'stealth', 'persuasion') for item bonus tracking
    """
    count, sides, mod = parse_dice(expression)
    result = roll(count, sides, mod + modifier)
    if target is not None:
        result.update(check(result["total"], target))
    if skill_type:
        result["skill_type"] = skill_type
    return result


@tool
def decrypt_cipher(method: str, text: str, key: str | None = None) -> dict:
    """Decrypt an encrypted data chip or message.

    Args:
        method: One of 'caesar', 'xor', 'substitute', 'reverse', 'base64', 'analyze'
        text: The encrypted text to decrypt
        key: Decryption key (number for caesar/xor, 26-char alphabet for substitute)
    """
    # Advanced methods require cipher toolkit
    if method in ("caesar", "xor", "substitute") and not _has_item("cipher"):
        return {"error": "Advanced decryption requires a Cipher Toolkit.",
                "hint": "Basic methods (reverse, base64, analyze) work without tools."}

    if method == "analyze":
        freq = frequency_analysis(text)
        return {"mode": "frequency_analysis", "frequencies": freq}

    if method == "caesar":
        return {"method": "caesar", "result": caesar_decrypt(text, int(key or 0))}
    elif method == "xor":
        return {"method": "xor", "result": xor_decrypt(text, int(key or 0))}
    elif method == "substitute":
        return {"method": "substitute", "result": substitute_decrypt(text, key or "")}
    elif method == "reverse":
        return {"method": "reverse", "result": reverse_decrypt(text)}
    elif method == "base64":
        return {"method": "base64", "result": base64_decrypt(text)}
    else:
        return {"error": f"Unknown method: {method}"}


@tool
def analyze_signal(evidence_id: str | None = None, description: str | None = None,
                   scan: bool = False, strength: int = 30,
                   resonate: bool = False) -> dict:
    """Analyze Signal fragments, perform area scans, or attempt deep resonance.

    Use one of three modes:
    - Evidence analysis: provide evidence_id and description
    - Area scan: set scan=True and provide strength (0-100)
    - Deep resonance: set resonate=True (WARNING: costs 1 Integrity)

    Args:
        evidence_id: Evidence ID to analyze (e.g. 'EVID-001')
        description: Evidence description for context
        scan: If True, perform a general area Signal scan
        strength: Signal strength for scan mode (0-100)
        resonate: If True, attempt deep resonance (dangerous)
    """
    if evidence_id:
        return analyze_evidence(evidence_id, description or "Unknown evidence")
    elif scan:
        return signal_scan(strength)
    elif resonate:
        result = deep_resonance()
        result["integrity_cost"] = 1  # Enforced by state_writer
        return result
    else:
        return {"error": "Specify evidence_id, scan=True, or resonate=True"}


@tool
def generate_glitch_event(district: str = "The Sprawl", strength: int = 30) -> dict:
    """Generate an atmospheric Signal manifestation for immersion.

    Use this periodically in areas with Signal presence.
    Manifestations can contain story hints at higher strengths.

    Args:
        district: Current district name
        strength: Signal strength (0-100). Faint <25, Moderate 26-60, Intense 61+
    """
    return generate_glitch(district, strength)


@tool
def generate_minor_npc(district: str | None = None, faction: str | None = None) -> dict:
    """Generate a random minor NPC to populate a scene.

    Each generated NPC has a name, occupation, personality, faction, and one piece
    of knowledge (a rumor or fact) they can share.

    Args:
        district: District for the NPC (affects occupation and faction distribution)
        faction: Force a specific faction affiliation
    """
    return generate_npc(district=district, faction=faction)


# ═══════════════════════════════════════════════════════════════════════════
# State mutation tools
# These don't directly modify files — they return structured deltas
# that the state_writer node processes.
# ═══════════════════════════════════════════════════════════════════════════


def _parse_json_arg(value: Any, fallback_key: str = "description") -> dict:
    """Parse a tool argument that should be a JSON object.

    Handles three input forms (common with simulated tool calling):
      1. dict  — pass through (already parsed by JSON extractor)
      2. JSON string — parse it
      3. plain string — wrap as {fallback_key: value} instead of erroring
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        # Plain string fallback — wrap it so the tool still succeeds
        return {fallback_key: value}
    return {fallback_key: str(value)}


@tool
def update_player(changes: str) -> str:
    """Update player state fields.

    Pass a JSON string of field:value pairs to update.
    Valid fields: integrity, credits, neural_implant, current_disguise, status_effects.
    Do NOT update turn or time — those are handled automatically.

    Args:
        changes: JSON string of changes, e.g. '{"credits": 40, "neural_implant": "Active"}'
    """
    parsed = _parse_json_arg(changes, "value")
    return json.dumps({"type": "update_player", "changes": parsed})


@tool
def add_knowledge(entry_type: str, entry: str) -> str:
    """Add a knowledge entry (fact, rumor, evidence, theory, or connection).

    Args:
        entry_type: One of 'fact', 'rumor', 'evidence', 'theory', 'connection'
        entry: JSON string of the entry. Must include 'description' and 'source'.
            For facts: {"id": "FACT-NNN", "description": "...", "source": "..."}
            For rumors: {"id": "RUMOR-NNN", "description": "...", "source": "...", "status": "unconfirmed"}
            For evidence: {"id": "EVID-NNN", "name": "...", "description": "...", "found": "..."}
            For theories: {"id": "THEO-NNN", "statement": "...", "based_on": ["FACT-001", "RUMOR-002"]}
            For connections: {"ids": ["FACT-001", "RUMOR-003"], "relationship": "..."}
    """
    parsed = _parse_json_arg(entry, "description")
    # Ensure a 'source' field exists (required by knowledge schema)
    if "source" not in parsed:
        parsed["source"] = "unknown"
    return json.dumps({"type": "add_knowledge", "entry_type": entry_type, "entry": parsed})


@tool
def update_npc(name: str, changes: str) -> str:
    """Update an encountered NPC's state, or add a newly encountered NPC.

    Args:
        name: NPC name (e.g. 'Mira', 'Ghost')
        changes: JSON string of changes.
            To update: {"trust_level": "cautious_ally", "location_last_seen": "..."}
            To add new: {"name": "Mira", "faction": "...", "trust_level": "neutral", ...}
    """
    parsed = _parse_json_arg(changes, "description")
    return json.dumps({"type": "update_npc", "name": name, "changes": parsed})


@tool
def update_location(location_data: str) -> str:
    """Update the player's current location. Must include ALL fields.

    Args:
        location_data: JSON string with ALL of these fields:
            - district: district name (e.g. "The Sprawl", "Neon Row")
            - area: specific place within the district
            - description: 2-3 sentence atmospheric description of what the player sees/hears/smells RIGHT NOW
            - signal_strength: e.g. "10%", "50%"
            - danger_level: one of "Safe", "Low", "Moderate", "High", "Extreme"
            - nexus_patrol: patrol presence description or "None"
            - exits: object mapping directions to short descriptions, e.g. {"north": "A busy main street...", "south": "Dark alley..."}
            - points_of_interest: list of notable things the player can interact with, e.g. ["Mira's Noodle Shop — steaming bowls..."]
            - npcs_present: list of characters visible here, e.g. ["Mira — behind the counter, watching you"]
    """
    parsed = _parse_json_arg(location_data, "description")
    return json.dumps({"type": "update_location", "data": parsed})


@tool
def update_inventory(action: str, item: str | None = None) -> str:
    """Modify the player's inventory.

    Args:
        action: One of 'add', 'remove', 'sell', 'update_credits'
        item: JSON string of the item for add/remove/sell, or credits amount for update_credits.
            Add: {"slot": N, "name": "...", "type": "...", "description": "..."}
            Remove: {"slot": N} or {"name": "..."}
            Sell: {"name": "...", "credits_gained": N} — removes item AND adds credits in one call.
                  Broken items cannot be sold, only discarded (use remove instead).
            Credits: just a number as string, e.g. "50" or "-10"
    """
    try:
        if action == "update_credits":
            return json.dumps({"type": "update_inventory", "action": action, "amount": int(item or 0)})
        parsed = _parse_json_arg(item or "{}", "name")
        if action == "sell":
            return json.dumps({
                "type": "update_inventory",
                "action": "sell",
                "item": parsed,
                "credits_gained": parsed.get("credits_gained", 0),
            })
        return json.dumps({"type": "update_inventory", "action": action, "item": parsed})
    except (json.JSONDecodeError, ValueError):
        return json.dumps({"error": "Invalid item data"})


@tool
def update_world_state(changes: str) -> str:
    """Update world state (NEXUS alert, fragment decay, district access, events).

    Args:
        changes: JSON string of changes.
            Examples: {"nexus_alert_delta": 10}, {"fragment_decay_delta": -5},
            {"discover_district": "The Undercroft"}, {"add_event": "NEXUS raid on Undercroft"}
    """
    parsed = _parse_json_arg(changes, "description")
    return json.dumps({"type": "update_world_state", "changes": parsed})


@tool
def advance_time(minutes: int, reason: str = "") -> str:
    """Report how many in-world minutes have elapsed this turn.

    Call this ONCE per turn AFTER resolving the player's action.
    Estimate realistically based on what happened in the narrative:
    - Quick look/examine: 1-5 minutes
    - Short conversation: 5-15 minutes
    - Detailed dialogue or investigation: 15-30 minutes
    - Travel between areas in same district: 10-20 minutes
    - Travel between districts: 30-60 minutes
    - Hacking/decryption task: 15-45 minutes
    - Resting/sleeping: 120-480 minutes

    Args:
        minutes: Number of in-world minutes that passed (1-480)
        reason: Brief reason for the time estimate (e.g. "short conversation with Mira")
    """
    clamped = max(1, min(480, minutes))
    return json.dumps({"type": "advance_time", "minutes": clamped, "reason": reason})


@tool
def add_log_entry(title: str, tag: str, text: str) -> str:
    """Add an entry to the session log.

    Args:
        title: Short entry title (bilingual preferred, e.g. "Discovery / 发现")
        tag: One of: movement, dialogue, discovery, danger, signal, system, trade
        text: Noir-toned description of what happened
    """
    return json.dumps({"type": "add_log_entry", "title": title, "tag": tag, "text": text})


@tool
def recall_conversation(last_n: int = 20, search: str | None = None) -> dict:
    """Retrieve older conversation history from the session log.

    Use this when the player references events, dialogue, or decisions from
    more than 5 turns ago that aren't visible in the current context window.

    Args:
        last_n: Number of most recent exchanges to retrieve (default 20, max 100)
        search: Optional keyword to filter entries by content (case-insensitive)
    """
    if not _current_session_dir:
        return {"entries": [], "count": 0, "error": "Session not initialized"}

    path = os.path.join(_current_session_dir, "conversation.jsonl")
    try:
        entries = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except FileNotFoundError:
        return {"entries": [], "count": 0, "error": "No conversation history yet"}
    except OSError as e:
        return {"entries": [], "count": 0, "error": str(e)}

    if search:
        entries = [e for e in entries if search.lower() in e.get("content", "").lower()]

    cap = min(int(last_n), 100)
    recent = entries[-cap:] if len(entries) > cap else entries

    formatted = [
        {
            "turn": e.get("turn", "?"),
            "role": e.get("role", "?"),
            "content": str(e.get("content", ""))[:400],
        }
        for e in recent
    ]
    return {"entries": formatted, "count": len(formatted)}


# ═══════════════════════════════════════════════════════════════════════════
# Tool collections for the graph
# ═══════════════════════════════════════════════════════════════════════════

# Game tools — the LLM calls these for gameplay mechanics
GAME_TOOLS = [
    roll_dice,
    decrypt_cipher,
    analyze_signal,
    generate_glitch_event,
    generate_minor_npc,
    recall_conversation,
]

# State mutation tools — the LLM calls these to express state changes
STATE_TOOLS = [
    update_player,
    add_knowledge,
    update_npc,
    update_location,
    update_inventory,
    update_world_state,
    advance_time,
    add_log_entry,
]

# All tools for binding to the LLM
ALL_TOOLS = GAME_TOOLS + STATE_TOOLS
