# OpenRouter Model Sweep — Signal Lost

A capability/cost sweep to find **cheap-yet-capable** OpenRouter models for running
Signal Lost, and to pin down the **minimum model capability** the engine needs.

- **Run date:** 2026-06-17
- **Models tested:** 35 (1B floor-probes → mid-tier MoE; Opus/premium tiers deliberately excluded)
- **Total cost:** ~$0.50 of OpenRouter spend
- **Harness:** [`tests/scripts/model_sweep.py`](scripts/model_sweep.py) + candidate list [`tests/scripts/sweep_models.json`](scripts/sweep_models.json)

---

## How to run it again

```bash
# Full sweep (8 turns/model, 6 parallel workers). Needs OPENROUTER_API_KEY in .env
uv run tests/scripts/model_sweep.py \
    --models tests/scripts/sweep_models.json \
    --turns 8 --workers 6 --call-timeout 110

# Quick smoke (2 models, 2 turns) to confirm the harness before a big run
printf '%s\n' '["deepseek/deepseek-chat","meta-llama/llama-3.2-1b-instruct"]' > /tmp/m.json
uv run tests/scripts/model_sweep.py --models /tmp/m.json --turns 2 --workers 2
```

Each run prints a ranked table and writes two files to `tests/reviews/sweep/` (gitignored):
`sweep_<ts>.json` (raw metrics) and `sweep_<ts>.md` (ranked report with live pricing).
Edit `sweep_models.json` to change the candidate set — IDs are plain OpenRouter model
slugs (`vendor/model`); browse the live catalog at `https://openrouter.ai/api/v1/models`.

### What it measures (and why it's representative)

OpenRouter runs on the **single-call bypass engine** (`engine.claude_code_engine.run_turn`),
not the full LangGraph tool loop — so the sweep drives that exact path. Every model plays
an **identical fixed action script** (apples-to-apples). Each turn the model must (a) follow
a long, layer-gated system prompt and (b) emit a valid **structured-JSON state mutation**.
The two capability signals are therefore:

- **Deepest layer reached (L0–L5)** — how far it drove the structured game state.
- **Traces discovered** — count of correctly-applied state mutations.

A model that only narrates prose (no valid JSON) still "runs" but stalls at **L0 / 0 traces**.

**Tiers:** EXCELLENT (L4+, ≥10 traces) · STRONG (L3+, ≥6) · OK (L2+, ≥3) · WEAK (shallow)
· UNAVAILABLE (404 — see caveat). `c/turn` = est. cents/turn at ~5k input + 1.2k output tokens.

---

## Minimum capability requirement

**It's format fidelity, not parameter count.** The gate is: *can the model reliably emit the
engine's structured-JSON mutations while following multi-layer instructions?*

- **The floor that works:** strong small models clear it — `qwen-2.5-7b` (L2) and even
  `gemma-3-4b` (L3) made real progress.
- **Same-size models that fail it:** `llama-3.1-8b` and `phi-4` (14B!) ran but froze at
  **L0 with 0 traces** — they narrate fluently but don't emit valid state JSON.
- **Practical minimum:** ~7B *with strong instruction/JSON adherence* (Qwen 2.5/3, Gemma 3,
  gpt-oss, Mistral Small families). Weak-format models of any size do not progress.
- **"Works well" (recommendable):** reaches **L3–L4 with ≥6 traces** — mid-tier instruct/MoE.

---

## Recommended: cheap-yet-powerful (cheapest first)

All real catalog IDs, all STRONG/EXCELLENT in the sweep.

| # | Model | c/turn | Tier | Layer | Traces | Latency(s) | Note |
|--:|-------|-------:|------|------:|------:|-----------:|------|
| 1 | `openai/gpt-oss-20b` | 0.031 | EXCELLENT | 4 | 12 | 15.1 | **best value** — cheapest EXCELLENT |
| 2 | `mistralai/mistral-small-24b-instruct-2501` | 0.035 | STRONG | 4 | 8 | 11.8 | great cheap dense |
| 3 | `openai/gpt-oss-120b` | 0.041 | EXCELLENT | 4 | 10 | 18.5 | |
| 4 | `qwen/qwen3-235b-a22b-2507` | 0.057 | EXCELLENT | 4 | 17 | 51.5 | deepest run, but slow |
| 5 | `google/gemma-3-27b-it` | 0.059 | STRONG | 3 | 7 | 19.2 | |
| 6 | `qwen/qwen3-8b` | 0.073 | STRONG | 4 | 8 | 31.3 | |
| 7 | `qwen/qwen3-32b` | 0.074 | EXCELLENT | 4 | 13 | 30.3 | |
| 8 | `qwen/qwen3-14b` | 0.079 | STRONG | 3 | 12 | 23.0 | |
| 9 | `meta-llama/llama-3.3-70b-instruct` | 0.088 | STRONG | 3 | 7 | 40.9 | slow |
| 10 | `openai/gpt-4.1-nano` | 0.098 | STRONG | 3 | 7 | **3.3** | fastest |
| 11 | `openai/gpt-4o-mini` | 0.147 | STRONG | 3 | 7 | 5.0 | common, reliable |
| 12 | `deepseek/deepseek-v3.2` | 0.156 | EXCELLENT | 4 | 12 | 39.9 | |
| 13 | `z-ai/glm-4.5-air` | 0.167 | STRONG | 3 | 6 | 19.1 | |
| 14 | `deepseek/deepseek-chat-v3-0324` | 0.192 | STRONG | 3 | 13 | 19.7 | |
| 15 | `deepseek/deepseek-chat` | 0.196 | STRONG | 4 | 9 | 17.8 | prior repo default |
| 16 | `qwen/qwen-2.5-72b-instruct` | 0.228 | STRONG | 3 | 8 | 26.3 | |
| 17 | `minimax/minimax-m2` | 0.248 | EXCELLENT | 4 | 13 | **9.2** | best depth+speed combo |
| 18 | `openai/gpt-5-mini` | 0.365 | EXCELLENT | 4 | 14 | 32.5 | richest knowledge (36) |
| 19 | `openai/gpt-4.1-mini` | 0.392 | STRONG | 3 | 6 | 7.8 | |
| 20 | `google/gemini-2.5-flash` | 0.450 | STRONG | 4 | 6 | 5.3 | fast |

**Top picks**
- **Best overall value:** `openai/gpt-oss-20b` — L4 depth at ~$0.03 per 100 turns.
- **Best for live/interactive play (latency matters — one call per turn):**
  `openai/gpt-4.1-nano` (3.3s), `google/gemini-2.5-flash-lite` (4.5s),
  `openai/gpt-4o-mini` (5.0s), `minimax/minimax-m2` (9.2s, and L4).
- **Deepest single run:** `qwen/qwen3-235b-a22b-2507` (17 traces, L4) — cheap but ~50s/turn.

---

## Full results

| Tier | Model | Turns | Traces | Knowledge | Layer | Latency(s) | c/turn |
|------|-------|------:|------:|----------:|------:|-----------:|-------:|
| EXCELLENT | `qwen/qwen3-235b-a22b-2507` | 8 | 17 | 28 | 4 | 51.5 | 0.057 |
| EXCELLENT | `openai/gpt-5-mini` | 8 | 14 | 36 | 4 | 32.5 | 0.365 |
| EXCELLENT | `qwen/qwen3-32b` | 8 | 13 | 25 | 4 | 30.3 | 0.074 |
| EXCELLENT | `minimax/minimax-m2` | 8 | 13 | 24 | 4 | 9.2 | 0.248 |
| EXCELLENT | `openai/gpt-oss-20b` | 8 | 12 | 25 | 4 | 15.1 | 0.031 |
| EXCELLENT | `deepseek/deepseek-v3.2` | 8 | 12 | 20 | 4 | 39.9 | 0.156 |
| EXCELLENT | `openai/gpt-oss-120b` | 8 | 10 | 20 | 4 | 18.5 | 0.041 |
| STRONG | `deepseek/deepseek-chat-v3-0324` | 8 | 13 | 19 | 3 | 19.7 | 0.192 |
| STRONG | `qwen/qwen3-14b` | 8 | 12 | 20 | 3 | 23.0 | 0.079 |
| STRONG | `deepseek/deepseek-chat` | 8 | 9 | 14 | 4 | 17.8 | 0.196 |
| STRONG | `qwen/qwen3-8b` | 6 | 8 | 15 | 4 | 31.3 | 0.073 |
| STRONG | `mistralai/mistral-small-24b-instruct-2501` | 8 | 8 | 13 | 4 | 11.8 | 0.035 |
| STRONG | `meta-llama/llama-3.3-70b-instruct` | 8 | 7 | 23 | 3 | 40.9 | 0.088 |
| STRONG | `google/gemma-3-27b-it` | 8 | 7 | 22 | 3 | 19.2 | 0.059 |
| STRONG | `qwen/qwen-2.5-72b-instruct` | 8 | 8 | 12 | 3 | 26.3 | 0.228 |
| STRONG | `openai/gpt-4.1-mini` | 8 | 6 | 20 | 3 | 7.8 | 0.392 |
| STRONG | `openai/gpt-4.1-nano` | 8 | 7 | 13 | 3 | 3.3 | 0.098 |
| STRONG | `google/gemini-2.5-flash` | 8 | 6 | 6 | 4 | 5.3 | 0.450 |
| STRONG | `openai/gpt-4o-mini` | 8 | 7 | 9 | 3 | 5.0 | 0.147 |
| STRONG | `z-ai/glm-4.5-air` | 8 | 6 | 13 | 3 | 19.1 | 0.167 |
| OK | `google/gemma-3-4b-it` | 8 | 5 | 25 | 3 | 20.2 | 0.037 |
| OK | `mistralai/mistral-small-3.2-24b-instruct` | 8 | 8 | 19 | 2 | 16.6 | 0.062 |
| OK | `meta-llama/llama-4-maverick` | 8 | 6 | 23 | 2 | 15.1 | 0.147 |
| OK | `google/gemini-2.5-flash-lite` | 8 | 6 | 22 | 2 | 4.5 | 0.098 |
| OK | `google/gemma-3-12b-it` | 8 | 4 | 22 | 2 | 13.1 | 0.043 |
| OK | `qwen/qwen-2.5-7b-instruct` | 8 | 4 | 16 | 2 | 7.8 | 0.032 |
| OK | `mistralai/ministral-8b-2512` | 8 | 3 | 4 | 2 | 14.9 | 0.093 |
| WEAK | `meta-llama/llama-4-scout` | 8 | 2 | 6 | 2 | 6.8 | 0.086 |
| WEAK | `mistralai/mistral-nemo` | 8 | 2 | 6 | 1 | 7.7 | 0.014 |
| WEAK | `meta-llama/llama-3.1-8b-instruct` | 8 | 0 | 2 | 0 | 5.7 | 0.014 |
| WEAK | `microsoft/phi-4` | 8 | 0 | 2 | 0 | 16.4 | 0.049 |
| UNAVAILABLE | `meta-llama/llama-3.2-3b-instruct` | 0 | — | — | — | — | 0.066 |
| UNAVAILABLE | `microsoft/phi-4-mini-instruct` | 0 | — | — | — | — | 0.082 |
| UNAVAILABLE | `meta-llama/llama-3.2-1b-instruct` | 0 | — | — | — | — | 0.038 |
| UNAVAILABLE | `cohere/command-r7b-12-2024` | 0 | — | — | — | — | 0.037 |

---

## Caveats

- **UNAVAILABLE ≠ incapable.** The 4 zero-turn models returned `404 — "No endpoints
  available matching your guardrail restrictions and data policy"`. That's the OpenRouter
  **account privacy setting** (`https://openrouter.ai/settings/privacy`) blocking providers
  that require prompt logging — not a capability verdict. Loosen that policy to test them.
- **Single run, fixed script.** Numbers are one 8-turn pass; trace/layer counts have
  run-to-run variance. For a final default, re-run the top ~8 at more turns/repeats.
- **Engine robustness note:** several models triggered a non-fatal
  `Game tool decrypt_cipher failed: 'str' object has no attribute 'get'` (model passed a
  string where a dict was expected). Logged, game continues — worth hardening separately.
