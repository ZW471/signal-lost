# OpenRouter Model Sweep — Signal Lost

Finds **cheap-yet-capable** OpenRouter models for Signal Lost and the **minimum capability**
the engine needs. As of the routing change, every API provider (incl. openrouter) runs the
**full 11-node LangGraph path with tool-calling** — only the OAuth CLI backends (codex/
claude-code) use the single-call bypass. **So the full-graph results below are the ones that
matter for real openrouter play;** the bypass results are kept as a secondary capability view.

## Runs

| Run | Date | Models | Turns | Path | Notes |
|-----|------|-------:|------:|------|-------|
| Bypass-quick | 2026-06-17 | 35 | 8 | single-call | initial bracket |
| Bypass-full | 2026-06-18 | 117 | 16 | single-call | structured-output capability |
| **Graph-full** | 2026-06-18 | **117** | **6** | **full LangGraph + tools** | **primary**; ~44 min, ~$4 |
| Narrative grades | 2026-06-18 | 70 | — | codex judge | scores graph transcripts 1-10 |

## How to run it again

```bash
# Full LangGraph path (real openrouter path) — needs OPENROUTER_API_KEY in .env
uv run tests/scripts/model_sweep.py --models tests/scripts/sweep_models_large.json \
    --turns 6 --workers 8 --engine graph --call-timeout 60

# Single-call bypass path (codex/claude-code style)
uv run tests/scripts/model_sweep.py --models tests/scripts/sweep_models_large.json \
    --turns 16 --workers 8 --engine bypass

# Narrative-quality grades over a sweep's collected transcripts (codex judge, no API spend)
uv run tests/scripts/grade_narratives.py --sweep tests/reviews/sweep/sweep_<ts>.json
```

## What it measures

- **Graph path**: each turn the candidate model plays every LLM node (resolver+tools, input
  validator, world sim, language check). It must **support tool/function-calling** and actually
  **drive the state-recording tools**. Signals: Layer (L0-L5), Traces, MutRate (fraction of
  turns that changed state), latency. Tiers: EXCELLENT (L4+,≥10 trc) · STRONG (L3+,≥6) ·
  OK (L2+,≥3) · WEAK (narrates but barely mutates) · NO_TOOLS / DATA_POLICY (404 — unavailable).
- **Narrative grade**: an anonymous transcript is scored 1-10 by a codex judge on atmosphere,
  prose, coherence, responsiveness, show-don't-tell, and overall.
- `c/turn` = est. cents/turn at ~5k in + 1.2k out tokens (one model call; the graph makes ~4-5).

## Minimum capability requirement (full path)

Two hard gates, both stricter than the bypass:

1. **Tool-calling support.** 17 models returned *“no endpoints that support
   tool use”* and 16 returned the data-policy 404 — together ~33 of 117 simply can't run the
   full path on this account. Whole families are out (Gemma-3, Llama-3, Mistral-Nemo/Small-3.1).
2. **Proactive tool use.** Of the models that *can* tool-call, ~50 land in WEAK: they narrate
   fluently but **never call the recording tools** (knowledge stays flat, L0). This includes
   strong general models — `openai/gpt-4o-mini`, `openai/gpt-4.1-nano`, `deepseek/deepseek-chat-v3-0324`,
   `minimax/minimax-m2`. Great prose ≠ driving the game.

Only **5 EXCELLENT + 13 STRONG + 15 OK** of 117 actually drive state on the full path
(vs 48 EXCELLENT on the bypass). The practical minimum: *a model that both supports tools and
proactively records discoveries each turn* — empirically the ByteDance-Seed, Qwen3(-next/32b+),
Nemotron, Gemma-4-MoE, GLM-4.6+, MiniMax-M3, and Kimi families.

## Recommended for the full path (drives state **and** narrates ≥6/10), cheapest first

| # | Model | c/turn | Tier | Layer | Traces | MutRate | Narr | Latency(s) |
|--:|-------|-------:|------|------:|------:|--------:|----:|-----------:|
| 1 | `qwen/qwen3-235b-a22b-2507` | 0.057 | STRONG | 3 | 10 | 0.67 | 6 | 27.8 |
| 2 | `google/gemma-4-26b-a4b-it` | 0.0696 | STRONG | 3 | 14 | 0.67 | 7 | 43.5 |
| 3 | `qwen/qwen3-32b` | 0.0736 | STRONG | 3 | 6 | 0.6 | 7 | 34.6 |
| 4 | `nvidia/nemotron-3-super-120b-a12b` | 0.099 | STRONG | 3 | 14 | 0.67 | 7 | 38.5 |
| 5 | `google/gemma-4-31b-it` | 0.102 | OK | 2 | 3 | 0.4 | 6 | 48.1 |
| 6 | `inclusionai/ring-2.6-1t` | 0.1125 | STRONG | 4 | 9 | 0.5 | 6 | 26.7 |
| 7 | `deepseek/deepseek-v3.1-terminus` | 0.249 | OK | 3 | 4 | 0.33 | 6 | 25.5 |
| 8 | `bytedance-seed/seed-1.6` | 0.365 | STRONG | 3 | 11 | 0.83 | 6 | 97.4 |
| 9 | `qwen/qwen3.5-122b-a10b` | 0.3796 | STRONG | 3 | 6 | 0.33 | 6 | 67.0 |
| 10 | `qwen/qwen3.5-397b-a17b` | 0.4865 | EXCELLENT | 4 | 12 | 0.67 | 6 | 100.1 |
| 11 | `qwen/qwen3.6-27b` | 0.5247 | OK | 2 | 4 | 0.5 | 6 | 78.6 |

**Sweet-spot picks** (good at *both* state-driving and prose, and cheap):
`google/gemma-4-26b-a4b-it` (0.07¢, STRONG, narr 7), `qwen/qwen3-32b` (0.07¢, STRONG, narr 7),
and `nvidia/nemotron-3-super-120b-a12b` (0.10¢, STRONG, narr 7). Cheapest viable is
`qwen/qwen3-235b-a22b-2507` (0.057¢). Deepest is `qwen/qwen3.5-397b-a17b` (EXCELLENT L4) but slow.

> Tension worth noting: the **best narrators** (`deepseek/deepseek-v4-pro` 8, `nvidia/nemotron-3-ultra-550b` 8,
> `mistralai/mistral-small-3.2-24b` 7, `tencent/hy3-preview` 7) are mostly **WEAK at driving state** —
> beautiful prose, but they don't record discoveries, so the game stalls. Pick for both, not one.

## Narrative-quality leaderboard (top 18, codex judge)

| Narr | Graph tier | c/turn | Model |
|----:|-----------|-------:|-------|
| 8 | WEAK | 0.3219 | `deepseek/deepseek-v4-pro` |
| 8 | WEAK | 0.514 | `nvidia/nemotron-3-ultra-550b-a55b` |
| 7 | WEAK | 0.0615 | `mistralai/mistral-small-3.2-24b-instruct` |
| 7 | WEAK | 0.0642 | `tencent/hy3-preview` |
| 7 | STRONG | 0.0696 | `google/gemma-4-26b-a4b-it` |
| 7 | STRONG | 0.0736 | `qwen/qwen3-32b` |
| 7 | STRONG | 0.099 | `nvidia/nemotron-3-super-120b-a12b` |
| 7 | WEAK | 0.195 | `qwen/qwen3.6-35b-a3b` |
| 7 | WEAK | 0.259 | `minimax/minimax-m2.1` |
| 7 | WEAK | 0.464 | `minimax/minimax-m1` |
| 6 | STRONG | 0.057 | `qwen/qwen3-235b-a22b-2507` |
| 6 | OK | 0.102 | `google/gemma-4-31b-it` |
| 6 | WEAK | 0.1125 | `inclusionai/ling-2.6-1t` |
| 6 | STRONG | 0.1125 | `inclusionai/ring-2.6-1t` |
| 6 | WEAK | 0.124 | `mistralai/ministral-14b-2512` |
| 6 | OK | 0.249 | `deepseek/deepseek-v3.1-terminus` |
| 6 | WEAK | 0.25 | `openai/gpt-5.4-nano` |
| 6 | WEAK | 0.2847 | `qwen/qwen3.5-27b` |

## Full graph-path results (117 models)

| Tier | Model | Traces | Layer | MutRate | Narr | Latency(s) | c/turn |
|------|-------|------:|------:|--------:|----:|-----------:|-------:|
| EXCELLENT | `bytedance-seed/seed-2.0-mini` | 17 | 4 | 1.0 | 5 | 161.5 | 0.098 |
| EXCELLENT | `moonshotai/kimi-k2.5` | 14 | 4 | 1.0 | 5 | 166.9 | 0.4305 |
| EXCELLENT | `bytedance-seed/seed-2.0-lite` | 13 | 4 | 0.5 | — | 47.4 | 0.365 |
| EXCELLENT | `qwen/qwen3.5-397b-a17b` | 12 | 4 | 0.67 | 6 | 100.1 | 0.4865 |
| EXCELLENT | `qwen/qwen3-next-80b-a3b-instruct` | 11 | 4 | 1.0 | — | 12.2 | 0.177 |
| STRONG | `google/gemma-4-26b-a4b-it` | 14 | 3 | 0.67 | 7 | 43.5 | 0.0696 |
| STRONG | `nvidia/nemotron-3-super-120b-a12b` | 14 | 3 | 0.67 | 7 | 38.5 | 0.099 |
| STRONG | `minimax/minimax-m3` | 13 | 3 | 0.83 | 4 | 138.3 | 0.294 |
| STRONG | `inclusionai/ring-2.6-1t` | 9 | 4 | 0.5 | 6 | 26.7 | 0.1125 |
| STRONG | `bytedance-seed/seed-1.6` | 11 | 3 | 0.83 | 6 | 97.4 | 0.365 |
| STRONG | `minimax/minimax-m2.7` | 8 | 4 | 0.33 | 5 | 40.9 | 0.245 |
| STRONG | `qwen/qwen3-235b-a22b-2507` | 10 | 3 | 0.67 | 6 | 27.8 | 0.057 |
| STRONG | `z-ai/glm-5` | 10 | 3 | 0.67 | 5 | 99.9 | 0.5304 |
| STRONG | `z-ai/glm-4.7` | 9 | 3 | 0.5 | 4 | 44.6 | 0.41 |
| STRONG | `openai/gpt-5-mini` | 7 | 3 | 1.0 | — | 80.3 | 0.365 |
| STRONG | `qwen/qwen3-32b` | 6 | 3 | 0.6 | 7 | 34.6 | 0.0736 |
| STRONG | `stepfun/step-3.7-flash` | 6 | 3 | 1.0 | — | 110.4 | 0.238 |
| STRONG | `qwen/qwen3.5-122b-a10b` | 6 | 3 | 0.33 | 6 | 67.0 | 0.3796 |
| OK | `openai/gpt-oss-120b` | 4 | 4 | 0.5 | — | 43.6 | 0.0411 |
| OK | `z-ai/glm-4.7-flash` | 3 | 4 | 0.33 | 4 | 26.4 | 0.078 |
| OK | `deepseek/deepseek-v3.2` | 3 | 4 | 0.5 | 3 | 82.8 | 0.1556 |
| OK | `deepseek/deepseek-v3.1-terminus` | 4 | 3 | 0.33 | 6 | 25.5 | 0.249 |
| OK | `nvidia/llama-3.3-nemotron-super-49b-v1.5` | 3 | 3 | 0.5 | 5 | 54.6 | 0.248 |
| OK | `deepseek/deepseek-v4-flash` | 5 | 2 | 0.33 | 5 | 28.3 | 0.0666 |
| OK | `z-ai/glm-4.6` | 5 | 2 | 0.5 | 5 | 41.0 | 0.4238 |
| OK | `google/gemini-2.5-flash` | 4 | 2 | 0.33 | 5 | 11.0 | 0.45 |
| OK | `qwen/qwen3.6-27b` | 4 | 2 | 0.5 | 6 | 78.6 | 0.5247 |
| OK | `amazon/nova-micro-v1` | 3 | 2 | 0.5 | 4 | 6.1 | 0.0343 |
| OK | `qwen/qwen3-8b` | 3 | 2 | 0.5 | 4 | 44.6 | 0.073 |
| OK | `meta-llama/llama-3.3-70b-instruct` | 3 | 2 | 0.5 | — | 19.7 | 0.0884 |
| OK | `openai/gpt-5-nano` | 3 | 2 | 0.83 | 5 | 91.9 | 0.073 |
| OK | `google/gemma-4-31b-it` | 3 | 2 | 0.4 | 6 | 48.1 | 0.102 |
| OK | `qwen/qwen-2.5-72b-instruct` | 3 | 2 | 0.33 | 4 | 43.6 | 0.228 |
| WEAK | `openai/gpt-oss-20b` | 2 | 2 | 0.83 | — | 25.0 | 0.0313 |
| WEAK | `z-ai/glm-4.6v` | 2 | 2 | 0.33 | 5 | 32.6 | 0.258 |
| WEAK | `qwen/qwen3-14b` | 1 | 1 | 1.0 | — | 40.1 | 0.0788 |
| WEAK | `mistralai/mistral-small-24b-instruct-2501` | 0 | 0 | 1.0 | — | 1.5 | 0.0346 |
| WEAK | `qwen/qwen-2.5-7b-instruct` | 0 | 0 | 1.0 | — | 4.5 | 0.032 |
| WEAK | `inclusionai/ling-2.6-flash` | 0 | 0 | 0.17 | 5 | 4.7 | 0.0086 |
| WEAK | `arcee-ai/trinity-mini` | 0 | 0 | 0.5 | — | 5.0 | 0.0405 |
| WEAK | `google/gemma-3-12b-it` | 0 | 0 | 0.17 | 5 | 9.3 | 0.043 |
| WEAK | `amazon/nova-lite-v1` | 0 | 0 | 0.17 | 3 | 9.7 | 0.0588 |
| WEAK | `meta-llama/llama-3.1-8b-instruct` | 0 | 0 | 0.17 | 2 | 21.1 | 0.0136 |
| WEAK | `qwen/qwen3-30b-a3b-instruct-2507` | 0 | 0 | 0.17 | 4 | 18.2 | 0.0472 |
| WEAK | `rekaai/reka-edge` | 0 | 0 | 0.5 | — | 2.0 | 0.062 |
| WEAK | `mistralai/mistral-small-3.2-24b-instruct` | 0 | 0 | 0.17 | 7 | 9.4 | 0.0615 |
| WEAK | `mistralai/ministral-3b-2512` | 0 | 0 | 0.17 | 4 | 5.0 | 0.062 |
| WEAK | `google/gemma-3-27b-it` | 0 | 0 | 0.2 | 4 | 18.3 | 0.0592 |
| WEAK | `qwen/qwen3.5-9b` | 0 | 0 | 0.5 | — | 34.6 | 0.068 |
| WEAK | `tencent/hy3-preview` | 0 | 0 | 0.17 | 7 | 41.7 | 0.0642 |
| WEAK | `bytedance-seed/seed-1.6-flash` | 0 | 0 | 0.17 | 5 | 24.3 | 0.0735 |
| WEAK | `nvidia/nemotron-3-nano-30b-a3b` | 0 | 0 | 0.17 | 3 | 75.2 | 0.049 |
| WEAK | `meta-llama/llama-4-scout` | 0 | 0 | 0.17 | 5 | 3.4 | 0.086 |
| WEAK | `essentialai/rnj-1-instruct` | 0 | 0 | 0.17 | 2 | 5.4 | 0.093 |
| WEAK | `mistralai/ministral-8b-2512` | 0 | 0 | 0.17 | 5 | 8.6 | 0.093 |
| WEAK | `google/gemini-2.5-flash-lite-preview-09-2025` | 0 | 0 | 0.17 | 4 | 6.1 | 0.098 |
| WEAK | `openai/gpt-4.1-nano` | 0 | 0 | 0.17 | 4 | 2.6 | 0.098 |
| WEAK | `inclusionai/ling-2.6-1t` | 0 | 0 | 0.17 | 6 | 6.2 | 0.1125 |
| WEAK | `meta-llama/llama-4-maverick` | 0 | 0 | 0.17 | 4 | 5.2 | 0.147 |
| WEAK | `mistralai/ministral-14b-2512` | 0 | 0 | 0.17 | 6 | 8.7 | 0.124 |
| WEAK | `openai/gpt-4o-mini-2024-07-18` | 0 | 0 | 0.17 | 5 | 8.5 | 0.147 |
| WEAK | `stepfun/step-3.5-flash` | 0 | 0 | 0.17 | 3 | 52.2 | 0.081 |
| WEAK | `minimax/minimax-m2.5` | 0 | 0 | 0.17 | 4 | 19.6 | 0.183 |
| WEAK | `z-ai/glm-4.5-air` | 0 | 0 | 0.17 | 5 | 34.4 | 0.167 |
| WEAK | `deepseek/deepseek-chat-v3-0324` | 0 | 0 | 0.17 | 4 | 23.4 | 0.1924 |
| WEAK | `prime-intellect/intellect-3` | 0 | 0 | 0.17 | 5 | 12.7 | 0.232 |
| WEAK | `qwen/qwen3.5-35b-a3b` | 0 | 0 | 0.17 | 5 | 37.9 | 0.19 |
| WEAK | `qwen/qwen3.6-35b-a3b` | 0 | 0 | 0.17 | 7 | 36.9 | 0.195 |
| WEAK | `minimax/minimax-m2` | 0 | 0 | 0.17 | 4 | 29.7 | 0.2475 |
| WEAK | `meta-llama/llama-3.1-70b-instruct` | 0 | 0 | 0.17 | 4 | 25.2 | 0.248 |
| WEAK | `openai/gpt-5.4-nano` | 0 | 0 | 0.17 | 6 | 10.0 | 0.25 |
| WEAK | `anthropic/claude-3-haiku` | 0 | 0 | 0.17 | 5 | 9.7 | 0.275 |
| WEAK | `minimax/minimax-m2.1` | 0 | 0 | 0.17 | 7 | 20.3 | 0.259 |
| WEAK | `google/gemini-3.1-flash-lite` | 0 | 0 | 0.17 | 6 | 8.7 | 0.305 |
| WEAK | `openai/gpt-4.1-mini` | 0 | 0 | 0.17 | 6 | 6.2 | 0.392 |
| WEAK | `deepseek/deepseek-v4-pro` | 0 | 0 | 0.17 | 8 | 58.2 | 0.3219 |
| WEAK | `openai/gpt-3.5-turbo` | 0 | 0 | 0.17 | 4 | 4.5 | 0.43 |
| WEAK | `qwen/qwen3.5-27b` | 0 | 0 | 0.17 | 6 | 80.7 | 0.2847 |
| WEAK | `amazon/nova-2-lite-v1` | 0 | 0 | 0.17 | 4 | 6.6 | 0.45 |
| WEAK | `minimax/minimax-m1` | 0 | 0 | 0.17 | 7 | 19.2 | 0.464 |
| WEAK | `nvidia/nemotron-3-ultra-550b-a55b` | 0 | 0 | 0.17 | 8 | 11.2 | 0.514 |
| WEAK | `z-ai/glm-4.5v` | 0 | 0 | 0.17 | 3 | 27.4 | 0.516 |
| WEAK | `deepseek/deepseek-r1-0528` | 0 | 0 | 0.17 | 5 | 100.2 | 0.508 |
| NO_TOOLS | `ibm-granite/granite-4.0-h-micro` | 0 | 1 | 0.0 | — | 3.2 | 0.0219 |
| NO_TOOLS | `liquid/lfm-2-24b-a2b` | 0 | 1 | 0.0 | — | 4.0 | 0.0294 |
| NO_TOOLS | `google/gemma-3-4b-it` | 0 | 1 | 0.0 | — | 0.8 | 0.037 |
| NO_TOOLS | `meta-llama/llama-3.2-1b-instruct` | 0 | 1 | 0.0 | — | 0.3 | 0.0376 |
| NO_TOOLS | `google/gemma-3n-e4b-it` | 0 | 1 | 0.0 | — | 2.4 | 0.0444 |
| NO_TOOLS | `microsoft/phi-4` | 0 | 1 | 0.0 | — | 1.9 | 0.0493 |
| NO_TOOLS | `meta-llama/llama-3.2-3b-instruct` | 0 | 1 | 0.0 | — | 0.4 | 0.0657 |
| NO_TOOLS | `microsoft/phi-4-mini-instruct` | 0 | 1 | 0.0 | — | 0.3 | 0.082 |
| NO_TOOLS | `rekaai/reka-flash-3` | 0 | 1 | 0.0 | — | 80.1 | 0.074 |
| NO_TOOLS | `meta-llama/llama-3-8b-instruct` | 0 | 1 | 0.0 | — | 1.6 | 0.0868 |
| NO_TOOLS | `tencent/hunyuan-a13b-instruct` | 0 | 1 | 0.0 | — | 1.6 | 0.1384 |
| NO_TOOLS | `minimax/minimax-01` | 0 | 1 | 0.0 | — | 0.7 | 0.232 |
| NO_TOOLS | `mistralai/mistral-small-3.1-24b-instruct` | 0 | 1 | 0.0 | — | 0.3 | 0.2421 |
| NO_TOOLS | `meta-llama/llama-3-70b-instruct` | 0 | 1 | 0.0 | — | 1.1 | 0.3438 |
| NO_TOOLS | `google/gemma-2-27b-it` | 0 | 1 | 0.0 | — | 1.4 | 0.403 |
| NO_TOOLS | `deepseek/deepseek-r1-distill-llama-70b` | 0 | 1 | 0.0 | — | 4.8 | 0.496 |
| NO_TOOLS | `aion-labs/aion-1.0-mini` | 0 | 1 | 0.0 | — | 0.3 | 0.518 |
| DATA_POLICY | `mistralai/mistral-nemo` | 0 | 1 | 0.0 | — | 3.7 | 0.0136 |
| DATA_POLICY | `ibm-granite/granite-4.1-8b` | 0 | 1 | 0.0 | — | 0.3 | 0.037 |
| DATA_POLICY | `qwen/qwen3.5-flash-02-23` | 0 | 1 | 0.0 | — | 0.3 | 0.0637 |
| DATA_POLICY | `allenai/olmo-3-32b-think` | 0 | 1 | 0.0 | — | 0.3 | 0.135 |
| DATA_POLICY | `mistralai/mistral-small-2603` | 0 | 1 | 0.0 | — | 1.2 | 0.147 |
| DATA_POLICY | `upstage/solar-pro-3` | 0 | 1 | 0.0 | — | 0.3 | 0.147 |
| DATA_POLICY | `mistralai/mistral-saba` | 0 | 1 | 0.0 | — | 3.1 | 0.172 |
| DATA_POLICY | `qwen/qwen-plus-2025-07-28` | 0 | 1 | 0.0 | — | 0.6 | 0.2236 |
| DATA_POLICY | `qwen/qwen3.6-flash` | 0 | 1 | 0.0 | — | 0.4 | 0.2288 |
| DATA_POLICY | `qwen/qwen3.7-plus` | 0 | 1 | 0.0 | — | 0.6 | 0.3136 |
| DATA_POLICY | `qwen/qwen3.5-plus-02-15` | 0 | 1 | 0.0 | — | 0.4 | 0.3172 |
| DATA_POLICY | `qwen/qwen3.5-plus-20260420` | 0 | 1 | 0.0 | — | 0.3 | 0.366 |
| DATA_POLICY | `qwen/qwen3.6-plus` | 0 | 1 | 0.0 | — | 0.4 | 0.3965 |
| DATA_POLICY | `mistralai/mistral-large-2512` | 0 | 1 | 0.0 | — | 0.6 | 0.43 |
| DATA_POLICY | `mistralai/mistral-medium-3` | 0 | 1 | 0.0 | — | 1.3 | 0.44 |
| DATA_POLICY | `mistralai/mistral-medium-3.1` | 0 | 1 | 0.0 | — | 0.3 | 0.44 |
| ERROR | `arcee-ai/virtuoso-large` | 0 | 1 | 0.0 | — | 1.2 | 0.519 |

## Secondary: single-call bypass path (codex/claude-code style)

The bypass forces structured-JSON mutations instead of tool-calls, so it's far more forgiving —
**48 EXCELLENT / 34 STRONG / 10 WEAK / 21 UNAVAILABLE** of 117. Cheapest EXCELLENT on the bypass:

| # | Model | c/turn | Layer | Traces |
|--:|-------|-------:|------:|------:|
| 1 | `inclusionai/ling-2.6-flash` | 0.0086 | 4 | 14 |
| 2 | `openai/gpt-oss-20b` | 0.0313 | 4 | 10 |
| 3 | `google/gemma-3-4b-it` | 0.037 | 4 | 13 |
| 4 | `arcee-ai/trinity-mini` | 0.0405 | 4 | 14 |
| 5 | `openai/gpt-oss-120b` | 0.0411 | 4 | 14 |
| 6 | `qwen/qwen3-30b-a3b-instruct-2507` | 0.0472 | 4 | 19 |
| 7 | `qwen/qwen3-235b-a22b-2507` | 0.057 | 4 | 19 |
| 8 | `google/gemma-3-27b-it` | 0.0592 | 4 | 10 |
| 9 | `mistralai/ministral-3b-2512` | 0.062 | 4 | 15 |
| 10 | `tencent/hy3-preview` | 0.0642 | 4 | 19 |
| 11 | `qwen/qwen3.5-9b` | 0.068 | 4 | 19 |
| 12 | `qwen/qwen3-8b` | 0.073 | 4 | 11 |

These matter only if you run codex/claude-code (which bypass), or as a structured-output
capability reference. For real openrouter play, use the full-path table above.

## Caveats

- **6 turns is shallow** for the full path (it's ~4-5x slower than the bypass; one model hit a
  663s opening turn). Traces/layer under-count what a longer game would reach — treat as relative.
- **Narrator ≠ driver.** Capability tier and narrative grade are different axes; the report keeps
  them separate on purpose. The judge penalized a common full-path flaw: leaking mechanics/status
  text into the prose.
- **Single run, real variance.** One pass per model; re-run top picks with seeds before locking a default.
- **UNAVAILABLE = no tool-capable endpoint under your data policy** (`openrouter.ai/settings/privacy`),
  not a capability verdict — though many UNAVAILABLE models genuinely lack tool support.