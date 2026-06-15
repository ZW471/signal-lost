#!/usr/bin/env python3
"""
Signal Lost — Parameterized Headless Play Engine (for parallel agent runs)

Like ``play_headless.py`` but every collision-prone path is parameterized via
environment variables so multiple agents can each drive their own isolated game
in parallel (see GAMEPLAY.md §2.5).

Env vars (all optional):
    HEADLESS_SESSION_NAME   session subdir under session/ (default "headless")
    HEADLESS_LANGUAGE       "en" | "zh"            (default "en")
    HEADLESS_BACKGROUND     netrunner | street_runner | corporate_exile
    HEADLESS_DIFFICULTY     paranoid|cautious|standard|reckless (default standard)
    HEADLESS_NAME           character name         (default "Kael")
    HEADLESS_ALIAS          character alias         (default "Ghost")
    HEADLESS_LOG            playthrough log path
                            (default logs/<session>_playthrough.md)

Protocol files live in session/<HEADLESS_SESSION_NAME>/:
    player_action.json   (player writes:  {"action": "...", "turn": N})
    game_response.json   (engine writes:  {"narrative", "turn", "game_over", ...})
    engine_status.json   (engine writes:  {"status": waiting|processing|done})
"""

from __future__ import annotations

import json
import os
import sys
import time

# Ensure game root is on sys.path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_GAME_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _GAME_ROOT not in sys.path:
    sys.path.insert(0, _GAME_ROOT)

from langchain_core.messages import HumanMessage

from engine.graph import compile_graph, set_llm
from engine.state import create_new_session, initial_state
from engine.llm_factory import create_llm, default_model_for, load_env, load_provider_config

# --- Bootstrap ---
load_env()

SESSIONS_ROOT = os.path.join(_GAME_ROOT, "session")
SESSION_NAME = os.environ.get("HEADLESS_SESSION_NAME", "headless")
SESSION_DIR = os.path.join(SESSIONS_ROOT, SESSION_NAME)

LANGUAGE = os.environ.get("HEADLESS_LANGUAGE", "en")
BACKGROUND = os.environ.get("HEADLESS_BACKGROUND", "netrunner")
DIFFICULTY = os.environ.get("HEADLESS_DIFFICULTY", "standard")
CHAR_NAME = os.environ.get("HEADLESS_NAME", "Kael")
CHAR_ALIAS = os.environ.get("HEADLESS_ALIAS", "Ghost")
LOG_FILE = os.environ.get(
    "HEADLESS_LOG", os.path.join(_GAME_ROOT, "logs", f"{SESSION_NAME}_playthrough.md")
)

# Load provider config
provider_cfg = load_provider_config()
PROVIDER = provider_cfg.get("provider", "openai")
MODEL = provider_cfg.get("model", default_model_for(PROVIDER))
TEMPERATURE = provider_cfg.get("temperature", 0.7)

# --- Communication protocol files ---
ACTION_FILE = os.path.join(SESSION_DIR, "player_action.json")
RESPONSE_FILE = os.path.join(SESSION_DIR, "game_response.json")
STATUS_FILE = os.path.join(SESSION_DIR, "engine_status.json")

POLL_INTERVAL = 1  # seconds


def write_status(status: str, turn: int = 0):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump({"status": status, "turn": turn, "timestamp": time.time()}, f, indent=2)


def write_response(narrative: str, turn: int, game_over: bool, state: dict):
    from engine.prompts import extract_deepest_layer
    player = state.get("player", {})
    location = state.get("location", {})
    integrity = player.get("integrity", {})
    traces = state.get("traces", {})
    world_state = state.get("world_state", {})
    discovered = len(traces.get("discovered", []))
    alert = world_state.get("nexus_alert", {})
    alert_cur = alert.get("current", "?") if isinstance(alert, dict) else alert
    with open(RESPONSE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "narrative": narrative,
            "turn": turn,
            "game_over": game_over,
            "ending": state.get("ending"),
            "state_summary": {
                "location": f"{location.get('district', '?')} — {location.get('area', '?')}",
                "integrity": f"{integrity.get('current', '?')}/{integrity.get('max', '?')}",
                "nexus_alert": alert_cur,
                "credits": player.get("credits", "?"),
                "traces_discovered": discovered,
                "deepest_layer": extract_deepest_layer(traces),
                "turn": player.get("turn", "?"),
            }
        }, f, ensure_ascii=False, indent=2)


def poll_for_action(expected_turn: int) -> str | None:
    while True:
        try:
            with open(ACTION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("turn") == expected_turn:
                return data["action"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass
        time.sleep(POLL_INTERVAL)


def main():
    print(f"=== Signal Lost — Headless Agent Engine ===")
    print(f"Session: {SESSION_NAME} | Lang: {LANGUAGE} | BG: {BACKGROUND} | Diff: {DIFFICULTY}")
    print(f"Provider: {PROVIDER} | Model: {MODEL}")
    print()

    llm = create_llm(PROVIDER, MODEL, temperature=TEMPERATURE)
    set_llm(llm, zero_cost=PROVIDER in ("claude-code", "local", "lmstudio"))

    create_new_session(
        session_dir=SESSION_DIR,
        name=CHAR_NAME,
        alias=CHAR_ALIAS,
        background=BACKGROUND,
        difficulty=DIFFICULTY,
        language=LANGUAGE,
    )

    graph = compile_graph()
    state = initial_state(SESSION_DIR)

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as log:
        log.write("# Signal Lost — Headless Agent Playthrough Log\n\n")
        log.write(f"**Date**: {time.strftime('%Y-%m-%d %H:%M')}\n")
        log.write(f"**Session**: {SESSION_NAME}\n")
        log.write(f"**Character**: {CHAR_NAME} (alias: {CHAR_ALIAS}) — {BACKGROUND}\n")
        log.write(f"**Provider**: {PROVIDER} / {MODEL}\n")
        log.write(f"**Difficulty**: {DIFFICULTY} | **Language**: {LANGUAGE}\n\n")
        log.write("---\n\n")
        log.flush()

        turn = 1
        while True:
            write_status("waiting", turn)
            print(f"\n--- Waiting for turn {turn} action... ---")

            action = poll_for_action(turn)
            if action is None:
                break

            write_status("processing", turn)
            print(f"\n{'='*60}\nTURN {turn}: {action}\n{'='*60}")

            state["messages"].append(HumanMessage(content=action))

            try:
                result = graph.invoke(state)
                state = result
                narrative = result.get("narrative", "(no narrative)")
                game_over = result.get("game_over", False)
                ending = result.get("ending")

                print(f"\nNARRATIVE:\n{narrative}")
                write_response(narrative, turn, game_over, state)
                write_status("done", turn)

                player = state.get("player", {})
                location = state.get("location", {})
                integrity = player.get("integrity", {})
                log.write(f"## Turn {turn}\n\n**Player**: {action}\n\n")
                log.write(f"**Response**:\n{narrative}\n\n")
                log.write(f"*Location: {location.get('district', '?')} — {location.get('area', '?')}*\n")
                log.write(f"*Integrity: {integrity.get('current', '?')}/{integrity.get('max', '?')} | "
                          f"NEXUS: {player.get('nexus_alert', '?')} | Credits: {player.get('credits', '?')} | "
                          f"Turn: {player.get('turn', '?')}*\n\n---\n\n")
                log.flush()

                if game_over:
                    print(f"\n*** GAME OVER — Ending: {ending} ***")
                    log.write(f"\n## GAME OVER\n\nEnding: {ending}\n")
                    log.flush()
                    break

            except Exception as e:
                print(f"\nERROR: {e}")
                write_response(f"[ENGINE ERROR: {e}]", turn, False, state)
                write_status("done", turn)
                log.write(f"## Turn {turn}\n\n**Player**: {action}\n\n**ERROR**: {e}\n\n---\n\n")
                log.flush()
                import traceback
                traceback.print_exc()

            turn += 1

    print(f"\n\nPlaythrough log saved to: {LOG_FILE}")


if __name__ == "__main__":
    main()
