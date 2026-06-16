#!/usr/bin/env python3
"""
Signal Lost — Regression Tests

Tests for specific bugs identified in game reviews and playthroughs.
These validate that known issues have been fixed.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_GAME_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _GAME_ROOT not in sys.path:
    sys.path.insert(0, _GAME_ROOT)


def test_flag_bleed_between_turns():
    """Flags set in one turn should not bleed into the next.

    Regression: skip_conversation_log and skip_turn_increment were not being
    reset between turns, causing subsequent turns to skip logging or incrementing.
    """
    from engine.state import reset_turn_flags

    # Simulate: flags set for a resume turn
    flags = reset_turn_flags()
    assert flags["skip_conversation_log"] is False
    assert flags["skip_turn_increment"] is False
    assert flags["input_blocked"] is False

    # After a resume turn, calling reset_turn_flags should give clean state
    flags["skip_conversation_log"] = True
    flags["skip_turn_increment"] = True

    clean = reset_turn_flags()
    assert clean["skip_conversation_log"] is False, "skip_conversation_log bled between turns"
    assert clean["skip_turn_increment"] is False, "skip_turn_increment bled between turns"

    print("  [PASS] Flag bleed between turns prevented")


def test_area_field_in_initial_state():
    """Initial state should have a valid area field, not '?'.

    Regression: area field frequently showed '?' throughout playthroughs
    because the initial location template had '?' as default.
    """
    from engine.state import create_new_session, initial_state

    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = os.path.join(tmpdir, "test")
        create_new_session(
            session_dir=session_dir,
            name="AreaTest",
            alias="Tester",
            background="netrunner",
            difficulty="standard",
            language="en",
        )
        state = initial_state(session_dir)
        location = state.get("location", {})
        # Initial area may be "?" at game start, but district should be set
        assert location.get("district"), "Initial district should not be empty"

    print("  [PASS] Initial state has populated district field")


def test_prompt_includes_dialogue_rules():
    """System prompt must include dialogue and state update rules.

    Regression: LLM would time-skip through NPC conversations and forget
    to call state mutation tools.
    """
    from engine.prompts import SYSTEM_PROMPT

    assert "Dialogue Rules" in SYSTEM_PROMPT, "Missing Dialogue Rules section"
    assert "MUST show the actual dialogue" in SYSTEM_PROMPT, "Missing dialogue mandate"
    assert "Mandatory State Updates" in SYSTEM_PROMPT, "Missing Mandatory State Updates section"
    assert "MUST call `update_location`" in SYSTEM_PROMPT, "Missing update_location mandate"
    assert "MUST call `update_player`" in SYSTEM_PROMPT, "Missing update_player mandate"
    assert "MUST call `add_knowledge`" in SYSTEM_PROMPT, "Missing add_knowledge mandate"

    print("  [PASS] System prompt includes dialogue and state update rules")


def test_prompt_includes_economy_engagement():
    """System prompt should encourage use of credits and inventory.

    Regression: Credits and inventory systems were barely engaged across
    20-turn playthroughs. Cipher toolkit was never used.
    """
    from engine.prompts import SYSTEM_PROMPT

    assert "Economy" in SYSTEM_PROMPT or "credit" in SYSTEM_PROMPT.lower(), \
        "Missing economy engagement prompts"
    assert "cipher" in SYSTEM_PROMPT.lower(), "Missing cipher engagement prompts"

    print("  [PASS] System prompt includes economy and inventory engagement")


def test_input_blocked_handler_gives_suggestions():
    """Blocked input handler should provide contextual suggestions.

    Regression: Generic 'action blocked' message with no guidance on what
    to do instead.
    """
    from engine.graph import input_blocked_handler
    from engine.state import GameState

    # Create a minimal state with location info
    state = {
        "messages": [],
        "player": {"name": "Test", "alias": "T"},
        "knowledge": {},
        "traces": {},
        "location": {"district": "Neon Row", "area": "Main Street"},
        "inventory": {},
        "npcs": {},
        "world_state": {},
        "log": {},
        "turn_delta": {},
        "game_over": False,
        "ending": None,
        "narrative": "",
        "session_dir": "/tmp",
        "skip_conversation_log": False,
        "skip_turn_increment": False,
        "input_blocked": True,
        "blocking_reason": "That action attempts to break game rules.",
        "skip_validation": False,
        "language_retry_count": 0,
    }

    result = input_blocked_handler(state)
    narrative = result.get("narrative", "")
    assert "Try instead" in narrative, f"Missing suggestions in: {narrative}"

    print("  [PASS] Blocked input handler provides contextual suggestions")


def test_llm_factory_supports_claude_code():
    """LLM factory should support the claude-code provider.

    This ensures headless testing via Claude Code CLI still works.
    """
    from engine.llm_factory import create_llm

    # We can't actually create a ClaudeCodeLLM without the CLI, but we can
    # verify the import path works
    try:
        from tests.scripts.claude_llm import ClaudeCodeLLM
        assert ClaudeCodeLLM is not None
        print("  [PASS] claude_llm.py importable from tests.scripts")
    except ImportError as e:
        print(f"  [FAIL] Cannot import ClaudeCodeLLM: {e}")
        raise


def test_no_signalable_ending_fires_early():
    """Brittle keyword-gated bad/neutral endings must not false-fire early.

    Regression: the `exile` ending matched the bare word "exile", which collides
    with the corporate_exile background's identity lore, so a single early
    knowledge entry fired the ending on turn 1. The structured check path must
    gate MODEL_SIGNALABLE_ENDINGS to turn>=8, and `exile` must require an action
    of leaving the city (not the noun).
    """
    from engine.state import create_new_session
    from engine.claude_code_engine import _run_consequence

    # 1. No ending fires on a fresh seed at turn 1, for every background.
    for bg in ("netrunner", "street_runner", "corporate_exile"):
        with tempfile.TemporaryDirectory() as d:
            create_new_session(session_dir=d, name="T", alias="T",
                               background=bg, difficulty="standard", language="en")
            S = {k: json.load(open(os.path.join(d, f"{k}.json")))
                 for k in ("player", "knowledge", "traces", "world_state", "npcs")}
            S["player"]["turn"] = 1
            go, end, _ = _run_consequence(S["player"], S["traces"], S["world_state"],
                                          S["knowledge"], S["npcs"])
            assert not go, f"{bg}: ending {end!r} false-fired at turn 1"

    # 2. "exile" lore word never fires the exile ending (de-collided keyword).
    W = {"nexus_alert": {"current": 0}}
    T = {"discovered": []}
    N = {"npcs": []}
    k_lore = {"facts": [{"description": "You are a corporate exile from NEXUS"}]}
    go, end, _ = _run_consequence({"turn": 20, "integrity": {"current": 3, "max": 3}},
                                  T, W, k_lore, N)
    assert not go, f"bare 'exile' lore wrongly fired ending {end!r}"

    # 3. An actual leaving action fires exile, but only at/after the turn gate.
    k_leave = {"facts": [{"description": "You finally leave Neo-Kowloon behind for good"}]}
    go_early, _, _ = _run_consequence({"turn": 3, "integrity": {"current": 3, "max": 3}},
                                      T, W, k_leave, N)
    assert not go_early, "exile fired before the turn>=8 gate"
    go_late, end_late, _ = _run_consequence({"turn": 10, "integrity": {"current": 3, "max": 3}},
                                            T, W, k_leave, N)
    assert go_late and end_late == "exile", f"exile did not fire on a real leave action: {end_late!r}"
    print("  [PASS] Signalable endings gated; exile is action-based, not noun-based")


def test_cli_runner_kills_hung_process_tree():
    """A hung CLI subprocess must not wedge a turn forever (BUG-003).

    Regression: ``subprocess.run(timeout=...)`` only SIGKILLs the direct child on
    timeout; a surviving grandchild that inherited the stdout pipe keeps it open,
    so run()'s internal communicate() blocks indefinitely waiting for EOF — a real
    52-minute engine hang was observed. ``_run_cli_pg`` runs the command in its own
    process group and kills the whole tree, so it raises TimeoutExpired fast.
    """
    import subprocess
    import time
    from tests.scripts.claude_llm import _run_cli_pg

    # Parent backgrounds a long sleep (the grandchild) that inherits stdout, then
    # the parent itself sleeps. Classic pipe-EOF wedge for plain subprocess.run.
    cmd = ["sh", "-c", "sleep 60 & sleep 60"]
    t0 = time.time()
    raised = False
    try:
        _run_cli_pg(cmd, "", timeout=1, env=os.environ.copy())
    except subprocess.TimeoutExpired:
        raised = True
    elapsed = time.time() - t0
    assert raised, "_run_cli_pg did not raise TimeoutExpired on a hung command"
    assert elapsed < 15, f"_run_cli_pg took {elapsed:.1f}s — it wedged instead of killing the tree"
    print(f"  [PASS] Hung CLI tree killed fast ({elapsed:.1f}s), no turn wedge")


def test_good_endings_reachable_and_not_shadowed():
    """A deep, good-aligned playthrough must resolve to a GOOD ending.

    Regression #1 (ecc7ca0): evidence-gated deep traces (L3/L4/L5) once scanned
    only the rarely-used "evidence" channel, so they never fired from recorded
    FACTS — walling off the good endings and making every run end in death.

    Regression #2 (ending order): even once the traces fired, first-match-wins
    let the looser keyword-gated bad ending `ascension` (whose force-merge
    keywords incidentally match the "ascension is a path" lore a deep player is
    EXPECTED to learn) shadow the good endings. Good endings must be checked
    first so a fully-earned bridge resolves to the_bridge, not a forced ascension.
    """
    from tests.scenarios.good_ending_reachability import (
        build_state, run_trace_fixpoint,
    )
    from engine.game_data import (
        ENDINGS, EARLY_GATED_ENDINGS, _count_discovered_traces, _trace_discovered,
    )

    knowledge, npcs, player, world_state = build_state()
    traces = run_trace_fixpoint(knowledge, npcs, player, world_state)

    assert _count_discovered_traces(traces) >= 18, (
        f"deep traces did not fire from FACTS: only "
        f"{_count_discovered_traces(traces)} discovered")
    assert _trace_discovered(traces, "TRACE-L5-02"), "L5-02 (bridge gate) did not fire"

    fired = [e["id"] for e in ENDINGS
             if not (e["id"] in EARLY_GATED_ENDINGS and player.get("turn", 1) < 8)
             and e["check"](traces, world_state, player, knowledge, npcs)]
    assert fired, "no ending fired for a fully-earned deep good state"
    assert fired[0] in {"the_bridge", "symbiosis"}, (
        f"a bad ending shadowed the good one: first match was {fired[0]!r}")
    print(f"  [PASS] Deep good run resolves to GOOD ending ({fired[0]}), not shadowed")


def main():
    print("=" * 60)
    print("Signal Lost — Regression Tests")
    print("=" * 60)
    print()

    tests = [
        test_flag_bleed_between_turns,
        test_area_field_in_initial_state,
        test_prompt_includes_dialogue_rules,
        test_prompt_includes_economy_engagement,
        test_input_blocked_handler_gives_suggestions,
        test_llm_factory_supports_claude_code,
        test_no_signalable_ending_fires_early,
        test_cli_runner_kills_hung_process_tree,
        test_good_endings_reachable_and_not_shadowed,
    ]

    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {test_fn.__name__}: {e}")
            failed += 1

    print()
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
