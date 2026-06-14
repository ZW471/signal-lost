"""
Signal Lost — Suggested-Action Outcome Cache (filesystem helpers)

When the ``predict_outcome`` feature is on, the GUI server speculatively runs
each suggested action in an *isolated copy* of the active session directory so
that, if the player later clicks that action, the pre-computed result can be
served instantly instead of waiting ~15-30s for a fresh LLM turn.

This module provides only the pure filesystem primitives. The GUI server
(``gui/server.py``) owns the orchestration: when to speculate, generation-based
cancellation, and validating that the live session still matches the snapshot a
prediction branched from before promoting it.

Layout (all under ``<session>/.action_cache/``):
    _base/            a frozen snapshot of the session at prediction time
    <action-hash>/    the post-turn state produced by speculating one action

Only the canonical session files are copied — never ``.action_cache`` itself,
so snapshots never nest.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil

logger = logging.getLogger(__name__)

CACHE_DIRNAME = ".action_cache"
BASE_DIRNAME = "_base"

# The canonical per-session files. State files determine the fingerprint;
# conversation.jsonl + session_settings.json are copied so a promoted snapshot
# is a complete, consistent session.
_STATE_FILES = [
    "player.json", "knowledge.json", "traces.json", "location.json",
    "inventory.json", "npcs.json", "world_state.json", "log.json",
]
_COPY_FILES = _STATE_FILES + ["conversation.jsonl", "session_settings.json"]


def cache_root(session_dir: str) -> str:
    return os.path.join(session_dir, CACHE_DIRNAME)


def clear(session_dir: str) -> None:
    """Remove the entire cache directory for a session (best effort)."""
    shutil.rmtree(cache_root(session_dir), ignore_errors=True)


def _copy_files(src: str, dst: str, names: list[str]) -> None:
    os.makedirs(dst, exist_ok=True)
    for name in names:
        sp = os.path.join(src, name)
        if os.path.isfile(sp):
            shutil.copy2(sp, os.path.join(dst, name))


def hash_action(text: str) -> str:
    """Stable short id for an action's text (normalized)."""
    norm = " ".join((text or "").split()).strip().lower()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def fingerprint(session_dir: str) -> str:
    """Content hash of the live session's canonical files.

    Used to detect any divergence (e.g. background world simulation) between
    when a prediction was made and when the player clicks. Includes
    conversation.jsonl so even a logged-but-otherwise-silent change is caught.
    """
    h = hashlib.sha1()
    for name in _STATE_FILES + ["conversation.jsonl"]:
        p = os.path.join(session_dir, name)
        h.update(name.encode("utf-8"))
        try:
            with open(p, "rb") as f:
                h.update(f.read())
        except OSError:
            h.update(b"\0")
    return h.hexdigest()


def make_base(session_dir: str) -> str:
    """Freeze the current session into ``.action_cache/_base`` and return its path."""
    base = os.path.join(cache_root(session_dir), BASE_DIRNAME)
    shutil.rmtree(base, ignore_errors=True)
    _copy_files(session_dir, base, _COPY_FILES)
    return base


def prepare_action_dir(session_dir: str, base: str, action_text: str) -> str:
    """Copy the frozen base into a per-action working dir and return its path."""
    dst = os.path.join(cache_root(session_dir), hash_action(action_text))
    shutil.rmtree(dst, ignore_errors=True)
    _copy_files(base, dst, _COPY_FILES)
    return dst


def promote(session_dir: str, state_dir: str) -> None:
    """Copy a speculative post-turn state back over the live session files.

    Makes the live session become exactly what the player would have reached by
    typing that action. Does not touch ``.action_cache`` (cleared separately).
    """
    _copy_files(state_dir, session_dir, _COPY_FILES)
