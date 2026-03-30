#!/usr/bin/env python3
"""
Signal Lost — Claude-Code Bypass Engine Test (8 parallel agents, 10 turns each)

Tests the claude_code_engine.py bypass path that makes a single `claude -p`
call per turn instead of multiple LangGraph node calls.

Each agent plays a different character with a different background and
difficulty. Logs timing, tool calls, errors, and narrative quality.
"""

import json
import os
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed

# Ensure game root on path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_GAME_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _GAME_ROOT not in sys.path:
    sys.path.insert(0, _GAME_ROOT)

from engine.state import create_new_session
from engine.llm_factory import create_llm, load_env
from engine.graph import set_llm

LOG_DIR = os.path.join(_GAME_ROOT, "logs", "cc_bypass_test")
SESSION_BASE = os.path.join(_GAME_ROOT, "session")

# 8 agents with different configs
AGENTS = [
    {"name": "Vex",     "alias": "Spark",   "background": "street_runner",   "difficulty": "standard",  "language": "en"},
    {"name": "Kira",    "alias": "Cipher",  "background": "corporate_exile",   "difficulty": "standard",  "language": "en"},
    {"name": "Zero",    "alias": "Ghost",   "background": "street_runner",   "difficulty": "cautious",  "language": "en"},
    {"name": "Juno",    "alias": "Drift",   "background": "street_runner",   "difficulty": "reckless",  "language": "en"},
    {"name": "幽灵",    "alias": "Shade",   "background": "street_runner",   "difficulty": "standard",  "language": "zh"},
    {"name": "Rex",     "alias": "Fuse",    "background": "corporate_exile",   "difficulty": "cautious",  "language": "en"},
    {"name": "Luna",    "alias": "Mirror",  "background": "street_runner",   "difficulty": "standard",  "language": "en"},
    {"name": "达达",    "alias": "Wraith",  "background": "corporate_exile",   "difficulty": "standard",  "language": "zh"},
]

# 10 actions per agent (varied to test different mechanics)
ACTIONS = [
    "Look around. Take in the scene.",
    "Talk to anyone nearby. Ask what's going on in the district.",
    "Search the area for anything interesting or useful.",
    "Ask about the Signal — what is it, what do people say about it?",
    "Try to find information about NEXUS and their operations here.",
    "Head to a market or vendor. See what's available.",
    "Look for someone who might know about neural implants.",
    "Explore a back alley or less-traveled path.",
    "Try to learn about the history of this place, before the Severance.",
    "Find a quiet spot and try to listen to the Signal.",
]


def run_single_agent(agent_idx: int) -> dict:
    """Run a single agent for 10 turns. Called in subprocess."""
    load_env()
    agent = AGENTS[agent_idx]
    session_name = f"cc_bypass_{agent['alias'].lower()}"
    session_dir = os.path.join(SESSION_BASE, session_name)

    # Create fresh session
    create_new_session(
        session_dir=session_dir,
        name=agent["name"],
        alias=agent["alias"],
        background=agent["background"],
        difficulty=agent["difficulty"],
        language=agent["language"],
    )

    # Set up LLM
    llm = create_llm("claude-code", "sonnet")
    set_llm(llm, zero_cost=True)

    # Import the bypass engine
    from engine.claude_code_engine import run_turn

    results = {
        "agent": agent,
        "session_name": session_name,
        "turns": [],
        "errors": [],
        "total_time": 0,
    }

    start_total = time.time()

    # Opening turn (resume mode)
    try:
        t0 = time.time()
        result = run_turn(session_dir, "", mode="resume")
        elapsed = time.time() - t0
        results["turns"].append({
            "turn": 0,
            "action": "(opening)",
            "elapsed": round(elapsed, 1),
            "narrative_len": len(result.get("narrative", "")),
            "tool_calls": 0,
            "knowledge_added": len(result.get("knowledge_notifications", [])),
            "discoveries": len(result.get("discovery_notifications", [])),
            "game_over": result.get("game_over", False),
            "parse_ok": not result.get("narrative", "").startswith("{"),
        })
        print(f"  Agent {agent_idx} ({agent['alias']}): opening in {elapsed:.1f}s", flush=True)
    except Exception as e:
        results["errors"].append({"turn": 0, "error": str(e)})
        print(f"  Agent {agent_idx} ({agent['alias']}): opening FAILED: {e}", flush=True)

    # 10 gameplay turns
    for turn_num in range(1, 11):
        action = ACTIONS[turn_num - 1]
        try:
            t0 = time.time()
            result = run_turn(session_dir, action, mode="play")
            elapsed = time.time() - t0

            narrative = result.get("narrative", "")
            parse_ok = not narrative.startswith("{") and len(narrative) > 10

            results["turns"].append({
                "turn": turn_num,
                "action": action[:50],
                "elapsed": round(elapsed, 1),
                "narrative_len": len(narrative),
                "knowledge_added": len(result.get("knowledge_notifications", [])),
                "discoveries": len(result.get("discovery_notifications", [])),
                "game_over": result.get("game_over", False),
                "parse_ok": parse_ok,
                "narrative_preview": narrative[:100],
            })

            status = "OK" if parse_ok else "PARSE_FAIL"
            print(f"  Agent {agent_idx} ({agent['alias']}): turn {turn_num} in {elapsed:.1f}s [{status}]", flush=True)

            if result.get("game_over"):
                print(f"  Agent {agent_idx} ({agent['alias']}): GAME OVER at turn {turn_num}", flush=True)
                break

        except Exception as e:
            traceback.print_exc()
            results["errors"].append({"turn": turn_num, "error": str(e)})
            print(f"  Agent {agent_idx} ({agent['alias']}): turn {turn_num} FAILED: {e}", flush=True)

    results["total_time"] = round(time.time() - start_total, 1)
    return results


def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    print("=" * 60)
    print("Signal Lost — Claude-Code Bypass Engine Test")
    print("8 agents × 10 turns, parallel execution")
    print("=" * 60)
    print()

    all_results = [None] * 8

    # Run all 8 agents in parallel processes
    with ProcessPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(run_single_agent, i): i for i in range(8)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                all_results[idx] = future.result()
            except Exception as e:
                all_results[idx] = {"agent": AGENTS[idx], "errors": [{"turn": -1, "error": str(e)}], "turns": [], "total_time": 0}
                print(f"  Agent {idx} CRASHED: {e}")

    # Save raw results
    with open(os.path.join(LOG_DIR, "raw_results.json"), "w") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # Generate summary
    print()
    print("=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    total_turns = 0
    total_time = 0
    total_errors = 0
    total_parse_fails = 0
    total_knowledge = 0
    total_discoveries = 0
    turn_times = []

    for r in all_results:
        if not r:
            continue
        agent = r["agent"]
        turns = r["turns"]
        errors = r["errors"]

        avg_time = sum(t["elapsed"] for t in turns) / len(turns) if turns else 0
        parse_fails = sum(1 for t in turns if not t.get("parse_ok", True))
        knowledge = sum(t.get("knowledge_added", 0) for t in turns)
        discoveries = sum(t.get("discoveries", 0) for t in turns)

        total_turns += len(turns)
        total_time += r["total_time"]
        total_errors += len(errors)
        total_parse_fails += parse_fails
        total_knowledge += knowledge
        total_discoveries += discoveries
        turn_times.extend(t["elapsed"] for t in turns)

        print(f"\n  {agent['alias']:>8} ({agent['background'][:12]}, {agent['difficulty'][:8]}, {agent['language']})")
        print(f"    Turns: {len(turns)}/11 | Avg: {avg_time:.1f}s | Total: {r['total_time']:.0f}s")
        print(f"    Parse OK: {len(turns) - parse_fails}/{len(turns)} | Errors: {len(errors)}")
        print(f"    Knowledge: +{knowledge} | Discoveries: {discoveries}")

    print(f"\n{'─' * 60}")
    avg_all = sum(turn_times) / len(turn_times) if turn_times else 0
    print(f"  TOTAL: {total_turns} turns in {total_time:.0f}s")
    print(f"  AVG TURN TIME: {avg_all:.1f}s")
    print(f"  PARSE FAILURES: {total_parse_fails}/{total_turns}")
    print(f"  ERRORS: {total_errors}")
    print(f"  KNOWLEDGE ADDED: {total_knowledge}")
    print(f"  TRACE DISCOVERIES: {total_discoveries}")

    # Save summary
    summary = {
        "total_turns": total_turns,
        "total_time": total_time,
        "avg_turn_time": round(avg_all, 1),
        "parse_failures": total_parse_fails,
        "errors": total_errors,
        "knowledge_added": total_knowledge,
        "discoveries": total_discoveries,
    }
    with open(os.path.join(LOG_DIR, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n  Results saved to: {LOG_DIR}/")


if __name__ == "__main__":
    main()
