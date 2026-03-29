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
    discovery_notifications: list  # Populated by trace_checker, consumed by server

    # --- Session directory path ---
    session_dir: str      # Path to session/ folder

    # --- Turn flags (reset at start of each turn via reset_turn_flags) ---
    skip_conversation_log: bool  # If True, state_writer skips logging to conversation.jsonl
    skip_turn_increment: bool    # If True, world_ticker skips incrementing the turn counter
    input_blocked: bool          # Set True by input_validator when a player message is rejected
    blocking_reason: str | None  # Human-readable reason for rejection
    skip_validation: bool        # If True, this turn is a system-injected event (resume/info)
    language_retry_count: int    # How many times output_language_checker has retried (cap: 1)


def reset_turn_flags() -> dict:
    """Return a dict of all turn flags set to their clean defaults.

    Call at the start of each turn (in input_gate) to prevent flag bleed
    between turns.
    """
    return {
        "skip_conversation_log": False,
        "skip_turn_increment": False,
        "input_blocked": False,
        "blocking_reason": None,
        "skip_validation": False,
        "language_retry_count": 0,
    }


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
        "starting_rumors_zh": [
            {"id": "RUMOR-001", "description": "NEXUS在蔓城安插了眼线", "source": "街头消息"},
            {"id": "RUMOR-002", "description": "有个叫米拉的女人知道不少事", "source": "街头消息"},
        ],
        "starting_item": {
            "slot": 1,
            "item": "Lockpick Set",
            "type": "tool",
            "description": "A well-worn set of picks. Your fingers know how to use them even if your mind doesn't.",
        },
        "starting_item_zh": {
            "slot": 1,
            "item": "撬锁工具",
            "type": "工具",
            "description": "一套磨损的撬锁器。你的手指知道怎么用，即使你的记忆已经不在了。",
        },
    },
    "corporate_exile": {
        "display": "Corporate Exile",
        "display_zh": "企业流亡者",
        "starting_rumors": [
            {"id": "RUMOR-001", "description": "NEXUS Project Division handles 'special acquisitions'", "source": "corporate_memory"},
            {"id": "RUMOR-002", "description": "Director Orin runs something off-books in Sector 7", "source": "corporate_memory"},
        ],
        "starting_rumors_zh": [
            {"id": "RUMOR-001", "description": "NEXUS项目部门负责处理'特殊征集'", "source": "企业记忆"},
            {"id": "RUMOR-002", "description": "主管奥林在第七区进行着账外活动", "source": "企业记忆"},
        ],
        "starting_item": {
            "slot": 1,
            "item": "Expired NEXUS Keycard",
            "type": "keycard",
            "description": "Level 2 clearance, expired 3 years ago. Might still open some doors in Sector 7.",
        },
        "starting_item_zh": {
            "slot": 1,
            "item": "过期的NEXUS门禁卡",
            "type": "门禁卡",
            "description": "二级权限，三年前过期。也许还能打开第七区的一些门。",
        },
    },
    "netrunner": {
        "display": "Netrunner",
        "display_zh": "网行者",
        "starting_rumors": [
            {"id": "RUMOR-001", "description": "The old network didn't just crash — something was in it", "source": "net_memory"},
            {"id": "RUMOR-002", "description": "A hacker called Ghost can crack anything", "source": "net_memory"},
        ],
        "starting_rumors_zh": [
            {"id": "RUMOR-001", "description": "旧网络不只是崩溃了——里面有东西", "source": "网络记忆"},
            {"id": "RUMOR-002", "description": "一个叫幽灵的黑客能破解任何东西", "source": "网络记忆"},
        ],
        "starting_item": {
            "slot": 1,
            "item": "Basic Cipher Toolkit",
            "type": "data_chip",
            "description": "A data chip loaded with decryption utilities. Old but functional.",
        },
        "starting_item_zh": {
            "slot": 1,
            "item": "基础密码工具包",
            "type": "数据芯片",
            "description": "一块装载着解密工具的数据芯片。虽旧但仍可用。",
        },
    },
}

DIFFICULTIES = {
    "paranoid": {"integrity_max": 4},
    "cautious": {"integrity_max": 3},
    "standard": {"integrity_max": 3},
    "reckless": {"integrity_max": 2},
}


# ---------------------------------------------------------------------------
# Locale strings for session initialization
# ---------------------------------------------------------------------------

_LOCALE: dict[str, dict[str, Any]] = {
    "en": {
        "player_title": "Player Status",
        "active": "Active",
        "none": "None",
        "signal_sensitivity": "Signal Sensitivity (faint)",
        "time_morning": "Morning",
        "knowledge_title": "Knowledge Database",
        "traces_title": "Traces of Truth",
        "layer_1": "The Surface",
        "layer_2": "The Conspiracy",
        "layer_3": "The Severance Truth",
        "layer_4": "The Mirror",
        "layer_5": "The Full Truth",
        "location_title": "Current Location",
        "district": "The Sprawl",
        "area": "Rain Alley (near Mira's Noodle Shop)",
        "zone": "Street Level",
        "location_desc": "A narrow alley between crumbling residential blocks. Neon signs for noodle shops and repair stalls cast colored light across wet concrete. The air smells of synthetic broth and ozone.",
        "safe": "Safe",
        "exit_north": "Main street — busier, more vendors, a public terminal",
        "exit_south": "Deeper alleys — darker, quieter, leads to residential blocks",
        "exit_east": "Mira's Noodle Shop — warm light, a woman watching from the counter",
        "exit_west": "Market square — open area, more people, more noise",
        "poi_mira": "Mira's Noodle Shop (east) — A small, steamy establishment. The owner seems to be watching you.",
        "poi_terminal": "Public Terminal (north, main street) — NEXUS-operated information kiosk. Free access.",
        "poi_repair": "Repair Stall (north) — Sells basic tools and electronics.",
        "npc_mira": "Mira — Behind the counter of her noodle shop. Watching.",
        "npc_pedestrians": "Various unnamed pedestrians.",
        "inventory_title": "Inventory",
        "npcs_title": "Encountered NPCs",
        "world_title": "World State",
        "calm": "Calm",
        "stable": "Stable",
        "open": "Open",
        "locked": "Locked",
        "restricted": "Restricted",
        "hidden": "Hidden",
        "district_sprawl": "The Sprawl",
        "district_neon": "Neon Row",
        "district_undercroft": "The Undercroft",
        "district_sector7": "Sector 7",
        "district_chrome": "Chrome Heights",
        "district_resonance": "The Resonance",
        "district_spire": "The Spire",
        "notes_starting": "Starting area",
        "notes_entertainment": "Entertainment and intel",
        "notes_undercroft": "Underground Listener territory",
        "notes_sector7": "Corporate zone",
        "notes_chrome": "Elite residential area",
        "notes_resonance": "Ancient pre-Severance facility",
        "notes_spire": "NEXUS HQ — endgame content",
        "unlock_layer4": "Requires Layer 4 completion",
        "unlock_trace": "Requires TRACE-L1-03",
        "unlock_keycard": "Requires keycard or disguise",
        "unlock_invitation": "Requires invitation or disguise",
        "unlock_layer3": "Requires Layer 3 completion",
        "log_title": "Session Log",
        "log_awakening": "Awakening",
        "log_awakening_desc": "You wake in a rain-soaked alley in The Sprawl with no memory and a humming neural implant.",
    },
    "zh": {
        "player_title": "玩家状态",
        "active": "激活",
        "none": "无",
        "signal_sensitivity": "信号敏感（微弱）",
        "time_morning": "晨",
        "knowledge_title": "知识库",
        "traces_title": "真相痕迹",
        "layer_1": "表层",
        "layer_2": "阴谋",
        "layer_3": "断离真相",
        "layer_4": "镜像",
        "layer_5": "完整真相",
        "location_title": "当前位置",
        "district": "蔓城",
        "area": "雨巷（米拉面馆附近）",
        "zone": "街道层",
        "location_desc": "破败居民楼之间的一条窄巷。面馆和修理铺的霓虹灯牌将斑斓的光投射在湿漉漉的水泥地上。空气中弥漫着合成高汤和臭氧的气味。",
        "safe": "安全",
        "exit_north": "大街——更繁忙，更多摊贩，有一台公共终端",
        "exit_south": "更深的巷子——更暗，更安静，通往居民区",
        "exit_east": "米拉面馆——温暖的灯光，一个女人在柜台后注视着",
        "exit_west": "集市广场——开阔地带，人更多，噪音更大",
        "poi_mira": "米拉面馆（东）— 一家小而蒸汽弥漫的店铺。老板似乎在注视着你。",
        "poi_terminal": "公共终端（北，大街）— NEXUS运营的信息亭。免费使用。",
        "poi_repair": "修理摊（北）— 出售基础工具和电子器件。",
        "npc_mira": "米拉 — 在面馆柜台后面。注视着。",
        "npc_pedestrians": "各种无名路人。",
        "inventory_title": "物品栏",
        "npcs_title": "已遇NPC",
        "world_title": "世界状态",
        "calm": "平静",
        "stable": "稳定",
        "open": "开放",
        "locked": "封锁",
        "restricted": "限制出入",
        "hidden": "隐藏",
        "district_sprawl": "蔓城",
        "district_neon": "霓虹街",
        "district_undercroft": "底渊",
        "district_sector7": "第七区",
        "district_chrome": "镀金台",
        "district_resonance": "共鸣所",
        "district_spire": "尖塔",
        "notes_starting": "起始区域",
        "notes_entertainment": "娱乐与情报",
        "notes_undercroft": "地下聆听者领地",
        "notes_sector7": "企业区",
        "notes_chrome": "精英住宅区",
        "notes_resonance": "断离前的古老设施",
        "notes_spire": "NEXUS总部——终局内容",
        "unlock_layer4": "需要完成第四层",
        "unlock_trace": "需要TRACE-L1-03",
        "unlock_keycard": "需要门禁卡或伪装",
        "unlock_invitation": "需要邀请函或伪装",
        "unlock_layer3": "需要完成第三层",
        "log_title": "会话日志",
        "log_awakening": "苏醒",
        "log_awakening_desc": "你在蔓城一条被雨水浸透的小巷中醒来，失去了记忆，耳后的神经植入体嗡嗡作响。",
    },
}


def _loc(data: dict, key: str, lang: str):
    """Pick the language-appropriate variant of a field from *data*."""
    if lang == "zh":
        zh_key = f"{key}_zh"
        if zh_key in data:
            return data[zh_key]
    return data[key]


def create_new_session(
    session_dir: str,
    name: str,
    alias: str,
    background: str,
    difficulty: str,
    language: str = "en",
) -> None:
    """Create all session files for a new game from templates.

    *session_dir* is the specific session path, e.g. ``…/session/my_save``.
    Only that subdirectory is (re)created — sibling sessions are untouched.
    All content is written in the language specified by *language* (``"en"``
    or ``"zh"``).
    """
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)
    os.makedirs(session_dir, exist_ok=True)

    bg = BACKGROUNDS[background]
    diff = DIFFICULTIES[difficulty]
    integrity_max = diff["integrity_max"]
    L = _LOCALE.get(language, _LOCALE["en"])

    # player.json
    _write_json(os.path.join(session_dir, "player.json"), {
        "title": L["player_title"],
        "name": name,
        "alias": alias,
        "background": _loc(bg, "display", language),
        "integrity": {"current": integrity_max, "max": integrity_max},
        "credits": 50,
        "neural_implant": L["active"],
        "current_disguise": L["none"],
        "turn": 1,
        "time": L["time_morning"],
        "status_effects": [L["signal_sensitivity"]],
    })

    # knowledge.json
    _write_json(os.path.join(session_dir, "knowledge.json"), {
        "title": L["knowledge_title"],
        "facts": [],
        "rumors": _loc(bg, "starting_rumors", language),
        "evidence": [],
        "theories": [],
        "connections": [],
    })

    # traces.json
    def _undiscovered(trace_id):
        return {"status": "undiscovered", "description": "[???]"}

    _write_json(os.path.join(session_dir, "traces.json"), {
        "title": L["traces_title"],
        "total_discovered": "0 / 16",
        "layers": {
            "layer_1_surface": {
                "name": L["layer_1"],
                "progress": "0/3",
                "traces": {f"TRACE-L1-0{i}": _undiscovered(f"TRACE-L1-0{i}") for i in range(1, 4)},
            },
            "layer_2_conspiracy": {
                "name": L["layer_2"],
                "progress": "0/4",
                "traces": {f"TRACE-L2-0{i}": _undiscovered(f"TRACE-L2-0{i}") for i in range(1, 5)},
            },
            "layer_3_severance_truth": {
                "name": L["layer_3"],
                "progress": "0/4",
                "traces": {f"TRACE-L3-0{i}": _undiscovered(f"TRACE-L3-0{i}") for i in range(1, 5)},
            },
            "layer_4_mirror": {
                "name": L["layer_4"],
                "progress": "0/3",
                "traces": {f"TRACE-L4-0{i}": _undiscovered(f"TRACE-L4-0{i}") for i in range(1, 4)},
            },
            "layer_5_full_truth": {
                "name": L["layer_5"],
                "progress": "0/2",
                "traces": {f"TRACE-L5-0{i}": _undiscovered(f"TRACE-L5-0{i}") for i in range(1, 3)},
            },
        },
    })

    # location.json
    _write_json(os.path.join(session_dir, "location.json"), {
        "title": L["location_title"],
        "district": L["district"],
        "area": L["area"],
        "zone": L["zone"],
        "description": L["location_desc"],
        "signal_strength": "10%",
        "danger_level": L["safe"],
        "nexus_patrol": L["none"],
        "exits": {
            "north": L["exit_north"],
            "south": L["exit_south"],
            "east": L["exit_east"],
            "west": L["exit_west"],
        },
        "points_of_interest": [
            L["poi_mira"],
            L["poi_terminal"],
            L["poi_repair"],
        ],
        "npcs_present": [
            L["npc_mira"],
            L["npc_pedestrians"],
        ],
    })

    # inventory.json
    _write_json(os.path.join(session_dir, "inventory.json"), {
        "title": L["inventory_title"],
        "credits": 50,
        "slots": {"used": 1, "max": 6},
        "items": [_loc(bg, "starting_item", language)],
    })

    # npcs.json
    _write_json(os.path.join(session_dir, "npcs.json"), {
        "title": L["npcs_title"],
        "npcs": [],
    })

    # world_state.json
    _write_json(os.path.join(session_dir, "world_state.json"), {
        "title": L["world_title"],
        "nexus_alert": {"current": 0, "status": L["calm"]},
        "fragment_decay": {"current": 0, "status": L["stable"]},
        "district_access": [
            {"name": L["district_sprawl"], "name_zh": "蔓城", "status": L["open"], "notes": L["notes_starting"]},
            {"name": L["district_neon"], "name_zh": "霓虹街", "status": L["open"], "notes": L["notes_entertainment"]},
        ],
        "_district_registry": {
            "hidden": True,
            "undiscovered": [
                {"name": L["district_undercroft"], "name_zh": "底渊", "status": L["locked"], "unlock": L["unlock_trace"], "notes": L["notes_undercroft"]},
                {"name": L["district_sector7"], "name_zh": "第七区", "status": L["restricted"], "unlock": L["unlock_keycard"], "notes": L["notes_sector7"]},
                {"name": L["district_chrome"], "name_zh": "镀金台", "status": L["restricted"], "unlock": L["unlock_invitation"], "notes": L["notes_chrome"]},
                {"name": L["district_resonance"], "name_zh": "共鸣所", "status": L["hidden"], "unlock": L["unlock_layer3"], "notes": L["notes_resonance"]},
                {"name": L["district_spire"], "name_zh": "尖塔", "status": L["hidden"], "unlock": L["unlock_layer4"], "notes": L["notes_spire"]},
            ],
        },
        "time": {"day": 1, "period": L["time_morning"]},
        "global_events": [],
        "_ending_trajectory": {"hidden": True, "value": "neutral — no direction yet"},
    })

    # log.json
    _write_json(os.path.join(session_dir, "log.json"), {
        "title": L["log_title"],
        "entries": [
            {
                "turn": 1,
                "title": L["log_awakening"],
                "description": L["log_awakening_desc"],
                "signal": True,
            }
        ],
    })

    # session_settings.json — per-session difficulty + language
    _write_json(os.path.join(session_dir, "session_settings.json"), {
        "difficulty": difficulty,
        "language": language,
    })

    # conversation.jsonl (empty)
    open(os.path.join(session_dir, "conversation.jsonl"), "w").close()


def copy_save_to_session(save_dir: str, session_dir: str) -> None:
    """Restore a save into a named session subdirectory.

    *session_dir* is the target path, e.g. ``…/session/my_save``.
    Only that subdirectory is replaced — other active sessions are untouched.
    """
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)
    shutil.copytree(save_dir, session_dir)


def list_active_sessions(sessions_root: str) -> list[dict]:
    """Return metadata for every active session under *sessions_root*.

    Each entry is a dict with keys: name, player_name, alias, turn, background.
    """
    sessions: list[dict] = []
    if not os.path.isdir(sessions_root):
        return sessions
    for entry in sorted(os.listdir(sessions_root)):
        sess_path = os.path.join(sessions_root, entry)
        if not os.path.isdir(sess_path):
            continue
        player = _read_json(os.path.join(sess_path, "player.json"))
        if not player:
            continue
        sessions.append({
            "name": entry,
            "path": sess_path,
            "player_name": player.get("name", "Unknown"),
            "alias": player.get("alias", ""),
            "turn": player.get("turn", "?"),
            "background": player.get("background", "?"),
        })
    return sessions


def save_game_to_slot(session_dir: str, save_name: str, saves_dir: str) -> str:
    """Copy the current session to a named save slot. Returns the save path."""
    dest = os.path.join(saves_dir, save_name)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(session_dir, dest)
    return dest
