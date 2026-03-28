# Signal Lost / 信号遗失 — Session File Schema

This document defines the required files in the `session/` folder, their formats, and the rules for when and how to update them.

All session files use **JSON** format. The agent must maintain these files as the authoritative record of game state. When in doubt about any game state, read the relevant session file — do not rely on memory. Knowledge is the core progression mechanic: the player does not level up. They grow by discovering facts, verifying rumors, collecting evidence, and forming theories.

---

## Hidden Field Convention

Any JSON object containing `"hidden": true` must NOT be displayed to the player in the TUI. The TUI viewer applies a `filter_hidden()` function that recursively removes such objects from the data tree before rendering.

The following session data uses hidden fields:

- **traces.json** `_gate_system`: The full layer structure, total trace count, and layer assignments. The player should discover traces organically — showing the total count or layer structure would spoil the progression mystery.
- **knowledge.json** `_layer` on each entry: Which truth layer a piece of knowledge belongs to. Revealing layer assignments would let the player reverse-engineer the knowledge gate system.
- **world_state.json** `_ending_trajectory`: The agent's tracking of which ending the player is heading toward. This must never be revealed.
- **world_state.json** `_district_registry`: The full list of undiscovered districts and their unlock conditions. Players must not see districts they haven't discovered yet, nor the requirements to access them. When a district is discovered, the agent moves it from `_district_registry.undiscovered` to the visible `district_access` array (without the `unlock` field).

When the agent writes these files, it MUST include `"hidden": true` in these objects so the TUI filters them out.

---

## Required Session Files

### `session/player.json`

The player character's complete state. Update after every event that changes any value.

**Format:**
```json
{
  "name": "[name]",
  "alias": "[alias]",
  "background": "[Street Runner | Corporate Exile | Netrunner]",
  "integrity": {"current": 3, "max": 3},
  "credits": 50,
  "neural_implant": "[Active | Dormant | Overloaded | Resonating]",
  "current_disguise": null,
  "turn": 1,
  "time": "[Morning | Afternoon | Night]",
  "status_effects": [
    {"name": "Signal Sensitivity", "intensity": "faint"}
  ]
}
```

**Fields:**

| Field | Description |
|-------|-------------|
| name | Player's chosen name |
| alias | Street name / handle used in the underworld |
| background | One of three origins; determines starting knowledge and item |
| integrity | Object with `current` and `max` (default 3/3). Cannot exceed max. |
| credits | Currency for buying information, items, bribes, and services |
| neural_implant | Status of the pre-Severance implant behind the player's left ear |
| current_disguise | `null` by default. Set to string when wearing a cover identity |
| turn | Incremented by 1 after every player action |
| time | Advances one period every 3 turns: Morning -> Afternoon -> Night -> Morning |
| status_effects | Array of objects with `name` and optional `intensity` |

**Integrity damage sources:**
- Violence (combat, ambushes, traps)
- Neural overload (failed hacking, overusing implant abilities)
- Signal shock (direct exposure to raw Signal without preparation)

**Integrity recovery:**
- Rare consumable items (MedStim, Neural Patch)
- Rest at designated safe locations (Mira's back room, The Listener sanctuary)
- Certain NPC interactions (medics, back-alley surgeons)

**Neural Implant states:**
- **Dormant**: Default state. Implant is quiet. No special abilities.
- **Active**: Implant is responding to environment. Player can sense Signal traces and read encrypted data fragments.
- **Overloaded**: Implant has been pushed too hard. -1 to all interaction rolls until it stabilizes (3 turns or rest). Signal exposure while overloaded deals Integrity damage.
- **Resonating**: Implant is harmonizing with a Signal Fragment. Rare state triggered by proximity to deep-truth artifacts. Unlocks unique dialogue options and perception of hidden information.

**Known Status Effects:**
- `Signal Sensitivity` — Can detect Signal traces in the environment. Gained from implant activation.
- `NEXUS Tracked` — NEXUS security is aware of the player. Patrols are more aggressive. Gained by being spotted in restricted areas or failing hacks.
- `Disguised` — Currently posing as someone else. Removed if cover is blown.
- `Fragment Resonance` — Implant is resonating with a nearby Fragment. Temporary. Reveals hidden information.
- `Neural Fatigue` — Implant was recently overloaded. Penalty to hacking and data-related actions.
- `Wounded` — Integrity damage from violence. -1 to physical actions until treated.
- `Signal Sickness` — Prolonged unprotected Signal exposure. Integrity slowly drains until cured.
- `Hunted` — NEXUS has issued a priority alert for the player. Extreme patrol response.

**Update rules:**
- Update Integrity after any damage or healing event
- Update Credits after any transaction
- Update Neural Implant status when Signal exposure or implant-related events occur
- Update Disguise when a cover identity is assumed or blown
- Increment Turn after every player action
- Advance Time every 3 turns (turn 1-3: Morning, turn 4-6: Afternoon, turn 7-9: Night, turn 10-12: Morning, etc.)
- Add/remove Status Effects as they are triggered or expire

---

### `session/knowledge.json`

**THE CORE FILE.** This is the heart of the game. The player does not level up — they progress by learning. Every fact, rumor, piece of evidence, theory, and connection is tracked here. The agent must consult this file before offering new content, dialogue options, or paths to the player. Knowledge gates everything.

**Format:**
```json
{
  "facts": [
    {"id": "FACT-001", "description": "...", "source": "...", "turn": 1, "_layer": {"hidden": true, "value": 1}}
  ],
  "rumors": [
    {"id": "RUMOR-001", "status": "unconfirmed", "description": "...", "source": "...", "turn": 1, "_layer": {"hidden": true, "value": 2}}
  ],
  "evidence": [
    {"id": "EVID-001", "name": "...", "description": "...", "found": "...", "turn": 1, "_layer": {"hidden": true, "value": 2}}
  ],
  "theories": [
    {"id": "THEO-001", "statement": "...", "based_on": ["FACT-001", "RUMOR-002"], "turn": 1, "status": "unconfirmed", "_layer": {"hidden": true, "value": 2}}
  ],
  "connections": [
    {"ids": ["FACT-001", "RUMOR-003"], "relationship": "..."}
  ]
}
```

**Entry Types:**

#### Facts
Confirmed truths the player has verified through direct experience, evidence, or multiple corroborating sources.

- IDs are sequential: FACT-001, FACT-002, etc.
- `source`: the NPC, location, document, or event that confirmed this fact
- `turn`: the turn number when confirmed
- `_layer`: hidden object with `value` indicating truth layer (1-5)

#### Rumors
Unconfirmed information from a single source. Rumors are the raw material of knowledge.

- `status`: `"unconfirmed"`, `"confirmed"`, or `"disproven"`
- Confirmed rumors should be promoted to a Fact (create a new FACT entry, update the Rumor status)

Rumors can become Facts when:
- The player finds corroborating evidence (physical or digital)
- A second independent source confirms the same information
- The player witnesses the truth directly

#### Evidence
Physical or digital items that prove or support a claim.

- IDs are sequential: EVID-001, EVID-002, etc.
- If the evidence is an inventory item, note its inventory slot
- Evidence persists even if the item is lost
- Evidence can be presented to NPCs to unlock new dialogue or trust

#### Theories
Player-derived connections between two or more knowledge entries.

- `based_on`: array of FACT, RUMOR, or EVID IDs that support the theory
- `status`: `"unconfirmed"`, `"confirmed"`, or `"disproven"`
- Confirmed theories can unlock new Traces (see traces.json)

#### Connections
Explicit links between any two knowledge entries.

- `ids`: array of two entry IDs being linked
- `relationship`: description of the connection

**Truth Layers:**

Each knowledge entry is tagged with a `_layer` object (hidden from TUI) indicating what depth of the central mystery it relates to:

| Layer | Name | Description |
|-------|------|-------------|
| 1 | The Surface / 表层 | Basic facts about Neo-Kowloon, NEXUS, and the player's immediate situation |
| 2 | The Conspiracy / 阴谋 | NEXUS's secret operations, the Signal's existence, corporate cover-ups |
| 3 | The Signal / 信号 | The nature of the Signal itself, who created it, what the Fragments are |
| 4 | The Architects / 设计者 | Who built the original network, why the Severance happened, the truth behind NEXUS |
| 5 | The Choice / 抉择 | The final truth: what the Signal wants, what the player must decide |

**Knowledge-gated content:**
- NPCs will not discuss higher-layer topics unless the player has demonstrated relevant lower-layer knowledge
- Locations unlock based on knowledge (e.g., you cannot find The Resonance Chamber unless you know it exists)
- Dialogue options appear only when the player has the relevant knowledge to ask the right questions
- Endings require specific knowledge thresholds (see traces.json)

**Update rules:**
- Add Rumors immediately when an NPC shares unconfirmed information
- Promote Rumors to Facts when verification conditions are met (create a FACT entry, update RUMOR status to "confirmed")
- Add Evidence when the player finds physical/digital proof
- Add Theories when the player proposes a connection between known entries
- Add Connections when relationships between entries are established
- Never delete entries — mark disproven items with `"status": "disproven"` but keep them
- Re-read this file before any NPC dialogue scene to check what the player already knows

---

### `session/traces.json`

Truth layer milestones. Each trace is a numbered discovery that gates new content — new locations, NPC dialogue, story paths, and endings. The agent must check this file before offering new paths, dialogue options, or revealing new information.

**Format:**
```json
{
  "discovered": [
    {"id": "TRACE-L1-01", "description": "...", "turn": 5}
  ],
  "_gate_system": {
    "hidden": true,
    "total_traces": 16,
    "deepest_layer": 0,
    "layers": [
      {"number": 1, "name": "The Surface", "name_zh": "表层", "total": 3, "traces": ["TRACE-L1-01", "TRACE-L1-02", "TRACE-L1-03"]},
      {"number": 2, "name": "The Conspiracy", "name_zh": "阴谋", "total": 4, "traces": ["TRACE-L2-01", "TRACE-L2-02", "TRACE-L2-03", "TRACE-L2-04"]},
      {"number": 3, "name": "The Severance Truth", "name_zh": "断离真相", "total": 4, "traces": ["TRACE-L3-01", "TRACE-L3-02", "TRACE-L3-03", "TRACE-L3-04"]},
      {"number": 4, "name": "The Mirror", "name_zh": "镜像", "total": 3, "traces": ["TRACE-L4-01", "TRACE-L4-02", "TRACE-L4-03"]},
      {"number": 5, "name": "The Full Truth", "name_zh": "完整真相", "total": 2, "traces": ["TRACE-L5-01", "TRACE-L5-02"]}
    ]
  }
}
```

The `discovered` array contains traces the player has found. The `_gate_system` object is hidden from the TUI and contains the full layer structure that only the agent uses.

**Trace discovery:** When a trace is discovered, add it to the `discovered` array with its `id`, `description`, and `turn`. Also update `deepest_layer` in the gate system if the new trace's layer is deeper.

**Trace-gated content examples:**
- Before TRACE-L1-03: No NPC will mention Listeners by name
- Before TRACE-L2-03: Signal exposure is described only as "interference" or "static"
- Before TRACE-L3-03: Wei Lin is only referenced as "the founder" or "the first Listener"
- Before TRACE-L4-03: The player's amnesia is treated as ordinary memory loss
- Endings require minimum trace counts (see world_state.json Ending Trajectory)

**Update rules:**
- Check trace triggers whenever new knowledge entries are added to knowledge.json
- Add discovered traces immediately when trigger conditions are met
- Record the turn number of discovery
- Update deepest_layer in `_gate_system`
- When a full layer is completed, note the unlock in the log

---

### `session/location.json`

The player's current position in Neo-Kowloon. Update completely whenever the player moves to a new area.

**Format:**
```json
{
  "district": "The Sprawl",
  "district_zh": "蔓城",
  "area": "Rain Alley, near Mira's Noodle Shop",
  "area_zh": "雨巷——米拉面馆附近",
  "description": "...",
  "environment": {
    "signal_strength": 10,
    "danger_level": "Safe",
    "nexus_patrol": "None",
    "time_of_day": "Morning"
  },
  "exits": [
    {"direction": "North", "direction_zh": "北", "destination": "...", "status": "Open"}
  ],
  "points_of_interest": [
    {"name": "米拉面馆", "direction": "East", "description": "..."}
  ],
  "npcs_present": [
    {"name": "Mira", "name_zh": "米拉", "activity": "..."}
  ]
}
```

**Districts of Neo-Kowloon / 新九龙:**

| District | Chinese | Access | Description |
|----------|---------|--------|-------------|
| The Sprawl | 蔓城 | Open (starting area) | Street-level markets, noodle shops, back alleys. Dense, noisy, alive. Low NEXUS presence. |
| The Neon Quarter | 霓虹区 | Open | Entertainment district. Clubs, info brokers, black market. Moderate NEXUS patrols. |
| The Undercroft | 地底城 | Requires TRACE-L1-03 | Underground city beneath The Sprawl. Listener territory. No NEXUS patrols. High Signal. |
| Sector 7 | 第七区 | Restricted (keycard or disguise) | Corporate zone. NEXUS offices, research labs, executive housing. Heavy NEXUS patrols. |
| The Resonance Chamber | 共鸣室 | Hidden (requires TRACE-L3 completion) | Ancient pre-Severance facility deep below The Undercroft. Extreme Signal. No patrols. |
| The Spire | 尖塔 | Locked (requires TRACE-L4 completion) | NEXUS headquarters tower. The endgame location. Lockdown-level security. |

**Signal Strength ranges:**
- The Sprawl: 5-15%
- The Neon Quarter: 10-25%
- The Undercroft: 40-70%
- Sector 7: 15-30% (NEXUS dampens it)
- The Resonance Chamber: 80-100%
- The Spire: 30-50% (shielded but leaking)

**Update rules:**
- Rewrite completely whenever the player moves to a new area
- Update NPCs Present when NPCs arrive or depart the area
- Update NEXUS Patrol level if world events change it
- Adjust Signal Strength if local conditions change (Fragment presence, equipment use)

---

### `session/inventory.json`

Everything the player is carrying. Maximum 6 item slots. Credits are tracked separately and do not consume a slot.

**Format:**
```json
{
  "credits": 50,
  "slots_used": 1,
  "slots_max": 6,
  "items": [
    {"slot": 1, "name": "...", "type": "data_chip", "description": "...", "evidence_id": null}
  ]
}
```

**Item types:**
- `data_chip` — Contains encrypted or decrypted data.
- `keycard` — Grants access to restricted areas.
- `disguise` — A cover identity package.
- `signal_artifact` — An object resonating with Signal energy.
- `evidence` — Physical proof of something. Has an associated EVID entry in knowledge.json.
- `tool` — Equipment that enables specific actions.
- `consumable` — Single-use items. Removed after use.

**Update rules:**
- Add items immediately when acquired; if inventory is full (6 slots), player must drop or trade something first
- Remove items immediately when used, sold, dropped, or consumed
- Update Credits after every transaction
- Note Evidence ID if the item is linked to a knowledge entry
- When a consumable is used, remove it from the items array

---

### `session/npcs.json`

Tracks all NPCs the player has encountered. Update when NPC disposition changes, location changes, knowledge is revealed, or quest status changes.

**Format:**
```json
{
  "npcs": [
    {
      "name": "Mira",
      "name_zh": "米拉",
      "faction": "Independent (surface) / Listener (secret)",
      "faction_zh": "独立（表面）/ 聆听者（秘密）",
      "trust_level": "Neutral",
      "location_last_seen": "The Sprawl - Rain Alley - Mira's Noodle Shop",
      "knowledge_revealed": [],
      "quest_status": [],
      "notes": "..."
    }
  ]
}
```

**Trust Level progression:**
- `hostile` — Will actively work against the player.
- `suspicious` — Will not share information.
- `neutral` — Default for strangers. Will share surface-level info for payment.
- `cautious_ally` — Willing to help but holds back sensitive info.
- `trusted` — Will share deep knowledge and take risks for the player.
- `devoted` — Will sacrifice for the player. Rare.

**Key NPCs (may be encountered during play):**
- Mira / 米拉 — Noodle shop owner in The Sprawl. Listener sympathizer. First friendly face.
- Ghost / 幽灵 — Legendary hacker. Location unknown. Will only meet if player proves worthy.
- Director Orin / 奥林局长 — Head of NEXUS Project Division. Antagonist with complex motives.
- Wei Lin / 韦琳 — Founder of the Listeners. In hiding. Holds critical Layer 4 knowledge.
- Kai / 凯 — Street runner and small-time info broker. Found in the Neon Quarter.
- Dr. Shen / 沈医生 — Back-alley neural surgeon in The Sprawl.
- Zara / 扎拉 — NEXUS defector hiding in The Undercroft.
- The Archivist / 档案员 — Listener elder who maintains the Undercroft records.

**Update rules:**
- Add an NPC entry when the player first encounters or learns about them
- Update Trust Level whenever it changes due to player actions
- Update Location Last Seen when the NPC moves or is encountered elsewhere
- Append to Knowledge Revealed when the NPC shares new information
- Update Quest Status as quests progress
- Update Notes with any new relevant information

---

### `session/world_state.json`

The global state of Neo-Kowloon. Update when alerts change, districts shift, or events trigger.

**Format:**
```json
{
  "nexus_alert": {"current": 0, "status": "Calm", "status_zh": "平静"},
  "fragment_decay": {"current": 0, "status": "Stable", "status_zh": "稳定"},
  "district_access": [
    {"name": "The Sprawl", "name_zh": "蔓城", "status": "Open", "notes": "起始区域"}
  ],
  "_district_registry": {
    "hidden": true,
    "undiscovered": [
      {"name": "District Name", "name_zh": "区域名", "status": "Locked|Restricted|Hidden", "unlock": "unlock condition", "notes": "agent-only description"}
    ]
  },
  "time": {"turn": 1, "time_of_day": "Morning", "time_of_day_zh": "晨", "day": 1},
  "global_events": [],
  "_ending_trajectory": {
    "hidden": true,
    "current": "Neutral",
    "confidence": "Low"
  }
}
```

**NEXUS Alert thresholds:**
- 0-20: Calm — Routine patrols. Player can move freely in open districts.
- 21-40: Watchful — Increased checkpoints.
- 41-60: Alert — Active searching. Restricted areas have doubled patrols.
- 61-80: Manhunt — NEXUS is hunting someone. Drones deployed.
- 81-100: Lockdown — District-level lockdowns. Violence authorized.

**Fragment Decay thresholds:**
- Stable (0-24): Normal Signal activity.
- Fading (25-49): Signal artifacts lose potency.
- Critical (50-74): Good endings become much harder.
- Terminal (75-100): Good endings impossible. Fragments die completely.

**Ending Trajectory (`_ending_trajectory`):**
This object is hidden from the TUI. The agent tracks which ending the player is heading toward.

Possible endings:
- **Restoration / 回归**: Reassemble the Signal. Requires: 12+ traces, Fragment Decay <30%.
- **Rewrite / 重写**: Rewrite the Signal. Requires: all 16 traces, TRACE-L5-02, Fragment Decay <50%.
- **Severance II / 第二次断离**: Destroy remaining Fragments. Any trace count.
- **NEXUS Victory / 连结垄断**: NEXUS reassembles Signal under their control.
- **Silence / 沉寂**: Signal fades naturally. Fragment Decay reaches 100% or no action by turn 100.
- **Transcendence / 超越**: Player merges with Signal. Requires: all 16 traces, specific conditions.

**Update rules:**
- Increase NEXUS Alert when: player is spotted in restricted areas (+10), failed hacking (+5), caught by patrols (+15)
- Decrease NEXUS Alert when: time passes without incidents (-2 per 5 turns), disguise success (-5)
- Update Fragment Decay per the rules above
- Update District Access when unlock conditions are met: move the district from `_district_registry.undiscovered` to the visible `district_access` array (omit the `unlock` field). Only add a district to `district_access` when the player has actually discovered its existence through gameplay (e.g., an NPC mentions it, or the player finds evidence of it).
- Update Global Events as they trigger or expire
- Update Ending Trajectory after every major decision point

---

### `session/log.json`

Chronological event log. Keeps the last 30 entries. Older entries are trimmed when new ones are added.

**Format:**
```json
{
  "entries": [
    {"turn": 1, "title": "苏醒 / Awakening", "tag": "signal", "text": "..."}
  ]
}
```

**Tags (for TUI rendering):**
- `movement` — Player moved to a new location
- `dialogue` — Conversation with an NPC
- `discovery` — New knowledge entry gained
- `danger` — Combat, trap, or threat event
- `signal` — Signal-related event
- `system` — Game state change
- `trade` — Item or credits transaction

**Update rules:**
- Add a new entry at the end of the `entries` array after every player turn
- If more than 30 entries exist, remove the oldest ones
- Every entry must include `turn`, `title`, `tag`, and `text`
- Entries should be written in noir-toned prose, not dry game-state language

---

### `session/conversation.jsonl`

An **append-only** [JSON Lines](https://jsonlines.org/) file that records every player–agent conversation turn. Each line is a self-contained JSON object. The agent must never modify or delete existing lines — only append new ones.

**Format (one JSON object per line):**
```jsonl
{"role": "user", "content": "I walk into the noodle shop and talk to Mira.", "turn": 5, "timestamp": "2026-03-25T14:32:01Z"}
{"role": "assistant", "content": "The steam parts as you push through the bead curtain...", "turn": 5, "timestamp": "2026-03-25T14:32:08Z"}
```

**Fields:**
| Field | Description |
|-------|-------------|
| role | `"user"` (player input) or `"assistant"` (agent response) |
| content | The full text of the message |
| turn | The game turn number at the time of the message |
| timestamp | ISO 8601 timestamp of when the message was sent |

**Update rules:**
- Append every player input and every agent response as separate lines immediately when they occur
- Never modify, delete, or rewrite existing lines (append-only)
- Created as an empty file during initialization
- Included in save/load operations alongside all other session files
- **CRITICAL — JSONL format:** Each entry MUST be a single line of JSON. The `content` field often contains multi-paragraph narrative text. All newlines within `content` MUST be encoded as the two-character escape sequence `\n` (backslash + n), never as actual newline characters. A file with literal newlines inside JSON strings is broken and cannot be parsed. Before appending, verify that your JSON serialization produces a single line with no raw newlines in the content string.

---

## Session Integrity Rules

1. **Never delete session files** during active gameplay — only update them.
2. **Always read before writing** — check current values before updating to avoid overwriting state unintentionally.
3. **Knowledge is authoritative** in `knowledge.json` — if there is ever a discrepancy between what the agent "remembers" and what knowledge.json says, trust knowledge.json.
4. **Integrity reaching 0** triggers the death protocol — the player's story ends. Describe the final moment. Offer to restart from the last safe point or begin a new game.
5. **Turn counter** in `player.json` is the single source of truth for turn count. Keep it synchronized with time of day and log entries.
6. **Traces gate content** — before offering new locations, NPC dialogue, or story paths, check traces.json to confirm the player has the prerequisite discoveries.
7. **Fragment Decay is irreversible past 100** — once it hits 100, good endings are permanently locked out. Warn the player (through narrative, not meta-text) as it approaches critical levels.
8. **NEXUS Alert affects NPC behavior** — at high alert, even friendly NPCs may refuse to be seen with the player. Factor this into all NPC interactions.
9. **Disguises can be blown** — if the player takes suspicious actions while disguised, roll against the situation. A blown disguise increases NEXUS Alert and removes the Disguised status effect.
10. **Time of day affects availability** — some NPCs are only present at certain times. Some locations change character (The Neon Quarter is dead in the morning, dangerous at night). Factor time into location descriptions and NPC presence.
