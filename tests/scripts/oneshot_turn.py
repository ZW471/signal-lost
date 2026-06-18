#!/usr/bin/env python3
"""Generic one-shot single-turn driver for headless agent play (any provider).

Why this exists: the persistent ``play_headless_agent.py`` daemon cannot survive
between separate Bash invocations in the agent harness (background process groups
are reaped when each Bash call returns). This driver instead runs exactly ONE
turn synchronously inside a single process: it loads state from disk, makes one
LLM call via the same engine path the real game uses, commits state back, and
prints a compact JSON summary. Each agent calls it once per turn.

It exercises the SAME code paths real players use:
  * providers in ``BYPASS_PROVIDERS`` (claude-code / codex) → the single-call
    bypass engine ``engine.claude_code_engine.run_turn``.
  * other providers (openrouter / openai / anthropic / local) → the full
    LangGraph pipeline.

All run parameters come from env vars so one shared script serves every agent
(no per-session hand-copied driver):

    HEADLESS_SESSION_NAME   session subdir under session/   (required)
    HEADLESS_PROVIDER       openrouter|claude-code|codex|… (default openrouter)
    HEADLESS_MODEL          model id                        (default per provider)
    HEADLESS_TEMPERATURE    float                           (default 0.7)
    HEADLESS_LANGUAGE       en|zh                           (default en)
    HEADLESS_BACKGROUND     netrunner|street_runner|corporate_exile (default netrunner)
    HEADLESS_DIFFICULTY     paranoid|cautious|standard|reckless     (default standard)
    HEADLESS_NAME           character name                  (default Kael)
    HEADLESS_ALIAS          character alias                 (default Ghost)

Usage:
    # create the session once (turn 0):
    HEADLESS_SESSION_NAME=x2_h1 HEADLESS_PROVIDER=claude-code \\
        python3 tests/scripts/oneshot_turn.py --init

    # then drive each turn (action via --action or stdin):
    HEADLESS_SESSION_NAME=x2_h1 HEADLESS_PROVIDER=claude-code \\
        python3 tests/scripts/oneshot_turn.py --turn 1 --action "look around"
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

_THIS = os.path.dirname(os.path.abspath(__file__))
_GAME_ROOT = os.path.abspath(os.path.join(_THIS, "..", ".."))
if _GAME_ROOT not in sys.path:
    sys.path.insert(0, _GAME_ROOT)

from engine.graph import set_llm
from engine.state import initial_state, create_new_session
from engine.llm_factory import (
    create_llm, load_env, default_model_for, BYPASS_PROVIDERS,
)
from engine.claude_code_engine import run_turn as cc_run_turn
from engine.prompts import extract_deepest_layer

SESSION = os.environ.get("HEADLESS_SESSION_NAME")
PROVIDER = os.environ.get("HEADLESS_PROVIDER", "openrouter")
MODEL = os.environ.get("HEADLESS_MODEL") or default_model_for(PROVIDER)
TEMPERATURE = float(os.environ.get("HEADLESS_TEMPERATURE", "0.7"))
LANGUAGE = os.environ.get("HEADLESS_LANGUAGE", "en")
BACKGROUND = os.environ.get("HEADLESS_BACKGROUND", "netrunner")
DIFFICULTY = os.environ.get("HEADLESS_DIFFICULTY", "standard")
CHAR_NAME = os.environ.get("HEADLESS_NAME", "Kael")
CHAR_ALIAS = os.environ.get("HEADLESS_ALIAS", "Ghost")

ZERO_COST_PROVIDERS = {"claude-code", "codex", "local", "lmstudio"}


def _session_dir() -> str:
    if not SESSION:
        print(json.dumps({"error": "HEADLESS_SESSION_NAME not set"}))
        raise SystemExit(2)
    return os.path.join(_GAME_ROOT, "session", SESSION)


def _make_llm():
    load_env()
    llm = create_llm(PROVIDER, MODEL, temperature=TEMPERATURE)
    set_llm(llm, zero_cost=PROVIDER in ZERO_COST_PROVIDERS)
    return llm


def do_init() -> int:
    session_dir = _session_dir()
    create_new_session(
        session_dir=session_dir, name=CHAR_NAME, alias=CHAR_ALIAS,
        background=BACKGROUND, difficulty=DIFFICULTY, language=LANGUAGE,
    )
    print(json.dumps({
        "ok": True, "session": SESSION, "provider": PROVIDER, "model": MODEL,
        "language": LANGUAGE, "background": BACKGROUND, "difficulty": DIFFICULTY,
        "engine_path": "BYPASS" if PROVIDER in BYPASS_PROVIDERS else "LangGraph",
    }, ensure_ascii=False, indent=2))
    return 0


def do_turn(turn: int, action: str) -> int:
    session_dir = _session_dir()
    if not action:
        print(json.dumps({"error": "empty action"}))
        return 1
    _make_llm()

    if PROVIDER not in BYPASS_PROVIDERS:
        # Full LangGraph path (rare for agent runs; bypass providers are the norm).
        from engine.graph import compile_graph
        from langchain_core.messages import HumanMessage
        state = initial_state(session_dir)
        state["messages"].append(HumanMessage(content=action))
        t0 = time.time()
        result = compile_graph().invoke(state)
        elapsed = round(time.time() - t0, 1)
        narrative = result.get("narrative", "(no narrative)")
        game_over = result.get("game_over", False)
        ending = result.get("ending")
    else:
        t0 = time.time()
        try:
            result = cc_run_turn(session_dir=session_dir, player_input=action, mode="play")
        except Exception as e:  # noqa: BLE001
            import traceback
            print(json.dumps({
                "_engine_error": True, "turn": turn,
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc()[-1500:],
            }, ensure_ascii=False, indent=2))
            return 3
        elapsed = round(time.time() - t0, 1)
        narrative = result.get("narrative", "(no narrative)")
        game_over = result.get("game_over", False)
        ending = result.get("ending")

    state = initial_state(session_dir)
    player = state.get("player", {})
    location = state.get("location", {})
    integrity = player.get("integrity", {})
    traces = state.get("traces", {})
    world_state = state.get("world_state", {})
    alert = world_state.get("nexus_alert", {})
    alert_cur = alert.get("current", "?") if isinstance(alert, dict) else alert
    decay = world_state.get("fragment_decay", {})
    decay_cur = decay.get("current", "?") if isinstance(decay, dict) else decay

    # Surface the in-chat notices the engine emits (meter changes + low-integrity
    # warnings) so a headless agent can actually SEE them — the GUI renders these
    # as system lines, but a driver that drops them hides e.g. the "one more hit
    # could kill you — rest or heal" warning from the agent making decisions.
    system_notices = result.get("system_notices", []) if isinstance(result, dict) else []
    discovery = result.get("discovery_notifications", []) if isinstance(result, dict) else []

    print(json.dumps({
        "narrative": narrative,
        "turn": turn,
        "game_over": game_over,
        "ending": ending,
        "elapsed_s": elapsed,
        "system_notices": system_notices,
        "discovery_notifications": discovery,
        "state_summary": {
            "location": f"{location.get('district', '?')} — {location.get('area', '?')}",
            "integrity": f"{integrity.get('current', '?')}/{integrity.get('max', '?')}",
            "nexus_alert": alert_cur,
            "fragment_decay": decay_cur,
            "credits": player.get("credits", "?"),
            "traces_discovered": len(traces.get("discovered", [])),
            "deepest_layer": extract_deepest_layer(traces),
            "player_turn": player.get("turn", "?"),
        },
    }, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true", help="create the session and exit")
    ap.add_argument("--turn", type=int, help="turn number to submit")
    ap.add_argument("--action", default=None, help="action text (else read stdin)")
    args = ap.parse_args()

    if args.init:
        return do_init()
    if args.turn is None:
        print(json.dumps({"error": "need --init or --turn N"}))
        return 2
    action = args.action if args.action is not None else sys.stdin.read().strip()
    return do_turn(args.turn, action)


if __name__ == "__main__":
    raise SystemExit(main())
