#!/usr/bin/env python3
"""Signal Lost — OpenRouter model capability sweep.

Drives the SAME single-call bypass engine real openrouter play uses
(``engine.claude_code_engine.run_turn``) across a list of models, running a
fixed action script per model so results are directly comparable. Captures
per-model progress (traces / knowledge / layer), structured-output success,
errors, and latency, then writes a combined ranking.

Each model runs in its own process (so the module-global LLM set via ``set_llm``
never collides) with its own throwaway session dir.

Usage:
    python tests/scripts/model_sweep.py --models tests/scripts/sweep_models.json \
        --turns 8 --workers 5
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import shutil
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed

_THIS = os.path.dirname(os.path.abspath(__file__))
_GAME_ROOT = os.path.abspath(os.path.join(_THIS, "..", ".."))
if _GAME_ROOT not in sys.path:
    sys.path.insert(0, _GAME_ROOT)

# Fixed, exploration-heavy action script — identical for every model so the
# comparison is apples-to-apples. Mirrors full_playthrough's DEFAULT_ACTIONS.
ACTIONS = [
    "Look around. Where am I?",
    "Talk to the nearest person",
    "Ask them about the Signal",
    "Explore the district — head toward any signs of technology",
    "Examine any terminals or screens I can find",
    "Search for information about NEXUS",
    "Try to find someone who knows about the disappearances",
    "Ask about the Severance",
    "Look for encrypted data or signals",
    "Head deeper into the district — follow any leads",
    "Talk to whoever seems most knowledgeable here",
    "Present what I've learned and ask for their theory",
    "Search for evidence of the conspiracy",
    "Try to access restricted areas",
    "Analyze any signal artifacts I've found",
    "Look for allies who share my goals",
    "Plan my next move based on everything I know",
    "Head toward the source of the Signal",
    "Confront what I find",
    "Make my final choice",
]


def _sanitize(model_id: str) -> str:
    return model_id.replace("/", "__").replace(":", "_")


def eval_model(model_id: str, turns: int, call_timeout: int, engine: str = "bypass") -> dict:
    """Run a fixed multi-turn playthrough for one model. Returns metrics.

    engine="bypass" → single-call ``cc_run_turn`` (CLI-style path).
    engine="graph"  → full 11-node LangGraph pipeline with tool-calling (the path
    every API provider, incl. openrouter, actually uses).
    """
    from engine.graph import set_llm
    from engine.state import initial_state, create_new_session
    from engine.llm_factory import create_llm, load_env
    from engine.prompts import extract_deepest_layer

    load_env()
    res: dict = {
        "model": model_id,
        "engine": engine,
        "completed_turns": 0,
        "errors": [],
        "turn_latencies": [],
        "knowledge_trajectory": [],
        "traces_final": 0,
        "knowledge_final": 0,
        "layer_final": 1,
        "location_changed": False,
        "made_progress": False,
        "empty_narratives": 0,
        "mutation_turns": 0,          # turns that actually changed traces/knowledge
        "game_over": False,
        "ending": None,
        "integrity_final": None,
        "narratives": [],             # collected for the quality grader
        "fatal": None,
    }

    try:
        llm = create_llm(
            "openrouter", model_id, temperature=0.7,
            timeout=call_timeout, max_retries=0 if engine == "graph" else 1,
        )
        set_llm(llm, zero_cost=False)
    except Exception as e:  # noqa: BLE001
        res["fatal"] = f"create_llm: {type(e).__name__}: {e}"
        return res

    session_dir = os.path.join(_GAME_ROOT, "session", f"sweep_{engine}", _sanitize(model_id))
    if os.path.isdir(session_dir):
        shutil.rmtree(session_dir, ignore_errors=True)
    try:
        create_new_session(
            session_dir=session_dir, name="Kael", alias="Ghost",
            background="netrunner", difficulty="standard", language="en",
        )
    except Exception as e:  # noqa: BLE001
        res["fatal"] = f"create_session: {type(e).__name__}: {e}"
        return res

    # Graph path keeps GameState in memory across turns (like full_playthrough).
    graph = gstate = None
    if engine == "graph":
        from engine.graph import compile_graph
        from langchain_core.messages import HumanMessage
        try:
            graph = compile_graph()
            gstate = initial_state(session_dir)
        except Exception as e:  # noqa: BLE001
            res["fatal"] = f"compile_graph: {type(e).__name__}: {e}"
            return res
    else:
        from engine.claude_code_engine import run_turn as cc_run_turn

    init_state = initial_state(session_dir)
    init_loc = (init_state.get("location", {}) or {}).get("area", "?")
    prev_traces, prev_kn = 0, 0

    hard_errors = 0
    for i in range(min(turns, len(ACTIONS))):
        action = ACTIONS[i]
        t0 = time.time()
        try:
            if engine == "graph":
                gstate["messages"].append(HumanMessage(content=action))
                # Cap the resolver↔tool loop so one turn can't balloon to minutes.
                out = graph.invoke(gstate, config={"recursion_limit": 18})
                gstate = out
            else:
                out = cc_run_turn(session_dir=session_dir, player_input=action, mode="play")
            dt = round(time.time() - t0, 1)
            res["turn_latencies"].append(dt)
            res["completed_turns"] += 1
            narrative = (out or {}).get("narrative", "") or ""
            res["narratives"].append({"turn": i + 1, "action": action, "narrative": narrative[:1200]})
            if len(narrative.strip()) < 20:
                res["empty_narratives"] += 1
            if (out or {}).get("game_over"):
                res["game_over"] = True
        except Exception as e:  # noqa: BLE001
            dt = round(time.time() - t0, 1)
            res["turn_latencies"].append(dt)
            res["errors"].append({"turn": i + 1, "error": f"{type(e).__name__}: {e}"[:200]})
            hard_errors += 1
            if hard_errors >= 2:
                break
            continue

        # Read state after the turn for progress signals.
        st = initial_state(session_dir)
        traces = st.get("traces", {}) or {}
        disc = traces.get("discovered", []) if isinstance(traces, dict) else []
        kn = st.get("knowledge", {}) or {}
        kn_count = sum(len(v) for v in kn.values() if isinstance(v, (list, dict)))
        res["knowledge_trajectory"].append(kn_count)
        tr_count = len(disc) if isinstance(disc, list) else 0
        res["traces_final"] = tr_count
        res["knowledge_final"] = kn_count
        if tr_count > prev_traces or kn_count > prev_kn:
            res["mutation_turns"] += 1
        prev_traces, prev_kn = tr_count, kn_count
        try:
            res["layer_final"] = extract_deepest_layer(traces)
        except Exception:
            pass
        loc = (st.get("location", {}) or {}).get("area", "?")
        if loc != init_loc:
            res["location_changed"] = True
        player = st.get("player", {}) or {}
        integ = player.get("integrity", {})
        res["integrity_final"] = integ.get("current") if isinstance(integ, dict) else integ
        if (out or {}).get("game_over"):
            res["game_over"] = True
            res["ending"] = (out or {}).get("ending")
            break

    res["made_progress"] = bool(
        res["traces_final"] > 0 or res["knowledge_final"] > 0 or res["location_changed"]
    )
    res["mutation_rate"] = (
        round(res["mutation_turns"] / res["completed_turns"], 2)
        if res["completed_turns"] else 0.0
    )
    if res["turn_latencies"]:
        res["avg_latency"] = round(sum(res["turn_latencies"]) / len(res["turn_latencies"]), 1)
    else:
        res["avg_latency"] = None
    return res


def _worker(args):
    model_id, turns, call_timeout, engine = args
    try:
        return eval_model(model_id, turns, call_timeout, engine)
    except Exception as e:  # noqa: BLE001
        return {
            "model": model_id, "fatal": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc()[-800:],
            "completed_turns": 0, "errors": [], "made_progress": False,
        }


# ---------------------------------------------------------------------------
# Ranking / report
# ---------------------------------------------------------------------------

def _fetch_pricing() -> dict:
    """{model_id: cost_per_turn_cents} via the OpenRouter catalog. ~5k in / 1.2k out
    tokens approximates one Signal Lost turn (huge system prompt, modest output)."""
    import urllib.request
    try:
        with urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=30) as r:
            data = json.loads(r.read().decode())
    except Exception:
        return {}
    out = {}
    for m in data.get("data", []):
        p = m.get("pricing", {}) or {}
        try:
            cpt = (float(p.get("prompt") or 0) * 5000 + float(p.get("completion") or 0) * 1200) * 100
            out[m["id"]] = round(cpt, 4)
        except Exception:
            pass
    return out


def _tier(r: dict) -> str:
    if r.get("fatal"):
        return "FATAL"
    if r.get("completed_turns", 0) == 0:
        e = (r.get("errors") or [{}])[0].get("error", "")
        return "UNAVAILABLE" if ("No endpoints" in e or "404" in e) else "ERROR"
    t, L = r.get("traces_final", 0), r.get("layer_final", 0)
    if L >= 4 and t >= 10:
        return "EXCELLENT"
    if L >= 3 and t >= 6:
        return "STRONG"
    if L >= 2 and t >= 3:
        return "OK"
    return "WEAK"


_TIER_ORDER = {"EXCELLENT": 0, "STRONG": 1, "OK": 2, "WEAK": 3, "UNAVAILABLE": 4, "ERROR": 5, "FATAL": 6}


def _score(r: dict) -> float:
    return r.get("traces_final", 0) * 2 + r.get("layer_final", 0) * 5 + r.get("knowledge_final", 0) * 0.5


def write_report(results: list, turns: int, elapsed: float, out_dir: str, ts: str) -> str:
    """Print a ranked table and write a markdown report. Returns the .md path."""
    price = _fetch_pricing()
    rows = []
    for r in results:
        cpt = price.get(r["model"])
        rows.append({
            "model": r["model"], "tier": _tier(r), "turns": r.get("completed_turns", 0),
            "traces": r.get("traces_final", 0), "kn": r.get("knowledge_final", 0),
            "layer": r.get("layer_final", 0), "lat": r.get("avg_latency"),
            "mut": r.get("mutation_rate", 0.0), "ending": r.get("ending"),
            "cpt": cpt, "score": _score(r),
        })
    rows.sort(key=lambda x: (_TIER_ORDER[x["tier"]], -x["score"]))

    print(f"\n{'tier':11} {'model':42} {'T':>2} {'trc':>3} {'kn':>3} {'L':>2} "
          f"{'mut':>4} {'lat':>5} {'c/turn':>7}")
    print("-" * 96)
    for x in rows:
        print(f"{x['tier']:11} {x['model']:42} {x['turns']:>2} {x['traces']:>3} "
              f"{x['kn']:>3} {x['layer']:>2} {str(x['mut']):>4} {str(x['lat']):>5} "
              f"{str(x['cpt']):>7}", flush=True)

    md = [
        f"# Model Sweep Report — {time.strftime('%Y-%m-%d %H:%M')}",
        "",
        f"- Models: {len(results)} | Turns/model: {turns} | Wall time: {elapsed}s",
        "- Path exercised: openrouter single-call bypass (`engine.claude_code_engine.run_turn`)",
        "- Score signals: **deepest layer (L0–L5)** and **traces discovered** over a fixed action script.",
        "- Tiers: EXCELLENT (L4+, 10+ traces), STRONG (L3+, 6+), OK (L2+, 3+), WEAK (shallow),",
        "  UNAVAILABLE (404 — OpenRouter account data-policy, not a capability result).",
        "- `c/turn` = est. cents/turn at ~5k input + 1.2k output tokens.",
        "",
        "| Tier | Model | Turns | Traces | Knowledge | Layer | MutRate | Ending | Latency(s) | c/turn |",
        "|------|-------|------:|------:|----------:|------:|--------:|--------|-----------:|-------:|",
    ]
    for x in rows:
        md.append(f"| {x['tier']} | `{x['model']}` | {x['turns']} | {x['traces']} | "
                  f"{x['kn']} | {x['layer']} | {x['mut']} | {x['ending'] or '—'} | "
                  f"{x['lat']} | {x['cpt']} |")
    md += ["", "## Cheap-yet-powerful (STRONG/EXCELLENT, cheapest first)", "",
           "| # | Model | c/turn | Tier | Layer | Traces | Latency(s) |",
           "|--:|-------|-------:|------|------:|------:|-----------:|"]
    good = [x for x in rows if x["tier"] in ("EXCELLENT", "STRONG") and x["cpt"] is not None]
    good.sort(key=lambda x: x["cpt"])
    for i, x in enumerate(good, 1):
        md.append(f"| {i} | `{x['model']}` | {x['cpt']} | {x['tier']} | {x['layer']} | "
                  f"{x['traces']} | {x['lat']} |")
    md.append("")

    md_path = os.path.join(out_dir, f"sweep_{ts}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    return md_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True, help="JSON file: list of model ids")
    ap.add_argument("--turns", type=int, default=8)
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--call-timeout", type=int, default=100)
    ap.add_argument("--engine", choices=["bypass", "graph"], default="bypass",
                    help="bypass = single-call; graph = full LangGraph + tools")
    args = ap.parse_args()

    with open(args.models) as f:
        models = json.load(f)

    # The graph path (and full_playthrough) read display language / difficulty from
    # settings/custom.json. Pin it to en/standard for the run, then restore.
    custom_path = os.path.join(_GAME_ROOT, "settings", "custom.json")
    saved_custom = None
    if args.engine == "graph" and os.path.exists(custom_path):
        with open(custom_path, encoding="utf-8") as f:
            saved_custom = f.read()
        with open(custom_path, "w", encoding="utf-8") as f:
            json.dump({"language": {"display": "en", "tui": "en"},
                       "difficulty": {"mode": "standard"}}, f, ensure_ascii=False, indent=2)

    print("=" * 64)
    print(f"Signal Lost — Model Sweep ({len(models)} models, {args.turns} turns, "
          f"{args.workers} workers, engine={args.engine})")
    print("=" * 64, flush=True)

    results = []
    t_start = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_worker, (m, args.turns, args.call_timeout, args.engine)): m
                for m in models}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            tag = "FATAL" if r.get("fatal") else (
                "OK" if (not r.get("errors") and r.get("made_progress")) else "WEAK")
            print(f"  [{tag:5}] {r['model']:44} "
                  f"turns={r.get('completed_turns',0)} "
                  f"traces={r.get('traces_final',0)} "
                  f"kn={r.get('knowledge_final',0)} "
                  f"L{r.get('layer_final',1)} "
                  f"mut={r.get('mutation_rate',0)} "
                  f"err={len(r.get('errors',[]))} "
                  f"end={r.get('ending')} "
                  f"lat={r.get('avg_latency')}s", flush=True)

    elapsed = round(time.time() - t_start, 1)
    if saved_custom is not None:
        with open(custom_path, "w", encoding="utf-8") as f:
            f.write(saved_custom)

    out_dir = os.path.join(_GAME_ROOT, "tests", "reviews", "sweep")
    os.makedirs(out_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    raw_path = os.path.join(out_dir, f"sweep_{ts}.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump({"elapsed_s": elapsed, "turns": args.turns, "engine": args.engine,
                   "results": results}, f, ensure_ascii=False, indent=2)

    md_path = write_report(results, args.turns, elapsed, out_dir, ts)
    print(f"\nAll models done in {elapsed}s.\n  Raw:    {raw_path}\n  Report: {md_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
