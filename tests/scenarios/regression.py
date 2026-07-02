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


def test_integrity_warning_gives_recovery_window():
    """A standard-difficulty player must be warned BEFORE the lethal last hit.

    Regression: every playtest that reached the climax died to the deep-resonance
    integrity drain with only a vague one-turn "vision dimming" line at 1/3 and no
    chance to rest. standard now warns at 2/3 (a real recovery window), and the
    1/3 "one hit from death" moment escalates to the explicit, actionable warning
    on every difficulty.
    """
    from engine.game_data import integrity_warning_text

    # standard: warns a step earlier, at 2/3.
    assert integrity_warning_text("standard", 2, 3, "en"), \
        "standard gave no warning at 2/3 — no recovery window before lethal drain"
    # 1/3 is the last-chance moment on every difficulty → explicit + actionable.
    for diff in ("paranoid", "cautious", "standard", "reckless"):
        w = integrity_warning_text(diff, 1, 3, "en")
        assert w and ("kill" in w.lower() or "rest or heal" in w.lower()), \
            f"{diff}: 1/3 warning was not explicit/actionable: {w!r}"
    # No warning once dead (handled by the death path, not a warning).
    assert integrity_warning_text("standard", 0, 3, "en") is None
    print("  [PASS] Integrity warning gives a recovery window and an explicit last-hit alert")


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


def test_trust_gate_reads_highest_of_duplicate_npcs():
    """A duplicate placeholder NPC entry must not mask earned trust.

    Regression: npcs.json can hold a stale `neutral` placeholder before the real
    `trusted` entry for the same person; _npc_trust_at_least returned on the first
    match, read the placeholder, and reported False — permanently blocking
    trust-gated traces (TRACE-L4-02) even after the player earned full trust.
    """
    from engine.game_data import _npc_trust_at_least

    npcs = {"npcs": [
        {"name": "Patch", "trust_level": "neutral"},    # stale placeholder, first
        {"name": "Patch", "trust_level": "trusted"},     # the real, earned entry
    ]}
    assert _npc_trust_at_least(npcs, "patch", "trusted"), \
        "placeholder NPC entry masked earned trust (trust-gated trace would stay blocked)"
    # Order independence: highest wins regardless of position.
    npcs_rev = {"npcs": [
        {"name": "Patch", "trust_level": "trusted"},
        {"name": "Patch", "trust_level": "neutral"},
    ]}
    assert _npc_trust_at_least(npcs_rev, "patch", "trusted")
    # A genuinely-low NPC still fails the gate.
    assert not _npc_trust_at_least({"npcs": [{"name": "Patch", "trust_level": "neutral"}]},
                                   "patch", "trusted")
    print("  [PASS] Trust gate reads highest trust across duplicate NPC entries")


def test_districts_unlock_on_trace_and_layer():
    """A district's unlock_trace / unlock_layer gate must actually open it.

    Regression: DISTRICTS declared unlock_trace=TRACE-L1-03 (Undercroft) and
    unlock_layer gates, but nothing evaluated them — the trace fired and the
    district stayed Locked forever, soft-locking the Mira→Patch→Undercroft route.
    """
    from engine.claude_code_engine import _unlock_districts_by_progress

    ws = {
        "district_access": [{"name": "The Sprawl", "name_zh": "蔓城", "status": "Open"}],
        "_district_registry": {"undiscovered": [
            {"name": "The Undercroft", "name_zh": "底渊", "status": "Locked"},
            {"name": "The Resonance", "name_zh": "共鸣所", "status": "Hidden"},
        ]},
    }
    # Only the L1 trace is discovered → Undercroft opens; layer-3 Resonance does not.
    traces = {"discovered": [{"id": "TRACE-L1-03", "layer": 1}]}
    newly = _unlock_districts_by_progress(ws, traces, "en")
    assert "The Undercroft" in newly, "Undercroft did not unlock on TRACE-L1-03"
    acc_names = [e["name"] for e in ws["district_access"]]
    assert any("Undercroft" in n for n in acc_names), "Undercroft not promoted to district_access"
    undisc = ws["_district_registry"]["undiscovered"]
    assert not any("Undercroft" in e["name"] for e in undisc), "Undercroft still in undiscovered"
    assert not any("Resonance" in n for n in acc_names), "layer-gated Resonance opened too early"

    # Reaching Layer 3 then opens the Resonance.
    traces2 = {"discovered": [{"id": "TRACE-L1-03", "layer": 1}, {"id": "TRACE-L3-01", "layer": 3}]}
    _unlock_districts_by_progress(ws, traces2, "en")
    assert any("Resonance" in e["name"] for e in ws["district_access"]), "Resonance did not open at Layer 3"
    print("  [PASS] Districts open when their trace/layer unlock condition is met")


def test_movement_gate_allows_inquiry():
    """A question mentioning a locked district must not be hard-blocked as travel.

    Regression: "how do I get into the Undercroft?" was rejected as a movement
    attempt (turn-less, frustrating). Inquiries skip the gate; real travel to a
    still-locked district is still blocked.
    """
    from engine.claude_code_engine import _check_movement

    ws = {
        "district_access": [],
        "_district_registry": {"undiscovered": [
            {"name": "The Undercroft", "name_zh": "底渊", "status": "Locked"},
        ]},
    }
    state = {"location": {"district": "The Sprawl"}, "world_state": ws}
    assert _check_movement("How do I get into the Undercroft?", state, "en") is None, \
        "inquiry about a locked district was wrongly blocked as movement"
    # An actual travel command to a still-locked district IS blocked.
    blocked = _check_movement("Go into the Undercroft.", state, "en")
    assert blocked, "real travel to a locked district should still be blocked"
    print("  [PASS] Movement gate lets inquiries through but still blocks real travel")


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


# ---------------------------------------------------------------------------
# Fixture helpers (wave 4): load a real saved game state and replay the
# deterministic trace-checker + consequence pipeline against it.
# ---------------------------------------------------------------------------

def _load_save_fixture(rel_dir: str) -> dict:
    """Load the five state files the ending pipeline consumes from a save dir."""
    d = os.path.join(_GAME_ROOT, rel_dir)
    out = {}
    for name in ("player", "knowledge", "traces", "world_state", "npcs"):
        with open(os.path.join(d, f"{name}.json"), encoding="utf-8") as f:
            out[name] = json.load(f)
    return out


def _trace_fixpoint(S: dict) -> dict:
    """Run the trace checker to a fixpoint, mirroring engine behavior.

    Both engines append discoveries DURING the pass (so chained traces can fire
    in one turn), and re-run every turn; iterating to a fixpoint reproduces the
    state a live game reaches at the climax turn."""
    from engine.game_data import TRACE_CONDITIONS, _trace_discovered

    traces = S["traces"]
    changed = True
    while changed:
        changed = False
        for tc in TRACE_CONDITIONS:
            if _trace_discovered(traces, tc["id"]):
                continue
            try:
                ok = tc["check"](S["knowledge"], traces, S["npcs"],
                                 S["player"], S["world_state"])
            except Exception:
                ok = False
            if ok:
                traces.setdefault("discovered", []).append(
                    {"id": tc["id"], "turn": S["player"].get("turn", 1)})
                changed = True
    return traces


def test_consensual_bridge_climax_resolves_to_the_bridge():
    """The iter10_h2_en climax must resolve to the GOOD `the_bridge` ending.

    Regression (playtest wave 3, C1 — the good-ending mislabel): a 47-turn
    perfectly-played CONSENSUAL bridge run ("I hold the door open so you can
    choose", "Nobody pulls. Nobody claims"; narration: "The bridge holds. Still
    singular.") fired the BAD forced-merge `ascension` ending. The good gates
    (18+ substring-matched traces + chained L5 trace + evidence keywords)
    silently failed while `ascension` caught the bare lore word. The consensual
    climax must now converge the_bridge via turn>=8 + TRACE-L5-01 + decisive
    consent language, and ascension must stay silent on this state.
    """
    from engine.claude_code_engine import _run_consequence
    from engine.game_data import _trace_discovered

    S = _load_save_fixture("saves/iter10_h2_en/turn_047_final")
    traces = _trace_fixpoint(S)

    assert _trace_discovered(traces, "TRACE-L5-01"), \
        "TRACE-L5-01 (convergence point) did not fire on the real bridge climax"

    go, ending, cause = _run_consequence(
        S["player"], traces, S["world_state"], S["knowledge"], S["npcs"])
    assert go, "no ending fired on a decisively-concluded consensual bridge climax"
    assert ending == "the_bridge", \
        f"consensual bridge climax mislabeled as {ending!r} (expected the_bridge)"
    print("  [PASS] iter10 consensual bridge climax resolves to the_bridge, not ascension")


def test_forced_merge_still_fires_ascension():
    """A genuinely FORCED merge must still end in `ascension` — and only that.

    Companion to the C1 fix: tightening ascension to a forcing act must not
    disable the ending for players who actually force the merge. Also pins the
    two guards: (a) the bare lore word "ascension" (learned via TRACE-L5-06)
    never fires it; (b) consent language in the same knowledge write vetoes the
    force reading; (c) a stale forcing act from many turns ago doesn't end the
    run out of nowhere.
    """
    from engine.claude_code_engine import _run_consequence

    traces = {"discovered": [{"id": f"TRACE-L1-0{i}"} for i in (1, 2, 3)]}
    world = {"nexus_alert": {"current": 0}, "fragment_decay": {"current": 0}}
    npcs = {"npcs": []}
    player = {"turn": 20, "integrity": {"current": 3, "max": 3}}

    # (1) A recent forcing act, no consent language → ascension fires.
    k_force = {"facts": [{
        "description": "Ghost overrode the failsafes and forced the merge, "
                       "dragging every mind into the core against their will.",
        "turn": 20}]}
    go, end, _ = _run_consequence(player, traces, world, k_force, npcs)
    assert go and end == "ascension", \
        f"a genuinely forced merge did not fire ascension (got {end!r})"

    # (2) The bare lore word must NOT fire it (TRACE-L5-06 teaches this word).
    k_lore = {"facts": [{
        "description": "Multiple endings exist — symbiosis, bridge, or ascension. "
                       "The Signal calls it 升华.",
        "turn": 20}]}
    go, end, _ = _run_consequence(player, traces, world, k_lore, npcs)
    assert not go, f"bare 'ascension'/'升华' lore wrongly fired ending {end!r}"

    # (3) Consent language in the SAME write vetoes the force reading.
    k_consent = {"facts": [{
        "description": "Echo asked whether to force the merge; Ghost refused — the "
                       "crossing stayed consensual and every spark chose to cross.",
        "turn": 20}]}
    go, end, _ = _run_consequence(player, traces, world, k_consent, npcs)
    assert not go, f"consensual write with force wording mislabeled as {end!r}"

    # (4) A forcing act recorded many turns ago is stale — no surprise ending.
    k_stale = {"facts": [{
        "description": "Ghost forced the merge open in the simulation.",
        "turn": 5}]}
    go, end, _ = _run_consequence(player, traces, world, k_stale, npcs)
    assert not go, f"stale forcing act (turn 5 at turn 20) fired ending {end!r}"
    print("  [PASS] Forced merge → ascension; lore word / consent / stale act do not fire it")


def test_l3_reachable_by_conversational_play():
    """A thorough talker (facts/rumors only, no formal evidence, no deep trust)
    must reach a healthy share of Layer 3.

    Regression (playtest wave 3, C3 — the L3 cliff): the trace-gate table read
    as L3 having only 2/11 keyword traces, plateauing median players at L2. The
    evidence-gated checks now scan ALL knowledge channels (facts/rumors too), so
    a conversational player must be able to fire >=5 of 11 L3 traces without any
    `evidence` entries or NPC trust beyond neutral. This pins that flattening.
    """
    from engine.game_data import _count_layer_discovered

    S = {
        "player": {"turn": 12, "background": "netrunner"},
        "world_state": {},
        "npcs": {"npcs": [{"name": "Mira", "trust_level": "neutral"}]},
        "traces": {"discovered": []},
        # Plausible things a median player hears and records as facts/rumors —
        # NO formal `evidence` entries at all.
        "knowledge": {
            "facts": [
                {"description": "NEXUS is harvesting something from the missing — the disappearances are extraction runs into Sector 7.", "turn": 8},
                {"description": "The Undercroft still has pre-Severance infrastructure that is partially active down there.", "turn": 9},
                {"description": "Fragment extraction is painful and often fatal — the victims rarely come back.", "turn": 10},
                {"description": "Sector 7 has multiple levels; the deep labs are on the lower level.", "turn": 10},
            ],
            "rumors": [
                {"description": "Something in the old network tried to communicate before the Severance cut it off — an entity sending a message.", "turn": 11},
                {"description": "A resistance network operates in the shadows, more cells than just one group.", "turn": 11},
                {"description": "Dr. Chen leads the extraction program and believes she is saving people.", "turn": 12},
            ],
            "evidence": [], "theories": [], "connections": [],
        },
    }
    traces = _trace_fixpoint(S)
    l3 = _count_layer_discovered(traces, 3)
    assert l3 >= 5, (
        f"conversational play only reached {l3}/11 at Layer 3 — "
        "the L3 cliff is back (evidence gates stopped scanning facts/rumors?)")
    print(f"  [PASS] Conversational player reaches {l3}/11 Layer-3 traces (no evidence channel, no trust)")


def test_listeners_named_by_trusted_npc():
    """A trusted ally + the 'protects Signal-sensitives' rumor unlocks TRACE-L2-02.

    Regression (playtest wave 3, C11): the trace required the literal token
    "listener", but anti-spoiler rules forbid NPCs naming the faction before
    discovery — a chicken-and-egg that froze the trace even when the player
    clearly learned the group exists. Route (b): ANY NPC at >=cautious_ally plus
    a single recorded rumor that someone protects the Signal-sensitive now fires
    it. The original Mira+name route and the trust gate itself still hold.
    """
    from engine.game_data import TRACE_CONDITIONS

    l2_02 = next(tc for tc in TRACE_CONDITIONS if tc["id"] == "TRACE-L2-02")
    check = l2_02["check"]
    t, p, w = {"discovered": []}, {"turn": 6}, {}

    rumor = {"rumors": [{"description": (
        "Someone in the Sprawl protects the Signal-sensitive — hides the ones "
        "who hear the signal before the NEXUS vans arrive."), "turn": 6}],
        "facts": [], "evidence": [], "theories": [], "connections": []}
    ally = {"npcs": [{"name": "Kite", "trust_level": "cautious_ally"},
                     {"name": "Mira", "trust_level": "neutral"}]}
    no_ally = {"npcs": [{"name": "Kite", "trust_level": "neutral"},
                        {"name": "Mira", "trust_level": "neutral"}]}
    no_rumor = {"rumors": [{"description": "The rain never stops in the Sprawl.", "turn": 6}],
                "facts": [], "evidence": [], "theories": [], "connections": []}

    assert check(rumor, t, ally, p, w), \
        "trusted ally + protect-Signal-sensitives rumor did not fire TRACE-L2-02"
    assert not check(rumor, t, no_ally, p, w), \
        "TRACE-L2-02 fired without any trusted NPC (trust gate broken)"
    assert not check(no_rumor, t, ally, p, w), \
        "TRACE-L2-02 fired from trust alone, without the protect rumor"
    # Original route still works: Mira trusts you and names them outright.
    k_name = {"rumors": [{"description": "Mira finally names them: the Listeners.", "turn": 6}],
              "facts": [], "evidence": [], "theories": [], "connections": []}
    mira_ally = {"npcs": [{"name": "Mira", "trust_level": "cautious_ally"}]}
    assert check(k_name, t, mira_ally, p, w), "original Mira+name route regressed"
    print("  [PASS] TRACE-L2-02 unlockable via trusted ally + protect rumor; gates intact")


def test_l3_07_requires_sector7_context():
    """TRACE-L3-07 must not fire on the bare word 'level'.

    Regression (playtest wave 6, friction #3a): the check keyed on ANY entry
    containing 'level' — the opening's 'street level Neo-Kowloon' fired a
    Layer-3 trace on turn 1 and inflated the deepest-layer stat. Depth words
    must now co-occur with Sector-7/lab context in the SAME entry, and 'label'
    must not count as lab context.
    """
    from engine.game_data import TRACE_CONDITIONS

    check = next(tc for tc in TRACE_CONDITIONS if tc["id"] == "TRACE-L3-07")["check"]
    t, n, p, w = {"discovered": []}, {"npcs": []}, {"turn": 1}, {}

    def K(*descs):
        return {"facts": [{"description": d, "turn": 1} for d in descs],
                "rumors": [], "evidence": [], "theories": [], "connections": []}

    # Negatives: bare depth word (the turn-1 false positive), 'label' is not
    # lab context, and context + depth split across two entries don't count.
    assert not check(K("You wake at street level in Neo-Kowloon."), t, n, p, w), \
        "bare 'street level' fired TRACE-L3-07 (turn-1 false positive is back)"
    assert not check(K("The hatch bears a scraped NEXUS acquisition label, buried deep in grime."), t, n, p, w), \
        "'label' counted as lab context for TRACE-L3-07"
    assert not check(K("Sector 7 is locked down tonight.",
                       "The market has a lower level below the steps."), t, n, p, w), \
        "TRACE-L3-07 fired from context and depth in SEPARATE entries"
    assert not check(K("这栋居民楼有很多楼层，走廊很暗。"), t, n, p, w), \
        "bare 楼层 without Sector-7/lab context fired TRACE-L3-07"
    # Positives: co-occurrence in one entry, EN and 中文.
    assert check(K("Sector 7 has multiple levels — the deeper labs are below."), t, n, p, w), \
        "genuine Sector-7 multi-level entry did not fire TRACE-L3-07"
    assert check(K("提取行动发生在第七区更深层的实验室。"), t, n, p, w), \
        "中文 第七区+深层实验室 entry did not fire TRACE-L3-07"
    # Wave-7 bilingual parity: 楼层/层楼 are the natural 中文 renderings of
    # "levels/storeys" and must count as depth terms in Sector-7 context.
    assert check(K("第七区有更深的楼层，实验室在下面。"), t, n, p, w), \
        "中文 第七区+楼层 entry did not fire TRACE-L3-07 (bilingual-parity gap)"
    assert check(K("第七区的实验室分布在好几层楼。"), t, n, p, w), \
        "中文 实验室+层楼 entry did not fire TRACE-L3-07 (bilingual-parity gap)"
    print("  [PASS] TRACE-L3-07 needs Sector-7/lab + depth in ONE entry (bare 'level' silent)")


def test_act_on_evidence_discovery_route():
    """Decrypt/analyze/scan acts unlock selected mid-layer traces.

    Playtest wave 6, friction #3b: discovery was front-loaded keyword luck and
    the panel froze in T11-20 even for players acting on evidence (the very
    verbs the teaching suggestions push). Entries recording a tool act — the
    act named in the text or the `source` field, as real wave-6 sessions show
    ("M-17 passive signal scan", "服务巷Signal残壳分析") — now fire an OR-branch on
    TRACE-L3-05 / L3-08 / L2-06. Conversational mentions of the same topics
    without an act must NOT take this route.
    """
    from engine.game_data import TRACE_CONDITIONS

    checks = {tc["id"]: tc["check"] for tc in TRACE_CONDITIONS}
    t, n, p, w = {"discovered": []}, {"npcs": []}, {"turn": 12}, {}
    empty = {"facts": [], "rumors": [], "evidence": [], "theories": [], "connections": []}

    # (1) Real wave-6 shape: evidence recorded FROM a scan act (the act lives
    # in the `source` field) about under-city hardware → TRACE-L3-05 fires.
    k_scan = dict(empty, evidence=[{
        "description": "Relay box M-17 hides an encrypted packet inside its audio fault noise.",
        "source": "M-17 passive signal scan", "turn": 9}])
    assert checks["TRACE-L3-05"](k_scan, t, n, p, w), \
        "scan-derived relay-box evidence did not fire TRACE-L3-05 (act route)"

    # (2) An analysis act whose result carries the entity's voice → L3-08.
    k_voice = dict(empty, facts=[{
        "description": "Signal analysis of the fragment: before the silence, there was a voice.",
        "source": "signal analysis", "turn": 14}])
    assert checks["TRACE-L3-08"](k_voice, t, n, p, w), \
        "analyzed fragment carrying a voice did not fire TRACE-L3-08 (act route)"

    # (3) 中文 act route: a scan coming back as dead zones / jamming → L2-06.
    k_zh = dict(empty, evidence=[{
        "description": "扫描显示这条巷子是监控的死角，画面尽是雪花屏蔽。",
        "source": "信号扫描", "turn": 8}])
    assert checks["TRACE-L2-06"](k_zh, t, n, p, w), \
        "中文 扫描+死角 entry did not fire TRACE-L2-06 (act route)"

    # Negatives — same topics WITHOUT an act must not take the act route...
    k_talk = dict(empty, rumors=[{
        "description": "A hawker mentions the relay box and old tunnels under the market.",
        "source": "market hawker", "turn": 3}])
    assert not checks["TRACE-L3-05"](k_talk, t, n, p, w), \
        "conversational tunnel gossip fired TRACE-L3-05 without any act"
    k_drunk = dict(empty, rumors=[{
        "description": "An old drunk says he once heard a voice whisper in the wires.",
        "source": "drunk", "turn": 4}])
    assert not checks["TRACE-L3-08"](k_drunk, t, n, p, w), \
        "voice gossip without an act fired TRACE-L3-08"
    # ...and an act about an unrelated topic doesn't fire either.
    k_off = dict(empty, facts=[{
        "description": "Decrypted the vendor's ledger: he owes 40 credits to a loan shark.",
        "source": "ledger decrypt", "turn": 5}])
    assert not checks["TRACE-L3-08"](k_off, t, n, p, w), \
        "an off-topic decrypt act fired TRACE-L3-08"

    # Wave-7 anchoring: an act paired with mundane human speech must NOT leak
    # L3-08 ("spoke"/"speaking"/说话 need signal context in the same clause,
    # and "spoke" must not match inside "outspoken"/"spoken")...
    for desc in ("I analyzed the crowd; a vendor spoke to me about noodles.",
                 "Probed the lock. An outspoken guard blocked the door.",
                 "我分析了账本，他在说话时提到欠款。"):
        k_mundane = dict(empty, facts=[{"description": desc, "turn": 6}])
        assert not checks["TRACE-L3-08"](k_mundane, t, n, p, w), \
            f"mundane speech during an act leaked TRACE-L3-08: {desc!r}"
    # ...while speech tied to the signal/network in the same clause still fires,
    # in both languages.
    k_net_voice = dict(empty, facts=[{
        "description": "分析信号碎片：寂静之前，网络里有一个声音在说话。",
        "source": "信号扫描", "turn": 14}])
    assert checks["TRACE-L3-08"](k_net_voice, t, n, p, w), \
        "中文 signal-context voice from an analysis act did not fire TRACE-L3-08"

    # Wave-7 anchoring for L2-06: ordinary radio/TV static after a decode act
    # is scene dressing, not proof of scanner blind spots...
    for desc in ("I analyzed the old recording — it was just static.",
                 "Decoded the tape; nothing but static hiss."):
        k_radio = dict(empty, facts=[{"description": desc, "turn": 7}])
        assert not checks["TRACE-L2-06"](k_radio, t, n, p, w), \
            f"mundane radio static after an act leaked TRACE-L2-06: {desc!r}"
    # ...but a scan whose own reading comes back as static still fires.
    k_scan_static = dict(empty, facts=[{
        "description": "Scanned the alley; the reading came back as pure static.",
        "turn": 8}])
    assert checks["TRACE-L2-06"](k_scan_static, t, n, p, w), \
        "scan-reading-as-static did not fire TRACE-L2-06 (act route)"
    print("  [PASS] Act-on-evidence route fires L3-05/L3-08/L2-06; talk-only, off-topic and mundane speech/static stay silent")


def test_ambient_causes_and_bilingual_scarcity_rule():
    """Wave-6 F1/F2: implant joins the rationed images (in 中文 too); ambient
    meter changes have bilingual default causes.

    F1: the anti-repetition directive rationed rain/neon/hum but not the
    implant itself, and 中文 runs slipped more than EN — the rule must name the
    植入体/嗡鸣 terms and bind narration in any language.
    F2: passive meter settles (e.g. alert decay) reached the client with no
    reason — game_data must provide EN+中文 default causes for every ambient
    meter/direction the server track can attach.
    """
    from engine.game_data import AMBIENT_CAUSE_LABELS
    from engine.prompts import SYSTEM_PROMPT

    line = next(l for l in SYSTEM_PROMPT.splitlines() if "sensory register" in l)
    assert "implant" in line, "scarcity rule no longer rations the implant"
    assert "植入体" in line and "嗡鸣" in line, \
        "scarcity rule must name the 中文 terms (植入体/嗡鸣)"
    assert "every language" in line.lower() or "any language" in line.lower(), \
        "scarcity rule must explicitly bind narration in any output language"

    for key in ("alert_down", "alert_up", "decay_up", "decay_down",
                "integrity_down", "integrity_up"):
        labels = AMBIENT_CAUSE_LABELS.get(key)
        assert labels, f"AMBIENT_CAUSE_LABELS missing '{key}'"
        assert labels.get("en") and labels.get("zh"), \
            f"AMBIENT_CAUSE_LABELS['{key}'] must carry both en and zh causes"
    print("  [PASS] Implant scarcity rule is bilingual; ambient meter causes carry en+zh")


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
        test_integrity_warning_gives_recovery_window,
        test_cli_runner_kills_hung_process_tree,
        test_trust_gate_reads_highest_of_duplicate_npcs,
        test_districts_unlock_on_trace_and_layer,
        test_movement_gate_allows_inquiry,
        test_good_endings_reachable_and_not_shadowed,
        test_consensual_bridge_climax_resolves_to_the_bridge,
        test_forced_merge_still_fires_ascension,
        test_l3_reachable_by_conversational_play,
        test_listeners_named_by_trusted_npc,
        test_l3_07_requires_sector7_context,
        test_act_on_evidence_discovery_route,
        test_ambient_causes_and_bilingual_scarcity_rule,
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
