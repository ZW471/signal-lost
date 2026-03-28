"""
Signal Lost — Game State Schema and I/O

Defines the GameState TypedDict used by the LangGraph StateGraph,
plus functions to load/save state from/to session JSON files.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


# ---------------------------------------------------------------------------
# State schema
# ---------------------------------------------------------------------------

class GameState(TypedDict):
    """Full game state flowing through the LangGraph graph."""

    # --- LangGraph conversation history (managed by add_messages reducer) ---
    messages: Annotated[list, add_messages]

    # --- Session state (mirrors session/*.json) ---
    player: dict          # session/player.json
    knowledge: dict       # session/knowledge.json
    traces: dict          # session/traces.json
    location: dict        # session/location.json
    inventory: dict       # session/inventory.json
    npcs: dict            # session/npcs.json
    world_state: dict     # session/world_state.json
    log: dict             # session/log.json

    # --- Turn metadata ---
    turn_delta: dict      # Accumulated state changes from this turn
    game_over: bool       # Whether the game has ended
    ending: str | None    # Which ending triggered, if any
    narrative: str        # The narrative text to display to the player

    # --- Session directory path ---
    session_dir: str      # Path to session/ folder

    # --- Flags ---
    skip_conversation_log: bool  # If True, state_writer skips logging to conversation.jsonl
    skip_turn_increment: bool    # If True, world_ticker skips incrementing the turn counter

    # --- Input validation ---
    input_blocked: bool          # Set True by input_validator when a player message is rejected
    blocking_reason: str | None  # Human-readable reason for rejection

    # --- System event flag ---
    skip_validation: bool        # If True, this turn is a system-injected event (resume/info),
                                 # not player input — bypasses input_validator entirely and
                                 # makes the turn ephemeral (messages removed from history)

    # --- Output language validation ---
    language_retry_count: int    # How many times output_language_checker has retried this turn
                                 # (capped at 1 to prevent infinite loops)


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------

SESSION_FILES = {
    "player": "player.json",
    "knowledge": "knowledge.json",
    "traces": "traces.json",
    "location": "location.json",
    "inventory": "inventory.json",
    "npcs": "npcs.json",
    "world_state": "world_state.json",
    "log": "log.json",
}


def _read_json(path: str) -> dict:
    """Read a JSON file, returning {} on any error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _write_json(path: str, data: dict) -> None:
    """Write a dict to a JSON file with pretty formatting."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_session(session_dir: str) -> dict[str, dict]:
    """Load all session JSON files into a dict keyed by state field name."""
    result = {}
    for key, filename in SESSION_FILES.items():
        result[key] = _read_json(os.path.join(session_dir, filename))
    return result


def save_session(session_dir: str, state: GameState) -> None:
    """Write all session state fields back to JSON files."""
    for key, filename in SESSION_FILES.items():
        data = state.get(key, {})
        if data:
            _write_json(os.path.join(session_dir, filename), data)


def save_session_file(session_dir: str, key: str, data: dict) -> None:
    """Write a single session file."""
    filename = SESSION_FILES.get(key)
    if filename and data:
        _write_json(os.path.join(session_dir, filename), data)


def append_conversation(session_dir: str, role: str, content: str, turn: int) -> None:
    """Append a line to conversation.jsonl."""
    path = os.path.join(session_dir, "conversation.jsonl")
    entry = {
        "role": role,
        "content": content,
        "turn": turn,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# State initialization helpers
# ---------------------------------------------------------------------------

def empty_turn_delta() -> dict:
    """Return an empty turn delta structure."""
    return {
        "player_changes": {},
        "knowledge_adds": [],
        "trace_discoveries": [],
        "npc_changes": [],
        "location_update": None,
        "inventory_changes": [],
        "world_state_changes": {},
        "log_entry": None,
    }


def initial_state(session_dir: str) -> GameState:
    """Build initial GameState by loading session files."""
    session_data = load_session(session_dir)
    return GameState(
        messages=[],
        player=session_data.get("player", {}),
        knowledge=session_data.get("knowledge", {}),
        traces=session_data.get("traces", {}),
        location=session_data.get("location", {}),
        inventory=session_data.get("inventory", {}),
        npcs=session_data.get("npcs", {}),
        world_state=session_data.get("world_state", {}),
        log=session_data.get("log", {}),
        turn_delta=empty_turn_delta(),
        game_over=False,
        ending=None,
        narrative="",
        session_dir=session_dir,
        skip_conversation_log=False,
        skip_turn_increment=False,
        input_blocked=False,
        blocking_reason=None,
        skip_validation=False,
        language_retry_count=0,
    )


# ---------------------------------------------------------------------------
# New game / save / load helpers
# ---------------------------------------------------------------------------

BACKGROUNDS = {
    "street_runner": {
        "display": "Street Runner",
        "display_zh": "街头行者",
        "starting_rumors": [
            {"id": "RUMOR-001", "description": "NEXUS has eyes in The Sprawl", "source": "street_knowledge"},
            {"id": "RUMOR-002", "description": "There's a woman named Mira who knows things", "source": "street_knowledge"},
        ],
        "starting_item": {
            "slot": 1,
            "item": "Lockpick Set",
            "type": "tool",
            "description": "A well-worn set of picks. Your fingers know how to use them even if your mind doesn't.",
        },
    },
    "corporate_exile": {
        "display": "Corporate Exile",
        "display_zh": "企业流亡者",
        "starting_rumors": [
            {"id": "RUMOR-001", "description": "NEXUS Project Division handles 'special acquisitions'", "source": "corporate_memory"},
            {"id": "RUMOR-002", "description": "Director Orin runs something off-books in Sector 7", "source": "corporate_memory"},
        ],
        "starting_item": {
            "slot": 1,
            "item": "Expired NEXUS Keycard",
            "type": "keycard",
            "description": "Level 2 clearance, expired 3 years ago. Might still open some doors in Sector 7.",
        },
    },
    "netrunner": {
        "display": "Netrunner",
        "display_zh": "网行者",
        "starting_rumors": [
            {"id": "RUMOR-001", "description": "The old network didn't just crash — something was in it", "source": "net_memory"},
            {"id": "RUMOR-002", "description": "A hacker called Ghost can crack anything", "source": "net_memory"},
        ],
        "starting_item": {
            "slot": 1,
            "item": "Basic Cipher Toolkit",
            "type": "data_chip",
            "description": "A data chip loaded with decryption utilities. Old but functional.",
        },
    },
}

DIFFICULTIES = {
    "paranoid": {"integrity_max": 4},
    "cautious": {"integrity_max": 3},
    "standard": {"integrity_max": 3},
    "reckless": {"integrity_max": 2},
}


def create_new_session(
    session_dir: str,
    name: str,
    alias: str,
    background: str,
    difficulty: str,
    language: str = "en",
) -> None:
    """Create all session files for a new game from templates."""
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)
    os.makedirs(session_dir, exist_ok=True)

    bg = BACKGROUNDS[background]
    diff = DIFFICULTIES[difficulty]
    integrity_max = diff["integrity_max"]

    # player.json
    _write_json(os.path.join(session_dir, "player.json"), {
        "title": "Player Status / 玩家状态",
        "name": name,
        "alias": alias,
        "background": bg["display"],
        "integrity": {"current": integrity_max, "max": integrity_max},
        "credits": 50,
        "neural_implant": "Active",
        "current_disguise": "None",
        "turn": 1,
        "time": "Morning" if language == "en" else "晨",
        "status_effects": ["Signal Sensitivity (faint)"],
    })

    # knowledge.json
    _write_json(os.path.join(session_dir, "knowledge.json"), {
        "title": "Knowledge Database / 知识库",
        "facts": [],
        "rumors": bg["starting_rumors"],
        "evidence": [],
        "theories": [],
        "connections": [],
    })

    # traces.json
    def _undiscovered(trace_id):
        return {"status": "undiscovered", "description": "[???]"}

    _write_json(os.path.join(session_dir, "traces.json"), {
        "title": "Traces of Truth / 真相痕迹",
        "total_discovered": "0 / 16",
        "layers": {
            "layer_1_surface": {
                "name": "The Surface / 表层",
                "progress": "0/3",
                "traces": {f"TRACE-L1-0{i}": _undiscovered(f"TRACE-L1-0{i}") for i in range(1, 4)},
            },
            "layer_2_conspiracy": {
                "name": "The Conspiracy / 阴谋",
                "progress": "0/4",
                "traces": {f"TRACE-L2-0{i}": _undiscovered(f"TRACE-L2-0{i}") for i in range(1, 5)},
            },
            "layer_3_severance_truth": {
                "name": "The Severance Truth / 断离真相",
                "progress": "0/4",
                "traces": {f"TRACE-L3-0{i}": _undiscovered(f"TRACE-L3-0{i}") for i in range(1, 5)},
            },
            "layer_4_mirror": {
                "name": "The Mirror / 镜像",
                "progress": "0/3",
                "traces": {f"TRACE-L4-0{i}": _undiscovered(f"TRACE-L4-0{i}") for i in range(1, 4)},
            },
            "layer_5_full_truth": {
                "name": "The Full Truth / 完整真相",
                "progress": "0/2",
                "traces": {f"TRACE-L5-0{i}": _undiscovered(f"TRACE-L5-0{i}") for i in range(1, 3)},
            },
        },
    })

    # location.json
    _write_json(os.path.join(session_dir, "location.json"), {
        "title": "Current Location / 当前位置",
        "district": "The Sprawl / 蔓城",
        "area": "Rain Alley (near Mira's Noodle Shop) / 雨巷（米拉面馆附近）",
        "zone": "Street Level",
        "description": "A narrow alley between crumbling residential blocks. Neon signs for noodle shops and repair stalls cast colored light across wet concrete. The air smells of synthetic broth and ozone.",
        "signal_strength": "10%",
        "danger_level": "Safe",
        "nexus_patrol": "None",
        "exits": {
            "north": "Main street — busier, more vendors, a public terminal",
            "south": "Deeper alleys — darker, quieter, leads to residential blocks",
            "east": "Mira's Noodle Shop — warm light, a woman watching from the counter",
            "west": "Market square — open area, more people, more noise",
        },
        "points_of_interest": [
            "Mira's Noodle Shop (east) — A small, steamy establishment. The owner seems to be watching you.",
            "Public Terminal (north, main street) — NEXUS-operated information kiosk. Free access.",
            "Repair Stall (north) — Sells basic tools and electronics.",
        ],
        "npcs_present": [
            "Mira (米拉) — Behind the counter of her noodle shop. Watching.",
            "Various unnamed pedestrians.",
        ],
    })

    # inventory.json
    _write_json(os.path.join(session_dir, "inventory.json"), {
        "title": "Inventory / 物品栏",
        "credits": 50,
        "slots": {"used": 1, "max": 6},
        "items": [bg["starting_item"]],
    })

    # npcs.json
    _write_json(os.path.join(session_dir, "npcs.json"), {
        "title": "Encountered NPCs / 已遇NPC",
        "npcs": [],
    })

    # world_state.json
    _write_json(os.path.join(session_dir, "world_state.json"), {
        "title": "World State / 世界状态",
        "nexus_alert": {"current": 0, "status": "Calm"},
        "fragment_decay": {"current": 0, "status": "Stable"},
        "district_access": [
            {"name": "The Sprawl", "name_zh": "蔓城", "status": "Open", "notes": "Starting area"},
            {"name": "Neon Row", "name_zh": "霓虹街", "status": "Open", "notes": "Entertainment and intel"},
        ],
        "_district_registry": {
            "hidden": True,
            "undiscovered": [
                {"name": "The Undercroft", "name_zh": "底渊", "status": "Locked", "unlock": "Requires TRACE-L1-03", "notes": "Underground Listener territory"},
                {"name": "Sector 7", "name_zh": "第七区", "status": "Restricted", "unlock": "Requires keycard or disguise", "notes": "Corporate zone"},
                {"name": "Chrome Heights", "name_zh": "镀金台", "status": "Restricted", "unlock": "Requires invitation or disguise", "notes": "Elite residential area"},
                {"name": "The Resonance", "name_zh": "共鸣所", "status": "Hidden", "unlock": "Requires Layer 3 completion", "notes": "Ancient pre-Severance facility"},
            ],
        },
        "time": {"day": 1, "period": "Morning" if language == "en" else "晨"},
        "global_events": [],
        "_ending_trajectory": {"hidden": True, "value": "neutral — no direction yet"},
    })

    # log.json
    _write_json(os.path.join(session_dir, "log.json"), {
        "title": "Session Log / 会話日志",
        "entries": [
            {
                "turn": 1,
                "title": "Awakening / 苏醒",
                "description": "You wake in a rain-soaked alley in The Sprawl with no memory and a humming neural implant.",
                "signal": True,
            }
        ],
    })

    # conversation.jsonl (empty)
    open(os.path.join(session_dir, "conversation.jsonl"), "w").close()


def copy_save_to_session(save_dir: str, session_dir: str) -> None:
    """Restore a save into the active session directory."""
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)
    shutil.copytree(save_dir, session_dir)


def save_game_to_slot(session_dir: str, save_name: str, saves_dir: str) -> str:
    """Copy the current session to a named save slot. Returns the save path."""
    dest = os.path.join(saves_dir, save_name)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(session_dir, dest)
    return dest
