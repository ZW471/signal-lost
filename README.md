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

### Browser GUI (Recommended)

The GUI provides a real-time game interface in your browser with a chat panel and live game state dashboard.

```bash
uv run gui/run_gui.py
uv run gui/run_gui.py --port 8080
uv run gui/run_gui.py --no-open   # don't auto-open browser
```

The GUI supports: New Game, Resume, Load Game, Save Game, and provider configuration — all from the browser.

### With an AI Agent (Headless Testing)

For automated playthroughs or agentic testing:

```bash
uv run tests/scripts/play_headless.py
```

The headless engine uses file-polling (`session/headless/player_action.json`) for communication, making it compatible with Claude Code and other AI agents.

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
- **Bilingual Support** — Play in English or 中文. Switch languages mid-game via settings.
- **6 Python Tools** — Dice roller, cipher decoder, Signal analyzer, district map, NPC generator, atmospheric glitch generator.
- **Multi-Provider** — Anthropic, OpenAI, LM Studio, or Claude Code CLI.

---

## Settings

Edit `settings/custom.json` to customize:

- **Difficulty**: `paranoid` (forgiving) → `cautious` → `standard` → `reckless` (brutal)
- **Language**: `display` for agent narration, `tui` for UI labels
- **Narrative**: Verbosity (terse/standard/immersive), tone (noir/clinical/poetic), death description level
- **Gameplay**: Auto-save frequency, Signal manifestation toggle, inventory slots

Edit `settings/provider.json` to configure the LLM provider.

---

## Testing

```bash
uv run tests/scenarios/smoke_test.py       # Quick validation (no LLM)
uv run tests/scenarios/regression.py       # Bug regression tests (no LLM)
uv run tests/scenarios/full_playthrough.py # Automated playthrough (requires LLM)
```

See `tests/README.md` for details.

---

## Prerequisites

This project uses [uv](https://docs.astral.sh/uv/) as its package manager. Install it first, then:

```bash
uv sync
```

**LLM Provider** — You need at least one of the following:

- **Anthropic** — Get an API key at https://console.anthropic.com and set `ANTHROPIC_API_KEY` in `.env`.
- **OpenAI** — Get an API key at https://platform.openai.com/api-keys and set `OPENAI_API_KEY` in `.env`.
- **Local LLM** — Run a local model via LM Studio, Ollama, or vLLM to avoid API costs entirely. Set `"provider": "local"` in `settings/provider.json`.
- **Claude Code** — Use the Claude Code CLI as the LLM backend (no API key needed). Set `"provider": "claude-code"` in `settings/provider.json`. Great for saving cost!

Configure your chosen provider in `settings/provider.json`:
```json
{
  "provider": "anthropic",
  "model": "claude-sonnet-4-6-20250514",
  "temperature": 0.7
}
```

**Optional: LangSmith** — To track token usage, cost, and detailed agentic workflow traces, set `LANGCHAIN_API_KEY` in `.env`. Entirely optional but useful for debugging and monitoring. Sign up at https://smith.langchain.com.

---

## The Signal is waiting. Will you listen?

*信号在等待。你愿意聆听吗？*
