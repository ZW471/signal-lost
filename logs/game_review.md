# Signal Lost — Comprehensive Review

**Reviewer**: Claude Code (Opus 4.6)
**Date**: 2026-03-27
**Basis**: 20-turn playthrough as both player and engine operator, full codebase analysis

---

## 1. Gameplay & Narrative Quality

### What Works Brilliantly

**The writing is exceptional.** Signal Lost produces consistently atmospheric, noir-drenched prose that rivals hand-crafted interactive fiction. The engine maintains tone across dozens of turns without degradation — rain on concrete, neon bleeding through steam, the particular silence of infrastructure the city forgot it was running on. The sensory palette is specific and disciplined.

**The mystery structure is genuinely compelling.** The five-layer revelation system (Surface → Conspiracy → Secret → Revelation → Truth) creates a satisfying investigative arc. In my 20-turn playthrough, I progressed from amnesia to rebuilding a sentient pre-Severance network — a complete narrative arc with genuine tension, character development, and a climactic choice. The game earned its emotional beats.

**Emergent storytelling is a standout feature.** The engine invented a recurring kid-messenger system (wax paper notes delivered by street runners) entirely on its own — not scripted, not prompted, just emergent from the NPC simulation and world state. This is the kind of unpredictable creativity that makes LLM-driven games uniquely interesting.

**NPCs feel alive.** Mira watching from her counter since 0400, Ray sorting chips with a glass eye, Dex slumped in a dead node for weeks — each NPC arrived with physical specificity and behavioral consistency. The trust system works subtly; NPCs reveal information at a pace that feels earned.

### What Needs Improvement

**The engine sometimes skips player-facing exposition.** In turn 5, I asked Mira a direct question but the engine time-skipped through her answer and narrated me already en route to a location she described. The player missed the actual conversation. The resolver should prioritize showing dialogue over advancing plot.

**State tracking has gaps.** The `area` field in location frequently showed "?" throughout the playthrough despite the narrative describing specific locations (Rain Alley, Mira's Noodle Shop, Neon Row maintenance corridor). The `update_location` tool isn't being called consistently, or isn't populating all fields.

**Integrity tracking diverges from narrative.** The prose described "one point of integrity" and "the floor" while the state showed 2/3. The tool-calling approach means the LLM must remember to call `update_player` for integrity changes — and sometimes it doesn't, or calls it with the wrong format ("integrity set to 2" as a string instead of a proper JSON delta).

**Credits and inventory are underused.** In 20 turns, only one transaction occurred (buying Ray's chip for 20 credits). The cipher toolkit was never used despite multiple opportunities. The inventory system exists but the engine doesn't create enough mechanical pressure to engage with it.

**The world simulator's kid-messenger pattern became repetitive.** Every turn ended with a kid delivering a wax paper message, regardless of context — even when the player was deep underground in layer zero. The world_simulator node needs better awareness of player context to avoid absurd juxtapositions.

---

## 2. The Agent Graph

### Architecture Strengths

The 11-node graph is well-designed:

```
input_gate → input_validator → resolver ⟷ tool_executor
  → output_language_checker → state_writer → world_ticker
  → world_simulator → trace_checker → consequence → END
```

**Deterministic/LLM separation is clean.** Pure Python nodes (input_gate, state_writer, world_ticker, trace_checker, consequence) handle mechanics. LLM nodes (resolver, input_validator, world_simulator) handle creativity. This means the game never breaks even when the LLM fails — validation failures are non-fatal, world simulation failures are silent. The game always continues.

**The trace system is excellent.** 16 traces across 5 layers, each with a `check()` lambda that evaluates against current state. Deterministic, never forgets discoveries, and gates what content the LLM can narrate. This is the right architecture for a knowledge-driven game.

**The 5-turn conversation window prevents token bloat.** System messages are rebuilt every turn (static prompt + dynamic state), older messages are trimmed via RemoveMessage, and the reducer collapses tool calls into compact summaries. This keeps context manageable across long playthroughs.

### Architecture Weaknesses

**Trace discovery depends entirely on the LLM calling `add_knowledge`.** If the resolver doesn't call the tool (because it forgot, or the response was cut short), the trace condition never triggers. There's no fallback — the system can't discover traces from narrative content alone. A post-resolver node that extracts knowledge claims from the narrative and auto-adds them would make the system more robust.

**State mutations via tools are lossy.** The resolver must call `update_player`, `update_location`, etc. correctly for state to change. If it forgets (common with non-API tool calling), the game world diverges from the narrative. The state_writer applies what it receives — it can't infer missing mutations.

**Flag proliferation is a maintenance risk.** GameState has 7 boolean/optional flags (skip_conversation_log, skip_turn_increment, input_blocked, blocking_reason, skip_validation, language_retry_count, plus turn_delta). These are set and reset across different nodes with no central management. Forgetting to reset a flag causes behavior to bleed into the next turn.

**The consequence node is terminal.** After consequence checks game_over conditions, the turn always ends. If consequence detects a special event that should be narrated, there's no mechanism to do so — the narrative was already written by the resolver earlier in the pipeline.

---

## 3. Playability Interfaces

### For Humans (TUI via compiled/run.py)

The Textual TUI is full-featured: conversation panel on the left, tabbed state panels on the right (identity, knowledge, traces, NPCs, inventory, district map, world state, event log). It supports new game, load, resume, save, settings, and language switching.

**Strengths**: Rich dashboard, real-time state updates, bilingual support.
**Weaknesses**: Complex screen flow (many transitions), panels poll session files every 5 seconds (latency), and if `graph.invoke()` hangs the TUI freezes with no timeout.

### For LLMs (play_headless.py + claude_llm.py)

The file-polling interface I built for this playthrough works but is primitive:

**The communication protocol is fragile.** JSON files (`player_action.json`, `game_response.json`, `engine_status.json`) are read/written without locking. If the writer crashes mid-write, the reader gets corrupted JSON. There's no acknowledgment mechanism — the engine assumes the player read the response before writing the next action.

**The Claude Code LLM wrapper (claude_llm.py) works but has rough edges:**
- Tool calling required extensive prompt engineering to get right (two-phase: tools first, narrative after)
- The response parser handles JSON-in-prose, fenced JSON, and pure JSON, but edge cases still slip through
- Each LLM call spawns a new `claude -p` subprocess — startup overhead adds ~5-10 seconds per call
- No conversation continuity between subprocess invocations (each is stateless)

**What would make it better for LLM players:**
- A proper API interface (HTTP/WebSocket) instead of file polling
- Structured response format that separates narrative, state changes, and available actions
- A "suggested actions" field in the response to help LLM players make informed choices
- An observation/action space definition (like OpenAI Gym) so agent frameworks can integrate cleanly

### For Both: Missing Features

**No action validation feedback.** When the input_validator blocks an action, the player gets a generic warning. It should explain why and suggest alternatives.

**No "what can I do" command.** Players (human or LLM) have no way to query available actions at the current location. The game relies entirely on the narrative to imply options.

**No turn timer or pacing control.** The game has no urgency mechanics beyond narrative tension. Adding optional time pressure (real-time or turn-limited objectives) would create more dynamic gameplay for both humans and LLMs.

---

## 4. Directory Structure Analysis

### Current Layout

```
Signal Lost/
├── agent/          # Prompt source documents (.md)
├── compiled/       # Game engine + integrated TUI
│   └── tui/        # Compiled TUI (imports from root tui/)
├── game/           # World content source documents (.md)
├── gui/            # Browser GUI (FastAPI)
├── logs/           # Runtime logs
├── saves/          # Save game slots
├── session/        # Live game state (JSON)
├── settings/       # Configuration files
├── tools/          # Python utility tools
├── tui/            # Original standalone TUI (2886 lines)
└── .venv/          # Virtual environment
```

### Critical Issues

**1. The "compiled" pattern is misleading — there is no build step.**

The `compiled/` directory contains manually-maintained Python files that duplicate content from `agent/*.md` and `game/*.md`. Specifically:
- `compiled/prompts.py` hardcodes text from `agent/system.md`, `agent/player.md`, `agent/game.md`
- `compiled/game_data.py` hardcodes trace conditions from `game/game.md`

There is no script that generates these. They must be manually kept in sync with the source `.md` files. This is the single biggest structural risk — changes to game design documents don't propagate to the running code.

**2. The dual TUI is a maintenance burden.**

`tui/tui_viewer.py` (2886 lines) is the "original" standalone TUI. `compiled/tui/tui_viewer.py` (708 lines) imports panel classes from it via `sys.path` manipulation. If anyone refactors the original TUI (renames a class, changes a constructor), the compiled TUI breaks silently. CLAUDE.md warns about this, but warnings don't prevent accidents.

**3. Three entry points duplicate the same setup code.**

`compiled/run.py`, `compiled/play_headless.py`, and `gui/server.py` all independently implement:
- `.env` file loading
- `create_llm()` function (identical logic)
- Settings loading from `settings/*.json`
- Session initialization

This violates DRY and means bug fixes must be applied in three places.

**4. Provider config is needlessly separated.**

`settings/provider.json` exists alongside `settings/default.json` and `settings/custom.json` with no clear reason for the split. All three are loaded by different code paths.

**5. The dependency split between root and compiled/ pyproject.toml is confusing.**

Root has FastAPI deps (for GUI), compiled/ has LangChain deps (for engine). Both have textual/rich/pyte. The workspace relationship isn't obvious — a developer might install the wrong subset.

### Recommended Directory Structure

```
Signal Lost/
├── engine/                    # Core game engine (renamed from compiled/)
│   ├── graph.py               # LangGraph state machine
│   ├── state.py               # GameState schema + session I/O
│   ├── tools.py               # LLM tool wrappers
│   ├── prompts.py             # Generated from content/*.md (with build script)
│   ├── game_data.py           # Generated from content/*.md (with build script)
│   ├── reducer.py             # Message compression
│   ├── llm_factory.py         # NEW: shared create_llm() + env loading
│   └── config.py              # NEW: centralized settings loader + validation
│
├── interfaces/                # All play interfaces
│   ├── tui/                   # Textual TUI (unified, no dual ownership)
│   │   ├── app.py             # Main Textual app (renamed from run.py)
│   │   ├── screens.py         # Screen flow
│   │   ├── panels.py          # Extracted panel components
│   │   └── game_screen.py     # Game screen + conversation widget
│   ├── headless/              # File-polling / API interface
│   │   └── server.py          # Polling loop or HTTP API
│   ├── web/                   # Browser GUI
│   │   ├── server.py          # FastAPI backend
│   │   └── static/            # Frontend assets
│   └── claude_code/           # Claude Code integration
│       └── llm_wrapper.py     # BaseChatModel for claude -p
│
├── content/                   # Game content (single source of truth)
│   ├── prompts/               # System prompt sources
│   │   ├── system.md
│   │   ├── player.md
│   │   └── game.md
│   ├── world/                 # World definition
│   │   ├── init.md
│   │   ├── background.md
│   │   ├── npcs.md
│   │   └── sessions.md
│   └── tools/                 # Utility tool implementations
│       ├── dice.py
│       ├── cipher.py
│       ├── signal.py
│       ├── glitch.py
│       ├── profile.py
│       └── map.py
│
├── data/                      # Runtime data
│   ├── session/               # Live game state
│   ├── saves/                 # Save game slots
│   ├── logs/                  # Runtime logs
│   └── settings/              # All config (merged)
│       ├── default.json       # Base config (includes provider)
│       └── custom.json        # User overrides
│
├── scripts/                   # Build & maintenance
│   ├── build_prompts.py       # Generate engine/prompts.py from content/
│   ├── build_game_data.py     # Generate engine/game_data.py from content/
│   └── validate_content.py    # Check content/ ↔ engine/ consistency
│
├── pyproject.toml             # Single dependency file
├── CLAUDE.md
└── README.md
```

### Key Changes and Why

| Change | Rationale |
|--------|-----------|
| `compiled/` → `engine/` | "Compiled" implies a build step that doesn't exist. "Engine" is accurate. |
| Unified `interfaces/tui/` | Eliminates dual TUI ownership. Panels extracted to their own module. |
| `content/` replaces `agent/` + `game/` + `tools/` | Single directory for all game content. Clear separation from engine code. |
| `data/` replaces `session/` + `saves/` + `logs/` + `settings/` | All runtime data in one place. Easy to gitignore, backup, or reset. |
| `scripts/build_*.py` | Automated generation of prompts.py and game_data.py from .md sources. |
| `engine/llm_factory.py` | Eliminates triple-duplicated create_llm() and .env loading. |
| `engine/config.py` | Centralized settings with validation. Merges provider into main config. |
| Single `pyproject.toml` | No confusing workspace split. Optional dependency groups for gui/dev. |

---

## 5. Agent Maintainability (Claude Code Perspective)

As a Claude Code agent that just maintained and extended this codebase, here are specific pain points:

**Finding the right file is harder than it should be.** The dual `tui/` directories, the `compiled/` misnomer, and the scattered settings files mean even simple questions like "where is the LLM configured?" require checking 3-4 locations.

**The sys.path manipulation is fragile.** Both `play_headless.py` and `compiled/tui/tui_viewer.py` insert directories into sys.path at runtime. This makes imports unpredictable — `from tools import ALL_TOOLS` works in `compiled/` but fails from the root directory. An agent that doesn't know this will waste time debugging import errors.

**No tests means no safety net.** Making changes (like adding the claude-code LLM provider) required manual testing at every step. A basic test suite — even just "does the graph compile?", "do tools return valid JSON?", "can a session be saved and loaded?" — would let agents make changes with confidence.

**The CLAUDE.md is good but insufficient.** It correctly describes the architecture and key files, but doesn't mention the dual TUI issue, the manual prompt compilation requirement, or the flag reset obligations. An agent following only CLAUDE.md would miss these landmines.

**Suggestions for agent-friendly structure:**
- Add a `Makefile` or `justfile` with common operations: `make build` (generate from .md), `make test`, `make play`, `make headless`
- Add type stubs or Pydantic models for state files so agents can validate changes
- Add a `ARCHITECTURE.md` with a dependency graph showing which files import from which
- Mark the canonical source for every piece of duplicated data (e.g., "trace conditions: canonical source is content/prompts/game.md, generated to engine/game_data.py")

---

## 6. Summary Scorecard

| Aspect | Score | Notes |
|--------|-------|-------|
| **Narrative Quality** | 9/10 | Exceptional noir prose, consistent tone, emergent storytelling |
| **Mystery Design** | 8/10 | Compelling 5-layer structure, satisfying revelations |
| **Game Mechanics** | 6/10 | Trace system is great, but inventory/credits underused |
| **State Management** | 5/10 | Functional but lossy — LLM must remember to call tools |
| **Graph Architecture** | 8/10 | Clean separation of concerns, non-fatal failures, good flow |
| **Human Playability (TUI)** | 7/10 | Feature-rich but complex, no action hints |
| **LLM Playability** | 4/10 | File-polling is primitive, no structured action space |
| **Directory Structure** | 4/10 | Dual TUI, misleading "compiled", scattered config |
| **Agent Maintainability** | 5/10 | No tests, fragile imports, manual sync requirements |
| **Documentation** | 6/10 | CLAUDE.md covers basics, misses structural hazards |

**Overall: A narratively exceptional game with solid graph architecture, held back by structural debt in its directory layout and interface design.** The core engine is production-quality; the packaging around it needs the same level of care.
