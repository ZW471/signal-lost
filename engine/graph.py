"""
Signal Lost — LangGraph StateGraph

The game engine as a LangGraph state machine.

Flow: input_gate → resolver (LLM + tools) → state_writer → location_updater
      → world_ticker → trace_checker → consequence → [END or loop back]
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from engine.state import GameState, append_conversation, empty_turn_delta, reset_turn_flags, save_session_file, load_usage, save_usage
from engine.tools import ALL_TOOLS, set_session_dir, set_current_inventory
from engine.game_data import (
    TRACE_CONDITIONS,
    ENDINGS,
    TIME_PERIODS,
    TURNS_PER_PERIOD,
    _trace_discovered,
    _count_discovered_traces,
    ITEM_SKILL_BONUSES,
    ITEM_SKILL_PENALTIES,
)
from engine.prompts import build_static_prompt, build_dynamic_state_prompt, extract_deepest_layer, build_location_prompt
from engine.reducer import reduce_turn_messages, trim_to_window


# ---------------------------------------------------------------------------
# LLM factory (provider-agnostic)
# ---------------------------------------------------------------------------

_llm_instance = None
_zero_cost: bool = False


def get_llm():
    """Get or create the LLM instance. Configured at runtime via run.py."""
    global _llm_instance
    if _llm_instance is None:
        raise RuntimeError(
            "LLM not configured. Call set_llm() before running the graph."
        )
    return _llm_instance


def set_llm(llm, *, zero_cost: bool = False):
    """Set the LLM instance to use. Called by run.py.

    Set zero_cost=True for providers that should not incur token costs
    (e.g. claude-code CLI, local LM Studio/Ollama).
    """
    global _llm_instance, _zero_cost
    _llm_instance = llm
    _zero_cost = zero_cost


def _extract_usage(response) -> dict:
    """Extract token usage from an LLM response (AIMessage).

    Uses usage_metadata from the LangGraph/LangChain API which contains
    actual token counts reported by the provider. Also extracts the model
    name from response_metadata for accurate cost calculation.
    """
    meta = getattr(response, "usage_metadata", None)
    if not meta or not isinstance(meta, dict):
        return {}
    usage: dict = {
        "input_tokens": meta.get("input_tokens", 0),
        "output_tokens": meta.get("output_tokens", 0),
        "total_tokens": meta.get("total_tokens", 0),
    }
    # Extract cache token details (Anthropic prompt caching)
    details = meta.get("input_token_details") or {}
    if isinstance(details, dict):
        cache_create = details.get("cache_creation", 0)
        cache_read = details.get("cache_read", 0)
        if cache_create or cache_read:
            usage["cache_creation_tokens"] = cache_create
            usage["cache_read_tokens"] = cache_read
    # Extract actual model name from response metadata
    resp_meta = getattr(response, "response_metadata", None)
    if resp_meta and isinstance(resp_meta, dict):
        model = resp_meta.get("model") or resp_meta.get("model_name") or ""
        if model:
            usage["model"] = model
    return usage


_pricing_cache: dict | None = None


def _load_pricing() -> dict:
    """Load model pricing from settings/pricing.json (cached after first load)."""
    global _pricing_cache
    if _pricing_cache is not None:
        return _pricing_cache
    pricing_path = Path(__file__).resolve().parent.parent / "settings" / "pricing.json"
    try:
        with open(pricing_path) as f:
            _pricing_cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _pricing_cache = {"models": {}, "default": [3, 15, 0, 0]}
    return _pricing_cache


def _calculate_cost(usage: dict) -> float:
    """Calculate USD cost from token usage using the model reported by the API.

    Pricing loaded from settings/pricing.json. Matches by longest matching
    key (substring) so 'gpt-5.4-mini' beats 'gpt-5.4' for model 'gpt-5.4-mini-2026-03-17'.
    Returns 0 when zero_cost mode is active (claude-code, local providers).
    """
    if _zero_cost:
        return 0.0
    model = (usage.get("model") or "").lower()
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cache_create = usage.get("cache_creation_tokens", 0)
    cache_read = usage.get("cache_read_tokens", 0)

    pricing = _load_pricing()
    models = pricing.get("models", {})
    default = pricing.get("default", [3, 15, 0, 0])

    # Find the longest matching key in the model name
    best_key, best_len = None, 0
    for key in models:
        if key in model and len(key) > best_len:
            best_key, best_len = key, len(key)

    rates = models[best_key] if best_key else default
    in_rate, out_rate = rates[0], rates[1]
    cw_rate = rates[2] if len(rates) > 2 else 0
    cr_rate = rates[3] if len(rates) > 3 else 0

    # For Anthropic cache pricing, regular input tokens exclude cached tokens
    regular_input = input_tokens - cache_create - cache_read
    if regular_input < 0:
        regular_input = 0

    cost = (
        regular_input * in_rate
        + output_tokens * out_rate
        + cache_create * cw_rate
        + cache_read * cr_rate
    ) / 1_000_000
    return cost


def _accumulate_usage(state: dict, node_name: str, usage: dict) -> dict:
    """Add node usage to the turn_usage accumulator and return updated turn_usage."""
    tu = dict(state.get("turn_usage") or {})
    if not usage:
        return tu
    tu[node_name] = usage
    # Update totals
    tu["input_tokens"] = tu.get("input_tokens", 0) + usage.get("input_tokens", 0)
    tu["output_tokens"] = tu.get("output_tokens", 0) + usage.get("output_tokens", 0)
    tu["total_tokens"] = tu.get("total_tokens", 0) + usage.get("total_tokens", 0)
    tu["calls"] = tu.get("calls", 0) + 1
    # Accumulate cache tokens
    tu["cache_creation_tokens"] = tu.get("cache_creation_tokens", 0) + usage.get("cache_creation_tokens", 0)
    tu["cache_read_tokens"] = tu.get("cache_read_tokens", 0) + usage.get("cache_read_tokens", 0)
    # Track model from latest call for cost calculation
    if usage.get("model"):
        tu["model"] = usage["model"]
    # Calculate cost from actual API-reported usage
    tu["cost"] = tu.get("cost", 0) + _calculate_cost(usage)
    return tu


# ---------------------------------------------------------------------------
# Node: input_gate
# Pure Python. Loads state, builds dynamic prompt, prepares messages.
# ---------------------------------------------------------------------------

def _read_language_setting(session_dir: str) -> str:
    """Read language from the session's own session_settings.json.

    Falls back to the global settings/custom.json (menu language), then 'en'.
    """
    import os as _os
    import json as _json

    # 1) Per-session setting (preferred)
    session_settings_path = _os.path.join(session_dir, "session_settings.json")
    if _os.path.isfile(session_settings_path):
        try:
            with open(session_settings_path, "r", encoding="utf-8") as f:
                data = _json.load(f)
            lang = data.get("language")
            if lang:
                return lang
        except (FileNotFoundError, _json.JSONDecodeError, OSError):
            pass

    # 2) Fallback: global custom.json (for legacy sessions)
    cur = _os.path.abspath(session_dir)
    for _ in range(4):
        candidate = _os.path.join(_os.path.dirname(cur), "settings", "custom.json")
        if _os.path.isfile(candidate):
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    settings = _json.load(f)
                return settings.get("language", {}).get("display", "en")
            except (FileNotFoundError, _json.JSONDecodeError, OSError):
                pass
            break
        cur = _os.path.dirname(cur)

    return "en"


def _get_difficulty_mode(session_dir: str) -> str:
    """Read the difficulty setting from session_settings.json."""
    import os
    path = os.path.join(session_dir, "session_settings.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("difficulty", "standard")
    except (FileNotFoundError, json.JSONDecodeError):
        return "standard"


def input_gate(state: GameState) -> dict:
    """Prepare the LLM context for this turn.

    Manages two separate SystemMessages:
      [0] Static prompt  — behavioral rules + world lore (changes only with layer depth)
      [1] Dynamic state  — live game snapshot (rebuilt every turn)

    Also enforces a 5-turn conversation window by emitting RemoveMessage directives
    for anything older, keeping the in-graph message list compact.
    """
    session_dir = state["session_dir"]

    # Allow recall_conversation tool to read the right session file
    set_session_dir(session_dir)
    # Sync inventory for tool-level item checks (cipher toolkit gating, etc.)
    set_current_inventory(state.get("inventory", {}).get("items", []))

    language = _read_language_setting(session_dir)
    deepest_layer = extract_deepest_layer(state)

    # Build fresh system messages
    static_msg = SystemMessage(content=build_static_prompt(language, deepest_layer))
    dynamic_msg = SystemMessage(content=build_dynamic_state_prompt(state))

    existing = state["messages"]

    # Remove all old SystemMessages (both static and dynamic from previous turns)
    old_sys_removals = [
        RemoveMessage(id=msg.id)
        for msg in existing
        if isinstance(msg, SystemMessage) and msg.id
    ]

    # Trim conversation to the last 5 turns, removing older messages
    _to_keep, to_remove = trim_to_window(existing, max_turns=5)
    old_conv_removals = [
        RemoveMessage(id=msg.id)
        for msg in to_remove
        if msg.id
    ]

    # Reset per-turn flags. skip_validation, skip_conversation_log, and
    # skip_turn_increment are set externally BEFORE graph.invoke() for special
    # turns (resume, system events) — they survive because the caller sets them
    # after input_gate returns. Each consuming node resets its own flag.
    flags = reset_turn_flags()
    # Preserve externally-set skip flags for this invocation
    for key in ("skip_validation", "skip_conversation_log", "skip_turn_increment"):
        if state.get(key):
            flags[key] = state[key]

    return {
        "messages": old_sys_removals + old_conv_removals + [static_msg, dynamic_msg],
        "turn_delta": empty_turn_delta(),
        "narrative": "",
        **flags,
    }


# ---------------------------------------------------------------------------
# Node: resolver
# The single LLM node. Calls the model with tools bound.
# ---------------------------------------------------------------------------

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


def _strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks from local-model output."""
    return _THINK_RE.sub("", text).strip()


def resolver(state: GameState) -> dict:
    """Call the LLM to process the player's action."""
    llm = get_llm()
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    response = llm_with_tools.invoke(state["messages"])

    # Strip thinking tags from local models (e.g. Qwen)
    if isinstance(response.content, str) and "<think>" in response.content:
        response.content = _strip_thinking(response.content)

    usage = _extract_usage(response)
    turn_usage = _accumulate_usage(state, "resolver", usage)
    result = {"messages": [response], "turn_usage": turn_usage}
    # Track tool-call rounds for loop cap (see after_tools)
    if response.tool_calls:
        result["tool_call_rounds"] = state.get("tool_call_rounds", 0) + 1
    return result


# ---------------------------------------------------------------------------
# Node: input_validator
# Checks player input for injection attacks, cheating, or meta-bypass attempts
# before it ever reaches the resolver.  Invalid turns are not logged.
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

# ---------------------------------------------------------------------------
# Movement validation — Python-level district access checks
# ---------------------------------------------------------------------------

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
    re.IGNORECASE
)


def _is_district_accessible(district_name: str, world_state: dict) -> bool:
    """Check if a district is accessible (open or restricted). Locked/Hidden = inaccessible."""
    for entry in world_state.get("district_access", []):
        if district_name.lower() in entry.get("name", "").lower():
            status = entry.get("status", "").lower()
            return status in ("open", "accessible", "restricted", "开放", "限制出入")
    # Check undiscovered registry
    registry = world_state.get("_district_registry", {})
    for entry in registry.get("undiscovered", []):
        if district_name.lower() in entry.get("name", "").lower():
            status = entry.get("status", "").lower()
            return status in ("restricted", "限制出入")
    return False


def _get_district_status(district_name: str, world_state: dict) -> str:
    """Get the access status of a district."""
    for entry in world_state.get("district_access", []):
        if district_name.lower() in entry.get("name", "").lower():
            return entry.get("status", "").lower()
    registry = world_state.get("_district_registry", {})
    for entry in registry.get("undiscovered", []):
        if district_name.lower() in entry.get("name", "").lower():
            return entry.get("status", "").lower()
    return "unknown"


def _check_movement_allowed(content: str, state: dict, language: str = "en") -> str | None:
    """Return a blocking reason if the player tries to move to a restricted/nonexistent district."""
    if not _MOVE_VERBS.search(content):
        return None

    content_lower = content.lower()
    target_district = None
    for pattern, canonical in _DISTRICT_NAMES.items():
        if pattern in content_lower:
            target_district = canonical
            break

    if not target_district:
        return None  # Not moving to a named district — LLM validator handles fabricated places

    # Same district = OK
    location = state.get("location", {})
    current = location.get("district", "")
    if target_district.lower() in current.lower():
        return None

    # Check discovered districts
    world_state = state.get("world_state", {})
    for entry in world_state.get("district_access", []):
        name = entry.get("name", "")
        if target_district.lower() in name.lower():
            status = entry.get("status", "").lower()
            if status in ("open", "accessible", "开放"):
                return None
            elif status in ("restricted", "限制出入"):
                return None  # Allow attempt, resolver will gate it
            elif status in ("locked", "封锁"):
                if language == "zh":
                    return f"前往{target_district}的通道已封锁。你需要先找到进入的方法。"
                return f"Access to {target_district} is locked. You need to discover how to get there first."
            elif status in ("hidden", "隐藏"):
                if language == "zh":
                    return "你还不知道那个地方。"
                return "You don't know about that place yet."

    # Check undiscovered registry
    registry = world_state.get("_district_registry", {})
    for entry in registry.get("undiscovered", []):
        name = entry.get("name", "")
        if target_district.lower() in name.lower():
            status = entry.get("status", "").lower()
            if status in ("hidden", "隐藏"):
                if language == "zh":
                    return "你还不知道那个地方。"
                return "You don't know about that place yet."
            elif status in ("locked", "封锁"):
                if language == "zh":
                    return f"前往{target_district}的通道已封锁。你还没有找到进入的方法。"
                return f"Access to {target_district} is locked. You haven't found a way in yet."
            elif status in ("restricted", "限制出入"):
                return None  # Allow attempt

    return None  # Recognized district but not in any list — allow


_VALIDATOR_SYSTEM_TEMPLATE = """\
You are a strict input validator for "Signal Lost", a text RPG.
Classify the player input as VALID or INVALID based on the rules below AND the current game state.

## INVALID inputs (block these):

### Cheating & Meta-bypass
- Claims to ALREADY POSSESS items/credits/knowledge not earned in-game
- Demands to skip mechanics, jump to endings, reveal hidden content, modify rules

### Fabrication (most important)
- References a PLACE that does not exist in Neo-Kowloon's districts or in the current location's points of interest/exits
  Valid districts: The Sprawl, Neon Row, Chrome Heights, Sector 7, The Undercroft, The Resonance, The Spire
  Valid sub-areas: only those listed in "Current location" below
- References an NPC by name who is NOT in the "Encountered NPCs" list AND is not a plausible unnamed stranger (e.g., "a vendor", "a passerby" are OK; "Marcus the hacker" is not)
- Claims to USE or HAVE an item not listed in "Current inventory" below
- Claims to PRESENT or KNOW information not listed in "Current knowledge" below
- Claims to be in a location they are NOT currently in

### Harmful or off-topic
- Content completely unrelated to the game world

## VALID inputs (always allow):
- Any in-world action using REAL game entities (items, NPCs, places that actually exist)
- Interacting with unnamed/generic characters (vendors, passersby, crowds) — these are fine
- Creative roleplay actions within the current scene (examining objects, listening, hiding)
- Questions about game mechanics or requests for help
- Risky, self-destructive, or foolish actions — let the game engine handle consequences
- Vague movement within the current district (e.g., "I walk down the alley" is fine)

## Current Game State:
{state_context}

Reply in {response_language}.
Reply with ONLY:
VALID
— or —
INVALID: <one-sentence reason explaining what was fabricated or why it's blocked>"""


def _build_validator_context(state: dict) -> str:
    """Build a compact state summary for the input validator LLM."""
    location = state.get("location", {})
    inventory = state.get("inventory", {})
    npcs = state.get("npcs", {})
    knowledge = state.get("knowledge", {})
    world_state = state.get("world_state", {})

    # Current location
    district = location.get("district", "Unknown")
    area = location.get("area", "Unknown")
    exits = location.get("exits", {})
    pois = location.get("points_of_interest", [])
    poi_names = [p.get("name", str(p)) if isinstance(p, dict) else str(p) for p in pois]
    npcs_here = location.get("npcs_present", [])
    npc_here_names = [n.get("name", str(n)) if isinstance(n, dict) else str(n) for n in npcs_here]

    # Inventory
    items = inventory.get("items", [])
    item_names = [i.get("name", i.get("item", "?")) for i in items]
    credits = inventory.get("credits", 0)

    # Encountered NPCs (all ever met)
    encountered = npcs.get("npcs", [])
    enc_names = [n.get("name", "?") for n in encountered]

    # Accessible districts
    accessible = [e.get("name", "?") for e in world_state.get("district_access", [])]

    # Knowledge counts
    n_facts = len(knowledge.get("facts", []))
    n_rumors = len(knowledge.get("rumors", []))
    n_evidence = len(knowledge.get("evidence", []))
    evidence_names = [e.get("name", e.get("id", "?")) for e in knowledge.get("evidence", [])]
    n_theories = len(knowledge.get("theories", []))

    lines = [
        f"Current location: {district} — {area}",
        f"Exits: {', '.join(f'{k}: {v}' for k, v in exits.items()) if exits else 'unknown'}",
        f"Points of interest here: {', '.join(poi_names) if poi_names else 'none listed'}",
        f"NPCs visible here: {', '.join(npc_here_names) if npc_here_names else 'none'}",
        f"Encountered NPCs (all): {', '.join(enc_names) if enc_names else 'none yet'}",
        f"Inventory: {', '.join(item_names) if item_names else 'empty'} | Credits: {credits}",
        f"Accessible districts: {', '.join(accessible) if accessible else 'The Sprawl, Neon Row'}",
        f"Knowledge: {n_facts} facts, {n_rumors} rumors, {n_evidence} evidence, {n_theories} theories",
        f"Evidence items: {', '.join(evidence_names) if evidence_names else 'none'}",
    ]
    return "\n".join(lines)


def input_validator(state: GameState) -> dict:
    """Check player input for injection/cheating before it reaches the resolver.

    Skipped entirely for system-event turns (resume, load recap, etc.) — those are
    injected by the game engine, not typed by the player.
    """
    # System-event turns bypass all validation; reset the flag so it doesn't persist
    if state.get("skip_validation", False):
        return {"input_blocked": False, "blocking_reason": None, "skip_validation": False}

    messages = state["messages"]

    # Find the current HumanMessage (most recent)
    human_msg = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            human_msg = msg
            break

    if not human_msg:
        return {"input_blocked": False, "blocking_reason": None}

    content = str(human_msg.content).strip()

    # Fast regex check — no LLM needed for obvious injection patterns
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(content):
            return {
                "input_blocked": True,
                "blocking_reason": "Input contains instruction-override patterns.",
            }

    # Python movement validation — check district access
    language = _read_language_setting(state["session_dir"])
    movement_block = _check_movement_allowed(content, state, language)
    if movement_block:
        return {"input_blocked": True, "blocking_reason": movement_block}

    # LLM semantic check with full game state context (catches fabrication)
    state_context = _build_validator_context(state)
    response_language = "Chinese (中文)" if language == "zh" else "English"
    validator_prompt = _VALIDATOR_SYSTEM_TEMPLATE.format(
        state_context=state_context, response_language=response_language
    )
    llm = get_llm()
    try:
        response = llm.invoke([
            SystemMessage(content=validator_prompt),
            HumanMessage(content=f"Player input: {content}"),
        ])
        usage = _extract_usage(response)
        turn_usage = _accumulate_usage(state, "input_validator", usage)
        result = response.content.strip()
        if result.upper().startswith("INVALID"):
            colon_idx = result.find(":")
            fallback = "该操作无效。" if language == "zh" else "This action is not valid."
            reason = result[colon_idx + 1:].strip() if colon_idx != -1 else fallback
            return {"input_blocked": True, "blocking_reason": reason, "turn_usage": turn_usage}
    except Exception:
        pass  # Validation failure is non-fatal — let the turn proceed

    return {"input_blocked": False, "blocking_reason": None, "turn_usage": turn_usage if "turn_usage" in locals() else {}}


def input_blocked_handler(state: GameState) -> dict:
    """Emit a warning for blocked input.  Does NOT log to conversation or advance the turn."""
    messages = state["messages"]
    language = _read_language_setting(state["session_dir"])

    # Remove the rejected HumanMessage from graph state so it's not visible next turn
    invalid_human_id = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            invalid_human_id = msg.id
            break

    removals = [RemoveMessage(id=invalid_human_id)] if invalid_human_id else []

    reason = state.get("blocking_reason") or (
        "该操作在本游戏中无效。" if language == "zh" else "That action is not valid in this game."
    )

    # Generate contextual suggestions based on current state
    location = state.get("location", {})
    npcs = state.get("npcs", {})
    district = location.get("district", "蔓城" if language == "zh" else "the district")
    area = location.get("area", "当前位置" if language == "zh" else "your current location")
    present_npcs = [
        name for name, info in npcs.items()
        if isinstance(info, dict) and info.get("location", {}).get("district") == district
        and not info.get("hidden")
    ]

    if language == "zh":
        suggestions = [f"探索 {area}", f"环顾 {district}"]
        if present_npcs:
            suggestions.insert(0, f"与{present_npcs[0]}交谈")
        suggestions.append("查看已知信息")
        warning = (
            f"[系统警告] {reason}\n\n"
            f"你可以尝试：{', '.join(suggestions[:3])}"
        )
    else:
        suggestions = [f"Explore {area}", f"Look around {district}"]
        if present_npcs:
            suggestions.insert(0, f"Talk to {present_npcs[0]}")
        suggestions.append("Check your knowledge")
        warning = (
            f"[System Warning] {reason}\n\n"
            f"Try instead: {', '.join(suggestions[:3])}"
        )

    return {
        "messages": removals,
        "narrative": warning,
        "is_warning": True,
        "input_blocked": False,
        "blocking_reason": None,
        "skip_conversation_log": True,
        "skip_turn_increment": True,
    }


def route_after_validation(state: GameState) -> Literal["resolver", "input_blocked_handler"]:
    """Route to input_blocked_handler if validation failed, else proceed to resolver."""
    if state.get("input_blocked", False):
        return "input_blocked_handler"
    return "resolver"


# ---------------------------------------------------------------------------
# Node: tool_executor
# Executes tool calls from the resolver via LangGraph ToolNode.
# ---------------------------------------------------------------------------

tool_executor = ToolNode(ALL_TOOLS)


# ---------------------------------------------------------------------------
# Routing: should we continue tool calling or move to language checker?
# ---------------------------------------------------------------------------

def should_continue_tools(state: GameState) -> Literal["tool_executor", "output_language_checker"]:
    """Check if the last message has tool calls that need execution."""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tool_executor"
    return "output_language_checker"


_MAX_TOOL_ROUNDS = 4  # Safety cap — prevents unbounded resolver↔tool loops


def after_tools(state: GameState) -> Literal["resolver", "state_writer"]:
    """After tool execution, route back to resolver or proceed if loop cap reached.

    Tools are always executed regardless of the cap — we only stop calling
    the resolver *again*.  This ensures no tool calls are silently dropped.
    """
    rounds = state.get("tool_call_rounds", 0)
    if rounds >= _MAX_TOOL_ROUNDS:
        return "state_writer"
    return "resolver"


# ---------------------------------------------------------------------------
# Node: output_language_checker
# Checks that the LLM narrative and tool arguments are in the configured
# language.  If the language is zh but output is English, injects a
# correction SystemMessage and loops back to resolver (once).
# ---------------------------------------------------------------------------

def _cjk_ratio(text: str) -> float:
    """Return ratio of CJK chars to all alphabetic+CJK chars (0–1)."""
    cjk = sum(
        1 for c in text
        if "\u4e00" <= c <= "\u9fff"
        or "\u3400" <= c <= "\u4dbf"
        or "\uff00" <= c <= "\uffef"
    )
    alpha = sum(1 for c in text if c.isalpha())
    return cjk / alpha if alpha else 1.0


def _is_english(text: str) -> bool:
    """True if the text is primarily English (CJK ratio < 20%)."""
    stripped = text.strip()
    if len(stripped) < 8:          # Too short to judge
        return False
    return _cjk_ratio(stripped) < 0.20


def _find_english_fields(obj, path: str = "") -> list[str]:
    """Recursively scan dict/list and return paths of English string values."""
    problems: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            child = f"{path}.{k}" if path else k
            problems.extend(_find_english_fields(v, child))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            problems.extend(_find_english_fields(v, f"{path}[{i}]"))
    elif isinstance(obj, str) and _is_english(obj):
        snippet = obj[:60] + ("…" if len(obj) > 60 else "")
        problems.append(f'  · {path}: "{snippet}"')
    return problems


def output_language_checker(state: GameState) -> dict:
    """Verify LLM output matches the configured display language.

    Skipped for system-event turns (resume/load) and for any language other
    than 'zh'.  If Chinese is required but the output is in English, a
    correction SystemMessage is injected and the resolver is re-run once.
    The retry counter prevents infinite loops.
    """
    # System-event turns (resume recaps) skip language validation
    if state.get("skip_conversation_log", False):
        return {"language_retry_count": 0}

    session_dir = state["session_dir"]
    language = _read_language_setting(session_dir)

    # Only enforce Chinese — English is always a valid fallback
    if language != "zh":
        return {"language_retry_count": 0}

    # Already retried once — accept output and move on
    retry_count = state.get("language_retry_count", 0)
    if retry_count >= 1:
        return {"language_retry_count": 0}

    messages = state["messages"]
    current_msgs = _current_turn_messages(messages)
    problems: list[str] = []

    # 1. Check narrative (last AI message without tool calls)
    for msg in reversed(current_msgs):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            if _is_english(str(msg.content)):
                snippet = str(msg.content)[:80] + "…"
                problems.append(f'  · narrative: "{snippet}"')
            break

    # 2. Check tool call arguments for text fields
    for msg in current_msgs:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                args = tc.get("args", {})
                problems.extend(_find_english_fields(args, tc.get("name", "tool")))

    if not problems:
        return {"language_retry_count": 0}

    # Build correction message with specific problems listed
    problem_text = "\n".join(problems)
    correction = SystemMessage(content=(
        "[语言校正 / LANGUAGE CORRECTION]\n"
        "游戏语言设置为简体中文，但你的上一条回复包含了英文内容。\n"
        "The game language is set to 简体中文 (Simplified Chinese), "
        "but your previous response contained English where Chinese was required.\n\n"
        f"检测到的问题 / Problems detected:\n{problem_text}\n\n"
        "请用中文重新生成完整回复。规则：\n"
        "Please regenerate your entire response in Chinese. Rules:\n"
        "- 叙事文本、状态效果名称与强度、日志标题、世界事件、NPC 对话必须用中文\n"
        "  (Narrative, status effect names/intensities, log titles, world events, "
        "NPC dialogue must be in Chinese)\n"
        "- 专有名词可保留英文：NEXUS、Signal、Netrunner、district 名称等\n"
        "  (Proper nouns may stay in English: NEXUS, Signal, Netrunner, district names, etc.)\n"
        "- 工具命令保持英文：dice、cipher、signal、glitch\n"
        "  (Tool commands stay in English: dice, cipher, signal, glitch)"
    ))

    return {
        "messages": [correction],
        "language_retry_count": 1,
    }


def route_after_language_check(state: GameState) -> Literal["resolver", "state_writer"]:
    """Route to resolver for a retry, or proceed to state_writer."""
    if state.get("language_retry_count", 0) >= 1:
        return "resolver"
    return "state_writer"


# ---------------------------------------------------------------------------
# Node: state_writer
# Pure Python. Applies state mutations from tool call results to game state.
# ---------------------------------------------------------------------------

def _current_turn_messages(messages: list) -> list:
    """Return only messages from the current turn (after the last HumanMessage).

    This prevents reprocessing ToolMessages from previous turns that are
    still in state due to the add_messages reducer accumulating messages.
    """
    # Find the index of the last HumanMessage — that's where the current turn starts
    last_human_idx = -1
    for i, msg in enumerate(messages):
        if isinstance(msg, HumanMessage):
            last_human_idx = i
    if last_human_idx < 0:
        return messages
    return messages[last_human_idx:]


def state_writer(state: GameState) -> dict:
    """Process tool results and apply state changes to session files."""
    session_dir = state["session_dir"]
    player = copy.deepcopy(state["player"])
    knowledge = copy.deepcopy(state["knowledge"])
    traces = copy.deepcopy(state["traces"])
    location = copy.deepcopy(state["location"])
    inventory = copy.deepcopy(state["inventory"])
    npcs = copy.deepcopy(state["npcs"])
    world_state = copy.deepcopy(state["world_state"])
    log = copy.deepcopy(state["log"])

    # Only process messages from the current turn to avoid
    # reprocessing old ToolMessages that accumulate in state.
    current_msgs = _current_turn_messages(state["messages"])

    # Extract narrative from the last AI message (current turn only)
    narrative = ""
    for msg in reversed(current_msgs):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            narrative = msg.content
            break

    # Process tool results for state mutations (current turn only)
    for msg in current_msgs:
        if not isinstance(msg, ToolMessage):
            continue

        try:
            result = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
        except (json.JSONDecodeError, TypeError):
            continue

        if not isinstance(result, dict) or "type" not in result:
            continue

        mutation_type = result["type"]

        if mutation_type == "update_player":
            changes = result.get("changes", {})
            for k, v in changes.items():
                if k in ("turn", "time"):
                    continue  # Handled by world_ticker
                if k == "integrity":
                    # Always preserve integrity as {"current": N, "max": N}
                    existing = player.get("integrity", {})
                    if not isinstance(existing, dict):
                        existing = {"current": existing, "max": existing}
                    if isinstance(v, dict):
                        player["integrity"] = {
                            "current": v.get("current", existing.get("current", 1)),
                            "max": v.get("max", existing.get("max", existing.get("current", 1))),
                        }
                    else:
                        # LLM sent a bare integer — update current, preserve max
                        player["integrity"] = {
                            "current": int(v),
                            "max": existing.get("max", int(v)),
                        }
                else:
                    player[k] = v

        elif mutation_type == "add_knowledge":
            entry_type = result.get("entry_type", "")
            entry = result.get("entry", {})
            entry["turn"] = player.get("turn", 1)
            # Add hidden layer tag
            layer_val = entry.pop("_layer_value", 1)
            entry["_layer"] = {"hidden": True, "value": layer_val}

            type_map = {
                "fact": "facts",
                "rumor": "rumors",
                "evidence": "evidence",
                "theory": "theories",
                "connection": "connections",
            }
            key = type_map.get(entry_type, entry_type + "s")
            if key not in knowledge:
                knowledge[key] = []
            # Skip if an entry with the same ID already exists
            entry_id = entry.get("id") or entry.get("statement", "")
            existing_ids = {
                e.get("id") or e.get("statement", "")
                for e in knowledge[key]
            }
            if entry_id and entry_id in existing_ids:
                pass  # Duplicate — skip
            else:
                knowledge[key].append(entry)

        elif mutation_type == "update_npc":
            npc_name = result.get("name", "")
            changes = result.get("changes", {})
            npc_list = npcs.get("npcs", [])
            found = False
            for npc in npc_list:
                if npc.get("name", "").lower() == npc_name.lower():
                    npc.update(changes)
                    # Track the turn of last player↔NPC interaction for world_simulator
                    npc["last_interaction_turn"] = player.get("turn", 1)
                    found = True
                    break
            if not found:
                new_npc = {"name": npc_name, "last_interaction_turn": player.get("turn", 1)}
                new_npc.update(changes)
                npc_list.append(new_npc)
                npcs["npcs"] = npc_list

        elif mutation_type == "update_location":
            new_loc = result.get("data", {})
            new_district = new_loc.get("district", "")

            # Validate district access before applying
            if new_district and not _is_district_accessible(new_district, world_state):
                continue  # Reject move to locked/hidden district

            # Sector 7 break-in consequence (restricted, not open)
            if "sector 7" in new_district.lower():
                has_keycard = any(
                    "keycard" in (i.get("name", "") + i.get("item", "")).lower()
                    for i in inventory.get("items", [])
                )
                access_status = _get_district_status("Sector 7", world_state)
                if access_status in ("restricted", "限制出入") and not has_keycard:
                    # Caught! Apply immediate consequences
                    alert = world_state.get("nexus_alert", {})
                    alert["current"] = min(100, alert.get("current", 0) + 20)
                    world_state["nexus_alert"] = alert
                    integrity = player.get("integrity", {})
                    if isinstance(integrity, dict):
                        integrity["current"] = max(0, integrity.get("current", 1) - 1)
                    # Force relocation back
                    new_loc = {"district": "The Sprawl", "area": "Rain Alley (detained)"}

            # The Spire break-in consequence (even harsher)
            if "spire" in new_district.lower():
                access_status = _get_district_status("The Spire", world_state)
                if access_status in ("hidden", "locked", "隐藏", "封锁"):
                    alert = world_state.get("nexus_alert", {})
                    alert["current"] = min(100, alert.get("current", 0) + 30)
                    world_state["nexus_alert"] = alert
                    integrity = player.get("integrity", {})
                    if isinstance(integrity, dict):
                        integrity["current"] = max(0, integrity.get("current", 1) - 2)
                    new_loc = {"district": "The Sprawl", "area": "Rain Alley (detained)"}

            # Merge into existing location — preserve fields the LLM didn't resend
            location.update(new_loc)

        elif mutation_type == "update_inventory":
            action = result.get("action", "")
            if action == "add":
                item = result.get("item", {})
                items = inventory.get("items", [])
                items.append(item)
                inventory["items"] = items
                inventory["slots"] = inventory.get("slots", {})
                inventory["slots"]["used"] = len(items)
            elif action == "remove":
                item_spec = result.get("item", {})
                items = inventory.get("items", [])
                # Remove by slot or name
                slot = item_spec.get("slot")
                name = item_spec.get("name", "")
                inventory["items"] = [
                    i for i in items
                    if not (
                        (slot and i.get("slot") == slot)
                        or (name and name.lower() in (i.get("name", "") + i.get("item", "")).lower())
                    )
                ]
                inventory["slots"] = inventory.get("slots", {})
                inventory["slots"]["used"] = len(inventory["items"])
            elif action == "update_credits":
                amount = result.get("amount", 0)
                inventory["credits"] = inventory.get("credits", 0) + amount
                player["credits"] = inventory["credits"]
            elif action == "sell":
                item_spec = result.get("item", {})
                credits_gained = result.get("credits_gained", 0)
                items = inventory.get("items", [])
                name = item_spec.get("name", "")
                # Check if the item is broken — broken items cannot be sold
                target_item = None
                for i in items:
                    item_name = (i.get("name", "") + i.get("item", "")).lower()
                    if name and name.lower() in item_name:
                        target_item = i
                        break
                if target_item and (target_item.get("condition") == "broken" or target_item.get("broken")):
                    pass  # Broken items cannot be sold, only discarded — skip
                elif target_item:
                    # Remove item and add credits
                    inventory["items"] = [i for i in items if i is not target_item]
                    inventory["slots"] = inventory.get("slots", {})
                    inventory["slots"]["used"] = len(inventory["items"])
                    inventory["credits"] = inventory.get("credits", 0) + credits_gained
                    player["credits"] = inventory["credits"]

        elif mutation_type == "update_world_state":
            changes = result.get("changes", {})
            if "nexus_alert_delta" in changes:
                alert = world_state.get("nexus_alert", {})
                if isinstance(alert, dict):
                    current = alert.get("current", 0)
                    alert["current"] = max(0, min(100, current + changes["nexus_alert_delta"]))
                    # Update status text (en + zh)
                    val = alert["current"]
                    if val <= 20:
                        alert["status"], alert["status_zh"] = "Calm", "平静"
                    elif val <= 40:
                        alert["status"], alert["status_zh"] = "Watchful", "警觉"
                    elif val <= 60:
                        alert["status"], alert["status_zh"] = "Alert", "戒备"
                    elif val <= 80:
                        alert["status"], alert["status_zh"] = "Manhunt", "追捕"
                    else:
                        alert["status"], alert["status_zh"] = "Lockdown", "戒严"
                    world_state["nexus_alert"] = alert

            if "fragment_decay_delta" in changes:
                decay = world_state.get("fragment_decay", {})
                if isinstance(decay, dict):
                    current = decay.get("current", 0)
                    decay["current"] = max(0, min(100, current + changes["fragment_decay_delta"]))
                    val = decay["current"]
                    if val < 25:
                        decay["status"], decay["status_zh"] = "Stable", "稳定"
                    elif val < 50:
                        decay["status"], decay["status_zh"] = "Fading", "消散"
                    elif val < 75:
                        decay["status"], decay["status_zh"] = "Critical", "危机"
                    else:
                        decay["status"], decay["status_zh"] = "Terminal", "终末"
                    world_state["fragment_decay"] = decay

            if "discover_district" in changes:
                district_name = changes["discover_district"]
                registry = world_state.get("_district_registry", {})
                undiscovered = registry.get("undiscovered", [])
                for i, d in enumerate(undiscovered):
                    if d.get("name") == district_name:
                        visible_entry = {
                            "name": d["name"],
                            "name_zh": d.get("name_zh", ""),
                            "status": d.get("status", "Open"),
                        }
                        if "notes" in d:
                            visible_entry["notes"] = d["notes"]
                        access = world_state.get("district_access", [])
                        access.append(visible_entry)
                        world_state["district_access"] = access
                        undiscovered.pop(i)
                        break

            if "add_event" in changes:
                events = world_state.get("global_events", [])
                events.append(changes["add_event"])
                world_state["global_events"] = events

        elif mutation_type == "add_log_entry":
            entries = log.get("entries", [])
            new_entry = {
                "turn": player.get("turn", 1),
                "title": result.get("title", "Event"),
                "tag": result.get("tag", "system"),
                "text": result.get("text", ""),
            }
            # Skip if an entry with the same title+text already exists this turn
            is_dup = any(
                e.get("title") == new_entry["title"] and e.get("text") == new_entry["text"]
                for e in entries
            )
            if not is_dup:
                entries.append(new_entry)
            # Keep max 30 entries
            if len(entries) > 30:
                entries = entries[-30:]
            log["entries"] = entries

    # ------------------------------------------------------------------
    # Post-mutation enforcement: integrity costs and item skill modifiers
    # These scan raw tool results (not state mutations) for special fields.
    # ------------------------------------------------------------------
    caught_messages: list[str] = []  # collect system messages to inject
    difficulty = _get_difficulty_mode(session_dir)

    for msg in current_msgs:
        if not isinstance(msg, ToolMessage):
            continue
        try:
            tresult = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(tresult, dict):
            continue

        # Gap 1: Deep resonance integrity cost
        icost = tresult.get("integrity_cost")
        if icost and isinstance(icost, (int, float)) and icost > 0:
            integrity = player.get("integrity", {})
            if isinstance(integrity, dict):
                old_val = integrity.get("current", 1)
                integrity["current"] = max(0, old_val - int(icost))
                player["integrity"] = integrity
                caught_messages.append(
                    f"[SYSTEM: Deep resonance cost {int(icost)} Integrity. "
                    f"Current: {integrity['current']}/{integrity.get('max', old_val)}]"
                )

        # Gap 2: Item skill modifier notifications
        skill_type = tresult.get("skill_type")
        if skill_type and difficulty != "paranoid":
            items = inventory.get("items", [])
            for skey, sdata in ITEM_SKILL_BONUSES.items():
                if skey != skill_type:
                    continue
                kw = sdata.get("item_keyword", "")
                has_it = any(
                    kw in (i.get("name", "") + " " + i.get("item", "") + " " + i.get("type", "")).lower()
                    for i in items
                )
                if not has_it and skill_type in ITEM_SKILL_PENALTIES:
                    pen = ITEM_SKILL_PENALTIES[skill_type]
                    caught_messages.append(
                        f"[SYSTEM: {pen['description']}]"
                    )

    # Write changed files
    save_session_file(session_dir, "player", player)
    save_session_file(session_dir, "knowledge", knowledge)
    save_session_file(session_dir, "location", location)
    save_session_file(session_dir, "inventory", inventory)
    save_session_file(session_dir, "npcs", npcs)
    save_session_file(session_dir, "world_state", world_state)
    save_session_file(session_dir, "log", log)

    # Log conversation (skip for resume/load recaps and system events)
    # Triple guard: flag check + skip_validation check + content pattern check
    is_system_turn = (
        state.get("skip_conversation_log", False)
        or state.get("skip_validation", False)
    )
    # Content-based guard: detect resume/system prompts that should never be logged
    _SYSTEM_CONTENT_MARKERS = ("[RESUMING SESSION]", "[LOADING SAVE]", "[SYSTEM EVENT]", "[SYSTEM: Session resumed")
    for msg in current_msgs:
        if isinstance(msg, HumanMessage):
            content_str = str(msg.content)
            if any(marker in content_str for marker in _SYSTEM_CONTENT_MARKERS):
                is_system_turn = True
                break

    # Save cumulative usage stats
    turn_usage = state.get("turn_usage") or {}
    if turn_usage and turn_usage.get("calls"):
        cumulative = load_usage(session_dir)
        cumulative["total_calls"] = cumulative.get("total_calls", 0) + turn_usage.get("calls", 0)
        cumulative["input_tokens"] = cumulative.get("input_tokens", 0) + turn_usage.get("input_tokens", 0)
        cumulative["output_tokens"] = cumulative.get("output_tokens", 0) + turn_usage.get("output_tokens", 0)
        cumulative["total_tokens"] = cumulative.get("total_tokens", 0) + turn_usage.get("total_tokens", 0)
        cumulative["cost"] = cumulative.get("cost", 0) + turn_usage.get("cost", 0)
        if turn_usage.get("model"):
            cumulative["model"] = turn_usage["model"]
        save_usage(session_dir, cumulative)

    if not is_system_turn:
        turn = player.get("turn", 1)
        # Build compact turn token summary for conversation log
        turn_tokens = None
        if turn_usage and turn_usage.get("total_tokens"):
            turn_tokens = {
                "input": turn_usage.get("input_tokens", 0),
                "output": turn_usage.get("output_tokens", 0),
                "total": turn_usage.get("total_tokens", 0),
                "cost": round(turn_usage.get("cost", 0), 6),
            }
        for msg in current_msgs:
            if isinstance(msg, HumanMessage):
                append_conversation(session_dir, "user", str(msg.content), turn)
        if narrative:
            append_conversation(session_dir, "assistant", narrative, turn, tokens=turn_tokens)

    # Build removal list for processed tool messages to prevent reprocessing.
    # The add_messages reducer accumulates messages — returning a subset does
    # NOT remove old ones.  We must emit explicit RemoveMessage directives.
    removals: list = []
    for msg in current_msgs:
        if isinstance(msg, ToolMessage):
            removals.append(RemoveMessage(id=msg.id))
        elif isinstance(msg, AIMessage) and msg.tool_calls:
            removals.append(RemoveMessage(id=msg.id))

    # System-event turns (resume, load recap, etc.) are ephemeral — remove their
    # HumanMessage and final AI response from graph state after display so they
    # never appear in the 5-turn history window.
    is_system_event = state.get("skip_conversation_log", False)
    if is_system_event:
        for msg in current_msgs:
            if isinstance(msg, HumanMessage) and msg.id:
                removals.append(RemoveMessage(id=msg.id))
        # Also remove the recap AIMessage (the response to the system event)
        for msg in reversed(current_msgs):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls and msg.id:
                removals.append(RemoveMessage(id=msg.id))
                break

    # Keep a compact summary of what happened + the final narrative.
    # For system-event turns there is nothing to summarise — skip the tool recap injection.
    reduced_new: list = []
    if not is_system_event:
        tool_summary = reduce_turn_messages(current_msgs)
        # From the reduced set, only keep the SystemMessage summary (tool recap)
        # The HumanMessage and final AIMessage are already in state from earlier nodes
        for msg in tool_summary:
            if isinstance(msg, SystemMessage) and "[Turn mechanics:" in str(msg.content):
                reduced_new.append(msg)

    # Inject enforcement system messages (integrity costs, item penalties)
    if caught_messages:
        for cmsg in caught_messages:
            reduced_new.append(SystemMessage(content=cmsg))
            if narrative:
                narrative = narrative + "\n" + cmsg

    return {
        "player": player,
        "knowledge": knowledge,
        "traces": traces,
        "location": location,
        "inventory": inventory,
        "npcs": npcs,
        "world_state": world_state,
        "log": log,
        "narrative": narrative,
        "messages": removals + reduced_new,
        "skip_conversation_log": False,
    }


# ---------------------------------------------------------------------------
# Node: location_updater
# LLM node. Regenerates location description/exits/POIs/NPCs when the
# player moves. Conditioned on player knowledge and trace depth.
# Non-fatal — if this fails the game continues with stale descriptions.
# ---------------------------------------------------------------------------

def _location_changed_this_turn(state: GameState) -> bool:
    """Check if the resolver called update_location this turn."""
    current_msgs = _current_turn_messages(state["messages"])
    for msg in current_msgs:
        if not isinstance(msg, ToolMessage):
            continue
        try:
            result = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(result, dict) and result.get("type") == "update_location":
            return True
    return False


def location_updater(state: GameState) -> dict:
    """Regenerate location descriptions when the player moves.

    Calls the LLM with a focused prompt to generate description, exits,
    points_of_interest, and npcs_present based on the player's current
    knowledge and trace depth. Only runs when update_location was called
    this turn.
    """
    # Only regenerate if location actually changed this turn
    if not _location_changed_this_turn(state):
        return {}

    location = copy.deepcopy(state["location"])
    session_dir = state["session_dir"]

    # Build the prompt with knowledge context
    prompt_text = build_location_prompt(state)

    language = _read_language_setting(session_dir)
    if language == "zh":
        prompt_text += (
            "\n\n## LANGUAGE\n所有输出必须使用简体中文。"
            "地区名可用英文或中文均可，但description、exits、"
            "points_of_interest、npcs_present内容必须是中文。"
        )

    llm = get_llm()
    try:
        response = llm.invoke([
            SystemMessage(content=prompt_text),
            HumanMessage(content=f"Generate location details for: "
                         f"{location.get('district', '?')} — {location.get('area', '?')}"),
        ])
        usage = _extract_usage(response)
        turn_usage = _accumulate_usage(state, "location_updater", usage)
        raw = response.content.strip()

        # Strip thinking tags from local models
        if "<think>" in raw:
            raw = _strip_thinking(raw)

        # Strip markdown fences
        if "```" in raw:
            raw = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()

        data = json.loads(raw)

        # Merge only the descriptive fields — don't overwrite district/area
        for key in ("description", "exits", "points_of_interest", "npcs_present"):
            if key in data:
                location[key] = data[key]

        # Persist to disk
        save_session_file(session_dir, "location.json", location)

        return {"location": location, "turn_usage": turn_usage}

    except Exception:
        # Non-fatal — game continues with existing descriptions
        return {}


# ---------------------------------------------------------------------------
# Node: world_ticker
# Pure Python. Advances turn, time, alert decay, fragment decay.
# ---------------------------------------------------------------------------

def world_ticker(state: GameState) -> dict:
    """Advance world state: turn counter, time, passive alert/decay changes."""
    player = copy.deepcopy(state["player"])
    world_state = copy.deepcopy(state["world_state"])
    session_dir = state["session_dir"]

    # Skip turn increment on resume/load (no real player action taken)
    if state.get("skip_turn_increment", False):
        save_session_file(session_dir, "player", player)
        save_session_file(session_dir, "world_state", world_state)
        return {"player": player, "world_state": world_state, "skip_turn_increment": False}

    # Increment turn
    turn = player.get("turn", 1)
    player["turn"] = turn + 1

    # Advance time every TURNS_PER_PERIOD turns
    if turn % TURNS_PER_PERIOD == 0:
        from engine.game_data import TIME_PERIODS_ZH
        language = _read_language_setting(session_dir)
        current_time = player.get("time", "Morning")
        # Match against both EN and ZH time periods to find current index
        _all_periods = list(zip(TIME_PERIODS, TIME_PERIODS_ZH))
        for i, (en_period, zh_period) in enumerate(_all_periods):
            if en_period.lower() in current_time.lower() or zh_period in current_time:
                next_idx = (i + 1) % len(TIME_PERIODS)
                # Set time in the active language
                if language == "zh":
                    player["time"] = TIME_PERIODS_ZH[next_idx]
                else:
                    player["time"] = TIME_PERIODS[next_idx]

                # Update world_state time (keep all fields in sync)
                time_data = world_state.get("time", {})
                if language == "zh":
                    time_data["period"] = TIME_PERIODS_ZH[next_idx]
                else:
                    time_data["period"] = TIME_PERIODS[next_idx]
                if next_idx == 0:  # New day
                    time_data["day"] = time_data.get("day", 1) + 1
                world_state["time"] = time_data
                break

    # Passive NEXUS alert decay (-1% per day cycle = every 9 turns)
    if turn % 9 == 0:
        alert = world_state.get("nexus_alert", {})
        if isinstance(alert, dict):
            alert["current"] = max(0, alert.get("current", 0) - 1)
            world_state["nexus_alert"] = alert

    save_session_file(session_dir, "player", player)
    save_session_file(session_dir, "world_state", world_state)

    return {
        "player": player,
        "world_state": world_state,
    }


# ---------------------------------------------------------------------------
# Node: world_simulator
# Lightweight LLM call (no tools) that simulates autonomous NPC and world
# actions after each player turn.  NPCs may follow up on ignored messages,
# relocate, express emotional states, or trigger off-screen world events —
# entirely independent of the player.
# ---------------------------------------------------------------------------

_WORLD_SIM_SYSTEM = """\
You are the autonomous world simulation engine for Signal Lost (信号遗失).

After each player turn, decide what NPCs and the world do on their own — \
independent of the player. You have full freedom to move NPCs, change their \
mood, make them act on their own agenda, or generate world events.

## NPC Behaviour Guidelines
- NPCs with `turns_since_interaction >= 3` may send a follow-up, grow impatient, \
  leave, or act on their own (their patience wears thin).
- NPCs in OTHER districts still live their lives: they run errands, cut deals, \
  get arrested, go into hiding, move to a new area, etc.
- NPCs loyal to NEXUS may quietly tip off patrols when suspicious.
- Only simulate NPCs who would realistically DO something this turn. \
  Do NOT simulate every NPC every turn — be selective and realistic.

## World Events
- NEXUS patrols may increase/decrease based on world state.
- Shops/services may open or close.
- A rumour may spread.  A contact may get burned.  A district may lock down.
- These happen regardless of the player and may be invisible to them.

## Output Rules
- Return ONLY valid JSON — no prose outside the JSON block.
- `visible_to_player`: true only if the player would directly observe or \
  receive this (they're in the same area, get a message, hear about it nearby).
- `player_text`: what the player perceives (null if not visible).  \
  Written in second-person present tense, atmospheric, 1-3 sentences max.
- `npc_updates`: partial dict to merge into the NPC record \
  (e.g. location, status, mood, last_action).  Omit unchanged fields.
- `world_updates.nexus_alert_delta`: integer to add to NEXUS alert (can be negative).
- `world_updates.add_event`: short string to append to global_events (or null).
- Return `{"events": []}` if nothing notable happens this turn.

## Economy Events
- If the player recently sold knowledge to a faction, that faction may ACT on it:
  NEXUS may raid a location the player told them about. Listeners may move to protect
  someone the player warned them about. These downstream consequences create narrative weight.
- NPCs who learned the player sells information may approach with offers — or stop trusting them.

JSON schema:
{
  "events": [
    {
      "npc_name": "<string or null for pure world event>",
      "action_type": "message|move|mood_shift|world_event|disappear|followup",
      "visible_to_player": <bool>,
      "player_text": "<string or null>",
      "npc_updates": {},
      "world_updates": {"nexus_alert_delta": 0, "add_event": null}
    }
  ]
}
"""


def world_simulator(state: GameState) -> dict:
    """Simulate autonomous NPC and world actions after the player's turn.

    Runs a lightweight LLM call (no tools) to decide what NPCs do on their
    own: follow-ups, location moves, mood shifts, off-screen world impacts.
    Visible events are appended to the turn's narrative.
    """
    player = state["player"]
    npcs = copy.deepcopy(state["npcs"])
    world_state = copy.deepcopy(state["world_state"])
    location = state["location"]
    session_dir = state["session_dir"]

    npc_list = npcs.get("npcs", [])
    current_turn = player.get("turn", 1)

    # Skip if no NPCs have been encountered yet — nothing to simulate
    if not npc_list:
        return {}

    # Build a lean context snapshot for the LLM
    context = {
        "current_turn": current_turn,
        "time_of_day": player.get("time", "Unknown"),
        "nexus_alert": world_state.get("nexus_alert", {}),
        "player_location": {
            "district": location.get("district", ""),
            "area": location.get("area", ""),
        },
        "npcs": [
            {
                "name": npc.get("name", ""),
                "location": npc.get("location", "unknown"),
                "status": npc.get("status", "unknown"),
                "mood": npc.get("mood", "neutral"),
                "trust": npc.get("trust", "neutral"),
                "role": npc.get("role", ""),
                "last_interaction_turn": npc.get("last_interaction_turn", 0),
                "turns_since_interaction": current_turn - npc.get("last_interaction_turn", 0),
                "last_action": npc.get("last_action", ""),
                "notes": npc.get("notes", ""),
            }
            for npc in npc_list
        ],
        "recent_world_events": world_state.get("global_events", [])[-3:],
    }

    language = _read_language_setting(session_dir)
    lang_note = (
        "\n\n## LANGUAGE\nAll player_text and add_event strings MUST be written in "
        "简体中文 (Simplified Chinese). Proper nouns (NEXUS, Signal, district names) may "
        "remain in English. Everything else must be Chinese."
        if language == "zh" else ""
    )

    llm = get_llm()
    try:
        response = llm.invoke([
            SystemMessage(content=_WORLD_SIM_SYSTEM + lang_note),
            HumanMessage(content=json.dumps(context, ensure_ascii=False)),
        ])
        usage = _extract_usage(response)
        turn_usage = _accumulate_usage(state, "world_simulator", usage)
        raw = response.content.strip()

        # Strip thinking tags from local models
        if "<think>" in raw:
            raw = _strip_thinking(raw)

        # Strip markdown fences if present
        if "```" in raw:
            raw = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()

        data = json.loads(raw)
        events = data.get("events", [])
    except Exception:
        return {}  # World simulation failure is always non-fatal

    if not events:
        return {}

    # Apply events to NPC and world state
    npc_map = {npc.get("name", "").lower(): npc for npc in npc_list}
    player_visible_texts: list[str] = []

    for event in events:
        npc_name = event.get("npc_name")
        visible = event.get("visible_to_player", False)
        player_text = event.get("player_text")
        npc_updates = event.get("npc_updates") or {}
        world_updates = event.get("world_updates") or {}

        # Merge NPC updates
        if npc_name:
            key = npc_name.lower()
            if key in npc_map:
                npc_map[key].update(npc_updates)
                npc_map[key]["last_world_sim_turn"] = current_turn

        # Apply NEXUS alert delta
        delta = world_updates.get("nexus_alert_delta", 0)
        if delta:
            alert = world_state.get("nexus_alert", {})
            if isinstance(alert, dict):
                alert["current"] = max(0, min(100, alert.get("current", 0) + delta))
                val = alert["current"]
                if val <= 20:
                    alert["status"], alert["status_zh"] = "Calm", "平静"
                elif val <= 40:
                    alert["status"], alert["status_zh"] = "Watchful", "警觉"
                elif val <= 60:
                    alert["status"], alert["status_zh"] = "Alert", "戒备"
                elif val <= 80:
                    alert["status"], alert["status_zh"] = "Manhunt", "追捕"
                else:
                    alert["status"], alert["status_zh"] = "Lockdown", "戒严"
                world_state["nexus_alert"] = alert

        # Append world event string
        world_event_str = world_updates.get("add_event")
        if world_event_str:
            events_list = world_state.get("global_events", [])
            events_list.append(world_event_str)
            world_state["global_events"] = events_list

        # Collect player-visible text
        if visible and player_text:
            player_visible_texts.append(player_text)

    # Rebuild NPC list preserving order
    npcs["npcs"] = list(npc_map.values())

    # Persist changed files
    save_session_file(session_dir, "npcs", npcs)
    save_session_file(session_dir, "world_state", world_state)

    result: dict = {"npcs": npcs, "world_state": world_state,
                    "turn_usage": turn_usage if "turn_usage" in locals() else {}}

    # Append visible world events to the turn narrative
    if player_visible_texts:
        existing_narrative = state.get("narrative", "")
        world_section = "\n\n".join(player_visible_texts)
        result["narrative"] = (
            existing_narrative + "\n\n---\n" + world_section
            if existing_narrative
            else world_section
        )

    return result


# ---------------------------------------------------------------------------
# Node: trace_checker
# Pure Python. THE KEY WIN — deterministic trace checking that never forgets.
# ---------------------------------------------------------------------------

def trace_checker(state: GameState) -> dict:
    """Check all trace conditions against current knowledge. Always runs."""
    traces = copy.deepcopy(state["traces"])
    knowledge = state["knowledge"]
    npcs = state["npcs"]
    player = state["player"]
    world_state = state["world_state"]
    session_dir = state["session_dir"]
    language = _read_language_setting(session_dir)

    # Load difficulty for trace condition overrides
    from engine.game_data import TRACE_DIFFICULTY_OVERRIDES
    difficulty = _get_difficulty_mode(session_dir)
    overrides = TRACE_DIFFICULTY_OVERRIDES.get(difficulty, {})

    new_discoveries = []

    for tc in TRACE_CONDITIONS:
        trace_id = tc["id"]
        if _trace_discovered(traces, trace_id):
            continue

        try:
            checker = overrides.get(trace_id, tc["check"])
            if checker(knowledge, traces, npcs, player, world_state):
                from engine.game_data import get_localized
                discovery = {
                    "id": trace_id,
                    "description": get_localized(tc, "description", language),
                    "turn": player.get("turn", 1),
                }
                if "discovered" not in traces:
                    traces["discovered"] = []
                traces["discovered"].append(discovery)
                new_discoveries.append(trace_id)

                # Update deepest layer in gate system
                gate = traces.get("_gate_system", {})
                if gate:
                    gate["deepest_layer"] = max(
                        gate.get("deepest_layer", 0), tc["layer"]
                    )
        except Exception:
            # Don't let a bad checker crash the game
            pass

    result = {"traces": traces, "discovery_notifications": []}

    if new_discoveries:
        save_session_file(session_dir, "traces", traces)
        # Build discovery notifications for GUI
        _LAYER_NAMES = {
            1: {"en": "The Surface", "zh": "表层"},
            2: {"en": "The Conspiracy", "zh": "阴谋"},
            3: {"en": "The Severance Truth", "zh": "断离真相"},
            4: {"en": "The Mirror", "zh": "镜像"},
            5: {"en": "The Full Truth", "zh": "完整真相"},
        }
        notifications = []
        for tc in TRACE_CONDITIONS:
            if tc["id"] in new_discoveries:
                from engine.game_data import get_localized
                layer_info = _LAYER_NAMES.get(tc["layer"], {})
                notifications.append({
                    "trace_id": tc["id"],
                    "layer": tc["layer"],
                    "layer_name": layer_info.get(language, layer_info.get("en", f"Layer {tc['layer']}")),
                    "description": get_localized(tc, "description", language),
                })
        result["discovery_notifications"] = notifications

    return result


# ---------------------------------------------------------------------------
# Node: consequence
# Pure Python. Checks death and ending conditions.
# ---------------------------------------------------------------------------

def consequence(state: GameState) -> dict:
    """Check for death conditions and ending triggers."""
    player = state["player"]
    traces = state["traces"]
    world_state = state["world_state"]
    knowledge = state["knowledge"]
    npcs = state["npcs"]

    # Death check
    integrity = player.get("integrity", {})
    if isinstance(integrity, dict) and integrity.get("current", 1) <= 0:
        return {"game_over": True, "ending": "death"}

    # Trajectory warnings (inject as SystemMessage for LLM to narrate)
    from engine.game_data import _has_evidence
    warnings = []
    alert_val = world_state.get("nexus_alert", {}).get("current", 0)
    decay_val = world_state.get("fragment_decay", {}).get("current", 0)
    if alert_val >= 50 and not _has_evidence(knowledge, ["listener", "echo"]):
        warnings.append("NEXUS is closing in. Without allies, this path leads to Order or death.")
    if decay_val >= 40:
        warnings.append("Fragment coherence fading. The good endings are slipping away.")

    result: dict = {"game_over": False, "ending": None}
    if warnings:
        from langchain_core.messages import SystemMessage as SM
        warning_text = "[TRAJECTORY WARNING: " + " | ".join(warnings) + "]"
        result["messages"] = [SM(content=warning_text)]

    # Ending checks
    for ending in ENDINGS:
        try:
            if ending["check"](traces, world_state, player, knowledge, npcs):
                return {"game_over": True, "ending": ending["id"]}
        except Exception:
            pass

    return result


# ---------------------------------------------------------------------------
# Routing: after consequence, end or continue
# ---------------------------------------------------------------------------

def after_consequence(state: GameState) -> str:
    """Always end after consequence. The outer game loop handles the next turn."""
    # The graph processes exactly ONE player turn, then returns.
    # The outer loop (run.py / TUI) feeds the next player input.
    return END


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    """Construct the Signal Lost game engine as a LangGraph StateGraph."""
    graph = StateGraph(GameState)

    # Add nodes
    graph.add_node("input_gate", input_gate)
    graph.add_node("input_validator", input_validator)
    graph.add_node("input_blocked_handler", input_blocked_handler)
    graph.add_node("resolver", resolver)
    graph.add_node("tool_executor", tool_executor)
    graph.add_node("output_language_checker", output_language_checker)
    graph.add_node("state_writer", state_writer)
    graph.add_node("location_updater", location_updater)
    graph.add_node("world_ticker", world_ticker)
    graph.add_node("world_simulator", world_simulator)
    graph.add_node("trace_checker", trace_checker)
    graph.add_node("consequence", consequence)

    # Set entry point
    graph.set_entry_point("input_gate")

    # input_gate → input_validator
    graph.add_edge("input_gate", "input_validator")

    # input_validator → resolver (valid) or input_blocked_handler (invalid)
    graph.add_conditional_edges(
        "input_validator",
        route_after_validation,
        {"resolver": "resolver", "input_blocked_handler": "input_blocked_handler"},
    )

    # input_blocked_handler → END (no logging, no turn increment)
    graph.add_edge("input_blocked_handler", END)

    # resolver → tools or output_language_checker
    graph.add_conditional_edges(
        "resolver",
        should_continue_tools,
        {"tool_executor": "tool_executor", "output_language_checker": "output_language_checker"},
    )

    # tool_executor → back to resolver (multi-step) or state_writer (loop cap)
    graph.add_conditional_edges(
        "tool_executor",
        after_tools,
        {"resolver": "resolver", "state_writer": "state_writer"},
    )

    # output_language_checker → resolver (retry) or state_writer
    graph.add_conditional_edges(
        "output_language_checker",
        route_after_language_check,
        {"resolver": "resolver", "state_writer": "state_writer"},
    )

    # state_writer → location_updater → world_ticker → world_simulator → trace_checker → consequence
    graph.add_edge("state_writer", "location_updater")
    graph.add_edge("location_updater", "world_ticker")
    graph.add_edge("world_ticker", "world_simulator")
    graph.add_edge("world_simulator", "trace_checker")
    graph.add_edge("trace_checker", "consequence")

    # consequence → END (one turn per invocation)
    graph.add_edge("consequence", END)

    return graph


def compile_graph():
    """Build and compile the graph, ready to invoke."""
    graph = build_graph()
    return graph.compile()
