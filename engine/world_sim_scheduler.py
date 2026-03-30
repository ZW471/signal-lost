"""
Signal Lost — Background World Simulator Scheduler

Decouples the world_simulator from the synchronous turn pipeline. Instead of
running inline after every turn, world simulation fires on a timer:

    Player input  →  turn processes  →  response sent
      ↳ scheduler.on_player_input()  →  schedule sim in INTERVAL seconds

Lifecycle:
    1. Player sends input → on_player_input() → schedule sim in 5 min
    2. Timer fires → _run_sim() → NPC/world events applied → schedule next in 5 min
    3. Next timer: was there player input since last sim?
       YES → run sim, schedule again
       NO  → mark inactive, stop scheduling
    4. Next player input when inactive → re-activate, schedule sim in 5 min
"""

from __future__ import annotations

import copy
import json
import logging
import re
import threading
import time
from typing import Callable

from langchain_core.messages import HumanMessage, SystemMessage

from engine.state import load_session_file, save_session_file
from engine.llm_factory import _read_json

logger = logging.getLogger(__name__)

# Default interval between world simulation runs (seconds)
DEFAULT_INTERVAL = 300  # 5 minutes


class WorldSimScheduler:
    """Timer-based background scheduler for autonomous NPC/world simulation.

    Thread-safe. Uses ``threading.Timer`` for scheduling and an internal lock
    for state mutations.  Acquires an external ``game_lock`` (if provided)
    before writing session files so it doesn't conflict with the game engine.
    """

    def __init__(
        self,
        session_dir: str,
        llm_getter: Callable,
        *,
        interval: int = DEFAULT_INTERVAL,
        game_lock: threading.Lock | None = None,
    ):
        self._session_dir = session_dir
        self._llm_getter = llm_getter  # callable that returns the LLM instance
        self._interval = interval
        self._game_lock = game_lock or threading.Lock()

        self._timer: threading.Timer | None = None
        self._active = False
        self._last_input_time: float = 0.0
        self._last_sim_time: float = 0.0
        self._pending_events: list[str] = []
        self._lock = threading.Lock()  # protects internal state

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def on_player_input(self):
        """Called after each player turn completes.

        Marks the session as active and (re)schedules the next world sim.
        """
        with self._lock:
            self._active = True
            self._last_input_time = time.time()
            self._cancel_timer()
            self._schedule(self._interval)

    def get_pending_events(self) -> list[str]:
        """Retrieve and clear any pending visible world events.

        Call this at the start of each player turn to prepend queued events
        to the turn narrative.
        """
        with self._lock:
            events = self._pending_events[:]
            self._pending_events.clear()
            return events

    def stop(self):
        """Cancel all timers and mark inactive. Call on session end."""
        with self._lock:
            self._active = False
            self._cancel_timer()

    @property
    def active(self) -> bool:
        return self._active

    def update_session_dir(self, session_dir: str):
        """Update the session directory (e.g. after session switch)."""
        with self._lock:
            self._cancel_timer()
            self._session_dir = session_dir
            self._active = False
            self._pending_events.clear()
            self._last_input_time = 0.0
            self._last_sim_time = 0.0

    # ------------------------------------------------------------------
    # Internal scheduling
    # ------------------------------------------------------------------

    def _cancel_timer(self):
        """Cancel the current timer if running. Must hold self._lock."""
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _schedule(self, delay: float):
        """Schedule the next sim run. Must hold self._lock."""
        self._cancel_timer()
        self._timer = threading.Timer(delay, self._on_timer)
        self._timer.daemon = True
        self._timer.start()

    def _on_timer(self):
        """Timer callback: decide whether to run sim or go inactive."""
        with self._lock:
            if not self._active:
                return

            # If no player input since last sim → go inactive
            if self._last_sim_time > 0 and self._last_input_time < self._last_sim_time:
                logger.info("WorldSimScheduler: no player activity since last sim, going inactive")
                self._active = False
                return

        # Run the simulation (outside self._lock to avoid deadlock with game_lock)
        self._run_sim()

        with self._lock:
            self._last_sim_time = time.time()
            if self._active:
                self._schedule(self._interval)

    # ------------------------------------------------------------------
    # World simulation execution
    # ------------------------------------------------------------------

    def _run_sim(self):
        """Execute world simulation against the current session state.

        Acquires the game_lock to safely read/write session files.
        """
        try:
            with self._game_lock:
                visible_texts = self._execute_world_sim()

            if visible_texts:
                with self._lock:
                    self._pending_events.extend(visible_texts)
                    logger.info(
                        "WorldSimScheduler: %d visible event(s) queued",
                        len(visible_texts),
                    )
        except Exception:
            logger.exception("WorldSimScheduler: world sim failed (non-fatal)")

    def _execute_world_sim(self) -> list[str]:
        """Run the actual world simulation logic. Must hold game_lock.

        Returns a list of player-visible event text strings.
        """
        from engine.graph import _WORLD_SIM_SYSTEM, _extract_usage, _strip_thinking

        # Load current state from disk
        player = load_session_file(self._session_dir, "player")
        npcs = load_session_file(self._session_dir, "npcs")
        world_state = load_session_file(self._session_dir, "world_state")
        location = load_session_file(self._session_dir, "location")

        npc_list = npcs.get("npcs", [])
        if not npc_list:
            return []

        current_turn = player.get("turn", 1)

        # Build context snapshot
        context = {
            "current_turn": current_turn,
            "time_of_day": player.get("time", "Unknown"),
            "nexus_alert": world_state.get("nexus_alert", {}),
            "player_location": {
                "district": location.get("district", ""),
                "area": location.get("area", ""),
            },
            "npcs": [
                {
                    "name": npc.get("name", ""),
                    "location": npc.get("location", "unknown"),
                    "status": npc.get("status", "unknown"),
                    "mood": npc.get("mood", "neutral"),
                    "trust": npc.get("trust", "neutral"),
                    "role": npc.get("role", ""),
                    "last_interaction_turn": npc.get("last_interaction_turn", 0),
                    "turns_since_interaction": current_turn - npc.get("last_interaction_turn", 0),
                    "last_action": npc.get("last_action", ""),
                    "notes": npc.get("notes", ""),
                }
                for npc in npc_list
            ],
            "recent_world_events": world_state.get("global_events", [])[-3:],
        }

        # Read language setting (session_settings.json is not in SESSION_FILES)
        import os
        session_settings = _read_json(
            os.path.join(self._session_dir, "session_settings.json")
        )
        language = session_settings.get("language", "en")
        lang_note = (
            "\n\n## LANGUAGE\nAll player_text and add_event strings MUST be written in "
            "简体中文 (Simplified Chinese). Proper nouns (NEXUS, Signal, district names) may "
            "remain in English. Everything else must be Chinese."
            if language == "zh" else ""
        )

        # Call LLM
        llm = self._llm_getter()
        response = llm.invoke([
            SystemMessage(content=_WORLD_SIM_SYSTEM + lang_note),
            HumanMessage(content=json.dumps(context, ensure_ascii=False)),
        ])

        raw = response.content.strip()

        # Strip thinking tags from local models
        if "<think>" in raw:
            raw = _strip_thinking(raw)

        # Strip markdown fences
        if "```" in raw:
            raw = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()

        data = json.loads(raw)
        events = data.get("events", [])

        if not events:
            return []

        # Apply events
        npc_map = {npc.get("name", "").lower(): npc for npc in npc_list}
        player_visible_texts: list[str] = []

        for event in events:
            npc_name = event.get("npc_name")
            visible = event.get("visible_to_player", False)
            player_text = event.get("player_text")
            npc_updates = event.get("npc_updates") or {}
            world_updates = event.get("world_updates") or {}

            # Merge NPC updates
            if npc_name:
                key = npc_name.lower()
                if key in npc_map:
                    npc_map[key].update(npc_updates)
                    npc_map[key]["last_world_sim_turn"] = current_turn

            # Apply NEXUS alert delta
            delta = world_updates.get("nexus_alert_delta", 0)
            if delta:
                alert = world_state.get("nexus_alert", {})
                if isinstance(alert, dict):
                    alert["current"] = max(0, min(100, alert.get("current", 0) + delta))
                    val = alert["current"]
                    if val <= 20:
                        alert["status"], alert["status_zh"] = "Calm", "平静"
                    elif val <= 40:
                        alert["status"], alert["status_zh"] = "Watchful", "警觉"
                    elif val <= 60:
                        alert["status"], alert["status_zh"] = "Alert", "戒备"
                    elif val <= 80:
                        alert["status"], alert["status_zh"] = "Manhunt", "追捕"
                    else:
                        alert["status"], alert["status_zh"] = "Lockdown", "戒严"
                    world_state["nexus_alert"] = alert

            # Append world event string
            world_event_str = world_updates.get("add_event")
            if world_event_str:
                events_list = world_state.get("global_events", [])
                events_list.append(world_event_str)
                world_state["global_events"] = events_list

            # Collect player-visible text
            if visible and player_text:
                player_visible_texts.append(player_text)

        # Persist changes
        npcs["npcs"] = list(npc_map.values())
        save_session_file(self._session_dir, "npcs", npcs)
        save_session_file(self._session_dir, "world_state", world_state)

        return player_visible_texts
