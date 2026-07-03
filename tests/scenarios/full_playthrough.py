#!/usr/bin/env python3
"""
Signal Lost — Full Playthrough Test

Automated multi-turn playthrough using a configured LLM.
Generates a structured review with metrics.

Usage:
    python tests/scenarios/full_playthrough.py [--turns N] [--actions-file FILE]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_GAME_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _GAME_ROOT not in sys.path:
    sys.path.insert(0, _GAME_ROOT)

from langchain_core.messages import HumanMessage

from engine.graph import compile_graph, set_llm
from engine.state import create_new_session, initial_state
from engine.llm_factory import create_llm, default_model_for, load_env, load_provider_config, SETTINGS_DIR

# Default action sequence for reproducible testing.
#
# Wave-12 friction #1: the back-half beats (restricted areas → source → confront)
# provoked the model into stacking NEXUS alert past 100 before deep-layer content
# unlocked, so both languages hit the designed alert-100 capture death (EN@T19)
# at L3. Note the engine does NOT apply alert amounts deterministically —
# game_data.ALERT_INCREASES is reference-only (see the NOTE above it); alert
# moves only when the model volunteers a `nexus_alert_delta`. The saturation
# was model-emergent, but consistent enough on provocative beats to kill runs.
# Two lay-low beats bleed off heat at the two spike points — one right after
# the restricted-area attempt, one right before the endgame run — replacing the
# two lowest-value beats (a duplicate "talk to the knowledgeable one" and a pure
# "plan my next move" reflection). A 20-turn run should now stay under the
# 90+ full-manhunt band (game_data.ALERT_THRESHOLDS) and reach L4 content,
# while alert still climbs visibly through the 25/50/75 thresholds. The list
# stays at exactly 20 entries so `--turns 20` still reaches the final choice.
# Beat 16 is a deep act (decrypt) rather than a social beat: with two rest
# turns in T14/T17, the back half needs enough act-driven discovery beats to
# exercise deep-layer content (wave-14 validation: survival and back-half
# depth are otherwise in tension).
DEFAULT_ACTIONS = [
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
    "Present what I've learned and ask for their theory",
    "Search for evidence of the conspiracy",
    "Try to access restricted areas",
    "Lay low at a quiet food stall until the patrols thin — rest and recover",
    "Analyze any signal artifacts I've found",
    "Decrypt any encrypted data I'm carrying — dig for what's underneath",
    "Find somewhere safe to sleep and let the heat die down before the final push",
    "Head toward the source of the Signal",
    "Confront what I find",
    "Make my final choice",
]


# Substrings marking a transient CLI/network stream drop worth retrying.
# Connection-phase errors only — no bare "timeout"/"timed out": those match a
# CLI turn that already burned its full multi-minute budget, and re-running it
# stacks tens of minutes of retries on a merely slow model (wave 4 review).
# Keep in sync with gui/server.py _TRANSIENT_CLI_MARKERS.
_TRANSIENT_MARKERS = (
    "tls handshake eof", "handshake eof", "connection reset", "connection refused",
    "connection aborted", "connection closed", "broken pipe", "reconnecting",
    "temporarily unavailable", "eof occurred",
    "stream closed", "network is unreachable", "read timed out", "remote end closed",
)


def _is_transient_error(err: BaseException) -> bool:
    """True if *err* looks like a transient network/CLI stream drop (safe to retry)."""
    msg = str(err).lower()
    return any(marker in msg for marker in _TRANSIENT_MARKERS)


def run_playthrough(max_turns: int, actions: list[str]) -> dict:
    """Run a full playthrough and return metrics."""
    load_env()
    provider_cfg = load_provider_config()
    provider = provider_cfg.get("provider", "openai")
    model = provider_cfg.get("model", default_model_for(provider))
    temperature = provider_cfg.get("temperature", 0.7)

    llm = create_llm(provider, model, temperature=temperature)
    set_llm(llm)

    session_dir = os.path.join(_GAME_ROOT, "session", "playthrough_test")
    create_new_session(
        session_dir=session_dir,
        name="TestKael",
        alias="Ghost",
        background="netrunner",
        difficulty="standard",
        language="en",
    )

    custom_path = os.path.join(SETTINGS_DIR, "custom.json")
    with open(custom_path, "w", encoding="utf-8") as f:
        json.dump({
            "language": {"display": "en", "tui": "en"},
            "difficulty": {"mode": "standard"},
        }, f, ensure_ascii=False, indent=2)

    graph = compile_graph()
    state = initial_state(session_dir)

    # Metrics
    metrics = {
        "turns_played": 0,
        "area_populated": 0,
        "area_missing": 0,
        "knowledge_count": 0,
        "traces_discovered": 0,
        "integrity_divergences": 0,
        "errors": [],
        "narratives": [],
        "game_over": False,
        "ending": None,
    }

    for turn_idx in range(min(max_turns, len(actions))):
        action = actions[turn_idx]
        state["messages"].append(HumanMessage(content=action))

        try:
            # A single transient stream drop (tls handshake eof, connection reset,
            # timeout) used to break the whole run on turn 1. Retry the invoke up to
            # 2 extra attempts with a short backoff on connection-ish errors before
            # giving up. Re-invoking the same `state` is safe — the HumanMessage was
            # already appended above and `state` is only reassigned on success.
            _last_err = None
            for _attempt in range(3):
                try:
                    result = graph.invoke(state)
                    break
                except Exception as _err:
                    _last_err = _err
                    if _attempt < 2 and _is_transient_error(_err):
                        time.sleep(2 * (_attempt + 1))
                        continue
                    raise
            state = result
            metrics["turns_played"] += 1

            narrative = result.get("narrative", "")
            metrics["narratives"].append({"turn": turn_idx + 1, "action": action, "narrative": narrative[:500]})

            # Check area field
            location = state.get("location", {})
            area = location.get("area", "?")
            if area and area != "?":
                metrics["area_populated"] += 1
            else:
                metrics["area_missing"] += 1

            # Check knowledge accumulation
            knowledge = state.get("knowledge", {})
            total_knowledge = sum(
                len(v) for v in knowledge.values() if isinstance(v, (list, dict))
            )
            metrics["knowledge_count"] = total_knowledge

            # Check traces
            traces = state.get("traces", {})
            discovered = sum(
                1 for t in traces.values()
                if isinstance(t, dict) and t.get("discovered")
            )
            metrics["traces_discovered"] = discovered

            if result.get("game_over"):
                metrics["game_over"] = True
                metrics["ending"] = result.get("ending")
                break

        except Exception as e:
            metrics["errors"].append({"turn": turn_idx + 1, "error": str(e)})
            break

    return metrics


def write_review(metrics: dict, output_dir: str):
    """Write a structured review to the reviews directory."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"playthrough_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    # Also write a human-readable summary
    summary_path = os.path.join(output_dir, f"playthrough_{timestamp}.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"# Playthrough Review — {time.strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**Turns played**: {metrics['turns_played']}\n")
        f.write(f"**Area tracking**: {metrics['area_populated']} populated, {metrics['area_missing']} missing\n")
        f.write(f"**Knowledge items**: {metrics['knowledge_count']}\n")
        f.write(f"**Traces discovered**: {metrics['traces_discovered']}\n")
        f.write(f"**Errors**: {len(metrics['errors'])}\n")
        f.write(f"**Game over**: {metrics['game_over']}\n")
        if metrics["ending"]:
            f.write(f"**Ending**: {metrics['ending']}\n")
        f.write("\n---\n\n")

        area_rate = metrics["area_populated"] / max(metrics["turns_played"], 1) * 100
        f.write(f"### Scoring\n")
        f.write(f"- Area tracking rate: {area_rate:.0f}%\n")
        f.write(f"- Knowledge per turn: {metrics['knowledge_count'] / max(metrics['turns_played'], 1):.1f}\n")
        f.write(f"- Error rate: {len(metrics['errors']) / max(metrics['turns_played'], 1) * 100:.0f}%\n")

    print(f"\nReview saved to: {filepath}")
    print(f"Summary saved to: {summary_path}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Signal Lost — Full Playthrough Test")
    parser.add_argument("--turns", type=int, default=20, help="Maximum turns (default: 20)")
    parser.add_argument("--actions-file", help="JSON file with action list (one string per turn)")
    args = parser.parse_args()

    actions = DEFAULT_ACTIONS
    if args.actions_file:
        with open(args.actions_file, "r") as f:
            actions = json.load(f)

    print("=" * 60)
    print("Signal Lost — Full Playthrough Test")
    print(f"Max turns: {args.turns}")
    print("=" * 60)
    print()

    metrics = run_playthrough(args.turns, actions)

    reviews_dir = os.path.join(_GAME_ROOT, "tests", "reviews")
    write_review(metrics, reviews_dir)

    # Summary
    print(f"\nTurns: {metrics['turns_played']}")
    print(f"Area tracking: {metrics['area_populated']}/{metrics['turns_played']} populated")
    print(f"Knowledge: {metrics['knowledge_count']} items")
    print(f"Traces: {metrics['traces_discovered']} discovered")
    print(f"Errors: {len(metrics['errors'])}")

    return 0 if len(metrics["errors"]) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
