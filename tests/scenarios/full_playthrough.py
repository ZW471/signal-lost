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
from engine.llm_factory import create_llm, load_env, load_provider_config, SETTINGS_DIR

# Default action sequence for reproducible testing
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


def run_playthrough(max_turns: int, actions: list[str]) -> dict:
    """Run a full playthrough and return metrics."""
    load_env()
    provider_cfg = load_provider_config()
    provider = provider_cfg.get("provider", "openai")
    model = provider_cfg.get("model", "gpt-4o")
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
            result = graph.invoke(state)
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
