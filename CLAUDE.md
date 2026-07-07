# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Signal Lost is a cyberpunk knowledge-roguelike text RPG. The game engine is a LangGraph state machine with a browser-based GUI (FastAPI + WebSocket). It supports multiple LLM providers (Anthropic, OpenAI, OpenRouter, LM Studio, Claude Code CLI, Codex CLI) and is bilingual (English/中文).

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
# Smoke tests — no LLM required (7 tests: graph compiles, tool schemas, session I/O,
# trace/ending validation, factory, turn-flag reset)
uv run tests/scenarios/smoke_test.py

# Regression tests — no LLM required (31 tests incl. ending-correctness fixtures:
# consensual bridge → the_bridge, forced merge → ascension, conversational L3 reach,
# discovered-only client payload / no-totals, endings-history dedup, priority lock)
uv run tests/scenarios/regression.py

# Good-ending reachability (no LLM required): a deep run first-matches the_bridge
uv run tests/scenarios/good_ending_reachability.py

# Full playthrough test (requires configured LLM in settings/provider.json)
uv run tests/scenarios/full_playthrough.py --turns 20
```

After any change under `gui/static/`, syntax-check the frontend: `node --check gui/static/app.js`.

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

The `resolver` system prompt (`engine/prompts.py`) carries a few narrative-quality directives worth knowing about: an **anti-repetition** rule (rotate the sensory register each turn; use rain/neon/the implant's hum at most once every few turns), a **meter-causality** rule (whenever NEXUS alert / integrity / fragment decay moves, the narration must name the in-world cause and fill any tool `reason` field — never raw numbers), a one-verb-per-turn teaching-suggestion rule, and a **Director Notes** contract (bracketed/labelled staging notes — trajectory warnings, integrity primers — are never quoted; their intent is expressed only through the fiction).

### Browser GUI (`gui/server.py`, `gui/static/`)

FastAPI + WebSocket backend driving a single-page frontend (`index.html` / `app.js` / `style.css`). The `/ws` protocol is **additive and forward-compatible**: the client ignores unknown frame types, so the server can add frames without breaking older clients. Turn-progress and delta frames layer on top of the base narrative/discovery/state frames:

- `state_delta` — incremental state patches (avoids resending full session snapshots)
- `roll` — dice/roll beat surfaced as a chip
- `phase` — per-turn heartbeat (validating → resolving → writing → world → checking); after ~10s of `resolving` the client reveals a CANCEL button
- `turn_cancelled` — server acknowledges a cancel; client runs `endTurnUI()`
- `save_deleted` — server confirmation of a `delete_save` WS action (both LIVE since wave 7). `_handle_delete_save` in `gui/server.py` sanitizes the name, blocks path traversal, refuses the active session, `shutil.rmtree`s the save dir and replies with the refreshed saves list; each save card renders a live delete button that opens a bilingual confirm dialog (`confirmDeleteSave`/`doDeleteSave` in `app.js`)

**Cancel-turn is a pre-commit abort.** `cancel_turn` flips `sess.cancel_requested`; the turn aborts at the next pre-commit seam, so a cancelled turn never half-writes session state (the rejected `HumanMessage` is also reverted so it can't leak into the next turn's LLM context). During a turn, `_run_turn` spawns a concurrent frame reader for exactly the executor-await window: `cancel_turn` fires immediately, other frames are requeued onto `sess.pending_frames` and replayed in order.

**Turn locks are account-wide.** `_turn_lock_for(uid)` returns one shared lock per account, held across superseded and replacement sessions that point at the same on-disk session dir — this prevents two unsynchronized writers (e.g. a force-kick/reconnect binding a fresh session while the old turn thread is still writing `player.json`/`knowledge.json`). Resume/load/new-game acquire it with a bounded timeout (bilingual busy error on contention); the prediction fast-path degrades to a cache miss rather than block.

**Panel IA: 7 grouped tabs** (`data-panel` in `index.html`): `knowledge`, `traces`, `network`, `world` (world-state + district sections), `character` (identity + inventory sections), `log`, `conversation`. Positional 1–7 shortcuts switch panels.

**i18n (single source of truth):** `LABELS` (a bilingual EN/中文 dict in `app.js`) is the ONLY string table; `L(key)` reads it for the active language. Static chrome uses the `data-i18n` / `data-i18n-placeholder` / `data-i18n-aria` attributes, and `applyStaticI18n(root)` localizes every keyed element in one pass (textContent / placeholder / aria-label). Add new UI strings to `LABELS` and tag the element with `data-i18n=<key>` — never hardcode player-visible text.

**Unified managers:** one toast stack (`#toastStack`, `dismissToast`), one dialog manager (`openDialog`/`closeDialog` with a deterministic z-index-ordered `_dialogStack`, focus trap, ARIA), and one SFX bus (`MusicEngine.sfx`, single mute state + persisted volume; `playBeep` is a category-tagged shim over it).

**Cache-busting discipline:** every `gui/static/` asset URL in `index.html` carries a `?v=<tag>` query and all three (`style.css`, `music.js`, `app.js`) bump together on any frontend edit. Current tag: **`w13`**.

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
│   ├── scripts/           # Headless engine + Claude/Codex CLI wrappers
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
| `tests/scripts/codex_llm.py` | OpenAI Codex CLI LLM wrapper (BaseChatModel) |

### Game State (`engine/state.py`)

`GameState` is a TypedDict with LangGraph's `add_messages` reducer. Session state mirrors `session/*.json` files: `player`, `knowledge`, `traces`, `location`, `inventory`, `npcs`, `world_state`, `log`.

**Critical invariants:**
- `messages` uses a 5-turn conversation window; older messages are trimmed via `RemoveMessage`
- System messages are rebuilt every turn (static prompt + dynamic state)
- ToolMessages are removed from state after `state_writer` processes them
- System events (resume/load) are ephemeral — removed after display
- Turn flags are reset via `reset_turn_flags()` at the start of each turn to prevent bleed

### Knowledge & Trace System

The engine tracks 47 traces across 5 layers (L1×8, L2×11, L3×11, L4×9, L5×8) — these totals are **engine-internal only**. Each trace has a `check()` lambda in `game_data.py` that evaluates against current state. `trace_checker` runs every turn and never forgets discoveries. `deepest_layer` gates what content the LLM can narrate (via `prompts.py` BACKGROUND_LAYERS).

**THE SPOILER RULE (no-totals):** the UI / client payloads must never reveal the *size* of undiscovered content — no "N/47" totals, no per-layer denominators ("3/8"), no fixed 5-segment depth gauges, no endings-gallery size. `gui/server.py` (`_present_traces`) strips the persisted trace scaffold down to a discovered-only presentation (the `discovered` list + `{num, name, name_zh}` for layers already reached); `_build_run_summary` and the endings payloads ship discovered counts only. Sealed/unknown content may be *hinted* only unquantified (a single `▓ ???` card, a lone "deeper" affordance). Discovered counts, depth reached so far, and already-known names are fine; in-game mechanical meters (integrity 3/3, alert %) are not content scope. The persisted `traces.json` scaffold (`reconcile_trace_presentation`, `LIVE_TRACE_TOTAL`, `LIVE_TRACES_PER_LAYER`) stays intact for engine gating — it just must never be transmitted.

### Endings & Consent (`engine/game_data.py`)

`ENDINGS` is a first-match-wins list. GOOD endings are checked **first** with the strictest, deepest gates so a well-earned run cannot fall through to a looser keyword-gated bad ending. The load-bearing case: a **consensual bridge** must converge to `the_bridge` (good), not the forced-merge `ascension` (bad). To hold that line, `ascension`'s force-merge keyword list deliberately **excludes** the bare lore words (`ascend`/`升华`/`飞升`) that a deep player is *expected* to learn, and only decisive **consensual-merge** climax phrases (with affirmative-consent phrases that veto a force reading in the same knowledge write) route to `the_bridge`. Regression + reachability suites pin this (see below).

### Conversation Logging

Conversation is logged to JSONL (`session/conversation.jsonl`). Each line must be a single JSON object — literal newlines in content must be escaped as `\n`. Append-only; system events are not logged.

### Game Specification (Reference Only)

`game_specification/agent/` and `game_specification/world/` contain the original markdown source files for system prompts and world definition. These are **reference only** — the engine uses the compiled versions in `engine/prompts.py` and `engine/game_data.py`.

## Settings

`settings/custom.json` overrides `settings/default.json`. Key settings: `difficulty` (paranoid/cautious/standard/reckless), `language` (display + tui), `narrative` (verbosity/tone), gameplay tuning.

`settings/provider.json` configures the LLM provider: `provider` (anthropic/openai/openrouter/lmstudio/claude-code/codex), `model`, `temperature`.

### CLI-bypass providers (claude-code / codex)

`claude-code` and `codex` both authenticate via their own CLI's OAuth flow (`claude /login` and `codex login` respectively — no API key needed in `settings/provider.json`). Both expose a `_call_claude(system, user) -> str` method, so they share the same fast-path bypass in `engine/claude_code_engine.py` — a single CLI invocation per turn instead of the full 11-node LangGraph loop. The bypass kicks in automatically when the active LLM has `_call_claude` and the provider is in `OAUTH_CLI_PROVIDERS` (see `engine/llm_factory.py`).

### OpenRouter

`openrouter` is an OpenAI-API-compatible gateway. The factory points `langchain_openai.ChatOpenAI` at `https://openrouter.ai/api/v1` and reads `OPENROUTER_API_KEY` (or `OPENAI_API_KEY` as fallback) from the environment. Model names use the `vendor/model` format, e.g. `openai/gpt-5.4`, `anthropic/claude-sonnet-4`, `deepseek/deepseek-chat`. Like every API provider, openrouter runs the **full 11-node LangGraph pipeline** (with tool-calling) — only the OAuth CLI backends use the single-call bypass, so an openrouter model must support function/tool calling to play.
