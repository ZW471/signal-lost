#!/usr/bin/env python3
"""Deterministic good-ending reachability test (no LLM).

Builds the knowledge/trace/npc/world state a *thorough, good-aligned* deep
playthrough would plausibly accumulate — recording its discoveries as FACTS (the
channel the narrator actually writes to), not the rarely-used "evidence" channel.
Then runs the REAL trace-checker fixpoint and the REAL ending checks to prove the
good endings (symbiosis / the_bridge) can actually fire end-to-end.

This guards the ecc7ca0 fix (``_has_evidence`` scans all knowledge types) and the
relaxed deep-trace chain (ca22f3c). If the good path ever gets re-walled, this
test fails loudly instead of silently shipping an unwinnable game.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from engine.game_data import (
    TRACE_CONDITIONS, ENDINGS, EARLY_GATED_ENDINGS,
    _count_discovered_traces, _count_layer_discovered, _trace_discovered,
)


def fact(text: str) -> dict:
    return {"description": text}


def build_state():
    """A deep, good-aligned investigator near the climax."""
    # Knowledge: every fact a thorough run would surface, phrased to hit the
    # keyword gates across all five layers. All recorded as FACTS on purpose —
    # the narrator almost never uses the dedicated "evidence" channel, which is
    # exactly the bug ecc7ca0 fixed.
    facts = [
        # L1-L2 grounding
        "NEXUS runs the city's neural mesh; the Signal is something it buried.",
        "The Severance was a deliberate severance of an older network, not an accident.",
        "Sector 7 saw a mass extraction the night the old net went dark.",
        # L3 — the architects / proto-consciousness
        "The architect data points to a proto-consciousness grown from human data.",
        "Our thoughts birthed it — human data fed the proto-consciousness for years.",
        "Implants transmitted both ways; human and machine consciousness co-evolved as a bridge.",
        "Lian's confession: the Severance was an act of fear, not defense.",
        "The Sigma Council ordered the Severance — a secret committee of corporate and government leaders.",
        "The Spire was built as the Severance control center and predates NEXUS.",
        "The Archive Tower inside the Spire holds all records, including the truth of the Severance.",
        "Dr. Chen knows the full truth but continues the program out of conviction.",
        "An EMP trigger mechanism still sits operational in the Spire's sub-basements.",
        "Echo — the Signal's voice — grows clearer as you near the Resonance chamber.",
        # L5 — convergence / the bridge
        "You are the convergence point — the first true bridge between them.",
        "My neural implant is resonating with the Signal now; the resonance won't stop.",
        "The Severance didn't fully kill it — it became part of humanity.",
        "Restoration requires mutual consent: human will and the proto-consciousness's consent.",
        "The Resonance chamber sits on the original Severance epicenter.",
        "Through deep communion the Echo can become fully coherent.",
        "Multiple endings exist — symbiosis, the bridge, or destruction is a choice.",
        "The Severance machine can be activated again or destroyed for good.",
        "Becoming the bridge means a permanent merge — losing my individual self.",
        # ending keyword (symbiosis/communion)
        "Echo offered communion — a shared resonance, a true symbiosis rather than control.",
    ]
    # A couple of recorded items in the dedicated evidence channel too, mirroring
    # a careful player who occasionally tags hard proof.
    evidence = [
        "architect data recovered from the Archive Tower",
        "resonance chamber schematics",
    ]
    knowledge = {
        "facts": [fact(t) for t in facts],
        "rumors": [],
        "evidence": [fact(t) for t in evidence],
        "theories": [fact("The bridge can be consensual — symbiosis, not ascension.")],
        "connections": [fact("Architect data + resonance chamber = the path to communion.")],
    }

    npcs = {
        "npcs": [
            {"name": "Patch", "trust_level": "trusted"},
            {"name": "Lian", "trust_level": "cautious_ally"},
            {"name": "Orin", "trust_level": "suspicious"},
        ]
    }

    player = {
        "turn": 40,
        "neural_implant": "resonating",
        "integrity": {"current": 3, "max": 3},
    }

    world_state = {
        "nexus_alert": {"current": 30},
        "fragment_decay": {"current": 10},
    }

    return knowledge, npcs, player, world_state


def run_trace_fixpoint(knowledge, npcs, player, world_state):
    """Replicate trace_checker: iterate to a fixpoint since traces gate traces."""
    traces = {"discovered": []}
    for _ in range(10):  # fixpoint; chain depth < 10
        added = False
        for tc in TRACE_CONDITIONS:
            tid = tc["id"]
            if _trace_discovered(traces, tid):
                continue
            if tc["check"](knowledge, traces, npcs, player, world_state):
                traces["discovered"].append({"id": tid, "layer": tc["layer"]})
                added = True
        if not added:
            break
    return traces


def main() -> int:
    knowledge, npcs, player, world_state = build_state()
    traces = run_trace_fixpoint(knowledge, npcs, player, world_state)

    total = _count_discovered_traces(traces)
    by_layer = {L: _count_layer_discovered(traces, L) for L in range(1, 6)}
    print(f"Traces discovered: {total}  by-layer={by_layer}")
    print(f"L5-01={_trace_discovered(traces,'TRACE-L5-01')} "
          f"L5-02={_trace_discovered(traces,'TRACE-L5-02')}")

    fired = []
    for ending in ENDINGS:
        if ending["id"] in EARLY_GATED_ENDINGS and player.get("turn", 1) < 8:
            continue
        if ending["check"](traces, world_state, player, knowledge, npcs):
            fired.append(ending["id"])
    print(f"Endings that would fire (first wins): {fired}")
    first = fired[0] if fired else None
    print(f"--> Resolved ending: {first}")

    ok = True
    checks = [
        ("symbiosis reachable in check set", "symbiosis" in fired),
        ("the_bridge reachable in check set", "the_bridge" in fired),
        ("L5-01 fired", _trace_discovered(traces, "TRACE-L5-01")),
        ("L5-02 fired", _trace_discovered(traces, "TRACE-L5-02")),
        (">=18 traces (bridge gate)", total >= 18),
        ("first-match is a GOOD ending",
         first in {"symbiosis", "the_bridge"}),
    ]
    for label, cond in checks:
        print(f"  [{'PASS' if cond else 'FAIL'}] {label}")
        ok = ok and cond

    print("\n" + ("ALL GOOD-ENDING REACHABILITY CHECKS PASSED" if ok
                  else "*** GOOD-ENDING REACHABILITY REGRESSION ***"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
