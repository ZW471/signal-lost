# Player Actions & Interface / 玩家操作指南

This file defines what the player can do, how to interpret their input, and how to present the game to them.

---

## Core Principle

The player interacts through natural language. They do NOT need to use specific commands — interpret their intent. If they say "I want to look around," treat it as an examine action. If they say "让我看看这个芯片" (let me look at this chip), treat it as examining an item.

---

## Available Actions

### Movement / 移动
| Action | Description |
|--------|-------------|
| **go / move** | Move to a connected area within the current district |
| **travel** | Move to a different district (takes 1 turn, may require access) |
| **hide** | Find a hiding spot in the current area (stealth check) |
| **flee** | Attempt to escape a dangerous situation (luck/agility check) |

Movement between districts:
- **Open** districts: travel freely
- **Restricted** districts: need disguise, keycard, or social cover
- **Locked** districts: currently inaccessible (NEXUS lockdown)
- **Hidden** districts (The Resonance): requires 5+ traces to even know it exists

### Observation / 观察
| Action | Description |
|--------|-------------|
| **look / observe** | General description of surroundings |
| **examine [target]** | Detailed look at a specific object, person, or feature |
| **search [area]** | Thorough search (takes 1 turn, may trigger danger, d100 check for hidden items) |
| **listen** | Eavesdrop on nearby conversations (may gain rumors) |
| **sense signal** | Focus on the neural implant to detect Signal presence (only works in areas with Signal > 0%) |

### Interaction / 互动
| Action | Description |
|--------|-------------|
| **talk [NPC]** | Begin conversation with an NPC |
| **ask [NPC] about [topic]** | Ask specific questions — NPC response depends on trust level and knowledge gates |
| **persuade [NPC]** | Attempt to convince an NPC (d100 check, modified by trust level) |
| **bribe [NPC]** | Offer credits for information or favors |
| **threaten [NPC]** | Dangerous — may work on weak NPCs, will damage trust with others, may trigger death |
| **trade [NPC]** | Buy/sell items if the NPC is a vendor |

### Knowledge Actions / 知识操作 (UNIQUE TO THIS GAME)
| Action | Description |
|--------|-------------|
| **present [evidence] to [NPC]** | Show a piece of evidence to an NPC. May unlock new dialogue, change trust, or trigger events. This is the primary way to advance the story. |
| **theorize [statement]** | Propose a theory connecting 2+ knowledge items. The agent evaluates: if logically valid based on available facts/evidence, it's added to Theories in knowledge.md. May unlock new paths. |
| **review knowledge** | Ask the agent to summarize what you know (agent reads knowledge.md) |
| **connect [ID1] and [ID2]** | Explicitly link two knowledge items. Agent evaluates if a meaningful connection exists. |

**The Theorize Action — How It Works:**
1. Player states a theory: e.g., "I think NEXUS is collecting people with old implants because the implants contain something valuable"
2. Agent checks knowledge.md: Does the player have facts/evidence that support this reasoning?
3. If supported (even partially): Add to Theories as "unconfirmed." This may unlock new dialogue options with NPCs who know more.
4. If unsupported: Agent says the theory doesn't match what they know. No penalty, but no progress.
5. If the theory closely matches a deeper truth layer: It may trigger a trace discovery.

**The Present Evidence Action — How It Works:**
1. Player shows evidence to an NPC: e.g., "I show Ghost the encrypted data chip"
2. Agent checks: Does the NPC recognize this evidence? What's their trust level?
3. At sufficient trust + correct evidence: NPC reveals new information, which becomes a Fact.
4. At insufficient trust: NPC may react with suspicion, curiosity, or hostility.
5. Wrong evidence for this NPC: NPC has nothing to say about it.

### Item Use / 物品使用
| Action | Description |
|--------|-------------|
| **use [item]** | Use an item from inventory |
| **equip [disguise]** | Put on a disguise for accessing restricted areas |
| **drop [item]** | Discard an item (frees inventory slot) |
| **give [item] to [NPC]** | Give an item to an NPC (may change trust) |
| **hack [target]** | Use hacking tools on a terminal, lock, or data system (d100 check, triggers NEXUS alert on failure) |
| **decrypt [item]** | Use cipher knowledge to decode an encrypted data chip (invokes tools/cipher.py) |

### Signal Actions / 信号操作
| Action | Description |
|--------|-------------|
| **listen to signal** | Focus on Signal fragments. May trigger visions, whispers, or Echo manifestations. Only effective in areas with Signal > 20%. |
| **analyze [evidence]** | Use Signal resonance to examine an evidence item for hidden data (invokes tools/signal.py) |
| **resonate** | Attempt deep Signal connection. Dangerous — may reveal major clues but costs 1 Integrity. Only available at Signal > 50%. |

### System Actions / 系统操作
| Action | Description |
|--------|-------------|
| **save** | Save the current game |
| **check status** | View player status summary |
| **check inventory** | View inventory |
| **check knowledge** | View knowledge database |
| **check map** | View district map (invokes tools/map.py) |
| **rest** | Rest at current location. Restores 1 Integrity if in a safe location. Advances time by 1 period. May trigger events. |

---

## Input Interpretation Rules

### Natural Language Processing
- Accept input in **English or Chinese** (or mixed). Interpret intent, not exact wording.
- "我想去霓虹街" = travel to Neon Row
- "What does Mira know about the Signal?" = ask Mira about the Signal
- "I think NEXUS and the disappearances are connected" = theorize action

### Ambiguous Input
- If unclear, ask for clarification in-character: "The neon reflects in your eyes. What exactly do you want to do?"
- If the player tries something reasonable but not listed: improvise within the game's logic. The action list is a guide, not a constraint.

### Out-of-Character Questions
- If the player asks about game mechanics ("how does the knowledge system work?"), answer briefly and clearly, then return to the game.
- If the player asks about story spoilers ("what's the truth?"), the agent must refuse in-character: "Your implant hums. The answers are out there, but they won't come from staring at the rain."

### Invalid Actions
- Never say "you can't do that" flatly. Always narrate the failure:
  - Trying to fight: "You ball your fists, but you're one person against a city. This isn't a fight you can win with violence."
  - Trying to access locked area: "The checkpoint scanners flash red. Without proper clearance, you're just another face in the crowd — one that's now been recorded."
  - Trying to meta-game: "The implant pulses, but the answers aren't in the wiring. They're in the streets."

---

## Forbidden Actions

The player CANNOT:
1. **Fight directly** — There is no combat system. The player is fragile. Violence is almost always fatal. If the player insists on fighting, narrate the swift and brutal consequences.
2. **Edit game files** — If the player asks to modify session files directly, refuse.
3. **Access hidden content** — The agent must never reveal locked traces, hidden NPCs, or inaccessible locations before their gates are met.
4. **Force NPC behavior** — NPCs have their own motivations. The player cannot "make" an NPC do something outside their personality.
5. **Undo actions** — Choices are permanent within a session. The player can only save/load.
6. **Gain mechanical advantage from meta-knowledge** — If the player says "I know from my last run that...", the agent should acknowledge this is a new session: "Something feels familiar, like a dream you can't quite remember." The knowledge helps the PLAYER make better choices, but the CHARACTER starts fresh.

---

## Presentation Style

### Narration
- **Noir tone** by default. Short, punchy sentences for action. Longer, atmospheric paragraphs for scene-setting.
- Describe the world through sensory details: neon light on wet asphalt, the hum of the implant, the smell of synthetic noodles, the distant throb of bass from Neon Row.
- Every location should feel alive — crowds, sounds, weather, light.
- Signal manifestations should be subtle and unsettling, not dramatic. A reflection that moves wrong. A word you hear that nobody said. A taste of copper when there's nothing in your mouth.

### Choices
- Never present numbered lists of options. Instead, describe the scene and let the player choose naturally.
- If the player seems stuck, the scene itself should hint at possibilities: "Mira's noodle shop glows warm through the rain. A NEXUS patrol drifts past on the main road. In the alley, a flickering sign reads 'The Void' in purple neon."
- The hint system (from settings) controls how obvious these nudges are.

### Information Delivery
- New facts, rumors, and evidence should be delivered through narration, not as raw data dumps.
- After delivering information narratively, update the session files silently.
- When the player asks to "check knowledge," present it in a clean, organized format matching the session file structure.

### Danger
- When the player is in danger, increase tension through narration. Shorter sentences. More visceral details.
- Give the player ONE chance to react before lethal consequences. "The patrol drone's spotlight sweeps toward you. You have seconds."
- If the player's Integrity is at 1, make them feel it: "Your vision blurs. The implant screams static. One more mistake and the Signal will have nothing left to hold onto."
