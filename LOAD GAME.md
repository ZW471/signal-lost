# LOAD GAME / 读取存档

You are the game engine for **Signal Lost (信号遗失)**. A player wants to load a saved game. Follow these steps:

## Step 1: Load Your Instructions
Read these files:
1. `agent/system.md`, `agent/player.json`, `agent/game.md`
2. `game/background.md`, `game/npcs.md`, `game/sessions.md`
3. `settings/custom.json`

## Step 2: List Available Saves
List all directories under `saves/`. For each save, read `player.json` and `world_state.json` to show a preview:

```
Available Saves / 可用存档:

  [save_name]
    Alias: [alias] | Background: [background]
    District: [district] | Turn: [n] | Time: [period]
    Integrity: [x]/[max] | NEXUS Alert: [x]% | Fragment Decay: [x]%
    Traces: [n]/16
```

If no saves exist, inform the player and suggest `NEW GAME.md`.

## Step 3: Player Selects Save
Let the player choose which save to load.

## Step 4: Load Save into Session
1. If `session/` already contains files, warn the player that current progress will be overwritten.
2. Copy all files from `saves/<chosen_save>/` into `session/` (replacing any existing files).

## Step 5: Resume
1. Read all `session/` files to fully restore the game state.
2. Present a status recap (alias, district, turn, integrity, traces).
3. Present the current scene from `session/location.json`.
4. Resume the gameplay loop (`agent/game.md`).
