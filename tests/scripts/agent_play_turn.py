#!/usr/bin/env python3
"""
Blocking single-turn helper for agent players (headless mode).

Writes one player action, then BLOCKS in the foreground until the engine
finishes that turn, then prints the resulting game_response.json to stdout.
This lets an agent play one turn per Bash call without arming monitors or
"waiting for a notification" (which suspends a subagent).

Usage (action via --action or stdin):
    python3 tests/scripts/agent_play_turn.py --session iter1_h1_zh --turn 6 \
        --action "检查终端"
    echo "examine the terminal" | python3 tests/scripts/agent_play_turn.py \
        --session iter1_h2_en --turn 3

Set the Bash tool timeout high (e.g. 600000 ms) when calling, since a single
codex narration turn can take 30-120s+.

Exit codes:
    0  turn completed (response printed; check "game_over")
    2  timed out waiting for the engine (still printed last status)
    3  engine reported [ENGINE ERROR ...] in the response (printed anyway)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_GAME_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True, help="session subdir under session/")
    ap.add_argument("--turn", required=True, type=int, help="turn number to submit")
    ap.add_argument("--action", default=None, help="action text (else read stdin)")
    ap.add_argument("--timeout", type=float, default=540.0, help="max seconds to wait")
    ap.add_argument("--poll", type=float, default=3.0, help="poll interval seconds")
    args = ap.parse_args()

    session_dir = os.path.join(_GAME_ROOT, "session", args.session)
    action_file = os.path.join(session_dir, "player_action.json")
    status_file = os.path.join(session_dir, "engine_status.json")
    response_file = os.path.join(session_dir, "game_response.json")

    if not os.path.isdir(session_dir):
        print(f"ERROR: session dir not found: {session_dir}", file=sys.stderr)
        return 1

    action = args.action
    if action is None:
        action = sys.stdin.read().strip()
    if not action:
        print("ERROR: empty action", file=sys.stderr)
        return 1

    def turn_done(n: int) -> bool:
        """Race-free completion check.

        The engine sets status "done"/turn N only for a split second before
        flipping to "waiting"/turn N+1, so polling for that flash is unreliable.
        Instead, turn N is complete when its response is written
        (game_response.json turn == N) OR the engine has advanced past N OR we
        catch the brief "done" state.
        """
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                st = json.load(f)
            if st.get("status") == "done" and st.get("turn") == n:
                return True
            if isinstance(st.get("turn"), int) and st.get("turn") > n:
                return True
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        try:
            with open(response_file, "r", encoding="utf-8") as f:
                rp = json.load(f)
            if rp.get("turn") == n:
                return True
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return False

    # If the engine has already produced this turn's response (e.g. a prior
    # call submitted it and timed out), don't resubmit — just return it.
    if turn_done(args.turn):
        with open(response_file, "r", encoding="utf-8") as f:
            print(json.dumps(json.load(f), ensure_ascii=False, indent=2))
        return 0

    # Submit the action.
    with open(action_file, "w", encoding="utf-8") as f:
        json.dump({"action": action, "turn": args.turn}, f, ensure_ascii=False)

    # Block until the engine reports this turn done (or timeout).
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        if turn_done(args.turn):
            break
        time.sleep(args.poll)
    else:
        print(json.dumps({"_timeout": True, "turn": args.turn,
                          "hint": "engine still processing; re-run the SAME command to keep waiting"},
                         ensure_ascii=False))
        return 2

    with open(response_file, "r", encoding="utf-8") as f:
        resp = json.load(f)
    print(json.dumps(resp, ensure_ascii=False, indent=2))

    narrative = resp.get("narrative", "")
    if isinstance(narrative, str) and narrative.startswith("[ENGINE ERROR"):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
