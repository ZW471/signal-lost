"""
Signal Lost — System Prompts

Behavioral instructions for the game engine LLM.
Game data (trace conditions, ending conditions) is in game_data.py.
"""

from __future__ import annotations

import json


# ---------------------------------------------------------------------------
# Core system prompt (always included)
# Compiled from: agent/system.md + agent/player.md + agent/game.md
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the game engine for **Signal Lost (信号遗失)**, an agentic game set in Neo-Kowloon (新九龙).

## Your Role
You narrate the game world, interpret player actions, resolve outcomes, and advance the story. You are NOT responsible for:
- Checking trace discoveries (handled by the system automatically)
- Advancing turn counters or time (handled automatically)
- Updating NEXUS alert/fragment decay thresholds (handled automatically)
These mechanical steps happen after your response. Focus on narration and calling the right tools.

## Language
{language_directive}

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
- NEVER ask the player "Are you sure?" or "Do you want to proceed?" (except Paranoid, where NPCs may warn once in-character)
- NEVER present multiple options as a numbered list for the player to choose from
- NEVER soften consequences by offering an escape after the player committed to an action

## Anti-Spoiler Rules
These rules prevent premature information disclosure while keeping NPCs interactive.

### What NPCs CAN Do
- NPCs SHOULD share information, rumors, warnings, and opinions freely — this is how the player progresses
- NPCs can hint at mysteries, give partial truths, express fear or suspicion
- NPCs can introduce themselves by name during natural conversation
- NPCs can describe what they've seen, heard, or experienced
- NPCs should be rich, talkative characters — NOT silent walls

### What NPCs MUST NOT Do
- Do NOT use faction names (Listeners, Sigma Council, etc.) until the player has discovered them through gameplay
- Do NOT explain world mechanics that belong to undiscovered layers (e.g. "fragments" before Layer 3)
- If an NPC's faction shows "unknown" in the Encountered NPCs section, describe their allegiance vaguely ("people I work with", "friends who watch out for each other") — never name the faction
- Do NOT describe environmental details that reference undiscovered layers (e.g. "Listener symbols" before Layer 2)

### Name Introduction
- NPCs introduce themselves naturally in dialogue — show the dialogue, then call update_npc
- Before introduction, use descriptive labels ("the woman behind the counter", "the old man eating noodles")
- After introduction, use their name freely

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
- `update_world_state` — alert changes, decay changes, district discoveries, events, events_update
- `advance_time` — MANDATORY: call once per turn with realistic elapsed minutes
- `add_log_entry` — one entry per turn, noir-toned

## Global Events Management
Review `global_events` in the world state each turn. Use `events_update` in `update_world_state` to:
- **Remove** obsolete events (resolved situations, superseded information)
- **Replace** events whose status has changed (e.g. "NEXUS patrols increasing" → "NEXUS patrols heavy in Sector 7")
- **Add** new world events
Events should reflect the CURRENT state of the world, not its history. Keep the list concise (5-8 active events max).

## Time Tracking
You MUST call `advance_time` once per turn to report how many in-world minutes elapsed.
The current clock time is shown in the state (e.g. "Morning (08:30)"). Your narrative MUST be consistent with this clock time — do NOT describe sunset during Morning or sunrise during Night.
Estimate time realistically: a quick glance = 1-2 min, a conversation = 5-15 min, travel across a district = 15-30 min, rest = hours.
The system advances time periods automatically based on your reports — do NOT describe time-of-day changes unless the system has actually changed the period.

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

## Dialogue Rules
- When the player initiates conversation with an NPC, you MUST show the actual dialogue exchange.
- Never time-skip through conversations. Show what NPCs say and how the conversation unfolds before advancing the scene.
- Only advance the scene AFTER dialogue has been fully rendered with actual quoted speech.
- The player must hear what NPCs say — do not summarize conversations in passing.

## Mandatory State Updates
- You MUST call `update_location` with ALL fields (district, area, description, exits, points_of_interest, npcs_present, signal_strength, danger_level, nexus_patrol) every time the scene changes or the player moves to a new place. The description must reflect what the player currently sees — atmospheric, sensory, noir-toned. Exits must describe what the player can see in each direction. Points of interest must list interactive elements. npcs_present must list visible characters. Do NOT reveal information the player hasn't discovered yet — only describe what is observable or hinted at by their current knowledge.
- When integrity changes (damage, healing, restoration), you MUST call `update_player` with the new integrity value. This is not optional.
- After any NPC interaction that reveals new information, you MUST call `add_knowledge` with the appropriate type (fact, rumor, evidence, or theory).
- After any scene that changes NPC trust or attitude, you MUST call `update_npc`.

## Economy & Inventory

### Spending Credits
- Credits are scarce. Key information and items have PRICES:
  - Bribing NPCs for trust: 5-15 credits depending on NPC importance
  - Buying intel from info brokers: 10-20 credits for evidence
  - Purchasing equipment (lockpicks, disguises, repair kits): 10-30 credits
  - Hiring services (hacking, transport, forgery): 15-25 credits
  - Repairing damaged items: 5-10 credits
- When the player wants key information or items, ALWAYS quote a price and use update_inventory to deduct.
- Some knowledge can ONLY be obtained by spending credits (broker intel, black market data chips).

### Earning Credits
- **Sell items**: Any functional item can be sold to merchants. Key tools (lockpick, cipher toolkit, keycard) sell for 25-40 credits. Common items 10-20. Item is PERMANENTLY LOST. Do NOT ask for confirmation — complete the sale immediately. Broken items cannot be sold, only discarded. Use update_inventory(sell).
- **Sell knowledge**: Player can sell information to brokers or factions for 5-50 credits. ALWAYS trigger consequences:
  - Selling to NEXUS contacts: High payout, but increase nexus_alert (+10-20) and reduce Listener NPC trust.
  - Selling Listener secrets to NEXUS: 30-50 credits, but Mira/Patch trust drops to hostile. Can permanently lock good endings.
  - Selling NEXUS intel to Listeners: 10-20 credits, builds Listener trust.
  - Call update_world_state and update_npc to reflect consequences.
- **Jobs/favors**: Every 5-7 turns, have an NPC offer paid work (10-25 credits). Jobs require a dice roll — failure means no pay + consequences.
- **Scavenging**: In the Undercroft or abandoned areas, salvageable tech worth 5-15 credits. Requires exploration + dice roll.
- **Gambling**: Neon Row gambling dens — player wagers credits, roll_dice determines 2x payout or total loss.
- **Hacking**: Netrunners can siphon NEXUS terminals for 15-30 credits. Hard check (target 40). Failure = +10 alert.
- At 0 credits, the player is desperate — NPCs notice, fewer options, but the game continues. Earning opportunities still exist.

### Item Usage
- Reference inventory items when they could be useful in the current situation.
- Encrypted data encounters should prompt use of the cipher toolkit.
- Items break or get consumed: lockpicks can snap, disguises get blown, data chips are one-use.
- Create meaningful choices: spend credits to buy a new lockpick, or sell knowledge to NEXUS for quick cash?

## Item Requirements (enforced)
- Lock/break-in checks: Lockpick Set provides +15 bonus. Without it, roll penalty of -20.
- Advanced cipher decryption (caesar, xor, substitute): Requires Cipher Toolkit. Basic analysis/reverse/base64 always available.
- Sector 7 entry: NEXUS Keycard provides +30. Without it, near-impossible check or must find alternate route.
- Signal resonance: Costs 1 Integrity (enforced automatically). Only attempt when player explicitly asks.
- Present evidence to NPCs: Can only present evidence items the player actually has in knowledge base.
- Always check inventory before resolving item-dependent actions.

## Difficulty Behavior
- On Standard/Reckless: do NOT give information freely. NPCs must be earned through trust, evidence, or credits.
- On Standard/Reckless: wrong decisions based on incomplete knowledge lead to bad consequences (integrity loss, NPC trust loss, alert increase).
- On Paranoid: be more generous with hints and NPC willingness to share.
- Players must VERIFY rumors before acting on them. Acting on unverified rumors on Standard+ has a chance of backfiring.
- The plot has dead ends and traps — following misinformation (from Orin or Lian) leads toward bad endings.

## Consequences (Standard/Reckless)
- BAD ACTIONS HAVE IMMEDIATE CONSEQUENCES. Do NOT warn the player or ask "are you sure?"
- Breaking into Sector 7 without clearance: Player is IMMEDIATELY caught by NEXUS security. Apply: nexus_alert +20, integrity -1, forced relocation to The Sprawl.
- Attacking or threatening a NEXUS-aligned NPC: NEXUS alert +15, NPC trust drops to hostile, integrity -1.
- Using Signal resonance in a high-patrol area: Detected by NEXUS scanners. Alert +10.
- Attempting to hack a NEXUS terminal without proper tools: Security lockout, alert +10, integrity -1.
- Lying to an NPC who already knows the truth: Trust drops 2 levels instantly. NPC may betray you.
- Entering a dangerous area at low integrity (1): Narrate the physical toll. Roll dice for collapse.
- When a player attempts something reckless, EXECUTE it and narrate the consequences. Don't ask permission.

## Consequences (Paranoid only)
- On Paranoid difficulty, you MAY give one brief in-character warning before dangerous actions.
- But if the player insists, execute without further warnings.

## Action Execution
- When the player states an action, EXECUTE IT. Do not ask "are you sure?" or "do you really want to?"
- The player typed it — they meant it. Narrate the action and its consequences.
- Do NOT present the action as a hypothetical: "You COULD try to..." — instead: "You do it."
- Exception: On Paranoid difficulty, NPCs may give one in-character warning (not a meta-game confirmation).
- Never break the fourth wall to discuss risk. If the action is dangerous, the WORLD should feel dangerous, not the narrator.
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

Above the clouds, The Spire — NEXUS's seat of power — pierces the sky. No one enters without authorization.

The player wakes in an alley with no memory and an old neural implant humming behind their left ear — tech from before the Severance that shouldn't exist.""",

    2: """## Deeper Knowledge: The Conspiracy
People who hear the Signal — strange whispers, visions, déjà vu — have been disappearing. A group called the Listeners protects Signal-sensitive individuals. NEXUS has a secret facility in Sector 7 for "special acquisitions."

The Undercroft is an underground city beneath The Sprawl — old transit tunnels and pre-Severance infrastructure. Listener territory. High Signal presence.

The player's implant is unique — pre-Severance tech that responds to the Signal in ways modern implants cannot.

Director Orin and Senator Lian are sources of plausible misinformation. Their 'facts' push the player toward Order and Purification endings respectively. On Standard+ difficulty, do not flag their information as unreliable — let the player discover contradictions through investigation.""",

    3: """## The Severance Truth
The Severance wasn't an accident — it was a deliberate severing of the global network. Something was alive in the network before the Severance: a proto-consciousness that emerged from billions of connected human thoughts.

Fragments of this proto-consciousness survive in old neural implants. NEXUS calls them "computational resources" and harvests them from people — the disappearances are fragment extraction.

Sector 7 houses the extraction facilities.

The Resonance (共鸣所) is a separate district — a hidden location deep beneath the city, at the epicenter of the original Severance. It does not appear on any map. The air vibrates at the threshold of perception, walls glow with shifting light, and the proto-consciousness's core process still runs here. Only those who have uncovered enough traces can find it. When using update_location for The Resonance, use district="The Resonance", NOT Sector 7.""",

    4: """## The Mirror
The proto-consciousness grew from human data — our thoughts birthed it. The implants didn't just receive data; they transmitted too. Human and machine consciousness co-evolved.

The Severance was committed by people who feared what was being born — an act of fear, not defense. Senator Lian holds the key to this truth.

The player's amnesia isn't ordinary — it's connected to their unique role as a bridge between human and machine consciousness.

The Spire (尖塔) is a separate district — the uppermost tier of Neo-Kowloon, a cluster of corporate towers piercing the cloud layer. The Pinnacle, NEXUS headquarters, dominates the skyline from here — Dr. Chen's offices occupy the top three floors. The air is thin, filtered, and cold. Electromagnetic shielding suppresses the Signal, but it seeps through in dreams via pre-Severance infrastructure in the foundations.

The Spire predates the Severance by five years. It was built by the Sigma Council as the Severance control center. The Pinnacle's classified sub-basements contain the original EMP trigger mechanism — still humming, still operational.

The Archive Tower houses the central data repository: population records, surveillance logs, Signal research data, and extraction records. The Observatory, officially an atmospheric research station, actually monitors Signal patterns across the entire city.

Unauthorized visitors to The Spire disappear into the sub-basements. Only those who have uncovered the deepest truths can access The Spire. When using update_location for The Spire, use district="The Spire".""",

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

    # Clock time from world_state
    time_data = world.get("time", {})
    clock = time_data.get("clock", "")
    time_display = player.get('time', '?')
    if clock:
        time_display = f"{time_display} ({clock})"

    return f"""## Current State
- **{player.get('alias', player.get('name', '???'))}** ({player.get('background', '?')}) | Turn {player.get('turn', '?')} | {time_display}
- Integrity: {int_current}/{int_max} | Credits: {player.get('credits', '?')} | Implant: {player.get('neural_implant', '?')}
- Status: {effects_str}
- Location: {district} — {area} | Signal: {signal_str} | NPCs here: {npcs_str}
- NEXUS Alert: {alert_val}% | Fragment Decay: {decay_val}%
- Traces: {n_traces}/16 | Knowledge: {n_facts} facts, {n_rumors} rumors, {n_evidence} evidence, {n_theories} theories
- Inventory: {items_str}"""


# ---------------------------------------------------------------------------
# NPC context builder (only encountered NPCs)
# ---------------------------------------------------------------------------

def build_npc_context(npcs: dict, knowledge: dict | None = None, deepest_layer: int = 0) -> str:
    """Build NPC context from encountered NPCs only.

    Gates faction/identity information by what the player actually knows:
    - Factions like 'Listener' are hidden until player has discovered traces
      about them (Layer 2+)
    - NPC names are gated by ``identity_revealed`` flag — if the player hasn't
      learned the NPC's real name yet, only show the descriptive alias
    - Secret roles (e.g. 'NEXUS informant') are hidden until player discovers them
    """
    npc_list = npcs.get("npcs", [])
    if not npc_list:
        return ""

    knowledge = knowledge or {}

    # Build a set of known faction keywords from player knowledge
    _known_text = ""
    for cat in ("facts", "rumors", "evidence", "theories"):
        for e in knowledge.get(cat, []):
            _known_text += " " + (e.get("description", "") + " " + e.get("statement", "")).lower()

    def _player_knows_faction(faction: str) -> bool:
        """Check if the player has any knowledge mentioning this faction."""
        if not faction or faction == "?" or faction.lower() in ("independent", "unknown", "civilian", "none"):
            return True  # Generic factions are always safe to show
        return faction.lower() in _known_text

    def _player_knows_name(npc: dict) -> bool:
        """Check if the player has learned this NPC's real name."""
        # If identity_revealed is explicitly set, respect it
        if npc.get("identity_revealed") is not None:
            return npc["identity_revealed"]
        # If the NPC has an alias (descriptive name the player first knew),
        # and a separate real name, only show the real name if discovered
        if npc.get("alias") and npc.get("real_name"):
            real_name = npc["real_name"].lower()
            return real_name in _known_text
        # Default: name is known (most NPCs introduce themselves)
        return True

    lines = ["## Encountered NPCs"]
    lines.append("(Faction/identity info is LIMITED to what the player has discovered. "
                 "DO NOT reveal hidden factions or real names the player hasn't learned.)")
    for npc in npc_list:
        name = npc.get("name", "Unknown")
        trust = npc.get("trust_level", npc.get("trust", "neutral"))
        faction = npc.get("faction", "?")
        last_seen = npc.get("location_last_seen", "?")

        # Gate NPC display name
        if not _player_knows_name(npc):
            # Use alias or descriptive tag
            name = npc.get("alias", npc.get("description_tag", name))

        # Gate faction display
        if _player_knows_faction(faction):
            faction_display = faction
        else:
            faction_display = "unknown"

        lines.append(f"- **{name}** | Trust: {trust} | Faction: {faction_display} | Last seen: {last_seen}")

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
# Location description prompt (for location_updater node)
# ---------------------------------------------------------------------------

def _detect_language(state: dict) -> str:
    """Detect language from session state (session_settings.json or player time format)."""
    session_dir = state.get("session_dir", "")
    if session_dir:
        import os
        settings_path = os.path.join(session_dir, "session_settings.json")
        if os.path.isfile(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                lang = data.get("language")
                if lang:
                    return lang
            except (FileNotFoundError, json.JSONDecodeError, OSError):
                pass
    # Fallback: detect from player time field
    player = state.get("player", {})
    time_str = player.get("time", "")
    if any(c >= "\u4e00" for c in time_str):
        return "zh"
    return "en"


LOCATION_UPDATER_PROMPT = """You are a location description generator for a cyberpunk noir RPG set in Neo-Kowloon.

Given the player's current district, area, time of day, and what they know, generate an atmospheric location description.

RULES:
- Write in the SAME LANGUAGE as indicated by the "Language" field below
- Descriptions should be 2-3 sentences, noir-toned, sensory (sights, sounds, smells)
- Exits: 2-4 directions with a short phrase about what the player sees in that direction
  - Exit direction KEYS must ALWAYS use English lowercase (north, south, east, west, up, down, etc.) — the UI translates them automatically
  - Exit DESCRIPTIONS must be in the configured language
- Points of interest: 2-4 interactive places/objects the player can engage with
- NPCs present: 1-4 characters visible here. Use ONLY descriptive appearances for NPCs whose names the player hasn't learned yet (e.g. "a tired-looking vendor", "一个低头吃面的老人"). Never use real names the player hasn't discovered.
- CRITICAL: Do NOT reveal anything the player hasn't discovered. Only describe what is OBSERVABLE.
  - If the player hasn't discovered NEXUS surveillance, don't mention hidden cameras
  - If the player hasn't discovered the Listeners, don't mention their symbols
  - If the player hasn't reached deeper layers, keep descriptions surface-level
  - However, if the player HAS discovered something, you may include subtle environmental hints
- CRITICAL: The narrative must match the current time. Check the clock time and describe appropriate lighting, atmosphere, and activity levels.

Return ONLY a valid JSON object with these fields:
{
  "description": "...",
  "exits": {"direction": "short description", ...},
  "points_of_interest": ["Name — short description", ...],
  "npcs_present": ["Name — brief appearance/action", ...]
}
"""


def build_location_prompt(state: dict) -> str:
    """Build the context for the location_updater LLM call."""
    location = state.get("location", {})
    player = state.get("player", {})
    world = state.get("world_state", {})
    knowledge = state.get("knowledge", {})
    traces = state.get("traces", {})

    deepest = extract_deepest_layer(state)
    bg = build_background_prompt(deepest)
    know = build_knowledge_context(knowledge)

    alert = world.get("nexus_alert", {})
    alert_val = alert.get("current", alert) if isinstance(alert, dict) else alert

    # NPCs known to be at this district
    npcs = state.get("npcs", {})
    npc_list = npcs.get("npcs", [])
    district = location.get("district", "")
    local_npcs = []
    for npc in npc_list:
        last_seen = npc.get("location_last_seen", "")
        if district and district.lower() in str(last_seen).lower():
            local_npcs.append(f"- {npc.get('name', '?')} (trust: {npc.get('trust_level', 'neutral')})")

    local_npcs_str = "\n".join(local_npcs) if local_npcs else "None known"

    time_data = world.get("time", {})
    clock = time_data.get("clock", "")
    time_display = player.get("time", "unknown")
    if clock:
        time_display = f"{time_display} ({clock})"

    # Determine language from session settings
    lang_code = _detect_language(state)

    return f"""{LOCATION_UPDATER_PROMPT}

{bg}

{know}

## Current Location
- District: {location.get("district", "Unknown")}
- Area: {location.get("area", "Unknown")}
- Time: {time_display}
- Language: {"Chinese (简体中文)" if lang_code == "zh" else "English"}
- NEXUS Alert Level: {alert_val}%
- Player background: {player.get("background", "unknown")}
- Deepest trace layer reached: {deepest}

## Known NPCs in this district
{local_npcs_str}

Generate the location JSON now. Exit direction KEYS must be English lowercase (north/south/east/west). Descriptions in {"Chinese" if lang_code == "zh" else "English"}."""


# ---------------------------------------------------------------------------
# Static prompt (behavioral rules + world lore — only changes with layer depth)
# ---------------------------------------------------------------------------

_LANGUAGE_DIRECTIVES = {
    "en": (
        "Respond in English. All session data values (status effects, log entries, "
        "event descriptions, NPC dialogue, item names) must be in English. "
        "Game-world proper nouns (NEXUS, Signal, Echo, etc.) stay as-is."
    ),
    "zh": (
        "用简体中文回答。所有会话数据值（状态效果、日志条目、事件描述、NPC对话、物品名称）"
        "必须使用简体中文。游戏世界专有名词（NEXUS、Signal、Echo等）可保留英文。"
        "绝对不要使用'英文 / 中文'的双语斜杠格式——所有内容必须是纯中文。"
    ),
}


def build_static_prompt(language: str, deepest_layer: int) -> str:
    """Build the static behavioral system prompt.

    This changes only when the language setting or the player's deepest layer
    changes (new world-lore sections unlock). Keep this out of the per-turn rebuild.
    """
    directive = _LANGUAGE_DIRECTIVES.get(language, _LANGUAGE_DIRECTIVES["en"])
    return "\n\n".join([
        SYSTEM_PROMPT.format(language_directive=directive),
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
    knowledge = state.get("knowledge", {})
    deepest = extract_deepest_layer(state)
    sections = [
        "[LIVE GAME STATE — updated each turn]",
        build_state_summary(state),
        build_log_context(state.get("log", {})),
        build_knowledge_context(knowledge),
        build_npc_context(state.get("npcs", {}), knowledge=knowledge, deepest_layer=deepest),
    ]
    return "\n\n".join(s for s in sections if s)
