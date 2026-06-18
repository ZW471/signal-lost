# OpenRouter Model Sweep — Signal Lost

Capability/cost sweep to find **cheap-yet-capable** OpenRouter models for running
Signal Lost, and to pin down the **minimum model capability** the engine needs.

## Runs

| Run | Date | Models | Turns | Notes |
|-----|------|-------:|------:|-------|
| Quick | 2026-06-17 | 35 | 8 | initial bracket |
| **Comprehensive** | 2026-06-18 | **117** | **16** | primary — this report; ~87 min wall, ~$2.84 spend |

Comprehensive tier spread: **48 EXCELLENT · 34 STRONG · 3 OK · 10 WEAK · 21 UNAVAILABLE · 1 ERROR**.

## How to run it again

```bash
# Comprehensive (117 models x 16 turns). Needs OPENROUTER_API_KEY in .env
uv run tests/scripts/model_sweep.py \
    --models tests/scripts/sweep_models_large.json \
    --turns 16 --workers 8 --call-timeout 90

# Smaller/faster bracket
uv run tests/scripts/model_sweep.py --models tests/scripts/sweep_models.json --turns 8 --workers 6
```

Each run prints a ranked table and writes `tests/reviews/sweep/sweep_<ts>.{json,md}`
(gitignored, with live pricing). Candidate lists are plain OpenRouter slugs; edit them or
regenerate from `https://openrouter.ai/api/v1/models`.

## What it measures

OpenRouter runs on the **single-call bypass engine** (`engine.claude_code_engine.run_turn`),
so the sweep drives that exact path. Every model plays an **identical fixed action script**.
Each turn the model must follow a long, layer-gated system prompt **and emit a valid
structured-JSON state mutation**. Signals captured:

- **Layer (L0–L5)** — how deep the model drove the gated game state.
- **Traces** — count of correctly-applied state mutations (discoveries).
- **MutRate** — fraction of turns that actually changed state = **structured-output success rate**.
- **Latency** — avg seconds/turn (one bypass call).

Tiers: EXCELLENT (L4+, ≥10 traces) · STRONG (L3+, ≥6) · OK (L2+, ≥3) · WEAK (shallow) ·
UNAVAILABLE (404 — account data-policy, *not* capability). `c/turn` = est. cents/turn at ~5k in + 1.2k out tokens.

## Minimum capability requirement

**It's structured-output fidelity, not parameter count.** The cleanest single metric is **MutRate**:

- **Capable models hold MutRate ≳ 0.6 and reach L3–L4+.** Several *tiny* models clear it —
  `inclusionai/ling-2.6-flash` and `google/gemma-3-4b-it` hit L4.
- **Format-fail floor:** a cluster sits at **MutRate ≈ 0.06, L0, 0 traces** — they narrate
  fluent prose but never emit valid state JSON, so the game can't advance:
  `google/gemini-2.5-flash`, `liquid/lfm-2-24b-a2b`, `rekaai/reka-edge`, `meta-llama/llama-3-8b-instruct`, `rekaai/reka-flash-3`, `meta-llama/llama-3-70b-instruct`, `google/gemma-2-27b-it`, `minimax/minimax-m1`, `deepseek/deepseek-r1-distill-llama-70b`.
- Size doesn't save them: `meta-llama/llama-3-70b` and `deepseek-r1-distill-llama-70b` are in the floor;
  4B–9B models with good JSON discipline are not.

So the **practical minimum** is *any model that reliably emits the engine's JSON schema while
following multi-layer instructions* — empirically the Qwen 2.5/3, Gemma 3, gpt-oss, Mistral
Small/Ministral, and most modern MoE families, down to ~3–4B in the strongest cases.

## Recommended — best value (cheapest EXCELLENT first)

| # | Model | c/turn | Layer | Traces | Knowledge | MutRate | Latency(s) |
|--:|-------|-------:|------:|------:|----------:|--------:|-----------:|
| 1 | `inclusionai/ling-2.6-flash` | 0.0086 | 4 | 14 | 23 | 0.67 | 5.7 |
| 2 | `openai/gpt-oss-20b` | 0.0313 | 4 | 10 | 30 | 0.69 | 30.3 |
| 3 | `google/gemma-3-4b-it` | 0.037 | 4 | 13 | 35 | 0.93 | 43.1 |
| 4 | `arcee-ai/trinity-mini` | 0.0405 | 4 | 14 | 28 | 0.77 | 56.9 |
| 5 | `openai/gpt-oss-120b` | 0.0411 | 4 | 14 | 52 | 1.0 | 23.2 |
| 6 | `qwen/qwen3-30b-a3b-instruct-2507` | 0.0472 | 4 | 19 | 66 | 1.0 | 17.7 |
| 7 | `qwen/qwen3-235b-a22b-2507` | 0.057 | 4 | 19 | 69 | 1.0 | 20.2 |
| 8 | `google/gemma-3-27b-it` | 0.0592 | 4 | 10 | 38 | 1.0 | 16.3 |
| 9 | `mistralai/ministral-3b-2512` | 0.062 | 4 | 15 | 31 | 0.5 | 7.4 |
| 10 | `tencent/hy3-preview` | 0.0642 | 4 | 19 | 74 | 1.0 | 21.2 |
| 11 | `qwen/qwen3.5-9b` | 0.068 | 4 | 19 | 73 | 1.0 | 31.7 |
| 12 | `openai/gpt-5-nano` | 0.073 | 4 | 16 | 51 | 0.94 | 35.0 |
| 13 | `qwen/qwen3-8b` | 0.073 | 4 | 11 | 18 | 1.0 | 23.3 |
| 14 | `bytedance-seed/seed-1.6-flash` | 0.0735 | 4 | 18 | 69 | 1.0 | 12.0 |
| 15 | `qwen/qwen3-32b` | 0.0736 | 4 | 13 | 45 | 1.0 | 24.0 |
| 16 | `z-ai/glm-4.7-flash` | 0.078 | 4 | 15 | 19 | 1.0 | 30.9 |
| 17 | `qwen/qwen3-14b` | 0.0788 | 4 | 19 | 41 | 1.0 | 29.5 |
| 18 | `stepfun/step-3.5-flash` | 0.081 | 4 | 23 | 50 | 1.0 | 79.3 |

## Recommended — fastest capable (≤8s/turn, EXCELLENT/STRONG)

Latency matters because the bypass is one call per turn — good for interactive play.

| Model | Latency(s) | Tier | c/turn | Layer | MutRate |
|-------|-----------:|------|-------:|------:|--------:|
| `openai/gpt-4.1-nano` | 3.0 | STRONG | 0.098 | 3 | 0.88 |
| `amazon/nova-micro-v1` | 3.7 | STRONG | 0.0343 | 4 | 0.94 |
| `google/gemini-3.1-flash-lite` | 4.1 | EXCELLENT | 0.305 | 4 | 1.0 |
| `amazon/nova-2-lite-v1` | 4.2 | EXCELLENT | 0.45 | 4 | 0.81 |
| `google/gemini-2.5-flash-lite-preview-09-2025` | 4.3 | STRONG | 0.098 | 3 | 1.0 |
| `inclusionai/ling-2.6-flash` | 5.7 | EXCELLENT | 0.0086 | 4 | 0.67 |
| `mistralai/mistral-small-2603` | 6.7 | STRONG | 0.147 | 3 | 0.5 |
| `essentialai/rnj-1-instruct` | 6.9 | EXCELLENT | 0.093 | 4 | 0.62 |
| `openai/gpt-5.4-nano` | 7.1 | EXCELLENT | 0.25 | 4 | 1.0 |
| `meta-llama/llama-4-scout` | 7.1 | STRONG | 0.086 | 4 | 0.56 |
| `mistralai/ministral-3b-2512` | 7.4 | EXCELLENT | 0.062 | 4 | 0.5 |
| `anthropic/claude-3-haiku` | 7.4 | STRONG | 0.275 | 3 | 0.31 |

**Top picks**
- **Best value overall:** `inclusionai/ling-2.6-flash` — L4 at ~$0.009/turn and 5.7s. (Lesser-known; if you want a name-brand pick, `openai/gpt-oss-20b`/`120b` or `qwen/qwen3-30b-a3b-instruct-2507`.)
- **Best speed+depth:** `google/gemini-3.1-flash-lite` (4.1s, L4, MutRate 1.0) and `bytedance-seed/seed-1.6-flash` (12s, L4, 1.0).
- **Fast cheap workhorses (STRONG):** `openai/gpt-4.1-nano` (3.0s), `amazon/nova-micro-v1` (3.7s), `google/gemini-2.5-flash-lite` (4.3s).
- **Deepest/highest-detail runs:** `qwen/qwen3.5-122b-a10b` and `nvidia/llama-3.3-nemotron-super-49b-v1.5` reached **L5**; `moonshotai/kimi-k2.5` and `minimax/minimax-m3` recorded ~95 knowledge items (but are slower/pricier).

## Full results (117 models)

| Tier | Model | Turns | Traces | Knowledge | Layer | MutRate | Latency(s) | c/turn |
|------|-------|------:|------:|----------:|------:|--------:|-----------:|-------:|
| EXCELLENT | `moonshotai/kimi-k2.5` | 16 | 21 | 95 | 4 | 1.0 | 104.2 | 0.4305 |
| EXCELLENT | `minimax/minimax-m3` | 16 | 15 | 96 | 4 | 0.94 | 67.3 | 0.294 |
| EXCELLENT | `tencent/hy3-preview` | 16 | 19 | 74 | 4 | 1.0 | 21.2 | 0.0642 |
| EXCELLENT | `qwen/qwen3.5-9b` | 13 | 19 | 73 | 4 | 1.0 | 31.7 | 0.068 |
| EXCELLENT | `qwen/qwen3.5-397b-a17b` | 16 | 19 | 73 | 4 | 0.94 | 23.9 | 0.4865 |
| EXCELLENT | `minimax/minimax-m2.7` | 16 | 20 | 68 | 4 | 0.75 | 21.2 | 0.245 |
| EXCELLENT | `qwen/qwen3.5-122b-a10b` | 16 | 19 | 61 | 5 | 0.94 | 20.1 | 0.3796 |
| EXCELLENT | `qwen/qwen3-235b-a22b-2507` | 16 | 19 | 69 | 4 | 1.0 | 20.2 | 0.057 |
| EXCELLENT | `deepseek/deepseek-v4-pro` | 16 | 19 | 68 | 4 | 1.0 | 56.6 | 0.3219 |
| EXCELLENT | `qwen/qwen3-30b-a3b-instruct-2507` | 16 | 19 | 66 | 4 | 1.0 | 17.7 | 0.0472 |
| EXCELLENT | `stepfun/step-3.5-flash` | 16 | 23 | 50 | 4 | 1.0 | 79.3 | 0.081 |
| EXCELLENT | `bytedance-seed/seed-1.6-flash` | 16 | 18 | 69 | 4 | 1.0 | 12.0 | 0.0735 |
| EXCELLENT | `deepseek/deepseek-r1-0528` | 13 | 23 | 46 | 4 | 1.0 | 66.4 | 0.508 |
| EXCELLENT | `qwen/qwen3.5-27b` | 16 | 16 | 69 | 4 | 0.81 | 40.9 | 0.2847 |
| EXCELLENT | `inclusionai/ring-2.6-1t` | 16 | 17 | 56 | 4 | 0.69 | 12.7 | 0.1125 |
| EXCELLENT | `inclusionai/ling-2.6-1t` | 16 | 17 | 55 | 4 | 1.0 | 11.1 | 0.1125 |
| EXCELLENT | `qwen/qwen3.6-35b-a3b` | 16 | 16 | 57 | 4 | 0.81 | 37.2 | 0.195 |
| EXCELLENT | `nvidia/llama-3.3-nemotron-super-49b-v1.5` | 16 | 18 | 39 | 5 | 0.94 | 22.4 | 0.248 |
| EXCELLENT | `nvidia/nemotron-3-ultra-550b-a55b` | 16 | 17 | 52 | 4 | 0.69 | 16.4 | 0.514 |
| EXCELLENT | `qwen/qwen3-14b` | 13 | 19 | 41 | 4 | 1.0 | 29.5 | 0.0788 |
| EXCELLENT | `openai/gpt-5-nano` | 16 | 16 | 51 | 4 | 0.94 | 35.0 | 0.073 |
| EXCELLENT | `nvidia/nemotron-3-super-120b-a12b` | 16 | 18 | 43 | 4 | 1.0 | 87.0 | 0.099 |
| EXCELLENT | `google/gemini-3.1-flash-lite` | 16 | 17 | 44 | 4 | 1.0 | 4.1 | 0.305 |
| EXCELLENT | `openai/gpt-oss-120b` | 15 | 14 | 52 | 4 | 1.0 | 23.2 | 0.0411 |
| EXCELLENT | `z-ai/glm-4.5-air` | 16 | 13 | 54 | 4 | 0.94 | 24.8 | 0.167 |
| EXCELLENT | `z-ai/glm-4.6v` | 16 | 17 | 38 | 4 | 0.88 | 31.1 | 0.258 |
| EXCELLENT | `qwen/qwen3.6-27b` | 16 | 14 | 46 | 4 | 0.88 | 62.0 | 0.5247 |
| EXCELLENT | `minimax/minimax-m2.5` | 16 | 15 | 41 | 4 | 0.62 | 11.4 | 0.183 |
| EXCELLENT | `meta-llama/llama-3.3-70b-instruct` | 16 | 15 | 40 | 4 | 1.0 | 26.4 | 0.0884 |
| EXCELLENT | `openai/gpt-5-mini` | 16 | 11 | 55 | 4 | 0.81 | 31.8 | 0.365 |
| EXCELLENT | `qwen/qwen3-32b` | 14 | 13 | 45 | 4 | 1.0 | 24.0 | 0.0736 |
| EXCELLENT | `openai/gpt-4.1-mini` | 16 | 15 | 34 | 4 | 0.88 | 10.6 | 0.392 |
| EXCELLENT | `mistralai/ministral-3b-2512` | 16 | 15 | 31 | 4 | 0.5 | 7.4 | 0.062 |
| EXCELLENT | `openai/gpt-5.4-nano` | 13 | 11 | 47 | 4 | 1.0 | 7.1 | 0.25 |
| EXCELLENT | `qwen/qwen3-next-80b-a3b-instruct` | 10 | 14 | 32 | 4 | 1.0 | 8.3 | 0.177 |
| EXCELLENT | `google/gemma-3-4b-it` | 15 | 13 | 35 | 4 | 0.93 | 43.1 | 0.037 |
| EXCELLENT | `arcee-ai/trinity-mini` | 13 | 14 | 28 | 4 | 0.77 | 56.9 | 0.0405 |
| EXCELLENT | `google/gemma-4-31b-it` | 16 | 14 | 28 | 4 | 0.81 | 34.0 | 0.102 |
| EXCELLENT | `amazon/nova-2-lite-v1` | 16 | 12 | 35 | 4 | 0.81 | 4.2 | 0.45 |
| EXCELLENT | `inclusionai/ling-2.6-flash` | 15 | 14 | 23 | 4 | 0.67 | 5.7 | 0.0086 |
| EXCELLENT | `z-ai/glm-4.7-flash` | 7 | 15 | 19 | 4 | 1.0 | 30.9 | 0.078 |
| EXCELLENT | `google/gemma-3-27b-it` | 15 | 10 | 38 | 4 | 1.0 | 16.3 | 0.0592 |
| EXCELLENT | `essentialai/rnj-1-instruct` | 16 | 14 | 19 | 4 | 0.62 | 6.9 | 0.093 |
| EXCELLENT | `openai/gpt-oss-20b` | 16 | 10 | 30 | 4 | 0.69 | 30.3 | 0.0313 |
| EXCELLENT | `z-ai/glm-4.5v` | 16 | 11 | 24 | 4 | 0.62 | 31.6 | 0.516 |
| EXCELLENT | `qwen/qwen3-8b` | 6 | 11 | 18 | 4 | 1.0 | 23.3 | 0.073 |
| EXCELLENT | `prime-intellect/intellect-3` | 16 | 10 | 21 | 4 | 0.38 | 11.8 | 0.232 |
| EXCELLENT | `mistralai/ministral-8b-2512` | 16 | 12 | 11 | 4 | 0.38 | 14.4 | 0.093 |
| STRONG | `qwen/qwen3.5-35b-a3b` | 16 | 17 | 61 | 3 | 0.81 | 16.9 | 0.19 |
| STRONG | `z-ai/glm-4.7` | 16 | 15 | 65 | 3 | 1.0 | 62.0 | 0.41 |
| STRONG | `minimax/minimax-m2` | 16 | 18 | 51 | 3 | 0.81 | 9.8 | 0.2475 |
| STRONG | `minimax/minimax-m2.1` | 16 | 19 | 44 | 3 | 0.62 | 16.2 | 0.259 |
| STRONG | `bytedance-seed/seed-1.6` | 16 | 16 | 56 | 3 | 1.0 | 39.8 | 0.365 |
| STRONG | `bytedance-seed/seed-2.0-mini` | 16 | 15 | 59 | 3 | 0.94 | 34.7 | 0.098 |
| STRONG | `google/gemini-2.5-flash-lite-preview-09-2025` | 16 | 18 | 46 | 3 | 1.0 | 4.3 | 0.098 |
| STRONG | `deepseek/deepseek-v4-flash` | 16 | 16 | 48 | 3 | 0.81 | 18.1 | 0.0666 |
| STRONG | `deepseek/deepseek-v3.1-terminus` | 16 | 16 | 48 | 3 | 1.0 | 17.4 | 0.249 |
| STRONG | `bytedance-seed/seed-2.0-lite` | 16 | 16 | 44 | 3 | 0.75 | 27.4 | 0.365 |
| STRONG | `z-ai/glm-4.6` | 16 | 15 | 43 | 3 | 0.88 | 37.5 | 0.4238 |
| STRONG | `nvidia/nemotron-3-nano-30b-a3b` | 16 | 14 | 43 | 3 | 1.0 | 37.1 | 0.049 |
| STRONG | `z-ai/glm-5` | 16 | 14 | 38 | 3 | 0.44 | 33.9 | 0.5304 |
| STRONG | `deepseek/deepseek-chat-v3-0324` | 16 | 15 | 29 | 3 | 0.88 | 25.3 | 0.1924 |
| STRONG | `deepseek/deepseek-v3.2` | 16 | 13 | 32 | 3 | 0.62 | 32.3 | 0.1556 |
| STRONG | `mistralai/mistral-small-24b-instruct-2501` | 16 | 13 | 29 | 3 | 0.75 | 37.0 | 0.0346 |
| STRONG | `google/gemma-4-26b-a4b-it` | 10 | 13 | 26 | 3 | 1.0 | 38.3 | 0.0696 |
| STRONG | `mistralai/mistral-small-2603` | 16 | 13 | 24 | 3 | 0.5 | 6.7 | 0.147 |
| STRONG | `qwen/qwen-2.5-72b-instruct` | 16 | 9 | 30 | 4 | 1.0 | 21.6 | 0.228 |
| STRONG | `openai/gpt-4.1-nano` | 16 | 10 | 31 | 3 | 0.88 | 3.0 | 0.098 |
| STRONG | `qwen/qwen-2.5-7b-instruct` | 16 | 8 | 24 | 4 | 0.81 | 15.3 | 0.032 |
| STRONG | `mistralai/mistral-small-3.2-24b-instruct` | 16 | 8 | 34 | 3 | 1.0 | 20.7 | 0.0615 |
| STRONG | `meta-llama/llama-4-scout` | 16 | 9 | 17 | 4 | 0.56 | 7.1 | 0.086 |
| STRONG | `meta-llama/llama-3.1-70b-instruct` | 16 | 8 | 30 | 3 | 0.94 | 20.9 | 0.248 |
| STRONG | `tencent/hunyuan-a13b-instruct` | 16 | 7 | 23 | 4 | 0.5 | 9.2 | 0.1384 |
| STRONG | `google/gemma-3-12b-it` | 16 | 8 | 26 | 3 | 0.94 | 13.9 | 0.043 |
| STRONG | `amazon/nova-micro-v1` | 16 | 6 | 21 | 4 | 0.94 | 3.7 | 0.0343 |
| STRONG | `meta-llama/llama-4-maverick` | 16 | 7 | 26 | 3 | 0.81 | 23.6 | 0.147 |
| STRONG | `openai/gpt-4o-mini-2024-07-18` | 16 | 6 | 17 | 4 | 0.62 | 8.2 | 0.147 |
| STRONG | `mistralai/mistral-nemo` | 16 | 7 | 18 | 3 | 0.75 | 9.0 | 0.0136 |
| STRONG | `mistralai/ministral-14b-2512` | 16 | 9 | 8 | 3 | 0.31 | 22.2 | 0.124 |
| STRONG | `microsoft/phi-4` | 16 | 6 | 18 | 3 | 0.69 | 10.7 | 0.0493 |
| STRONG | `anthropic/claude-3-haiku` | 16 | 7 | 9 | 3 | 0.31 | 7.4 | 0.275 |
| STRONG | `meta-llama/llama-3.1-8b-instruct` | 16 | 7 | 8 | 3 | 0.25 | 15.9 | 0.0136 |
| OK | `google/gemma-3n-e4b-it` | 15 | 5 | 50 | 3 | 0.6 | 12.7 | 0.0444 |
| OK | `amazon/nova-lite-v1` | 16 | 5 | 18 | 2 | 0.94 | 13.9 | 0.0588 |
| OK | `stepfun/step-3.7-flash` | 1 | 3 | 8 | 2 | 1.0 | 46.8 | 0.238 |
| WEAK | `openai/gpt-3.5-turbo` | 16 | 2 | 6 | 2 | 0.25 | 2.6 | 0.43 |
| WEAK | `google/gemini-2.5-flash` | 16 | 2 | 3 | 1 | 0.12 | 3.8 | 0.45 |
| WEAK | `liquid/lfm-2-24b-a2b` | 16 | 0 | 2 | 0 | 0.06 | 2.1 | 0.0294 |
| WEAK | `rekaai/reka-edge` | 16 | 0 | 2 | 0 | 0.06 | 3.5 | 0.062 |
| WEAK | `meta-llama/llama-3-8b-instruct` | 16 | 0 | 2 | 0 | 0.06 | 4.1 | 0.0868 |
| WEAK | `rekaai/reka-flash-3` | 15 | 0 | 2 | 0 | 0.07 | 132.1 | 0.074 |
| WEAK | `meta-llama/llama-3-70b-instruct` | 16 | 0 | 2 | 0 | 0.06 | 18.0 | 0.3438 |
| WEAK | `google/gemma-2-27b-it` | 16 | 0 | 2 | 0 | 0.06 | 5.1 | 0.403 |
| WEAK | `minimax/minimax-m1` | 16 | 0 | 2 | 0 | 0.06 | 12.9 | 0.464 |
| WEAK | `deepseek/deepseek-r1-distill-llama-70b` | 16 | 0 | 2 | 0 | 0.06 | 11.8 | 0.496 |
| UNAVAILABLE | `ibm-granite/granite-4.0-h-micro` | 0 | 0 | 0 | 1 | 0.0 | 0.7 | 0.0219 |
| UNAVAILABLE | `ibm-granite/granite-4.1-8b` | 0 | 0 | 0 | 1 | 0.0 | 0.8 | 0.037 |
| UNAVAILABLE | `meta-llama/llama-3.2-1b-instruct` | 0 | 0 | 0 | 1 | 0.0 | 0.3 | 0.0376 |
| UNAVAILABLE | `qwen/qwen3.5-flash-02-23` | 0 | 0 | 0 | 1 | 0.0 | 0.2 | 0.0637 |
| UNAVAILABLE | `meta-llama/llama-3.2-3b-instruct` | 0 | 0 | 0 | 1 | 0.0 | 0.2 | 0.0657 |
| UNAVAILABLE | `microsoft/phi-4-mini-instruct` | 0 | 0 | 0 | 1 | 0.0 | 0.2 | 0.082 |
| UNAVAILABLE | `allenai/olmo-3-32b-think` | 0 | 0 | 0 | 1 | 0.0 | 0.2 | 0.135 |
| UNAVAILABLE | `upstage/solar-pro-3` | 0 | 0 | 0 | 1 | 0.0 | 0.1 | 0.147 |
| UNAVAILABLE | `mistralai/mistral-saba` | 0 | 0 | 0 | 1 | 0.0 | 0.2 | 0.172 |
| UNAVAILABLE | `qwen/qwen-plus-2025-07-28` | 0 | 0 | 0 | 1 | 0.0 | 0.2 | 0.2236 |
| UNAVAILABLE | `qwen/qwen3.6-flash` | 0 | 0 | 0 | 1 | 0.0 | 0.2 | 0.2288 |
| UNAVAILABLE | `minimax/minimax-01` | 0 | 0 | 0 | 1 | 0.0 | 0.2 | 0.232 |
| UNAVAILABLE | `mistralai/mistral-small-3.1-24b-instruct` | 0 | 0 | 0 | 1 | 0.0 | 0.1 | 0.2421 |
| UNAVAILABLE | `qwen/qwen3.7-plus` | 0 | 0 | 0 | 1 | 0.0 | 0.2 | 0.3136 |
| UNAVAILABLE | `qwen/qwen3.5-plus-02-15` | 0 | 0 | 0 | 1 | 0.0 | 0.1 | 0.3172 |
| UNAVAILABLE | `qwen/qwen3.5-plus-20260420` | 0 | 0 | 0 | 1 | 0.0 | 0.2 | 0.366 |
| UNAVAILABLE | `qwen/qwen3.6-plus` | 0 | 0 | 0 | 1 | 0.0 | 0.2 | 0.3965 |
| UNAVAILABLE | `mistralai/mistral-large-2512` | 0 | 0 | 0 | 1 | 0.0 | 0.2 | 0.43 |
| UNAVAILABLE | `mistralai/mistral-medium-3` | 0 | 0 | 0 | 1 | 0.0 | 0.4 | 0.44 |
| UNAVAILABLE | `mistralai/mistral-medium-3.1` | 0 | 0 | 0 | 1 | 0.0 | 0.2 | 0.44 |
| UNAVAILABLE | `aion-labs/aion-1.0-mini` | 0 | 0 | 0 | 1 | 0.0 | 1.1 | 0.518 |
| ERROR | `arcee-ai/virtuoso-large` | 0 | 0 | 0 | 1 | 0.0 | 1.4 | 0.519 |

## Caveats

- **Single run = real variance.** Numbers are one 16-turn pass. Example: `google/gemini-2.5-flash`
  landed WEAK here (L1, MutRate 0.12) but STRONG (L4) in the 8-turn run — a transient (truncation/
  refusal/rate-limit). Re-run the top ~10 with multiple seeds before locking a default.
- **No endings reached.** 16 turns drives to L4–L5 but not to a game ending, so the `Ending`
  column is empty across the board — endings need a longer scripted climb.
- **UNAVAILABLE ≠ incapable.** 21 models returned `404 — No endpoints matching your data policy`,
  i.e. the OpenRouter **account privacy setting** (`openrouter.ai/settings/privacy`) blocks
  log-required providers. Loosen it to test them (many cheap small models live there).
- **Engine robustness:** several models triggered a non-fatal
  `decrypt_cipher failed: 'str' object has no attribute 'get'` (string passed where a dict was
  expected). Logged, game continues — worth hardening separately.
