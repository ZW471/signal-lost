#!/usr/bin/env python3
"""
Signal Lost — Headless Play Script

Plays the game using the LangGraph engine without a GUI.
Sends predefined actions via file-polling and logs all responses.
Used for agentic testing (e.g. Claude Code as player).
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
from engine.llm_factory import create_llm, load_env, load_provider_config, SETTINGS_DIR

# --- Bootstrap ---
load_env()

SESSIONS_ROOT = os.path.join(_GAME_ROOT, "session")
HEADLESS_SESSION_NAME = "headless"
SESSION_DIR = os.path.join(SESSIONS_ROOT, HEADLESS_SESSION_NAME)
LOG_FILE = os.path.join(_GAME_ROOT, "logs", "headless_playthrough.md")

# Load provider config
provider_cfg = load_provider_config()
PROVIDER = provider_cfg.get("provider", "openai")
MODEL = provider_cfg.get("model", "gpt-5.4")
TEMPERATURE = provider_cfg.get("temperature", 0.7)


# --- Communication protocol files ---
ACTION_FILE = os.path.join(SESSION_DIR, "player_action.json")
RESPONSE_FILE = os.path.join(SESSION_DIR, "game_response.json")
STATUS_FILE = os.path.join(SESSION_DIR, "engine_status.json")

POLL_INTERVAL = 1  # seconds


def write_status(status: str, turn: int = 0):
    """Write engine status to file."""
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump({"status": status, "turn": turn, "timestamp": time.time()}, f, indent=2)


def write_response(narrative: str, turn: int, game_over: bool, state: dict):
    """Write game response to file."""
    player = state.get("player", {})
    location = state.get("location", {})
    integrity = player.get("integrity", {})
    with open(RESPONSE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "narrative": narrative,
            "turn": turn,
            "game_over": game_over,
            "ending": state.get("ending"),
            "state_summary": {
                "location": f"{location.get('district', '?')} — {location.get('area', '?')}",
                "integrity": f"{integrity.get('current', '?')}/{integrity.get('max', '?')}",
                "credits": player.get("credits", "?"),
                "turn": player.get("turn", "?"),
            }
        }, f, ensure_ascii=False, indent=2)


def poll_for_action(expected_turn: int) -> str | None:
    """Wait for a new player action in the action file."""
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
    print(f"=== Signal Lost — Game Engine (Headless) ===")
    print(f"Provider: {PROVIDER} | Model: {MODEL}")
    print()

    # Set up LLM
    llm = create_llm(PROVIDER, MODEL, temperature=TEMPERATURE)
    set_llm(llm)

    # Create new session
    create_new_session(
        session_dir=SESSION_DIR,
        name="Kael",
        alias="Ghost",
        background="netrunner",
        difficulty="standard",
        language="en",
    )

    # Update language setting
    custom_path = os.path.join(SETTINGS_DIR, "custom.json")
    with open(custom_path, "w", encoding="utf-8") as f:
        json.dump({
            "language": {"display": "en", "tui": "en"},
            "difficulty": {"mode": "standard"}
        }, f, ensure_ascii=False, indent=2)

    # Compile graph and load state
    graph = compile_graph()
    state = initial_state(SESSION_DIR)

    # Open log file
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as log:
        log.write("# Signal Lost — Headless Playthrough Log\n\n")
        log.write(f"**Date**: {time.strftime('%Y-%m-%d %H:%M')}\n")
        log.write(f"**Character**: Kael (alias: Ghost) — Netrunner\n")
        log.write(f"**Provider**: {PROVIDER} / {MODEL}\n")
        log.write(f"**Difficulty**: Standard\n\n")
        log.write("---\n\n")

        turn = 1
        while True:
            write_status("waiting", turn)
            print(f"\n--- Waiting for turn {turn} action... ---")

            action = poll_for_action(turn)
            if action is None:
                break

            write_status("processing", turn)
            print(f"\n{'='*60}")
            print(f"TURN {turn}: {action}")
            print(f"{'='*60}")

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

                log.write(f"## Turn {turn}\n\n")
                log.write(f"**Player**: {action}\n\n")
                log.write(f"**Response**:\n{narrative}\n\n")

                player = state.get("player", {})
                location = state.get("location", {})
                integrity = player.get("integrity", {})
                log.write(f"*Location: {location.get('district', '?')} — {location.get('area', '?')}*\n")
                log.write(f"*Integrity: {integrity.get('current', '?')}/{integrity.get('max', '?')} | Credits: {player.get('credits', '?')} | Turn: {player.get('turn', '?')}*\n\n")
                log.write("---\n\n")
                log.flush()

                if game_over:
                    print(f"\n*** GAME OVER — Ending: {ending} ***")
                    log.write(f"\n## GAME OVER\n\nEnding: {ending}\n")
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
