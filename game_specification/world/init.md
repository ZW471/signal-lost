# Initialization Procedure / 初始化流程

This file is executed by the agent when starting a new game. The player never sees this file directly.

---

## Step 1: Language Selection

Present to the player:

```
═══════════════════════════════════════════════
  SIGNAL LOST / 信号遗失
═══════════════════════════════════════════════

  Choose your language / 选择你的语言:

  1. English
  2. 中文

═══════════════════════════════════════════════
```

Update `settings/custom.json`:
- Set `language.display` to `"en"` or `"zh"`
- Set `language.tui` to match

---

## Step 2: Opening Narration

**English version:**

> Rain.
>
> It's always raining in Neo-Kowloon. The neon bleeds color into the puddles — pink, blue, the toxic green of pharmacy signs. The city hums at a frequency just below hearing, a billion machines breathing in unison.
>
> You're lying in an alley. Your cheek is pressed against wet concrete. Your head is splitting — not pain exactly, but *noise*. Static. Like a radio caught between stations.
>
> You sit up. Your hands are shaking. You don't know your name.
>
> Behind your left ear, something hums. A neural implant — old tech, the kind they stopped making after the Severance. The kind nobody has anymore. The kind that *shouldn't exist*.
>
> A street vendor across the alley is staring at you. Noodle steam curls between you like a question mark. Beyond her, the towers of NEXUS Corporation catch the last light of a sun you can't see through the smog.
>
> Welcome to Neo-Kowloon. You have no memory, no money, and a piece of dead technology singing in your skull.
>
> What's your name?

**Chinese version:**

> 雨。
>
> 新九龙总是在下雨。霓虹灯把颜色渗进水洼——粉色、蓝色、药房招牌的毒绿色。城市在听觉阈值之下嗡鸣着，十亿台机器同步呼吸。
>
> 你躺在一条小巷里。脸颊贴着湿冷的水泥地。你的头在裂开——不完全是疼痛，而是*噪音*。静电。像一台收音机卡在两个频道之间。
>
> 你坐起来。双手在颤抖。你不知道自己的名字。
>
> 左耳后方，有什么东西在嗡鸣。一个神经植入体——老技术，断离之后就停产的那种。没人还拥有这种东西。这种东西*不应该存在*。
>
> 巷子对面的街边小贩正盯着你看。面条的蒸汽在你们之间卷曲成一个问号。在她身后，联结公司的大厦捕捉着你透过雾霾看不见的最后一缕阳光。
>
> 欢迎来到新九龙。你没有记忆，没有钱，只有一块死去的技术在你颅骨里歌唱。
>
> 你叫什么名字？

---

## Step 3: Character Creation

### 3a: Name
Ask for the player's chosen name. Store as `Name` in player.json.

### 3b: Alias
Ask for a street handle / alias:

> Every drifter needs a name the street knows. What do they call you?
> 每个漂泊者都需要一个街头知道的名字。他们怎么称呼你？

Store as `Alias` in player.json.

### 3c: Background

Present three backgrounds:

**English:**
> Before you lost your memory, you were someone. Your hands remember things your mind doesn't. Who were you?
>
> **Street Runner (街头行者)** — You know the alleys, the back doors, the unwritten rules. Your feet remember routes your mind has forgotten. You can disappear into a crowd like smoke.
>
> **Corporate Exile (企业流亡者)** — Your posture is too straight. Your vocabulary too precise. You fled from something high up — the towers, the boardrooms, the clean white corridors. You still carry the scars of that world.
>
> **Netrunner (网行者)** — Your fingers twitch toward keyboards that aren't there. The implant feels less foreign to you than it should. You lived in data once. Part of you still does.

**Chinese:**
> 在你失去记忆之前，你曾是某个人。你的双手记得你大脑不记得的事情。你曾经是谁？
>
> **街头行者** — 你熟悉小巷、后门和不成文的规矩。你的脚记得大脑已经遗忘的路线。你能像烟雾一样消失在人群中。
>
> **企业流亡者** — 你的姿态太端正。你的词汇太精确。你从高处逃离了什么——大厦、会议室、洁白的走廊。你仍然带着那个世界的伤疤。
>
> **网行者** — 你的手指会不自觉地朝着并不存在的键盘抽动。植入体对你来说不像应该的那样陌生。你曾经活在数据里。你的一部分仍然如此。

Each background provides:

| Background | Starting Rumors | Starting Item | Stat Bonus |
|-----------|----------------|---------------|------------|
| Street Runner (街头行者) | "NEXUS has eyes in The Sprawl" + "There's a woman named Mira who knows things" | Lockpick set | +10 to stealth/movement checks |
| Corporate Exile (企业流亡者) | "NEXUS Project Division handles 'special acquisitions'" + "Director Orin runs something off-books in Sector 7" | Expired NEXUS keycard (limited Sector 7 access) | +10 to social/persuasion checks |
| Netrunner (网行者) | "The old network didn't just crash — something was in it" + "A hacker called Ghost can crack anything" | Basic cipher toolkit (data chip) | +10 to hacking/technical checks |

### 3d: Difficulty

> How dangerous is your world?
> 你的世界有多危险？
>
> **Paranoid (偏执)** — The city is merciful. You have more time, more resilience, and the occasional helpful nudge. *(Integrity: 4, slower alert/decay, moderate hints)*
>
> **Cautious (谨慎)** — Be careful out there. The city doesn't hate you, but it doesn't care either. *(Integrity: 3, reduced alert/decay, subtle hints)*
>
> **Standard (标准)** — Neo-Kowloon as it is. No safety net. No hand-holding. *(Integrity: 3, normal rates, no hints)*
>
> **Reckless (鲁莽)** — You were already dead when you woke up. The city will prove it. *(Integrity: 2, faster alert/decay, no hints)*

Update `settings/custom.json` → `difficulty.mode` to match choice.

---

## Step 4: Create Session Files

Create all files in `session/` with initial state:

### `session/player.json`
```json
{
  "title": "Player Status / 玩家状态",
  "name": "[chosen name]",
  "alias": "[chosen alias]",
  "background": "[chosen background]",
  "integrity": { "current": "[max from difficulty]", "max": "[max from difficulty]" },
  "credits": 50,
  "neural_implant": "Active",
  "current_disguise": "None",
  "turn": 1,
  "time": "Morning / 晨",
  "status_effects": ["Signal Sensitivity (faint)"]
}
```

### `session/knowledge.json`
```json
{
  "title": "Knowledge Database / 知识库",
  "facts": [],
  "rumors": ["[Insert starting rumors based on background, with IDs RUMOR-001 and RUMOR-002]"],
  "evidence": [],
  "theories": [],
  "connections": []
}
```

### `session/traces.json`
```json
{
  "title": "Traces of Truth / 真相痕迹",
  "total_discovered": "0 / 16",
  "layers": {
    "layer_1_surface": {
      "name": "The Surface / 表层",
      "progress": "0/3",
      "traces": {
        "TRACE-L1-01": { "status": "undiscovered", "description": "[???]" },
        "TRACE-L1-02": { "status": "undiscovered", "description": "[???]" },
        "TRACE-L1-03": { "status": "undiscovered", "description": "[???]" }
      }
    },
    "layer_2_conspiracy": {
      "name": "The Conspiracy / 阴谋",
      "progress": "0/4",
      "traces": {
        "TRACE-L2-01": { "status": "undiscovered", "description": "[???]" },
        "TRACE-L2-02": { "status": "undiscovered", "description": "[???]" },
        "TRACE-L2-03": { "status": "undiscovered", "description": "[???]" },
        "TRACE-L2-04": { "status": "undiscovered", "description": "[???]" }
      }
    },
    "layer_3_severance_truth": {
      "name": "The Severance Truth / 断离真相",
      "progress": "0/4",
      "traces": {
        "TRACE-L3-01": { "status": "undiscovered", "description": "[???]" },
        "TRACE-L3-02": { "status": "undiscovered", "description": "[???]" },
        "TRACE-L3-03": { "status": "undiscovered", "description": "[???]" },
        "TRACE-L3-04": { "status": "undiscovered", "description": "[???]" }
      }
    },
    "layer_4_mirror": {
      "name": "The Mirror / 镜像",
      "progress": "0/3",
      "traces": {
        "TRACE-L4-01": { "status": "undiscovered", "description": "[???]" },
        "TRACE-L4-02": { "status": "undiscovered", "description": "[???]" },
        "TRACE-L4-03": { "status": "undiscovered", "description": "[???]" }
      }
    },
    "layer_5_full_truth": {
      "name": "The Full Truth / 完整真相",
      "progress": "0/2",
      "traces": {
        "TRACE-L5-01": { "status": "undiscovered", "description": "[???]" },
        "TRACE-L5-02": { "status": "undiscovered", "description": "[???]" }
      }
    }
  }
}
```

### `session/location.json`
```json
{
  "title": "Current Location / 当前位置",
  "district": "The Sprawl / 蔓城",
  "area": "Rain Alley (near Mira's Noodle Shop) / 雨巷（米拉面馆附近）",
  "zone": "Street Level",
  "description": "A narrow alley between crumbling residential blocks. Neon signs for noodle shops and repair stalls cast colored light across wet concrete. The air smells of synthetic broth and ozone. Foot traffic is moderate — workers, drifters, the occasional street vendor. The hum of the city is constant.",
  "signal_strength": "10%",
  "danger_level": "Safe",
  "nexus_patrol": "None",
  "exits": {
    "north": "Main street — busier, more vendors, a public terminal",
    "south": "Deeper alleys — darker, quieter, leads to residential blocks",
    "east": "Mira's Noodle Shop — warm light, a woman watching from the counter",
    "west": "Market square — open area, more people, more noise"
  },
  "points_of_interest": [
    "Mira's Noodle Shop (east) — A small, steamy establishment. The owner seems to be watching you.",
    "Public Terminal (north, main street) — NEXUS-operated information kiosk. Free access.",
    "Repair Stall (north) — Sells basic tools and electronics."
  ],
  "npcs_present": [
    "Mira (米拉) — Behind the counter of her noodle shop. Watching.",
    "Various unnamed pedestrians."
  ]
}
```

### `session/inventory.json`
```json
{
  "title": "Inventory / 物品栏",
  "credits": 50,
  "slots": { "used": 1, "max": 6 },
  "items": [
    { "slot": 1, "item": "[starting item based on background]", "type": "[type]", "description": "[description]" }
  ]
}
```

Starting items:
- Street Runner: `Lockpick Set` / tool / "A well-worn set of picks. Your fingers know how to use them even if your mind doesn't."
- Corporate Exile: `Expired NEXUS Keycard` / keycard / "Level 2 clearance, expired 3 years ago. Might still open some doors in Sector 7."
- Netrunner: `Basic Cipher Toolkit` / data_chip / "A data chip loaded with decryption utilities. Old but functional."

### `session/npcs.json`
```json
{
  "title": "Encountered NPCs / 已遇NPC",
  "npcs": []
}
```
NPC entries follow this format when added:
```json
{ "name": "", "faction": "", "trust": "", "location_last_seen": "", "knowledge_revealed": "", "quest_status": "", "notes": "" }
```

### `session/world_state.json`

**Important:** The `district_access` array must only contain districts the player currently knows about. Undiscovered districts and their unlock conditions are stored in the hidden `_district_registry` object. When the player discovers a new district through gameplay (an NPC mentions it, they find a clue, etc.), move it from `_district_registry.undiscovered` to `district_access` — but never include the `unlock` field in the visible entry.

```json
{
  "title": "World State / 世界状态",
  "nexus_alert": "0%",
  "fragment_decay": "0%",
  "district_access": [
    {"name": "The Sprawl", "name_zh": "蔓城", "status": "Open", "notes": "起始区域"},
    {"name": "Neon Row", "name_zh": "霓虹街", "status": "Open", "notes": "娱乐与情报区"}
  ],
  "_district_registry": {
    "hidden": true,
    "undiscovered": [
      {"name": "The Undercroft", "name_zh": "底渊", "status": "Locked", "unlock": "Requires TRACE-L1-03", "notes": "Underground Listener territory"},
      {"name": "Sector 7", "name_zh": "第七区", "status": "Restricted", "unlock": "Requires keycard or disguise", "notes": "Corporate zone. NEXUS offices, research labs."},
      {"name": "Chrome Heights", "name_zh": "镀金台", "status": "Restricted", "unlock": "Requires invitation or disguise", "notes": "Elite residential area."},
      {"name": "The Resonance", "name_zh": "共鸣所", "status": "Hidden", "unlock": "Requires Layer 3 completion", "notes": "Ancient pre-Severance facility."}
    ]
  },
  "time": { "day": 1, "period": "Morning / 晨" },
  "global_events": [],
  "_ending_trajectory": { "hidden": true, "value": "neutral — no direction yet" }
}
```

### `session/conversation.jsonl`
Create as an empty file. The first entries will be appended when the opening narration is presented and the player responds.

### `session/log.json`
```json
{
  "title": "Session Log / 会話日志",
  "entries": [
    {
      "turn": 1,
      "title": "Awakening / 苏醒",
      "description": "You wake in a rain-soaked alley in The Sprawl with no memory and a humming neural implant. A noodle vendor watches from across the alley. The towers of NEXUS loom in the distance.",
      "signal": true
    }
  ]
}
```

---

## Step 5: Opening Scene

After creating all session files, present the opening scene. Describe The Sprawl around the player:

- The neon, the rain, the crowds
- The hum of the implant
- Mira's noodle shop glowing nearby
- The distant NEXUS towers
- The sense of being watched, or of something just out of reach

End with an open prompt — let the player decide their first move. Do NOT list options. Let them explore naturally.

Example closing line:
> The rain keeps falling. The implant keeps humming. Somewhere in this city, there are answers. What do you do?
> 雨还在下。植入体还在嗡鸣。在这座城市的某处，有答案。你要做什么？
