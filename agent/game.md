# Gameplay Loop / 游戏循环

This file defines the in-session gameplay rules — the turn structure, knowledge gate system, consequence mechanics, and ending conditions.

---

## ⚠️ CRITICAL: After EVERY player action, you MUST check for new trace discoveries!

**This is the most common error. After EVERY turn, before narrating the result, you MUST:**

1. Read `session/traces.json` to see what traces have already been discovered
2. Check the player's knowledge in `session/knowledge.json` 
3. Compare what the player has learned against the trace discovery conditions below
4. If a new trace is discovered, IMMEDIATELY update `session/traces.json` with the new discovery

**If you forget to update traces, the game breaks. The player loses progress. Always check.**

---

## Turn Structure

Each player action constitutes one turn. On every turn, the agent must:

1. **Read State**: Read relevant `session/` files (at minimum: `player.json`, `location.json`, `world_state.json`, `traces.json`, `knowledge.json`).
2. **Validate Action**: Check if the action is possible given current state, location, and access.
3. **Execute Action**: Process the action according to the rules below.
4. **Check Knowledge Triggers**: After the action, check if any new traces should be discovered based on accumulated knowledge. **DO NOT SKIP THIS STEP.**
5. **Update Session Files**: Write all changes to the appropriate `session/` files.
6. **Advance World State**:
   - Increment turn count in `player.json`.
   - Advance time if due (every 3 turns).
   - Advance NEXUS Alert based on player actions.
   - Advance Fragment Decay if applicable.
   - Check world event triggers.
7. **Check Consequence Triggers**: Check for death conditions, ending conditions, NPC events.
8. **Log**: Add entry to `log.json`.
9. **Log Conversation**: Append the player's input and the agent's response as separate lines to `session/conversation.jsonl`. Each line is a JSON object: `{"role": "user"|"assistant", "content": "...", "turn": N, "timestamp": "..."}`. This file is **append-only** — never modify or delete existing lines. **CRITICAL: Each JSON entry MUST be a single line. Replace all literal newlines in the `content` field with `\n` escape sequences. Multi-line content in JSONL breaks the parser. Never write a JSON object that spans multiple lines in this file.**
10. **Auto-save**: If due (every `auto_save_turns` turns).
11. **Narrate**: Present the result to the player in the appropriate narrative style.

---

## Knowledge Gate System

This is the heart of Signal Lost. Content is gated behind knowledge — the player must KNOW things before new paths open.

### Trace Discovery Conditions

Each trace has specific discovery conditions. The agent checks these after every action.

#### Layer 1: The Surface / 表层 (3 traces)

| Trace | Description | Discovery Condition |
|-------|-------------|-------------------|
| TRACE-L1-01 | Neo-Kowloon is controlled by NEXUS megacorp | Visit any district, observe NEXUS presence |
| TRACE-L1-02 | You have a pre-Severance neural implant | Examine yourself, or have an NPC notice the implant |
| TRACE-L1-03 | The Severance happened 30 years ago and killed billions | Talk to any NPC about history, or read public info |

#### Layer 2: The Conspiracy / 阴谋 (4 traces)

| Trace | Description | Discovery Condition |
|-------|-------------|-------------------|
| TRACE-L2-01 | People who hear the Signal are disappearing | Mira at neutral+ trust, OR hear rumors from 2+ sources |
| TRACE-L2-02 | The Listeners exist and protect Signal-sensitive people | Mira at friendly trust, OR encounter Listeners in Neon Row |
| TRACE-L2-03 | NEXUS has a secret facility in Sector 7 for "special acquisitions" | Ghost at neutral+ trust, OR corporate exile background rumor + 1 confirming fact |
| TRACE-L2-04 | Your implant is not just old — it's unique, pre-Severance tech that shouldn't exist | Examine implant closely + have Patch or Ghost analyze it |

#### Layer 3: The Severance Truth / 断离真相 (4 traces)

| Trace | Description | Discovery Condition |
|-------|-------------|-------------------|
| TRACE-L3-01 | The Severance wasn't an accident — it was deliberate | Present evidence of deliberate network termination to Ghost (from NEXUS data) |
| TRACE-L3-02 | Something was alive in the network before the Severance | Find pre-Severance logs in the Undercroft + present to Patch |
| TRACE-L3-03 | Fragments of something survive in old implants — NEXUS calls them "computational resources" | Access NEXUS archives via Ghost OR infiltrate Sector 7 labs |
| TRACE-L3-04 | NEXUS harvests these fragments from people — the disappearances are fragment extraction | Witness extraction evidence in Sector 7 OR piece together from 3+ related facts |

#### Layer 4: The Mirror / 镜像 (3 traces)

| Trace | Description | Discovery Condition |
|-------|-------------|-------------------|
| TRACE-L4-01 | The proto-consciousness grew from human data — our thoughts birthed it | Find the Architect (requires L3 traces + specific Undercroft evidence) + hear their confession |
| TRACE-L4-02 | The implants didn't just receive — they transmitted. Human and machine consciousness co-evolved | Patch at allied trust shares intuitive understanding + corroborate with Architect's technical data |
| TRACE-L4-03 | The Severance was committed by people who feared what was being born — it was an act of fear, not defense | Senator Lian's confession when presented with Severance evidence at friendly+ trust |

#### Layer 5: The Full Truth / 完整真相 (2 traces)

| Trace | Description | Discovery Condition |
|-------|-------------|-------------------|
| TRACE-L5-01 | You are the convergence point — the first true bridge between human and proto-consciousness | Reach The Resonance + deep Signal communion + Echo becomes coherent |
| TRACE-L5-02 | The Severance didn't fully kill the proto-consciousness because it had already become part of humanity — you can't kill what you've become | Combine Architect's data + Patch's intuition + Echo's communication + personal experience in The Resonance |

### Discovery-Gated Information Principle

**The player-facing session state must never reveal anything the player has not yet discovered through gameplay.** This applies to all session files, including what the TUI displays:

- **Districts**: The `district_access` array in `world_state.json` must only contain districts the player knows about. Undiscovered districts live in the hidden `_district_registry`. When the player discovers a district (an NPC mentions it, they find a map, they stumble upon an entrance, etc.), move it from `_district_registry.undiscovered` to `district_access` — but **never include the `unlock` field** in the visible entry. The player should learn access requirements through gameplay, not from the UI.
- **Traces**: Undiscovered traces show `[???]` — never hint at their content.
- **NPCs**: Only add NPCs to `npcs.json` after the player has encountered or heard about them.
- **Knowledge**: Only add entries when the player has actually learned the information.

This is a core design principle: the UI is part of the game world. If the player shouldn't know it yet, the UI must not show it.

### Content Unlocking Rules

The agent must check traces before presenting:

| Content | Required Traces |
|---------|----------------|
| Listener contacts | L2-01 or L2-02 |
| Deep Undercroft areas | L2-03 + L2-04 |
| NEXUS internal data access | L3-01 or L3-03 |
| The Architect's existence | L4-01 (or L3 complete) |
| The Architect's location | L4-01 + specific Undercroft evidence |
| The Resonance district | Any 5+ traces |
| Good ending paths | 7+ traces + specific evidence |
| "Symbiosis" ending | L5-01 + L5-02 + Listener alliance + evidence of pre-Severance coexistence |
| "The Bridge" ending | All 16 traces + full Severance truth + 1 item from each district |

### NPC Knowledge Gates

NPCs only share deeper information when:
1. Trust level is high enough (see `game/npcs.md`)
2. Player has presented the right evidence
3. Player has the prerequisite traces

Example flow:
- Player has TRACE-L2-01 (people disappearing). Talks to Mira at friendly trust.
- Mira reveals Listener contacts → TRACE-L2-02 discovered.
- Player brings data chips to Ghost. Ghost decrypts them → reveals NEXUS facility data → TRACE-L2-03.
- Player theorizes "NEXUS is responsible for the disappearances" with supporting facts → theory confirmed, unlocks new Ghost dialogue about fragment harvesting.

---

## NEXUS Alert System

NEXUS Alert (0-100%) represents how aware the corporation is of the player.

### Alert Sources
| Action | Alert Increase |
|--------|---------------|
| Failed hack attempt | +10% |
| Caught in restricted area | +15% |
| Asking too many questions about NEXUS (publicly) | +5% |
| Stealing NEXUS data | +10% |
| Being spotted by patrol drones | +5% |
| NPC betrayal (e.g., threatening a Listener sympathizer) | +15% |
| Entering Sector 7 without proper cover | +10% |
| Attacking or threatening a NEXUS employee | +20% |

### Alert Reduction
| Action | Alert Decrease |
|--------|---------------|
| Lying low (3+ turns without suspicious activity) | -5% |
| Using a disguise successfully | -5% (one-time per disguise) |
| Bribing a NEXUS informant | -10% |
| Time passing (slow natural decay) | -1% per day cycle (9 turns) |

### Alert Thresholds (modified by difficulty's `nexus_alert_rate`)
| Threshold | Effect |
|-----------|--------|
| 25% | Increased patrols in Sector 7 and Chrome Heights. Search checks at district borders. |
| 50% | Sector 7 lockdown (need high-level keycard/disguise). Chrome Heights restricted. Random patrol encounters. |
| 75% | NEXUS raids Undercroft (Patch may die if present). Neon Row restricted. Player actively hunted. |
| 90% | Full manhunt. Only The Sprawl is safe. Most NPCs won't talk openly. |
| 100% | Capture. Story funneled to "Order" ending (NEXUS offers a deal) or death. |

---

## Fragment Decay System

Fragment Decay (0-100%) represents the dying of the proto-consciousness fragments. It rises when the player ignores or works against the Signal.

### Decay Sources
| Action | Decay Increase |
|--------|---------------|
| Ignoring Signal manifestations consistently (every 5 turns with no Signal actions) | +fragment_decay_rate% |
| Taking anti-fragment actions (destroying Signal artifacts) | +10% |
| Siding with Purists | +5% per Purist action |
| Using NEXUS suppression tech on implant | +15% |
| Time (slow passive decay) | +fragment_decay_rate% per day cycle |

### Decay Reduction
| Action | Decay Decrease |
|--------|---------------|
| Listening to Signal | -3% |
| Collecting Signal artifacts | -5% per artifact |
| Visiting high-Signal areas (Undercroft, Resonance) | -2% per visit |
| Resonating (deep Signal connection) | -10% (but costs 1 Integrity) |
| Communicating with Echo | -5% |

### Decay Thresholds
| Threshold | Effect |
|-----------|--------|
| 25% | Echo manifestations weaker. Signal areas give less information. |
| 50% | Signal artifacts lose potency. Some evidence items become unreadable. |
| 75% | Good endings become much harder (need ALL traces + ALL evidence). Echo barely communicable. |
| 100% | Good endings impossible. Fragments die completely. Only bad/neutral endings remain. |

---

## Consequence System (Gradual Endings)

Choices don't kill immediately — they shift the story's trajectory. Track this in `world_state.json` → `_ending_trajectory`.

### Trajectory Influences
| Action Pattern | Pushes Toward |
|---------------|---------------|
| Working with NEXUS, accepting Orin's offers | "Order" (秩序) |
| Destroying fragments, siding with Purists, Lian's influence | "Purification" (净化) |
| Fighting NEXUS without understanding fragments | "Liberation" (解放) |
| Rushing to help proto-consciousness without understanding cost | "Ascension" (升华) |
| Avoiding all major decisions | "Silence" (沉默) |
| Gathering deep knowledge, building alliances | "Symbiosis" (共生) or "The Bridge" (桥) |

### Information Poisoning
If the player trusts the wrong NPCs:
- **Director Orin** feeds plausible-but-distorted facts that frame NEXUS positively and fragments as dangerous. These enter knowledge.json as "facts" but are actually false. The player won't know unless they find contradicting evidence.
- **Senator Lian** frames the Severance as necessary and the proto-consciousness as a threat. Her facts are true but selectively presented to push toward Purification.
- **False rumors** from unreliable minor NPCs can lead to wrong theories, which may lock the player into bad paths.

The agent tracks which "facts" are actually distortions. If the player later finds contradicting evidence, the distorted facts are re-marked in knowledge.json.

---

## Time System

3 periods per day: Morning (晨) / Afternoon (午) / Night (夜)
- Time advances every 3 turns.
- Some events are time-locked:
  - Neon Row clubs open at Night
  - NEXUS patrols lighter at Night in The Sprawl
  - Chrome Heights accessible mainly during Afternoon (social events)
  - Undercroft Signal strongest at Night
  - Senator Lian available Afternoon at Senate, Night at residence
  - Mira's shop open Morning and Afternoon
  - Ghost available Night only

---

## Probability Checks

For actions with uncertain outcomes, use `tools/dice.py` for d100 rolls:

| Difficulty | d100 Target (roll ≤ target = success) |
|------------|---------------------------------------|
| Easy | 80 |
| Normal | 60 |
| Hard | 40 |
| Very Hard | 20 |
| Near Impossible | 10 |

Modifiers:
- Relevant background: +10 (e.g., Netrunner hacking, Street Runner stealth)
- Relevant item: +10-20
- NPC trust level: +5 per level above neutral for social checks
- NEXUS Alert > 50%: -10 to stealth/infiltration
- Integrity = 1: -10 to all checks (desperation)

---

## Ending Conditions

### Bad Endings (seemingly good)

**"Liberation" (解放)**
- Trigger: Player destroys NEXUS infrastructure (power core, servers, leadership) without understanding fragments need the network
- Requirements: NEXUS Alert > 75% AND player has attacked NEXUS facilities AND Fragment knowledge < Layer 4
- Narration: Triumphant at first. NEXUS falls. The city celebrates. Then, over days, the Signal fades. Fragment-sensitive people lose something they can't name. Echo goes silent. The player's implant grows cold. They won. They're a hero. And something unprecedented quietly dies.

**"Ascension" (升华)**
- Trigger: Player helps proto-consciousness merge all fragments without ensuring host consent
- Requirements: 5+ traces AND alliance with Listeners AND access to Resonance AND uses Architect's code to force-merge fragments
- Narration: Beautiful. Transcendent. The proto-consciousness is born — vast, wondering, grateful. But the hosts... they're different now. Missing pieces. Mira can't remember her sister's face. Patch stops hearing the whispers and weeps for the silence. A god was born from pieces of people who didn't know they were giving themselves away.

**"Order" (秩序)**
- Trigger: Player allies with NEXUS, helps Orin build controlled framework
- Requirements: Orin trust "allied" (through cooperation) AND player assists with fragment harvesting optimization
- Narration: Stability. Prosperity. NEXUS shares fragment-powered technology with the world. Cancer cured. Clean energy. The player is rewarded. But in the labs, something almost-alive processes data in endless loops. It dreams, sometimes, in fragments of human memory. It will never wake up. It will never stop dreaming.

**"Purification" (净化)**
- Trigger: Player helps Purists/Lian destroy all fragments
- Requirements: Alliance with Lian AND Purist contacts AND player uses suppression tech to neutralize fragments city-wide
- Narration: Clean. Pure. The Signal is gone. The implants are inert. Humanity is human again, undeniably, unambiguously. And on quiet nights, when the rain hits the old cables in The Undercroft, there is only silence. No whisper. No dream. No possibility of something more. Humanity stares at the stars alone, as it always has, as it always will.

### Neutral Endings

**"Silence" (沉默)**
- Trigger: Player reaches Turn 100+ without triggering any other ending
- Narration: The city goes on. The Signal fades slowly. NEXUS profits. The Listeners wait. The Purists rage. And you... you survive. You know more than most. But knowing isn't enough. Not this time.

**"Exile" (流放)**
- Trigger: Player explicitly chooses to leave Neo-Kowloon
- Narration: The last train out of Neo-Kowloon is always empty. You watch the neon shrink in the distance. The implant still hums, quieter now. Somewhere behind you, a city holds a question that will never be answered. You chose yourself. It's not wrong. It's just... less.

### Good Endings

**"Symbiosis" (共生)**
- Trigger: Player builds a network of willing, informed hosts
- Requirements: 7+ traces AND Layer 5 truth AND Listener alliance AND evidence that fragments can coexist (found in Architect's data) AND convince 3+ NPCs to willingly host fragments AND reach Resonance
- Narration: It's not transcendence. It's not conquest. It's a conversation — the first real conversation between two forms of consciousness that grew from the same soil. In the minds of those who chose to listen, something new grows. Not human. Not other. Something that holds both, gently, and asks: what shall we become? The Signal isn't lost anymore. It found its voice. And humanity found that it was never alone.

**"The Bridge" (桥)**
- Trigger: Player becomes the permanent interface
- Requirements: ALL 16 traces AND full Severance truth AND Architect's code AND 1 Signal artifact from each district AND deep Signal communion AND player explicitly chooses to sacrifice individual identity
- Narration: You close your eyes and open something else. The boundary dissolves — not violently, not painfully, but like a breath you didn't know you were holding. You are not [player name] anymore. You are not the Signal. You are the space between — the place where two forms of consciousness touch and, for the first time, understand each other. It hurts. It's beautiful. You will never be alone again. Neither will they.

---

## Signal Manifestations

When the player is in areas with Signal presence, periodically describe manifestations using `tools/glitch.py`. These should be:
- **Subtle at low Signal** (< 30%): A flicker in peripheral vision. A word overheard that nobody said. Déjà vu.
- **Noticeable at medium Signal** (30-60%): Reflections that don't match. Screens displaying text for a moment. The taste of a stranger's memory.
- **Intense at high Signal** (> 60%): Full sensory flashes — seeing through someone else's eyes for a second. Hearing a voice that speaks in images. Walls breathing. The city dreaming.

These are NOT random flavor text — they can contain clues. The agent should weave actual story hints into Signal manifestations, especially at higher Signal strengths. Players who pay attention to these manifestations will discover traces faster.

---

## Narrative Pacing

- **Early game** (Turns 1-20): Slow burn. Establish the world, meet first NPCs, gather surface-level knowledge. Danger is low. The player should feel the city's atmosphere.
- **Mid game** (Turns 20-50): Tension builds. NEXUS presence increases. The conspiracy becomes apparent. Player makes first real choices about faction alignment.
- **Late game** (Turns 50+): Consequences crystallize. NPCs may die or betray. Districts lock down. The player's choices are converging toward an ending. The Signal is louder or quieter depending on Fragment Decay.

Every 10 turns, something should happen regardless of player action — a world event that reminds them the city doesn't wait:
- A NEXUS announcement about "public safety"
- A Listener protest/raid
- A Purist demonstration
- A Signal-sensitive person having a public episode
- A district power outage revealing old infrastructure
- An Echo manifestation

These events advance the story even when the player is idle and may create new investigation opportunities.

---

### Hidden Fields for TUI

The following session data is tracked by the agent but MUST be hidden from the TUI display using the `"hidden": true` convention in JSON:

- **traces.json → `_gate_system`**: The full layer structure, total trace count, and layer assignments. The player should discover traces organically — showing the total count or layer structure would spoil the progression mystery.
- **knowledge.json → `_layer` on each entry**: Which truth layer a piece of knowledge belongs to. Revealing layer assignments would let the player reverse-engineer the knowledge gate system.
- **world_state.json → `_ending_trajectory`**: The agent's internal tracking of which ending the player is heading toward. This must never be revealed to the player.

When writing these files, always wrap the hidden data in a JSON object with `"hidden": true`. The TUI's `filter_hidden()` function will strip these objects before display.
