#!/usr/bin/env python3
"""
Signal Lost — Smoke Test

Quick validation tests that do NOT require an LLM.
Checks: graph compilation, tool schemas, session create/save/load roundtrip.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

# Ensure game root is on sys.path
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_GAME_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", ".."))
if _GAME_ROOT not in sys.path:
    sys.path.insert(0, _GAME_ROOT)


def test_graph_compiles():
    """The LangGraph StateGraph compiles without errors."""
    from engine.graph import compile_graph
    graph = compile_graph()
    assert graph is not None, "compile_graph() returned None"
    print("  [PASS] Graph compiles successfully")


def test_tools_have_valid_schemas():
    """All tools have names, descriptions, and valid parameter schemas."""
    from engine.tools import ALL_TOOLS
    assert len(ALL_TOOLS) > 0, "No tools found"
    for tool in ALL_TOOLS:
        assert hasattr(tool, "name"), f"Tool missing name: {tool}"
        assert hasattr(tool, "description"), f"Tool {tool.name} missing description"
        assert tool.name, f"Tool has empty name"
        assert tool.description, f"Tool {tool.name} has empty description"
    print(f"  [PASS] All {len(ALL_TOOLS)} tools have valid schemas")


def test_session_create_and_load():
    """Session create → load roundtrip preserves data."""
    from engine.state import create_new_session, initial_state

    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = os.path.join(tmpdir, "test_session")

        create_new_session(
            session_dir=session_dir,
            name="TestPlayer",
            alias="Tester",
            background="netrunner",
            difficulty="standard",
            language="en",
        )

        # Verify files exist
        for fname in ["player.json", "knowledge.json", "traces.json",
                       "location.json", "inventory.json", "npcs.json",
                       "world_state.json", "log.json"]:
            path = os.path.join(session_dir, fname)
            assert os.path.exists(path), f"Missing: {fname}"
            with open(path, "r") as f:
                data = json.load(f)
            assert isinstance(data, dict), f"{fname} is not a dict"

        # Load state
        state = initial_state(session_dir)
        assert state["player"]["name"] == "TestPlayer"
        assert state["player"]["alias"] == "Tester"
        assert state["session_dir"] == session_dir

    print("  [PASS] Session create/load roundtrip works")


def test_session_save_and_restore():
    """Save → load roundtrip preserves session data."""
    from engine.state import create_new_session, initial_state, save_game_to_slot, copy_save_to_session

    with tempfile.TemporaryDirectory() as tmpdir:
        session_dir = os.path.join(tmpdir, "session", "test")
        saves_dir = os.path.join(tmpdir, "saves")

        create_new_session(
            session_dir=session_dir,
            name="SaveTest",
            alias="Saver",
            background="street_runner",
            difficulty="standard",
            language="en",
        )

        # Save
        save_game_to_slot(session_dir, "test_save", saves_dir)
        save_path = os.path.join(saves_dir, "test_save")
        assert os.path.isdir(save_path), "Save directory not created"

        # Restore to a new session
        restored_dir = os.path.join(tmpdir, "session", "restored")
        copy_save_to_session(save_path, restored_dir)

        state = initial_state(restored_dir)
        assert state["player"]["name"] == "SaveTest"

    print("  [PASS] Session save/restore roundtrip works")


def test_game_data_integrity():
    """Trace conditions and endings are well-formed."""
    from engine.game_data import TRACE_CONDITIONS, ENDINGS

    assert len(TRACE_CONDITIONS) > 0, "No trace conditions"
    for tc in TRACE_CONDITIONS:
        assert "id" in tc, f"Trace missing id: {tc}"
        assert "layer" in tc, f"Trace {tc['id']} missing layer"
        assert "check" in tc, f"Trace {tc['id']} missing check function"
        assert callable(tc["check"]), f"Trace {tc['id']} check is not callable"

    assert len(ENDINGS) > 0, "No endings defined"
    print(f"  [PASS] {len(TRACE_CONDITIONS)} traces, {len(ENDINGS)} endings validated")


def test_llm_factory_providers():
    """LLM factory supports expected providers (without creating actual instances)."""
    from engine.llm_factory import create_llm
    import pytest

    # Unknown provider should raise
    try:
        create_llm("nonexistent_provider", "model")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "nonexistent_provider" in str(e)

    print("  [PASS] LLM factory validates providers correctly")


def test_reset_turn_flags():
    """reset_turn_flags returns correct defaults."""
    from engine.state import reset_turn_flags

    flags = reset_turn_flags()
    assert flags["skip_conversation_log"] is False
    assert flags["skip_turn_increment"] is False
    assert flags["input_blocked"] is False
    assert flags["blocking_reason"] is None
    assert flags["skip_validation"] is False
    assert flags["language_retry_count"] == 0
    print("  [PASS] reset_turn_flags returns clean defaults")


def main():
    print("=" * 60)
    print("Signal Lost — Smoke Test")
    print("=" * 60)
    print()

    tests = [
        test_graph_compiles,
        test_tools_have_valid_schemas,
        test_session_create_and_load,
        test_session_save_and_restore,
        test_game_data_integrity,
        test_llm_factory_providers,
        test_reset_turn_flags,
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
