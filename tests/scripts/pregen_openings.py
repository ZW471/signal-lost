"""
Signal Lost — Pre-generate Opening Scenes

Warms the persistent opening cache (``settings/openings/``) so a new game can
present its turn-1 scene instantly, with no LLM call. One scene is generated per
``(language, background)`` combo using the configured provider
(``settings/provider.json``). The openings are written name-agnostically (second
person, no player name/alias), so each is valid for every new player of that
combo — see ``engine/opening_cache.py``.

Usage:
    uv run tests/scripts/pregen_openings.py            # all combos
    uv run tests/scripts/pregen_openings.py --force    # regenerate even if cached
    uv run tests/scripts/pregen_openings.py --lang en  # only one language
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_GAME_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _GAME_ROOT not in sys.path:
    sys.path.insert(0, _GAME_ROOT)

from engine import opening_cache
from engine.state import BACKGROUNDS, create_new_session
from engine.claude_code_engine import run_turn as cc_run_turn
from engine.suggestions import normalize_actions, read_features
from engine.graph import set_llm
from engine.llm_factory import (
    create_llm,
    load_env,
    load_provider_config,
    default_model_for,
    OAUTH_CLI_PROVIDERS,
)

LANGUAGES = ["en", "zh"]


def _build_llm():
    cfg = load_provider_config()
    provider = cfg.get("provider", "codex")
    model = cfg.get("model", default_model_for(provider))
    extra = {}
    if provider not in OAUTH_CLI_PROVIDERS:
        extra["temperature"] = cfg.get("temperature", 0.7)
    if provider in ("lmstudio", "local", "openrouter") and cfg.get("base_url"):
        extra["base_url"] = cfg["base_url"]
    llm = create_llm(provider, model, **extra)
    set_llm(llm)
    return provider, model


def _generate(language: str, background: str, count: int) -> dict:
    """Run the turn-1 opening generation in a throwaway session."""
    tmp = tempfile.mkdtemp(prefix="sl_pregen_")
    try:
        create_new_session(
            session_dir=tmp,
            name="",            # name-agnostic: nothing to leak into the cache
            alias="",
            background=background,
            difficulty="standard",
            language=language,
        )
        result = cc_run_turn(session_dir=tmp, player_input="", mode="resume")
        narrative = (result.get("narrative") or "").strip()
        # cc_run_turn already normalized suggested_actions; re-normalize defensively.
        actions = normalize_actions(result.get("suggested_actions") or [], count)
        return {"narrative": narrative, "suggested_actions": actions}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    load_env()
    ap = argparse.ArgumentParser(description="Pre-generate Signal Lost opening scenes.")
    ap.add_argument("--force", action="store_true", help="Regenerate even if already cached.")
    ap.add_argument("--lang", choices=LANGUAGES, help="Limit to one language.")
    ap.add_argument("--background", choices=list(BACKGROUNDS.keys()), help="Limit to one background.")
    args = ap.parse_args()

    provider, model = _build_llm()
    count = read_features()["suggested_actions_count"]
    langs = [args.lang] if args.lang else LANGUAGES
    bgs = [args.background] if args.background else list(BACKGROUNDS.keys())

    print(f"Pre-generating openings via {provider}/{model} "
          f"({len(langs) * len(bgs)} combo(s), {count} actions each)\n")

    ok = 0
    for language in langs:
        for background in bgs:
            key = f"{language}/{background}"
            if not args.force and opening_cache.load(language, background):
                print(f"  [skip] {key} — already cached")
                ok += 1
                continue
            print(f"  [gen ] {key} …", flush=True)
            try:
                scene = _generate(language, background, count)
            except Exception as e:
                print(f"  [FAIL] {key}: {e}")
                continue
            if not scene["narrative"]:
                print(f"  [FAIL] {key}: empty narrative")
                continue
            opening_cache.save(language, background, scene["narrative"], scene["suggested_actions"])
            preview = scene["narrative"].replace("\n", " ")[:90]
            print(f"  [done] {key} — {len(scene['suggested_actions'])} actions · \"{preview}…\"")
            ok += 1

    total = len(langs) * len(bgs)
    print(f"\n{ok}/{total} openings ready in {opening_cache.CACHE_DIR}")
    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
