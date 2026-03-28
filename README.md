# Signal Lost / 信号遗失

*The network died thirty years ago. Something inside it didn't.*

---

## Background

Rain falls on Neo-Kowloon like it always has — relentless, neon-stained, indifferent. Thirty years ago, the global network collapsed in what they call the Severance. Billions died. The megacorporation NEXUS rebuilt the city from the ashes, and now controls everything: water, power, data, truth.

You wake in an alley with no memory and a neural implant humming behind your left ear. The implant is old — pre-Severance tech that shouldn't exist anymore. It whispers to you in frequencies that have no name. Sometimes, in the static, you hear something that sounds almost like a voice.

They call it the Signal. Most people can't hear it. Those who can tend to disappear.

This is not a story about saving the world. This is a story about understanding it — and what you find may change what you think it means to be human.

---

## How to Play

### With the TUI (Recommended)

The TUI provides a split-screen experience: a live terminal on the left for interacting with your AI agent, and a tabbed dashboard on the right showing all game state.

```bash
cd "Examples/Signal Lost/compiled"
.venv/bin/python tui/tui_viewer.py .
```

Options:
- `--terminal false` — Dashboard only (use a separate terminal for the agent)
- `--refresh 10` — Auto-refresh every 10 seconds (default: 5)
- `--refresh 0` — Disable auto-refresh (press `r` to refresh manually)

TUI shortcuts: `r` refresh, `t` focus terminal, `1`-`9` switch tabs, `q` quit.

### With an AI Agent

Tell your AI agent to read `compiled/NEW GAME.md` to start a new game. Compatible agents:
- Claude Code
- Any agentic coding assistant that can read/write files

---

## Game Lifecycle

| Command | What it does |
|---------|-------------|
| `NEW GAME.md` | Start a fresh playthrough — choose language, name, background, difficulty |
| `RESUME.md` | Continue the current session in a new conversation |
| `LOAD GAME.md` | Load a previously saved game |
| `SAVE GAME.md` | Save the current session |

---

## Game Features

- **Knowledge-Based Progression** — No levels, no XP. You grow by discovering facts, verifying rumors, collecting evidence, and forming theories. What you know determines what paths open.
- **5 Layers of Truth** — The city hides its secrets in layers. Surface reality is just the beginning. Each layer reveals a deeper, stranger truth about Neo-Kowloon, the Severance, and what the Signal really is.
- **16 Traces** — Key discoveries that gate new content. Track your progress toward the full truth.
- **12+ Endings** — Most look like victories but carry hidden costs. Only 2 endings are truly good — and they require deep understanding, not just luck.
- **3 Backgrounds** — Street Runner, Corporate Exile, or Netrunner. Each starts with different knowledge and items.
- **7 Major NPCs** — Each with trust mechanics, knowledge gates, faction loyalties, and the capacity to help, betray, or mislead you.
- **6 Districts** — From the neon slums of The Sprawl to the hidden depths of The Resonance. Access is gated by knowledge, disguises, and world state.
- **The Theorize Mechanic** — Propose theories connecting your knowledge. Valid theories unlock new paths and dialogue.
- **No Combat** — You are fragile. Violence is almost always fatal. Survive through knowledge, cunning, and the right words.
- **Bilingual Support** — Play in English or 中文. Switch languages mid-game by saving and reloading.
- **6 Python Tools** — Dice roller, cipher decoder, Signal analyzer, district map, NPC generator, atmospheric glitch generator.
- **Cyberpunk TUI** — Neon-themed terminal dashboard with real-time session state, knowledge tracker, trace progress, and integrated terminal.

---

## Settings

Edit `settings/custom.json` to customize:

- **Difficulty**: `paranoid` (forgiving) → `cautious` → `standard` → `reckless` (brutal)
- **Language**: `display` for agent narration, `tui` for dashboard labels
- **Narrative**: Verbosity (terse/standard/immersive), tone (noir/clinical/poetic), death description level
- **Gameplay**: Auto-save frequency, Signal manifestation toggle, inventory slots

---

## The Signal is waiting. Will you listen?

*信号在等待。你愿意聆听吗？*
