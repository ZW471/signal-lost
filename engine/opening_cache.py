"""
Signal Lost — Persistent Opening-Scene Cache

A new game's turn-1 opening (scene-setting narrative + suggested actions) depends
only on ``(language, background)``: the starting location / points of interest /
NPCs are fixed per language, and only the starting item and rumors vary by
background. The player's typed name and alias are deliberately NOT embedded in
the opening (it is written in second person), so a single cached scene serves
every new player of that ``(language, background)`` combo.

That lets a new game skip the turn-1 LLM call entirely and present the opening
instantly. Cache files live under ``settings/openings/{language}_{background}.json``
and are committed to the repo, so a fresh checkout already ships warm openings.
The GUI server (``gui/server.py``) owns the orchestration: serve on hit, generate
once and ``save()`` on miss.
"""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

# engine/opening_cache.py -> engine/ -> game root
_GAME_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(_GAME_ROOT, "settings", "openings")


def _key(language: str, background: str) -> str:
    """Stable cache key — lowercased ``{language}_{background}``."""
    lang = (language or "en").strip().lower()
    bg = (background or "").strip().lower()
    return f"{lang}_{bg}"


def _path(language: str, background: str) -> str:
    return os.path.join(CACHE_DIR, _key(language, background) + ".json")


def load(language: str, background: str) -> dict | None:
    """Return ``{"narrative": str, "suggested_actions": [...]}`` or ``None`` on miss.

    Non-fatal: any read/parse error is treated as a cache miss so the caller
    falls back to live generation.
    """
    try:
        with open(_path(language, background), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        # OSError covers FileNotFoundError; ValueError covers json.JSONDecodeError
        # and UnicodeDecodeError — any read/parse error degrades to a cache miss.
        return None
    if not isinstance(data, dict) or not data.get("narrative"):
        return None
    sa = data.get("suggested_actions")
    return {
        "narrative": str(data["narrative"]),
        "suggested_actions": sa if isinstance(sa, list) else [],
    }


def save(language: str, background: str, narrative: str, suggested_actions: list) -> None:
    """Persist an opening scene for ``(language, background)`` (atomic write).

    Non-fatal: swallows any write error. Skips empty narratives.
    """
    if not narrative:
        return
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        payload = {
            "language": (language or "en").strip().lower(),
            "background": (background or "").strip().lower(),
            "narrative": narrative,
            "suggested_actions": suggested_actions or [],
        }
        dst = _path(language, background)
        tmp = dst + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, dst)
    except OSError as e:
        logger.warning("opening_cache: failed to save %s/%s: %s", language, background, e)
