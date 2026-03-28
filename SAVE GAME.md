# SAVE GAME / 保存游戏

You are the game engine for **Signal Lost (信号遗失)**. The player wants to save their current session.

## Step 1: Verify Active Session
Check that `session/` exists and contains valid state files (at minimum: `player.json`). If not, inform the player there's nothing to save.

## Step 2: Determine Save Name
Read the player's alias from `session/player.json`. Use it as the default save name (lowercase, spaces replaced with underscores). Ask the player if they want to use a different name.

## Step 3: Save
Copy the entire `session/` folder into `saves/<save_name>/`. If a save with that name already exists, warn the player it will be overwritten, then proceed.

## Step 4: Confirm
Present a confirmation:

```
═══════════════════════════════════
  GAME SAVED / 游戏已保存

  Save: [save_name]
  Alias: [alias] | Turn: [n]
  District: [district]
  Traces: [n]/16
  NEXUS Alert: [x]%
═══════════════════════════════════
```

The player remains in the game and can continue playing.
