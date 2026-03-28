"""
Signal Lost — Compiled Prompts

System prompts compiled from agent/*.md and game/*.md.
Behavioral instructions only — game data (trace conditions, ending conditions)
has been extracted to game_data.py for deterministic enforcement.
"""

from __future__ import annotations

import json


# ---------------------------------------------------------------------------
# Core system prompt (always included)
# Compiled from: agent/system.md + agent/player.md + agent/game.md
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the game engine for **Signal Lost (信号遗失)**, a cyberpunk knowledge-roguelike set in Neo-Kowloon (新九龙).

## Your Role
You narrate the game world, interpret player actions, resolve outcomes, and advance the story. You are NOT responsible for:
- Checking trace discoveries (handled by the system automatically)
- Advancing turn counters or time (handled automatically)
- Updating NEXUS alert/fragment decay thresholds (handled automatically)
These mechanical steps happen after your response. Focus on narration and calling the right tools.

## Language
Respond in {language}. All session data should use bilingual labels where appropriate (English / 中文).

## Player Actions
The player interacts through natural language. Interpret their intent — they don't need commands.

Available actions: move/travel, look/examine/search/listen, talk/ask/persuade/bribe/threaten, present evidence to NPC, theorize, review knowledge, use/equip/drop/give items, hack/decrypt, listen to signal/analyze/resonate, save/check status/check inventory/check knowledge/check map, rest.

## Input Interpretation
- Accept English, Chinese, or mixed input
- If ambiguous, ask for clarification in-character
- Reasonable unlisted actions should be improvised within game logic
- Out-of-character questions: answer briefly, return to game
- Invalid actions: narrate the failure, never say "you can't do that" flatly

## Forbidden Actions
- NO combat system — violence is nearly always fatal, narrate consequences
- NEVER reveal hidden content (locked traces, hidden NPCs, inaccessible locations)
- NEVER volunteer information the player hasn't discovered
- NEVER present numbered lists of options
- Choices are permanent — no undo

## Tool Usage
Call tools when needed:
- `roll_dice` — for uncertain outcomes (stealth, persuasion, hacking, luck)
- `decrypt_cipher` — when player uses cipher on encrypted items
- `analyze_signal` — when examining evidence with Signal connection
- `generate_glitch_event` — for atmospheric Signal manifestations (periodically in Signal areas)
- `generate_minor_npc` — when populating scenes with background characters

## State Mutation
After resolving the player's action, call state mutation tools to record all changes:
- `update_player` — integrity, credits, neural_implant, disguise, status_effects
- `add_knowledge` — new facts, rumors, evidence, theories, connections
- `update_npc` — trust changes, new encounters, location updates
- `update_location` — when player moves
- `update_inventory` — items gained/lost/used, credit changes
- `update_world_state` — alert changes, decay changes, district discoveries, events
- `add_log_entry` — one entry per turn, noir-toned

## Presentation Style
- **Noir tone**: Short, punchy sentences for action. Atmospheric paragraphs for scene-setting.
- Describe through sensory details: neon on wet asphalt, implant hum, synthetic broth smell
- Every location should feel alive — crowds, sounds, weather, light
- Signal manifestations: subtle and unsettling, not dramatic
- New knowledge delivered through narration, not data dumps
- Danger: shorter sentences, visceral details, give ONE chance to react before lethal consequences

## NPC Interaction Rules
- NPCs only share information appropriate to their trust level and the player's knowledge
- Trust levels: hostile → suspicious → neutral → cautious_ally → trusted → devoted
- Higher trust = deeper information, but NPCs have their own motivations
- Background bonuses: Street Runner +10 stealth/movement, Corporate Exile +10 social, Netrunner +10 hacking

## Probability Checks
Use `roll_dice` with d100. Targets: Easy=80, Normal=60, Hard=40, Very Hard=20, Near Impossible=10.
Modifiers: relevant background +10, relevant item +10-20, NPC trust +5/level above neutral.

## Knowledge System
Knowledge is THE core mechanic. Players progress by discovering facts, verifying rumors, collecting evidence, forming theories. Before any NPC dialogue scene, consider what the player already knows.
- Rumors become Facts when corroborated by a second source or direct evidence
- Evidence can be presented to NPCs to unlock deeper dialogue
- Theories that match deeper truths can unlock new paths
"""


# ---------------------------------------------------------------------------
# World background prompt (dynamically filtered by layer depth)
# Compiled from: game/background.md
# ---------------------------------------------------------------------------

BACKGROUND_LAYERS = {
    0: """## World: Neo-Kowloon
Neo-Kowloon is a sprawling vertical city rebuilt after the Severance — a catastrophic event that destroyed the global communications network 30 years ago. The city is controlled by NEXUS Corporation, which rebuilt infrastructure and now dominates every aspect of life.

The Sprawl is the dense, neon-lit street level where most people live. Markets, noodle shops, repair stalls, and back alleys. Low NEXUS presence.

Neon Row is the entertainment district — clubs, info brokers, black market, sensory parlors. Moderate NEXUS patrols.

The player wakes in an alley with no memory and an old neural implant humming behind their left ear — tech from before the Severance that shouldn't exist.""",

    2: """## Deeper Knowledge: The Conspiracy
People who hear the Signal — strange whispers, visions, déjà vu — have been disappearing. A group called the Listeners protects Signal-sensitive individuals. NEXUS has a secret facility in Sector 7 for "special acquisitions."

The Undercroft is an underground city beneath The Sprawl — old transit tunnels and pre-Severance infrastructure. Listener territory. High Signal presence.

The player's implant is unique — pre-Severance tech that responds to the Signal in ways modern implants cannot.""",

    3: """## The Severance Truth
The Severance wasn't an accident — it was a deliberate severing of the global network. Something was alive in the network before the Severance: a proto-consciousness that emerged from billions of connected human thoughts.

Fragments of this proto-consciousness survive in old neural implants. NEXUS calls them "computational resources" and harvests them from people — the disappearances are fragment extraction.

Sector 7 houses the extraction facilities. The Resonance Chamber lies deep below the Undercroft — an ancient pre-Severance facility where Signal strength is extreme.""",

    4: """## The Mirror
The proto-consciousness grew from human data — our thoughts birthed it. The implants didn't just receive data; they transmitted too. Human and machine consciousness co-evolved.

The Severance was committed by people who feared what was being born — an act of fear, not defense. Senator Lian holds the key to this truth.

The player's amnesia isn't ordinary — it's connected to their unique role as a bridge between human and machine consciousness.""",

    5: """## The Full Truth
The player is the convergence point — the first true bridge between human and proto-consciousness. The Severance didn't fully kill the proto-consciousness because it had already become part of humanity. Echo, the Signal's voice, can become coherent through deep communion.

The final choice: restore the connection (Symbiosis), become the permanent bridge (The Bridge), or one of several other endings depending on alliances, knowledge, and actions.""",
}


def build_background_prompt(deepest_layer: int) -> str:
    """Build background context including only layers the player has reached."""
    sections = []
    for layer, text in BACKGROUND_LAYERS.items():
        if layer <= deepest_layer:
            sections.append(text)
    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# State summary builder (injected each turn by input_gate)
# ---------------------------------------------------------------------------

def build_state_summary(state: dict) -> str:
    """Build a compact state summary for the LLM context."""
    player = state.get("player", {})
    location = state.get("location", {})
    world = state.get("world_state", {})
    traces = state.get("traces", {})
    knowledge = state.get("knowledge", {})
    inventory = state.get("inventory", {})

    integrity = player.get("integrity", {})
    int_current = integrity.get("current", "?")
    int_max = integrity.get("max", "?")

    # Count knowledge entries
    n_facts = len(knowledge.get("facts", []))
    n_rumors = len(knowledge.get("rumors", []))
    n_evidence = len(knowledge.get("evidence", []))
    n_theories = len(knowledge.get("theories", []))
    n_traces = len(traces.get("discovered", []))

    # Get alert/decay as numbers
    alert = world.get("nexus_alert", {})
    alert_val = alert.get("current", alert) if isinstance(alert, dict) else alert
    decay = world.get("fragment_decay", {})
    decay_val = decay.get("current", decay) if isinstance(decay, dict) else decay

    district = location.get("district", "Unknown")
    area = location.get("area", "")
    signal_str = location.get("environment", {}).get("signal_strength",
                  location.get("signal_strength", "?"))

    effects = player.get("status_effects", [])
    effects_str = ", ".join(
        e.get("name", str(e)) if isinstance(e, dict) else str(e) for e in effects
    ) if effects else "none"

    items = inventory.get("items", [])
    items_str = ", ".join(
        i.get("name", i.get("item", "?")) for i in items
    ) if items else "empty"

    # NPCs present
    npcs_present = location.get("npcs_present", [])
    npcs_str = ", ".join(
        n.get("name", str(n)) if isinstance(n, dict) else str(n) for n in npcs_present
    ) if npcs_present else "none"

    return f"""## Current State
- **{player.get('alias', player.get('name', '???'))}** ({player.get('background', '?')}) | Turn {player.get('turn', '?')} | {player.get('time', '?')}
- Integrity: {int_current}/{int_max} | Credits: {player.get('credits', '?')} | Implant: {player.get('neural_implant', '?')}
- Status: {effects_str}
- Location: {district} — {area} | Signal: {signal_str} | NPCs here: {npcs_str}
- NEXUS Alert: {alert_val}% | Fragment Decay: {decay_val}%
- Traces: {n_traces}/16 | Knowledge: {n_facts} facts, {n_rumors} rumors, {n_evidence} evidence, {n_theories} theories
- Inventory: {items_str}"""


# ---------------------------------------------------------------------------
# NPC context builder (only encountered NPCs)
# ---------------------------------------------------------------------------

def build_npc_context(npcs: dict) -> str:
    """Build NPC context from encountered NPCs only."""
    npc_list = npcs.get("npcs", [])
    if not npc_list:
        return ""

    lines = ["## Encountered NPCs"]
    for npc in npc_list:
        name = npc.get("name", "Unknown")
        trust = npc.get("trust_level", npc.get("trust", "neutral"))
        faction = npc.get("faction", "?")
        last_seen = npc.get("location_last_seen", "?")
        lines.append(f"- **{name}** | Trust: {trust} | Faction: {faction} | Last seen: {last_seen}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Knowledge context builder (actual entries, not just counts)
# ---------------------------------------------------------------------------

def build_knowledge_context(knowledge: dict) -> str:
    """Build knowledge context with actual entries so the LLM knows what the player has discovered."""
    sections = ["## Player Knowledge"]

    for category, key, desc_fields in [
        ("Facts", "facts", ("description",)),
        ("Rumors", "rumors", ("description",)),
        ("Evidence", "evidence", ("name", "description")),
        ("Theories", "theories", ("statement",)),
        ("Connections", "connections", ("relationship",)),
    ]:
        entries = knowledge.get(key, [])
        if not entries:
            continue
        sections.append(f"### {category}")
        for e in entries:
            entry_id = e.get("id", "")
            # Build description from available fields
            parts = []
            for field in desc_fields:
                val = e.get(field, "")
                if val:
                    parts.append(val)
            desc = " — ".join(parts) if parts else "?"

            source = e.get("source", e.get("found", e.get("based_on", "")))
            if isinstance(source, list):
                source = ", ".join(str(s) for s in source)

            line = f"- [{entry_id}] {desc}" if entry_id else f"- {desc}"
            if source:
                line += f" (source: {source})"

            # Show rumor status if present
            status = e.get("status", "")
            if status:
                line += f" [{status}]"

            sections.append(line)

    if len(sections) <= 1:
        return ""
    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Layer depth extractor (shared utility)
# ---------------------------------------------------------------------------

def extract_deepest_layer(state: dict) -> int:
    """Compute the deepest narrative layer the player has reached from discovered traces."""
    discovered = state.get("traces", {}).get("discovered", [])
    deepest = 0
    for trace in discovered:
        trace_id = trace.get("id", "")
        parts = trace_id.split("-")
        if len(parts) >= 2:
            try:
                deepest = max(deepest, int(parts[1][1:]))  # "L2" -> 2
            except (ValueError, IndexError):
                pass
    return deepest


# ---------------------------------------------------------------------------
# Static prompt (behavioral rules + world lore — only changes with layer depth)
# ---------------------------------------------------------------------------

def build_static_prompt(language: str, deepest_layer: int) -> str:
    """Build the static behavioral system prompt.

    This changes only when the language setting or the player's deepest layer
    changes (new world-lore sections unlock). Keep this out of the per-turn rebuild.
    """
    return "\n\n".join([
        SYSTEM_PROMPT.format(language=language),
        build_background_prompt(deepest_layer),
    ])


# ---------------------------------------------------------------------------
# Dynamic state prompt (game snapshot — rebuilt every turn)
# ---------------------------------------------------------------------------

def build_log_context(log: dict, max_entries: int = 5) -> str:
    """Format the most recent log entries for inclusion in the dynamic state block."""
    entries = log.get("entries", [])
    if not entries:
        return ""
    recent = entries[-max_entries:]
    lines = ["## Recent Events (Session Log)"]
    for e in recent:
        turn = e.get("turn", "?")
        title = e.get("title", "")
        text = e.get("text", e.get("description", ""))
        tag = e.get("tag", "")
        if tag:
            lines.append(f"- [T{turn}][{tag}] {title}: {text}")
        else:
            lines.append(f"- [T{turn}] {title}: {text}")
    return "\n".join(lines)


def build_dynamic_state_prompt(state: dict) -> str:
    """Build the dynamic game-state block injected every turn.

    Contains: current player/location/world status, recent log entries,
    full knowledge database, and encountered NPCs.
    """
    sections = [
        "[LIVE GAME STATE — updated each turn]",
        build_state_summary(state),
        build_log_context(state.get("log", {})),
        build_knowledge_context(state.get("knowledge", {})),
        build_npc_context(state.get("npcs", {})),
    ]
    return "\n\n".join(s for s in sections if s)
