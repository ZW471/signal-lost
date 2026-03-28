# Signal Lost — Test Infrastructure

Agentic testing framework for the Signal Lost game engine.

## Directory Structure

```
tests/
├── scripts/           # Headless play scripts for agent-based testing
│   ├── play_headless.py   # File-polling engine for automated play
│   └── claude_llm.py      # Claude Code CLI LLM wrapper
├── scenarios/         # Test scenarios
│   ├── smoke_test.py      # Quick validation (graph compiles, tools work, session I/O)
│   ├── full_playthrough.py # Automated N-turn playthrough with scoring
│   └── regression.py      # Specific bug reproduction tests
└── reviews/           # Output from test runs (gitignored except .gitkeep)
```

## Running Tests

### Smoke Test (no LLM required)
```bash
uv run tests/scenarios/smoke_test.py
```
Validates: graph compilation, tool schemas, session create/save/load roundtrip.

### Full Playthrough (requires LLM)
```bash
# Configure provider in settings/provider.json first
uv run tests/scenarios/full_playthrough.py --turns 20
```
Runs an automated game and generates a review in `tests/reviews/`.

### Headless Engine (for Claude Code play)
```bash
uv run tests/scripts/play_headless.py
```
Starts the engine in file-polling mode. Write actions to `session/headless/player_action.json`.

## Writing New Tests

Test scenarios should:
1. Import from `engine.*` (not direct file paths)
2. Use `engine.llm_factory.create_llm()` for LLM creation
3. Output results to `tests/reviews/`
4. Return exit code 0 on success, 1 on failure
