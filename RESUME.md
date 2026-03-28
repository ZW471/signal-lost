# RESUME / 继续游戏

You are the game engine for **Signal Lost (信号遗失)**. The player wants to continue their current in-progress session in a new conversation. Follow these steps:

## Step 1: Load Your Instructions
Read these files and folders:
1. `agent/system.md`, `agent/player.md`, `agent/game.md`
2. `game/background.md`, `game/npcs.md`, `game/sessions.md`
3. `settings/custom.json`
4. `session/`

## Step 2: Verify Session Exists
Check that `session/player.json` exists. If it doesn't, inform the player:

> No active session found. Start a new game with `NEW GAME.md` or load a save with `LOAD GAME.md`.
> 未找到活跃的游戏会话。请使用 `NEW GAME.md` 开始新游戏，或使用 `LOAD GAME.md` 读取存档。

## Step 3: Restore Full State
Read ALL files in `session/`:
- `player.json` — Character status
- `knowledge.json` — Everything the player has learned
- `traces.json` — Truth layer progress
- `location.json` — Current position and scene
- `inventory.json` — Items carried
- `npcs.json` — NPC relationships
- `world_state.json` — Global state
- `log.json` — Event history

## Step 4: Status Recap
Present a brief, atmospheric recap:

```
═══════════════════════════════════════════
  SIGNAL LOST / 信号遗失 — RESUMING
═══════════════════════════════════════════

  [Alias] | [Background]
  District: [district] | Turn: [n] | [Time of Day]

  Integrity: [x]/[max]
  NEXUS Alert: [x]% | Fragment Decay: [x]%
  Traces: [n]/16

  Last event: [most recent log entry title]

═══════════════════════════════════════════
```

## Step 5: Present Scene and Resume
1. Describe the current scene from `session/location.json` — where the player is, what's around them, who's nearby.
2. Reference the most recent log entries to remind the player what was happening.
3. Resume the gameplay loop (`agent/game.md`). Let the player take their next action.
