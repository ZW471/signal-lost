# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Signal Lost is a cyberpunk knowledge-roguelike text RPG. The game engine is a LangGraph state machine with a Textual TUI dashboard. It supports multiple LLM providers (Anthropic, OpenAI, LM Studio) and is bilingual (English/中文).

## Running the Game

```bash
# Run the TUI (recommended) — from the compiled/ directory
cd compiled
../.venv/bin/python tui/tui_viewer.py .

# Run headless (no TUI)
cd compiled
../.venv/bin/python play_headless.py

# Run the standalone TUI entry point
cd compiled
../.venv/bin/python run.py
```

The TUI can also be launched from the repo root: `.venv/bin/python compiled/tui/tui_viewer.py compiled/`

## Build & Dependencies

Uses **uv** as the package manager. Python 3.13+ required.

```bash
uv sync          # Install dependencies
```

The workspace has two pyproject.toml files: root and `compiled/`. Key deps: `langchain-core`, `langchain-anthropic`, `langchain-openai`, `langgraph`, `textual`, `rich`, `pyte`.

## Architecture

### LangGraph State Machine (`compiled/graph.py`)

The game loop is a deterministic state graph with 11 nodes executing in sequence each turn:

```
input_gate → input_validator → resolver (+ tool_executor loop) → output_language_checker
  → state_writer → world_ticker → world_simulator → trace_checker → consequence → END/loop
```

- **Pure Python nodes** (deterministic): `input_gate`, `input_blocked_handler`, `state_writer`, `world_ticker`, `trace_checker`, `consequence`
- **LLM nodes**: `resolver` (narration + tool use), `input_validator` (cheat detection), `world_simulator` (NPC autonomy), `output_language_checker`
- All LLM-calling nodes are **non-fatal** on failure — the game continues even if validation/simulation fails

### Key Source Files

| File | Purpose |
|------|---------|
| `compiled/graph.py` | LangGraph state machine (all 11 nodes) |
| `compiled/state.py` | `GameState` TypedDict, session file I/O |
| `compiled/game_data.py` | Trace conditions, ending conditions, time periods |
| `compiled/prompts.py` | System prompt builder (static + dynamic, layer-gated) |
| `compiled/tools.py` | LLM tool wrappers (state mutation + utility tools) |
| `compiled/reducer.py` | Message compression (collapses tool calls into summaries) |
| `compiled/run.py` | Main entry point (Textual app, provider selection) |
| `compiled/tui/screens.py` | Provider selection UI and game screen |
| `compiled/tui/tui_viewer.py` | Dashboard panels (identity, knowledge, traces, etc.) |

### Content & Prompts

| Directory | Purpose |
|-----------|---------|
| `agent/` | System prompts: `system.md`, `player.md`, `game.md` |
| `game/` | World definition: `init.md`, `npcs.md`, `sessions.md`, `background.md` |
| `tools/` | 6 Python utility tools (dice, cipher, signal, glitch, profile, map) |
| `settings/` | `default.json` (base config), `custom.json` (active overrides) |
| `session/` | Active game state as JSON files |
| `saves/` | Save game backups |

### Game State (`compiled/state.py`)

`GameState` is a TypedDict with LangGraph's `add_messages` reducer. Session state mirrors `session/*.json` files: `player`, `knowledge`, `traces`, `location`, `inventory`, `npcs`, `world_state`, `log`.

**Critical invariants:**
- `messages` uses a 5-turn conversation window; older messages are trimmed via `RemoveMessage`
- System messages are rebuilt every turn (static prompt + dynamic state)
- ToolMessages are removed from state after `state_writer` processes them
- System events (resume/load) are ephemeral — removed after display

### Knowledge & Trace System

16 traces across 5 layers. Each trace has a `check()` lambda in `game_data.py` that evaluates against current state. `trace_checker` runs every turn and never forgets discoveries. `deepest_layer` gates what content the LLM can narrate (via `prompts.py` BACKGROUND_LAYERS).

### Conversation Logging

Conversation is logged to JSONL (`session/conversation.jsonl`). Each line must be a single JSON object — literal newlines in content must be escaped as `\n`. Append-only; system events are not logged.

## Dual Codebase Pattern

The `tui/` directory at the repo root contains the original TUI code. `compiled/tui/` is the compiled/integrated version used by the game engine. When modifying TUI behavior, edit `compiled/tui/` for the running game, but keep `tui/` in sync if changes should persist across recompilation.

## Settings

`settings/custom.json` overrides `settings/default.json`. Key settings: `difficulty` (paranoid/cautious/standard/reckless), `language` (display + tui), `narrative` (verbosity/tone), gameplay tuning.
