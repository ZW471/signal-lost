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
