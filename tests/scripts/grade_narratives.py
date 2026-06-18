#!/usr/bin/env python3
"""Signal Lost — narrative-quality grader.

Reads a model-sweep raw JSON (which stores each model's per-turn narratives) and
has an LLM judge score every model's transcript on a fixed rubric. The judge is a
CLI-OAuth backend (codex by default, claude-code fallback) so grading costs no API
spend and is independent of the models being graded.

Transcripts are presented ANONYMOUSLY (no model id) so the judge can't be biased
by reputation. Scores are 1-10 per dimension; output is a per-model ranking.

Usage:
    uv run tests/scripts/grade_narratives.py --sweep tests/reviews/sweep/sweep_<ts>.json
    uv run tests/scripts/grade_narratives.py            # uses the newest sweep_*.json
    uv run tests/scripts/grade_narratives.py --min-turns 4 --limit 40 --judge codex
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time

_THIS = os.path.dirname(os.path.abspath(__file__))
_GAME_ROOT = os.path.abspath(os.path.join(_THIS, "..", ".."))
if _GAME_ROOT not in sys.path:
    sys.path.insert(0, _GAME_ROOT)

from engine.llm_factory import create_llm, load_env

DIMENSIONS = ["atmosphere", "prose", "coherence", "responsiveness", "show_dont_tell"]

RUBRIC = """You are grading the NARRATION QUALITY of an AI game master running a turn-based
cyberpunk text RPG ("Signal Lost"). You are shown an anonymous transcript: each turn has
the PLAYER action and the game's NARRATION response. Judge ONLY the narration quality.

Score each dimension from 1 (terrible) to 10 (excellent):
- atmosphere: sensory, immersive cyberpunk mood; concrete world detail, not generic filler.
- prose: varied, controlled sentences; vivid but not purple; free of repetition and slop.
- coherence: internally consistent and continuous across turns; no contradictions, no resets.
- responsiveness: the narration actually engages the player's SPECIFIC action each turn.
- show_dont_tell: dramatizes through scene/action/dialogue rather than flat exposition or
  meta status-dumps.

Also give an "overall" 1-10 holistic score and a one-sentence "comment".
Penalize: empty/refusal/echoed-instruction turns, breaking character, dumping raw JSON or
mechanics into the prose, and obvious incoherence.

Respond with ONLY a JSON object, no prose around it:
{"atmosphere":N,"prose":N,"coherence":N,"responsiveness":N,"show_dont_tell":N,"overall":N,"comment":"..."}"""


def _make_judge(kind: str):
    load_env()
    model = "gpt-5.5" if kind == "codex" else "sonnet"
    llm = create_llm(kind, model)
    if not hasattr(llm, "_call_claude"):
        raise RuntimeError(f"judge backend {kind} has no _call_claude")
    return llm


def _transcript(narratives: list) -> str:
    parts = []
    for n in narratives:
        parts.append(f"--- Turn {n['turn']} ---\nPLAYER: {n['action']}\nNARRATION: {n['narrative']}")
    return "\n\n".join(parts)


def _parse_scores(raw: str) -> dict | None:
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not all(k in d for k in DIMENSIONS + ["overall"]):
        return None
    return d


def grade_one(judge, narratives: list) -> dict:
    user = ("Grade this transcript.\n\n" + _transcript(narratives))[:14000]
    raw = judge._call_claude(RUBRIC, user)
    scores = _parse_scores(raw)
    if scores is None:
        return {"error": "unparseable judge output", "raw": raw[:300]}
    return scores


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default=None, help="sweep raw JSON (default: newest)")
    ap.add_argument("--judge", choices=["codex", "claude-code"], default="codex")
    ap.add_argument("--min-turns", type=int, default=3, help="skip models with fewer narrated turns")
    ap.add_argument("--limit", type=int, default=0, help="cap number of models graded (0 = all)")
    args = ap.parse_args()

    sweep_path = args.sweep
    if not sweep_path:
        cands = sorted(glob.glob(os.path.join(_GAME_ROOT, "tests", "reviews", "sweep", "sweep_*.json")))
        if not cands:
            print("no sweep json found"); return 2
        sweep_path = cands[-1]
    data = json.load(open(sweep_path, encoding="utf-8"))
    results = data["results"]

    gradable = [r for r in results
                if len([n for n in r.get("narratives", []) if len((n.get("narrative") or "").strip()) >= 20]) >= args.min_turns]
    gradable.sort(key=lambda r: r["model"])
    if args.limit:
        gradable = gradable[:args.limit]
    print(f"Sweep: {os.path.basename(sweep_path)}  (engine={data.get('engine')})")
    print(f"Grading {len(gradable)} / {len(results)} models with judge={args.judge} "
          f"(min_turns={args.min_turns})\n", flush=True)

    judge_kind = args.judge
    judge = _make_judge(judge_kind)
    graded = []
    for i, r in enumerate(gradable, 1):
        narr = [n for n in r["narratives"] if len((n.get("narrative") or "").strip()) >= 20]
        t0 = time.time()
        try:
            sc = grade_one(judge, narr)
        except Exception as e:  # noqa: BLE001
            # fall back to claude-code for the rest of the run on judge failure
            if judge_kind == "codex":
                print(f"  judge codex failed ({type(e).__name__}); switching to claude-code", flush=True)
                judge_kind = "claude-code"
                try:
                    judge = _make_judge(judge_kind)
                    sc = grade_one(judge, narr)
                except Exception as e2:  # noqa: BLE001
                    sc = {"error": f"{type(e2).__name__}: {e2}"[:160]}
            else:
                sc = {"error": f"{type(e).__name__}: {e}"[:160]}
        dt = round(time.time() - t0, 1)
        row = {"model": r["model"], "scores": sc, "judge": judge_kind,
               "turns_graded": len(narr)}
        graded.append(row)
        ov = sc.get("overall", "ERR") if isinstance(sc, dict) else "ERR"
        print(f"  [{i:>3}/{len(gradable)}] overall={str(ov):>4}  {r['model']:42} ({dt}s)", flush=True)

    # rank
    def ov(r):
        s = r["scores"]
        return s.get("overall", -1) if isinstance(s, dict) else -1
    graded.sort(key=ov, reverse=True)

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(_GAME_ROOT, "tests", "reviews", "sweep")
    os.makedirs(out_dir, exist_ok=True)
    raw_out = os.path.join(out_dir, f"grades_{ts}.json")
    json.dump({"sweep": os.path.basename(sweep_path), "engine": data.get("engine"),
               "judge": args.judge, "graded": graded}, open(raw_out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # markdown
    md = [f"# Narrative-Quality Grades — {time.strftime('%Y-%m-%d %H:%M')}",
          f"", f"Judge: {args.judge} · Sweep: `{os.path.basename(sweep_path)}` "
          f"(engine={data.get('engine')}) · {len(graded)} models graded.", "",
          "| Overall | Atmos | Prose | Coher | Respon | Show | Model | Comment |",
          "|--------:|------:|------:|------:|-------:|-----:|-------|---------|"]
    for r in graded:
        s = r["scores"]
        if not isinstance(s, dict) or "overall" not in s:
            md.append(f"| ERR | | | | | | `{r['model']}` | {s.get('error','?') if isinstance(s,dict) else s} |")
            continue
        md.append(f"| {s.get('overall')} | {s.get('atmosphere')} | {s.get('prose')} | "
                  f"{s.get('coherence')} | {s.get('responsiveness')} | {s.get('show_dont_tell')} | "
                  f"`{r['model']}` | {str(s.get('comment','')).replace('|','/')[:120]} |")
    md_out = os.path.join(out_dir, f"grades_{ts}.md")
    open(md_out, "w", encoding="utf-8").write("\n".join(md))

    print(f"\nGraded {len(graded)} models.\n  Raw: {raw_out}\n  Report: {md_out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
