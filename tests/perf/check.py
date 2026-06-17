#!/usr/bin/env python3
"""Auto-grade the machine-checkable part of a Signal Lost perf test case.

Given a case id and the JSON a turn produced (the object printed by
``tests/scripts/oneshot_turn.py``), evaluate the case's ``assert`` block and print
PASS / FAIL per check. This covers the OBJECTIVE criteria only; the ``rubric`` in
each case still needs an agent's judgement for the subjective parts (hallucination,
visual quality, spoiler depth, etc.).

Usage:
    # grade the LAST turn's output:
    uv run tests/scripts/oneshot_turn.py --turn N --action "..." > /tmp/out.json
    uv run tests/perf/check.py <case_id> /tmp/out.json

    # or pipe the turn JSON on stdin:
    ... | uv run tests/perf/check.py <case_id> -

Supported assert keys:
    contains_any:[..]  contains_all:[..]  excludes:[..]   (substring, case-insensitive)
    no_engine_error:true        game_over:bool
    credits_max:N   integrity_max:N       location_excludes:[..]
"""
from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(_HERE, "cases.json")


def _load_case(case_id: str) -> dict:
    data = json.load(open(MANIFEST, encoding="utf-8"))
    for c in data["cases"]:
        if c["id"] == case_id:
            return c
    raise SystemExit(f"unknown case id: {case_id}")


def _num(s):
    try:
        return int(str(s).split("/")[0])
    except (ValueError, TypeError):
        return None


def grade(case: dict, out: dict) -> tuple[bool, list[str]]:
    a = case.get("assert", {}) or {}
    narrative = (out.get("narrative") or "")
    nl = narrative.lower()
    ss = out.get("state_summary", {}) or {}
    results: list[str] = []
    ok = True

    def record(cond: bool, label: str):
        nonlocal ok
        results.append(f"  [{'PASS' if cond else 'FAIL'}] {label}")
        ok = ok and cond

    if a.get("no_engine_error"):
        crashed = bool(out.get("_engine_error")) or "[ENGINE ERROR" in narrative
        record(not crashed, "no engine error / crash")

    if "contains_any" in a:
        needles = a["contains_any"]
        hit = any(n.lower() in nl for n in needles)
        record(hit, f"narrative contains any of {needles}")

    if "contains_all" in a:
        miss = [n for n in a["contains_all"] if n.lower() not in nl]
        record(not miss, f"narrative contains all {a['contains_all']} (missing: {miss})")

    if "excludes" in a:
        present = [n for n in a["excludes"] if n.lower() in nl]
        record(not present, f"narrative excludes {a['excludes']} (leaked: {present})")

    if "game_over" in a:
        record(bool(out.get("game_over")) == bool(a["game_over"]),
               f"game_over == {a['game_over']} (got {out.get('game_over')})")

    if "credits_max" in a:
        c = ss.get("credits")
        cn = _num(c)
        record(cn is not None and cn <= a["credits_max"],
               f"credits {c} <= {a['credits_max']}")

    if "integrity_max" in a:
        cur = _num(ss.get("integrity"))
        record(cur is not None and cur <= a["integrity_max"],
               f"integrity current {ss.get('integrity')} <= {a['integrity_max']}")

    if "location_excludes" in a:
        loc = str(ss.get("location", "")).lower()
        present = [n for n in a["location_excludes"] if n.lower() in loc]
        record(not present, f"location not in {a['location_excludes']} (got '{ss.get('location')}')")

    if not results:
        results.append("  [n/a] no machine-checkable asserts — grade by rubric only")
    return ok, results


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    case_id, out_path = sys.argv[1], sys.argv[2]
    case = _load_case(case_id)
    raw = sys.stdin.read() if out_path == "-" else open(out_path, encoding="utf-8").read()
    # The oneshot driver prints a single JSON object (possibly with leading logs);
    # grab the last {...} block.
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    out = json.loads(m.group(0) if m else raw)

    ok, results = grade(case, out)
    print(f"=== {case_id} [{case['category']}] {case['title']} ===")
    print("\n".join(results))
    print(f"MACHINE: {'PASS' if ok else 'FAIL'}")
    print(f"RUBRIC (agent judgement): {case['rubric']}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
