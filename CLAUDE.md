# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Signal Lost is a cyberpunk knowledge-roguelike text RPG. The game engine is a LangGraph state machine with a browser-based GUI (FastAPI + WebSocket). It supports multiple LLM providers (Anthropic, OpenAI, LM Studio, Claude Code CLI) and is bilingual (English/中文).

## Running the Game

```bash
# Run the browser GUI (primary interface)
uv run gui/run_gui.py
uv run gui/run_gui.py --port 8080

# Run headless for agentic testing
uv run tests/scripts/play_headless.py
```

## Running Tests

```bash
# Smoke tests (no LLM required)
uv run tests/scenarios/smoke_test.py

# Regression tests (no LLM required)
uv run tests/scenarios/regression.py

# Full playthrough test (requires configured LLM in settings/provider.json)
uv run tests/scenarios/full_playthrough.py --turns 20
```

## Build & Dependencies

Uses **uv** as the package manager. Python 3.13+ required.

```bash
uv sync          # Install dependencies
```

Key deps: `langchain-core`, `langchain-anthropic`, `langchain-openai`, `langgraph`, `rich`, `fastapi`, `uvicorn`.

## Architecture

### LangGraph State Machine (`engine/graph.py`)

The game loop is a deterministic state graph with 11 nodes executing in sequence each turn:

```
input_gate → input_validator → resolver (+ tool_executor loop) → output_language_checker
  → state_writer → world_ticker → world_simulator → trace_checker → consequence → END/loop
```

- **Pure Python nodes** (deterministic): `input_gate`, `input_blocked_handler`, `state_writer`, `world_ticker`, `trace_checker`, `consequence`
- **LLM nodes**: `resolver` (narration + tool use), `input_validator` (cheat detection), `world_simulator` (NPC autonomy), `output_language_checker`
- All LLM-calling nodes are **non-fatal** on failure — the game continues even if validation/simulation fails

### Directory Structure

```
Signal Lost/
├── engine/                # Core game engine (LangGraph)
│   ├��─ graph.py           # State machine (11 nodes)
│   ├── state.py           # GameState TypedDict, session I/O
│   ├── game_data.py       # Trace/ending conditions, time periods
│   ├── prompts.py         # System prompts (static + dynamic)
│   ├── tools.py           # LLM tool wrappers (state + utility)
│   ├─��� reducer.py         # Message compression
│   └── llm_factory.py     # Shared LLM creation + env loading
├── gui/                   # Browser GUI (FastAPI + WebSocket)
│   ├── server.py          # Backend
│   ├── run_gui.py         # Launcher
│   └── static/            # Frontend (HTML/JS/CSS)
├── tools/                 # Game mechanic tools (dice, cipher, signal, etc.)
├── tests/                 # Agentic testing framework
│   ├── scripts/           # Headless engine + Claude CLI wrapper
│   ├── scenarios/         # Smoke, playthrough, regression tests
│   └── reviews/           # Test output
├── game_specification/    # Reference-only design docs
│   ├── agent/             # System prompt sources
│   └── world/             # World definition sources
├── session/               # Active game state (JSON)
├── saves/                 # Save game backups
├── settings/              # Configuration (default.json, custom.json, provider.json)
└── logs/                  # Game reviews and playthrough logs
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `engine/graph.py` | LangGraph state machine (all 11 nodes) |
| `engine/state.py` | `GameState` TypedDict, session file I/O, `reset_turn_flags()` |
| `engine/game_data.py` | Trace conditions, ending conditions, time periods |
| `engine/prompts.py` | System prompt builder (static + dynamic, layer-gated) |
| `engine/tools.py` | LLM tool wrappers (state mutation + utility tools) |
| `engine/reducer.py` | Message compression (collapses tool calls into summaries) |
| `engine/llm_factory.py` | Single source for `create_llm()`, `load_env()`, `load_settings()` |
| `gui/server.py` | FastAPI + WebSocket backend |
| `tests/scripts/play_headless.py` | File-polling headless engine for agentic testing |
| `tests/scripts/claude_llm.py` | Claude Code CLI LLM wrapper (BaseChatModel) |

### Game State (`engine/state.py`)

`GameState` is a TypedDict with LangGraph's `add_messages` reducer. Session state mirrors `session/*.json` files: `player`, `knowledge`, `traces`, `location`, `inventory`, `npcs`, `world_state`, `log`.

**Critical invariants:**
- `messages` uses a 5-turn conversation window; older messages are trimmed via `RemoveMessage`
- System messages are rebuilt every turn (static prompt + dynamic state)
- ToolMessages are removed from state after `state_writer` processes them
- System events (resume/load) are ephemeral — removed after display
- Turn flags are reset via `reset_turn_flags()` at the start of each turn to prevent bleed

### Knowledge & Trace System

16 traces across 5 layers. Each trace has a `check()` lambda in `game_data.py` that evaluates against current state. `trace_checker` runs every turn and never forgets discoveries. `deepest_layer` gates what content the LLM can narrate (via `prompts.py` BACKGROUND_LAYERS).

### Conversation Logging

Conversation is logged to JSONL (`session/conversation.jsonl`). Each line must be a single JSON object — literal newlines in content must be escaped as `\n`. Append-only; system events are not logged.

### Game Specification (Reference Only)

`game_specification/agent/` and `game_specification/world/` contain the original markdown source files for system prompts and world definition. These are **reference only** — the engine uses the compiled versions in `engine/prompts.py` and `engine/game_data.py`.

## Settings

`settings/custom.json` overrides `settings/default.json`. Key settings: `difficulty` (paranoid/cautious/standard/reckless), `language` (display + tui), `narrative` (verbosity/tone), gameplay tuning.

`settings/provider.json` configures the LLM provider: `provider` (anthropic/openai/lmstudio/claude-code), `model`, `temperature`.
