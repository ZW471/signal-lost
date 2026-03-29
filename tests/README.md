# Signal Lost — Test Infrastructure

Agentic testing framework for the Signal Lost game engine.

## Prerequisites

**LLM provider** — You need at least one of the following to run LLM-powered tests:

- **Anthropic** — Obtain an API key at https://console.anthropic.com and set it in `.env` as `ANTHROPIC_API_KEY`.
- **OpenAI** — Obtain an API key at https://platform.openai.com/api-keys and set it in `.env` as `OPENAI_API_KEY`.
- **Local LLM** — Run a local model via LM Studio, Ollama, or vLLM to avoid API costs entirely. Set `"provider": "local"` in `settings/provider.json`.
- **Claude Code** — Use the Claude Code CLI as the LLM backend (no API key needed, uses your Claude Code session). Set `"provider": "claude-code"` in `settings/provider.json`. Great for saving cost!

Configure your chosen provider in `settings/provider.json`:
```json
{
  "provider": "anthropic",
  "model": "claude-sonnet-4-6-20250514",
  "temperature": 0.7
}
```

**Optional: LangSmith** — To track token usage, cost, and detailed agentic workflow traces, set a LangSmith API key in `.env` as `LANGCHAIN_API_KEY`. This is entirely optional but useful for debugging and monitoring. Sign up at https://smith.langchain.com.

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
