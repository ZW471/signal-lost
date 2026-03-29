#!/usr/bin/env python3
"""
Signal Lost — Run 12 Automated Sessions

Launches 12 game sessions with different difficulty/background combos,
each driven by an LLM agent. Writes logs to logs/v1/.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_GAME_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _GAME_ROOT not in sys.path:
    sys.path.insert(0, _GAME_ROOT)

from langchain_core.messages import HumanMessage
from engine.graph import compile_graph, set_llm
from engine.state import create_new_session, initial_state
from engine.llm_factory import create_llm, load_env, load_provider_config

load_env()

# 12 sessions: 4 difficulties x 3 backgrounds
SESSIONS = [
    {"difficulty": "paranoid",  "background": "street_runner",   "name": "Vex",     "alias": "Spark",    "language": "en"},
    {"difficulty": "paranoid",  "background": "corporate_exile", "name": "Lyra",    "alias": "Cipher",   "language": "en"},
    {"difficulty": "paranoid",  "background": "netrunner",       "name": "Kael",    "alias": "Ghost",    "language": "en"},
    {"difficulty": "cautious",  "background": "street_runner",   "name": "Rook",    "alias": "Blade",    "language": "en"},
    {"difficulty": "cautious",  "background": "corporate_exile", "name": "Sable",   "alias": "Mirror",   "language": "en"},
    {"difficulty": "cautious",  "background": "netrunner",       "name": "Zephyr",  "alias": "Pulse",    "language": "zh"},
    {"difficulty": "standard",  "background": "street_runner",   "name": "Raze",    "alias": "Flicker",  "language": "en"},
    {"difficulty": "standard",  "background": "corporate_exile", "name": "Orin",    "alias": "Shade",    "language": "zh"},
    {"difficulty": "standard",  "background": "netrunner",       "name": "Nyx",     "alias": "Drift",    "language": "en"},
    {"difficulty": "reckless",  "background": "street_runner",   "name": "Talon",   "alias": "Fuse",     "language": "en"},
    {"difficulty": "reckless",  "background": "corporate_exile", "name": "Sera",    "alias": "Ash",      "language": "zh"},
    {"difficulty": "reckless",  "background": "netrunner",       "name": "Hex",     "alias": "Wraith",   "language": "en"},
]

MAX_TURNS = 20

# Agent action generator prompt template
AGENT_SYSTEM = """You are playing Signal Lost, a cyberpunk text RPG. You are {name} ({alias}), a {background}.
Difficulty: {difficulty}. Language: {language_desc}.

You've just received a game narrative. Decide your next action.
Think about what you've learned, what mysteries to pursue, and how to survive.
Be creative, strategic, and true to your character's background.

Respond with ONLY your in-character action (what you do/say next). Keep it 1-3 sentences.
Do NOT include meta-commentary, just the action."""

FIRST_ACTIONS = {
    "street_runner": "I scan the alley for threats, check my pockets for anything useful, and size up the woman in the noodle shop. Streets taught me to read people before they read me.",
    "corporate_exile": "I straighten up, brushing the rain off my coat. Old habits. I check for my keycard instinctively, then study the noodle shop — the woman behind the counter has been watching. Time to find out what she knows.",
    "netrunner": "I reach behind my ear, feeling the implant's hum. Pre-Severance tech... My fingers itch for a terminal. I scan for any active network signals in the area while heading toward the noodle shop.",
}


def run_session(session_idx: int, session_cfg: dict, provider: str, model: str, temperature: float):
    """Run a single game session and return the log content."""
    name = session_cfg["name"]
    alias = session_cfg["alias"]
    bg = session_cfg["background"]
    diff = session_cfg["difficulty"]
    lang = session_cfg["language"]

    session_dir = os.path.join(_GAME_ROOT, "session", f"v1_{alias.lower()}")
    log_dir = os.path.join(_GAME_ROOT, "logs", "v1")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"session_{session_idx + 1:02d}_{alias.lower()}.md")

    print(f"\n[Session {session_idx + 1}] {name} ({alias}) — {bg} / {diff} / {lang}")

    # Create session
    create_new_session(
        session_dir=session_dir,
        name=name,
        alias=alias,
        background=bg,
        difficulty=diff,
        language=lang,
    )

    # Create LLM for the agent (separate from game engine LLM)
    agent_llm = create_llm(provider, model, temperature=0.9)

    # Set game engine LLM
    game_llm = create_llm(provider, model, temperature=temperature)
    set_llm(game_llm)

    graph = compile_graph()
    state = initial_state(session_dir)

    bg_display = {"street_runner": "Street Runner", "corporate_exile": "Corporate Exile", "netrunner": "Netrunner"}[bg]
    lang_desc = "English" if lang == "en" else "Chinese (中文)"

    log_lines = []
    log_lines.append(f"# Signal Lost — Session {session_idx + 1} Playthrough Log\n")
    log_lines.append(f"**Date**: {time.strftime('%Y-%m-%d %H:%M')}")
    log_lines.append(f"**Character**: {name} (alias: {alias}) — {bg_display}")
    log_lines.append(f"**Provider**: {provider} / {model}")
    log_lines.append(f"**Difficulty**: {diff.capitalize()}")
    log_lines.append(f"**Language**: {lang_desc}")
    log_lines.append(f"\n---\n")

    # Resume turn (scene-setting)
    player = state.get("player", {})
    location = state.get("location", {})
    resume_text = (
        f"[SYSTEM: Session resumed. The player is {name} "
        f"(alias: {alias}), a {bg_display}. "
        f"Currently at {location.get('area', '?')} in {location.get('district', '?')}. "
        f"Turn {player.get('turn', 1)}. Provide a brief scene-setting narrative.]"
    )
    state["messages"].append(HumanMessage(content=resume_text))
    state["skip_conversation_log"] = True
    state["skip_turn_increment"] = True
    state["skip_validation"] = True

    try:
        result = graph.invoke(state)
        state = result
        opening_narrative = result.get("narrative", "(no narrative)")
        print(f"  Opening: {opening_narrative[:100]}...")

        log_lines.append(f"## Opening\n")
        log_lines.append(f"**Response**:\n{opening_narrative}\n")
        log_lines.append(f"\n---\n")
    except Exception as e:
        print(f"  ERROR on opening: {e}")
        traceback.print_exc()
        opening_narrative = "(engine error on opening)"
        log_lines.append(f"## Opening\n\n**ERROR**: {e}\n\n---\n")

    # Play turns
    last_narrative = opening_narrative
    for turn in range(1, MAX_TURNS + 1):
        # Generate agent action
        if turn == 1:
            action = FIRST_ACTIONS.get(bg, "I look around and take stock of my situation.")
        else:
            try:
                agent_prompt = AGENT_SYSTEM.format(
                    name=name, alias=alias, background=bg_display,
                    difficulty=diff, language_desc=lang_desc,
                )
                from langchain_core.messages import SystemMessage, HumanMessage as HM
                agent_msgs = [
                    SystemMessage(content=agent_prompt),
                    HM(content=f"Game narrative:\n\n{last_narrative}\n\nWhat do you do next?"),
                ]
                agent_response = agent_llm.invoke(agent_msgs)
                action = agent_response.content.strip()
                if len(action) > 500:
                    action = action[:500]
            except Exception as e:
                print(f"  [Turn {turn}] Agent error: {e}")
                action = "I look around carefully and investigate my surroundings."

        print(f"  [Turn {turn}] Action: {action[:80]}...")

        # Agent thought (commentary)
        agent_thought = ""
        try:
            thought_msgs = [
                SystemMessage(content=f"You are playing {name} ({alias}) in Signal Lost. Briefly share your strategic thinking about what's happening in the game and your next move. 2-3 sentences max."),
                HM(content=f"Last narrative:\n{last_narrative[:500]}\n\nYour action: {action}"),
            ]
            thought_response = agent_llm.invoke(thought_msgs)
            agent_thought = thought_response.content.strip()
        except Exception:
            agent_thought = "(no thought generated)"

        # Run game turn
        state["messages"].append(HumanMessage(content=action))
        try:
            result = graph.invoke(state)
            state = result
            narrative = result.get("narrative", "(no narrative)")
            game_over = result.get("game_over", False)
            ending = result.get("ending")
            last_narrative = narrative

            player = state.get("player", {})
            location = state.get("location", {})
            integrity = player.get("integrity", {})

            log_lines.append(f"## Turn {turn}\n")
            log_lines.append(f"**Player**: {action}\n")
            log_lines.append(f"**Agent Thought**: {agent_thought}\n")
            log_lines.append(f"**Response**:\n{narrative}\n")
            log_lines.append(f"*Location: {location.get('district', '?')} — {location.get('area', '?')}*")
            log_lines.append(f"*Integrity: {integrity.get('current', '?')}/{integrity.get('max', '?')} | Credits: {player.get('credits', '?')} | Turn: {player.get('turn', '?')}*\n")

            # Game comment
            try:
                comment_msgs = [
                    SystemMessage(content="You are a game reviewer. Comment on this turn's quality: narrative writing, game mechanics, player agency, atmosphere. 2-3 sentences."),
                    HM(content=f"Player action: {action}\nGame response: {narrative[:800]}"),
                ]
                comment_response = agent_llm.invoke(comment_msgs)
                comment = comment_response.content.strip()
            except Exception:
                comment = "(no comment)"

            log_lines.append(f"**Game Comment**: {comment}\n")
            log_lines.append(f"\n---\n")

            print(f"  [Turn {turn}] Done. Integrity: {integrity.get('current', '?')}/{integrity.get('max', '?')}")

            if game_over:
                print(f"  *** GAME OVER — Ending: {ending} ***")
                log_lines.append(f"\n## GAME OVER\n\nEnding: {ending}\n")
                break

        except Exception as e:
            print(f"  [Turn {turn}] Engine error: {e}")
            traceback.print_exc()
            log_lines.append(f"## Turn {turn}\n\n**Player**: {action}\n\n**ERROR**: {e}\n\n---\n")
            last_narrative = "(engine error)"

    # Write log
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    print(f"  Log saved: {log_path}")
    return log_path


def main():
    provider_cfg = load_provider_config()
    provider = provider_cfg.get("provider", "openai")
    model = provider_cfg.get("model", "gpt-5.4")
    temperature = provider_cfg.get("temperature", 0.7)

    print(f"=== Signal Lost — 12 Session Runner ===")
    print(f"Provider: {provider} | Model: {model}")
    print(f"Max turns per session: {MAX_TURNS}")
    print()

    # Parse optional session index from args
    session_idx = None
    if len(sys.argv) > 1:
        session_idx = int(sys.argv[1])
        print(f"Running single session: {session_idx}")
        cfg = SESSIONS[session_idx]
        run_session(session_idx, cfg, provider, model, temperature)
        return

    # Run all 12 sequentially (for parallel, use separate processes)
    log_paths = []
    for i, cfg in enumerate(SESSIONS):
        try:
            path = run_session(i, cfg, provider, model, temperature)
            log_paths.append(path)
        except Exception as e:
            print(f"\n[Session {i + 1}] FATAL ERROR: {e}")
            traceback.print_exc()

    print(f"\n\n=== All sessions complete. {len(log_paths)}/{len(SESSIONS)} logs written. ===")


if __name__ == "__main__":
    main()
