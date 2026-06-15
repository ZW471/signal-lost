"""
Signal Lost — Browser GUI Backend

FastAPI + WebSocket server that interfaces with the LangGraph game engine.
Serves the static frontend and handles real-time game communication.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import sys
import threading

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# Ensure game root is on sys.path so `engine` package is importable
# ---------------------------------------------------------------------------

_GUI_DIR = os.path.dirname(os.path.abspath(__file__))
_GAME_ROOT = os.path.abspath(os.path.join(_GUI_DIR, ".."))
if _GAME_ROOT not in sys.path:
    sys.path.insert(0, _GAME_ROOT)

from langchain_core.messages import HumanMessage

from engine.graph import compile_graph, set_llm, set_fast_llm, get_llm, get_fast_llm
from engine.world_sim_scheduler import WorldSimScheduler
from engine.claude_code_engine import run_turn as cc_run_turn
from engine import action_cache
from engine import opening_cache
from engine import companion
from engine.suggestions import read_features, generate_suggested_actions
from engine.state import (
    create_new_session,
    copy_save_to_session,
    initial_state,
    list_active_sessions,
    load_session,
    save_game_to_slot,
)
from engine.llm_factory import (
    create_llm,
    default_model_for,
    load_env,
    load_settings,
    load_provider_config,
    save_env_key,
    _read_json,
    GAME_ROOT,
    SETTINGS_DIR,
    ZERO_COST_PROVIDERS,
    OAUTH_CLI_PROVIDERS,
)

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_env()

SESSION_DIR = os.path.join(GAME_ROOT, "session")
SAVES_DIR = os.path.join(GAME_ROOT, "saves")
STATIC_DIR = os.path.join(_GUI_DIR, "static")
ASSETS_DIR = os.path.join(GAME_ROOT, "assets")


def _get_langsmith_status() -> dict:
    """Return current LangSmith config (without exposing the full key)."""
    enabled = bool(os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true"
                   and os.environ.get("LANGCHAIN_API_KEY"))
    return {
        "enabled": enabled,
        "project": os.environ.get("LANGCHAIN_PROJECT", "signal_lost"),
    }


def _apply_langsmith(cfg: dict):
    """Apply LangSmith settings to environment variables."""
    api_key = cfg.get("api_key", "")
    project = cfg.get("project", "signal_lost")

    if api_key:
        os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = project or "signal_lost"
        save_env_key("LANGCHAIN_API_KEY", api_key)
        save_env_key("LANGCHAIN_TRACING_V2", "true")
        save_env_key("LANGCHAIN_PROJECT", project or "signal_lost")
    elif project:
        os.environ["LANGCHAIN_PROJECT"] = project
        save_env_key("LANGCHAIN_PROJECT", project)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Signal Lost")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
if os.path.isdir(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# ---------------------------------------------------------------------------
# Game engine state (per-server singleton for now)
# ---------------------------------------------------------------------------

_game_graph = None
_game_state = None
_game_lock = threading.Lock()
_active_session_dir: str | None = None
_world_sim_scheduler: WorldSimScheduler | None = None


_is_cli_bypass: bool = False


# --- Suggested-action outcome cache (predict_outcome feature) --------------
# In-memory map: action-hash -> {text, state_dir, result, ready}.
# Backed by speculative session snapshots under <session>/.action_cache/.
_action_cache: dict[str, dict] = {}
_action_cache_turn: int | None = None      # player turn the cache branched from
_action_cache_fp: str | None = None        # fingerprint of that base state
_predict_generation: int = 0               # bumped to invalidate in-flight work
_predict_task: "asyncio.Task | None" = None
# Guards the in-memory cache bookkeeping above. Held only for microsecond-scale
# critical sections (dict get/set, generation bump) — NEVER during disk or LLM
# work — so it cannot stall the event loop. Distinct from _game_lock, which
# serializes actual turn execution.
_cache_lock = threading.Lock()


def _setup_fast_llm(provider: str):
    """Set up a fast (haiku-class) LLM for lightweight tasks.

    Uses Anthropic haiku when the main provider has an Anthropic API key.
    Falls back to the main LLM otherwise (claude-code, codex, local, etc.).
    """
    if provider == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            fast = create_llm("anthropic", "claude-haiku-4-5-20250620")
            set_fast_llm(fast)
        except Exception:
            pass  # Fall back to main LLM
    # For other providers, fast_llm stays None → get_fast_llm() returns main LLM


def _env_var_for_provider(provider: str) -> str | None:
    """Return the env var name an API key should be written to for *provider*."""
    return {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }.get(provider)


def _build_llm_from_config(provider_cfg: dict):
    """Resolve a provider config dict into a live LLM + side-effects.

    - Stashes the API key into the right env var (and .env where relevant).
    - Builds the LLM via create_llm.
    - Registers it with the engine as the main + fast LLM.
    - Returns (provider, model, temperature) for the caller to persist.

    Mutates module globals: _is_cli_bypass.
    """
    global _is_cli_bypass

    provider = provider_cfg.get("provider", "openai")
    model = provider_cfg.get("model", default_model_for(provider))
    temperature = provider_cfg.get("temperature", 0.7)

    api_key = provider_cfg.get("api_key")
    if api_key and provider not in OAUTH_CLI_PROVIDERS and provider not in ("local", "lmstudio"):
        env_var = _env_var_for_provider(provider)
        if env_var:
            os.environ[env_var] = api_key

    extra: dict = {}
    if provider in ("lmstudio", "local"):
        extra["base_url"] = provider_cfg.get("base_url", "http://localhost:1234/v1")
    if provider == "openrouter":
        if provider_cfg.get("base_url"):
            extra["base_url"] = provider_cfg["base_url"]
    if provider not in OAUTH_CLI_PROVIDERS:
        extra["temperature"] = temperature

    llm = create_llm(provider, model, **extra)
    set_llm(llm, zero_cost=provider in ZERO_COST_PROVIDERS)
    _is_cli_bypass = provider in OAUTH_CLI_PROVIDERS
    _setup_fast_llm(provider)

    return provider, model, temperature


def _start_world_sim_scheduler(session_dir: str):
    """Create or restart the WorldSimScheduler for the active session."""
    global _world_sim_scheduler
    if _world_sim_scheduler is not None:
        _world_sim_scheduler.stop()
    _world_sim_scheduler = WorldSimScheduler(
        session_dir=session_dir,
        llm_getter=get_llm,
        game_lock=_game_lock,
    )


def _filter_hidden(obj):
    """Recursively remove any dict that contains 'hidden': True."""
    if isinstance(obj, dict):
        if obj.get("hidden") is True:
            return None
        return {k: v for k, v in ((k, _filter_hidden(v)) for k, v in obj.items()
                                   if not k.startswith("_")) if v is not None}
    if isinstance(obj, list):
        return [v for v in (_filter_hidden(x) for x in obj) if v is not None]
    return obj


def _get_session_data(session_dir: str | None = None) -> dict:
    """Read all session JSON files, filter hidden fields, and return as a dict."""
    sd = session_dir or _active_session_dir or SESSION_DIR
    data = load_session(sd)
    data = _filter_hidden(data)
    conv_path = os.path.join(sd, "conversation.jsonl")
    conversation = []
    if os.path.exists(conv_path):
        with open(conv_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        conversation.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    data["conversation"] = conversation
    # Include cumulative usage stats
    usage_path = os.path.join(sd, "usage.json")
    if os.path.exists(usage_path):
        try:
            with open(usage_path, "r", encoding="utf-8") as f:
                data["usage"] = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return data


def _list_saves() -> list[dict]:
    """List available save games, sorted newest-first by last modification time."""
    saves = []
    if os.path.isdir(SAVES_DIR):
        for name in os.listdir(SAVES_DIR):
            save_path = os.path.join(SAVES_DIR, name)
            if os.path.isdir(save_path):
                player = _read_json(os.path.join(save_path, "player.json"))
                player_file = os.path.join(save_path, "player.json")
                mtime = os.path.getmtime(player_file) if os.path.isfile(player_file) else os.path.getmtime(save_path)
                saves.append({
                    "name": name,
                    "player_name": player.get("name", "Unknown"),
                    "turn": player.get("turn", "?"),
                    "mtime": mtime,
                })
    saves.sort(key=lambda s: s["mtime"], reverse=True)
    for s in saves:
        del s["mtime"]
    return saves


# --- Auto-save -------------------------------------------------------------
AUTOSAVE_PREFIX = "autosave_"
AUTOSAVE_INTERVAL = 5   # turns
AUTOSAVE_MAX = 10       # keep at most this many autosaves; prune the oldest


def _prune_autosaves() -> None:
    """Keep at most AUTOSAVE_MAX autosaves; delete the oldest beyond that."""
    try:
        autos = []
        for name in os.listdir(SAVES_DIR):
            if name.startswith(AUTOSAVE_PREFIX):
                p = os.path.join(SAVES_DIR, name)
                if os.path.isdir(p):
                    autos.append((p, os.path.getmtime(p)))
        autos.sort(key=lambda t: t[1], reverse=True)
        for p, _ in autos[AUTOSAVE_MAX:]:
            shutil.rmtree(p, ignore_errors=True)
    except OSError:
        pass


def _maybe_autosave(session_dir: str) -> None:
    """Autosave every AUTOSAVE_INTERVAL turns, then prune to AUTOSAVE_MAX.

    Named with the turn + a timestamp so each is unique and the list stays
    chronological. Best-effort: never let a save failure break a turn.
    """
    try:
        turn = _player_turn(session_dir)
        if not isinstance(turn, int) or turn % AUTOSAVE_INTERVAL != 0:
            return
        import time as _t
        name = f"{AUTOSAVE_PREFIX}T{turn:03d}_{_t.strftime('%H%M%S')}"
        save_game_to_slot(session_dir, name, SAVES_DIR)
        _prune_autosaves()
    except Exception:
        pass


def _list_sessions() -> list[dict]:
    """List active sessions under session/."""
    return list_active_sessions(SESSION_DIR)


def _has_session() -> bool:
    """Check if any resumable sessions exist under session/."""
    return bool(_list_sessions())


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/status")
async def status():
    return {
        "has_session": _has_session(),
        "sessions": _list_sessions(),
        "saves": _list_saves(),
        "settings": load_settings(),
        "provider": load_provider_config(),
        "langsmith": _get_langsmith_status(),
    }


@app.get("/api/session")
async def session_data():
    if not _active_session_dir:
        return {"error": "No active session"}
    return _get_session_data()


# ---------------------------------------------------------------------------
# WebSocket — main game communication
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    global _game_graph, _game_state, _active_session_dir

    await ws.accept()

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            action = msg.get("action")

            if action == "init":
                await ws.send_json({
                    "type": "status",
                    "has_session": _has_session(),
                    "sessions": _list_sessions(),
                    "saves": _list_saves(),
                    "settings": load_settings(),
                    "provider": load_provider_config(),
                    "langsmith": _get_langsmith_status(),
                })

            elif action == "new_game":
                _reset_prediction()  # cancel/clear any prior session's predictions
                config = msg.get("config", {})
                provider_cfg = msg.get("provider", {})

                try:
                    provider, model, temperature = _build_llm_from_config(provider_cfg)
                except Exception as e:
                    await ws.send_json({"type": "error", "message": f"Failed to create LLM: {e}"})
                    continue

                # Save provider config (global)
                cfg_to_save = {
                    "provider": provider,
                    "model": model,
                    "temperature": temperature,
                }
                if provider_cfg.get("base_url") and provider in ("local", "lmstudio", "openrouter"):
                    cfg_to_save["base_url"] = provider_cfg["base_url"]
                with open(os.path.join(SETTINGS_DIR, "provider.json"), "w", encoding="utf-8") as f:
                    json.dump(cfg_to_save, f, indent=2)

                lang = config.get("language", "en")
                diff = config.get("difficulty", "standard")

                save_name = config.get("save_name", config.get("alias", "Unknown"))
                save_name = re.sub(r"[^\w\-]", "_", save_name)
                _active_session_dir = os.path.join(SESSION_DIR, save_name)

                # create_new_session now writes session_settings.json
                # inside the session dir (per-session difficulty + language)
                create_new_session(
                    session_dir=_active_session_dir,
                    name=config.get("name", "Unknown"),
                    alias=config.get("alias", "Unknown"),
                    background=config.get("background", "street_runner"),
                    difficulty=diff,
                    language=lang,
                )

                _game_graph = compile_graph()
                _game_state = initial_state(_active_session_dir)
                _start_world_sim_scheduler(_active_session_dir)

                await ws.send_json({
                    "type": "game_started",
                    "session": _get_session_data(),
                })

                await _run_opening(ws, lang, config.get("background", "street_runner"))

            elif action == "resume":
                _reset_prediction()  # cancel/clear any prior session's predictions
                session_name = msg.get("session_name", "")
                if not session_name:
                    await ws.send_json({"type": "error", "message": "No session_name provided."})
                    continue
                sess_path = os.path.join(SESSION_DIR, session_name)
                if not os.path.isdir(sess_path):
                    await ws.send_json({"type": "error", "message": f"Session not found: {session_name}"})
                    continue

                provider_cfg = msg.get("provider", load_provider_config())

                try:
                    _build_llm_from_config(provider_cfg)
                except Exception as e:
                    await ws.send_json({"type": "error", "message": f"Failed to create LLM: {e}"})
                    continue

                _active_session_dir = sess_path
                _game_graph = compile_graph()
                _game_state = initial_state(_active_session_dir)
                _start_world_sim_scheduler(_active_session_dir)

                await ws.send_json({
                    "type": "game_started",
                    "session": _get_session_data(),
                })

                await _run_turn(ws, mode="resume")

            elif action == "load_game":
                _reset_prediction()  # cancel/clear any prior session's predictions
                save_name = msg.get("save_name", "")
                save_path = os.path.join(SAVES_DIR, save_name)
                if not os.path.isdir(save_path):
                    await ws.send_json({"type": "error", "message": f"Save not found: {save_name}"})
                    continue

                provider_cfg = msg.get("provider", load_provider_config())

                try:
                    _build_llm_from_config(provider_cfg)
                except Exception as e:
                    await ws.send_json({"type": "error", "message": f"Failed to create LLM: {e}"})
                    continue

                _active_session_dir = os.path.join(SESSION_DIR, save_name)
                copy_save_to_session(save_path, _active_session_dir)
                _game_graph = compile_graph()
                _game_state = initial_state(_active_session_dir)
                _start_world_sim_scheduler(_active_session_dir)

                await ws.send_json({
                    "type": "game_started",
                    "session": _get_session_data(),
                })

                await _run_turn(ws, mode="resume")

            elif action == "player_input":
                text = msg.get("text", "").strip()
                if not text:
                    continue
                if _game_graph is None or _game_state is None:
                    await ws.send_json({"type": "error", "message": "No active game. Start or resume first."})
                    continue

                # Fast path: serve a pre-computed suggested-action outcome.
                # Run the lock-guarded validate+promote off the event loop so a
                # background prediction holding _game_lock can't stall the server.
                import time as _t
                _start = _t.time()
                cached = await asyncio.get_event_loop().run_in_executor(
                    None, _try_serve_cached, text
                )
                if cached is not None:
                    await ws.send_json({"type": "thinking"})
                    _reset_prediction()  # the promoted snapshot is now the live turn
                    served = {**cached, "elapsed_seconds": round(_t.time() - _start, 1)}
                    await _finish_turn(ws, served, "play", _start)
                else:
                    await _run_turn(ws, player_input=text)

            elif action == "save_game":
                save_name = msg.get("save_name", "quicksave")
                if not _active_session_dir:
                    await ws.send_json({"type": "error", "message": "No active session to save."})
                    continue
                try:
                    path = save_game_to_slot(_active_session_dir, save_name, SAVES_DIR)
                    await ws.send_json({"type": "saved", "save_name": save_name, "path": path})
                except Exception as e:
                    await ws.send_json({"type": "error", "message": f"Save failed: {e}"})

            elif action == "refresh":
                if _active_session_dir:
                    await ws.send_json({
                        "type": "session_update",
                        "session": _get_session_data(),
                    })

            elif action == "save_provider":
                provider_cfg = msg.get("provider", {})
                os.makedirs(SETTINGS_DIR, exist_ok=True)
                prov = provider_cfg.get("provider", "openai")
                cfg_to_save = {
                    "provider": prov,
                    "model": provider_cfg.get("model", default_model_for(prov)),
                    "temperature": provider_cfg.get("temperature", 0.7),
                }
                if provider_cfg.get("base_url") and prov in ("local", "lmstudio", "openrouter"):
                    cfg_to_save["base_url"] = provider_cfg["base_url"]
                with open(os.path.join(SETTINGS_DIR, "provider.json"), "w", encoding="utf-8") as f:
                    json.dump(cfg_to_save, f, indent=2)

                lang = msg.get("language")
                if lang:
                    # Update session-level language if a session is active
                    if _active_session_dir:
                        ss_path = os.path.join(_active_session_dir, "session_settings.json")
                        ss = _read_json(ss_path)
                        ss["language"] = lang
                        with open(ss_path, "w", encoding="utf-8") as f:
                            json.dump(ss, f, ensure_ascii=False, indent=2)
                    # Also update the global menu language
                    custom_path = os.path.join(SETTINGS_DIR, "custom.json")
                    custom = _read_json(custom_path)
                    custom.setdefault("language", {})
                    custom["language"]["display"] = lang
                    custom["language"]["tui"] = lang
                    with open(custom_path, "w", encoding="utf-8") as f:
                        json.dump(custom, f, ensure_ascii=False, indent=2)

                api_key = provider_cfg.get("api_key")
                if api_key and prov not in OAUTH_CLI_PROVIDERS and prov not in ("local", "lmstudio"):
                    env_var = _env_var_for_provider(prov)
                    if env_var:
                        os.environ[env_var] = api_key
                        save_env_key(env_var, api_key)

                langsmith_cfg = msg.get("langsmith")
                if langsmith_cfg:
                    _apply_langsmith(langsmith_cfg)

                # Gameplay feature toggles (suggested actions / outcome prediction)
                features = msg.get("features")
                if isinstance(features, dict):
                    # Persist globally (custom.json overrides default.json)
                    custom_path = os.path.join(SETTINGS_DIR, "custom.json")
                    custom = _read_json(custom_path)
                    custom.setdefault("features", {})
                    custom["features"].update(features)
                    with open(custom_path, "w", encoding="utf-8") as f:
                        json.dump(custom, f, ensure_ascii=False, indent=2)
                    # And per-session so it applies to the running game immediately
                    if _active_session_dir:
                        ss_path = os.path.join(_active_session_dir, "session_settings.json")
                        ss = _read_json(ss_path)
                        ss.setdefault("features", {})
                        ss["features"].update(features)
                        with open(ss_path, "w", encoding="utf-8") as f:
                            json.dump(ss, f, ensure_ascii=False, indent=2)
                    # Turning prediction off (or changing options) invalidates the cache.
                    _reset_prediction()

                await ws.send_json({
                    "type": "provider_saved",
                    "provider": cfg_to_save,
                    "langsmith": _get_langsmith_status(),
                    "features": read_features(_active_session_dir),
                })

    except WebSocketDisconnect:
        _reset_prediction()  # cancel any in-flight speculation
        if _world_sim_scheduler:
            _world_sim_scheduler.stop()
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


# ---------------------------------------------------------------------------
# WebSocket — implant companion (side-channel "ask the implant" Q&A)
# ---------------------------------------------------------------------------

@app.websocket("/ws/companion")
async def companion_endpoint(ws: WebSocket):
    """Side-channel for the player to ask questions without advancing the game.

    Deliberately a SEPARATE socket from ``/ws`` so it runs truly concurrently:
    while the main game loop is blocked awaiting a turn, this loop keeps
    receiving and can answer immediately. It is strictly read-only — it never
    takes ``_game_lock``, never mutates session state, never advances the turn,
    and never writes to the conversation log. The LLM call runs in the executor
    so it doesn't stall the event loop. Nothing is persisted server-side; the
    transcript lives only in the browser and is gone on reload.
    """
    await ws.accept()
    loop = asyncio.get_event_loop()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if msg.get("action") != "ask":
                continue

            question = (msg.get("text") or "").strip()
            if not question:
                continue

            session_dir = _active_session_dir
            if not session_dir:
                await ws.send_json({"type": "companion_reply", "error": True, "code": "no_session"})
                continue

            llm = get_llm()
            if llm is None:
                await ws.send_json({"type": "companion_reply", "error": True, "code": "no_session"})
                continue

            history = msg.get("history") or []
            try:
                answer = await loop.run_in_executor(
                    None, lambda: companion.ask(session_dir, question, history, llm)
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("companion ask failed: %s", e)
                await ws.send_json({"type": "companion_reply", "error": True, "code": "failed"})
                continue

            await ws.send_json({"type": "companion_reply", "text": answer or ""})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Suggested-action prediction cache (predict_outcome feature)
# ---------------------------------------------------------------------------

def _reset_prediction(*, clear_disk: bool = True) -> None:
    """Invalidate any cached or in-flight suggested-action predictions.

    Called whenever a real turn happens or the session changes (the predictions
    were computed from the now-superseded state). Bumping the generation counter
    makes any in-flight background task abandon its remaining work. The in-memory
    bookkeeping is mutated under ``_cache_lock`` so a background task can't write
    a stale entry into a cache we are concurrently clearing.
    """
    global _action_cache, _action_cache_turn, _action_cache_fp, _predict_generation, _predict_task
    with _cache_lock:
        _predict_generation += 1
        _action_cache = {}
        _action_cache_turn = None
        _action_cache_fp = None
    if _predict_task is not None and not _predict_task.done():
        _predict_task.cancel()
    _predict_task = None
    # Disk clear is bounded (<=4 tiny snapshot dirs) so it stays inexpensive.
    if clear_disk and _active_session_dir:
        action_cache.clear(_active_session_dir)


def _player_turn(session_dir: str) -> int | None:
    try:
        with open(os.path.join(session_dir, "player.json"), "r", encoding="utf-8") as f:
            return json.load(f).get("turn")
    except (OSError, json.JSONDecodeError):
        return None


def _session_language(session_dir: str | None) -> str:
    if not session_dir:
        return "en"
    ss = _read_json(os.path.join(session_dir, "session_settings.json"))
    return ss.get("language", "en")


def _maybe_schedule_prediction(result: dict, ws: WebSocket | None = None) -> None:
    """If predict_outcome is on, speculatively pre-compute each suggested action."""
    global _predict_task
    session_dir = _active_session_dir
    if not (_is_cli_bypass and session_dir) or result.get("game_over"):
        return
    actions = [a.get("text", "") for a in (result.get("suggested_actions") or []) if a.get("text")]
    if not actions or not read_features(session_dir)["predict_outcome"]:
        return
    try:
        # Capture session_dir now so the task can't be diverted to a different
        # session if the player switches games while it runs.
        _predict_task = asyncio.get_event_loop().create_task(
            _predict_outcomes(actions, _predict_generation, session_dir, ws)
        )
    except RuntimeError:
        pass  # no running loop


async def _predict_outcomes(action_texts: list[str], gen: int, session_dir: str,
                            ws: WebSocket | None = None) -> None:
    """Background: speculate the suggested actions, ALL IN PARALLEL.

    The base snapshot is taken once under ``_game_lock`` (so it can't tear against
    a live turn). Each action then branches from that frozen snapshot into its own
    isolated working dir and runs a full speculative turn concurrently — codex/
    claude-code spawn an independent subprocess per call, and the tools' per-turn
    context is thread-local, so parallel speculations (and the live turn) never
    interfere. Running them in parallel means all outcomes are ready in roughly
    one turn's time instead of N turns' time, which is what makes a click actually
    land on a warm cache. Cancellable via the generation counter; the click-time
    turn+fingerprint check (in _try_serve_cached) is the authoritative guard
    against serving a stale outcome.
    """
    global _action_cache_turn, _action_cache_fp
    if not session_dir:
        return
    loop = asyncio.get_event_loop()

    def _make_base():
        with _game_lock:
            if gen != _predict_generation:
                return None
            action_cache.clear(session_dir)
            base = action_cache.make_base(session_dir)
            return base, action_cache.fingerprint(session_dir), _player_turn(session_dir)

    try:
        info = await loop.run_in_executor(None, _make_base)
        if not info:
            return
        base, fp, turn = info
        with _cache_lock:
            if gen != _predict_generation:
                return
            _action_cache_fp, _action_cache_turn = fp, turn

        def _spec(text):
            # No _game_lock: operates only on its own copy of the frozen base,
            # and tool context is thread-local. Independent of the live session.
            if gen != _predict_generation:
                return None
            work_dir = action_cache.prepare_action_dir(session_dir, base, text)
            res = cc_run_turn(session_dir=work_dir, player_input=text, mode="play")
            return work_dir, res

        async def _one(text):
            try:
                outcome = await loop.run_in_executor(None, _spec, text)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("prediction failed for %r: %s", text, e)
                return
            if outcome and gen == _predict_generation:
                work_dir, res = outcome
                stored = False
                with _cache_lock:
                    if gen == _predict_generation:
                        _action_cache[action_cache.hash_action(text)] = {
                            "text": text, "state_dir": work_dir, "result": res, "ready": True,
                        }
                        stored = True
                # Tell the client this action is now instant-clickable.
                if stored and ws is not None:
                    try:
                        await ws.send_json({"type": "prediction_ready", "text": text})
                    except Exception:
                        pass

        await asyncio.gather(*[_one(t) for t in action_texts])
    except asyncio.CancelledError:
        pass


def _try_serve_cached(text: str) -> dict | None:
    """Return a pre-computed result for *text* if a valid cache hit exists.

    Confirms (under ``_game_lock``) that the live session still matches the
    snapshot the prediction branched from (same turn + fingerprint), then
    promotes that snapshot to be the live session. Returns the cached result, or
    None to fall back to a normal live turn. In-memory bookkeeping reads/writes
    are guarded by ``_cache_lock``.
    """
    session_dir = _active_session_dir
    if not (_is_cli_bypass and session_dir):
        return None
    if not read_features(session_dir)["predict_outcome"]:
        return None
    global _predict_generation
    with _cache_lock:
        entry = _action_cache.get(action_cache.hash_action(text))
        exp_turn, exp_fp = _action_cache_turn, _action_cache_fp
    if not entry or not entry.get("ready"):
        return None
    with _game_lock:
        if _player_turn(session_dir) != exp_turn:
            return None
        if action_cache.fingerprint(session_dir) != exp_fp:
            return None
        action_cache.promote(session_dir, entry["state_dir"])
    # Invalidate in-flight speculation: the live state is now the next turn.
    with _cache_lock:
        _predict_generation += 1
    return entry["result"]


async def _finish_turn(ws: WebSocket, result: dict, mode: str, turn_start: float) -> None:
    """Send a completed turn's result to the client and schedule follow-ups.

    Shared by live turns (``_run_turn``) and instant cache hits so both paths
    emit identical message sequences.
    """
    import time as _time

    narrative = result.get("narrative", "")
    game_over = result.get("game_over", False)
    ending = result.get("ending")

    if mode == "resume":
        msg_role = "system"
    elif result.get("is_warning"):
        msg_role = "warning"
    else:
        msg_role = "agent"

    turn_usage = result.get("turn_usage") or {}
    elapsed = result.get("elapsed_seconds")
    if elapsed is None:
        elapsed = round(_time.time() - turn_start, 1)

    await ws.send_json({
        "type": "narrative",
        "text": narrative,
        "game_over": game_over,
        "ending": ending,
        "role": msg_role,
        "elapsed_seconds": elapsed,
        "suggested_actions": [] if game_over else (result.get("suggested_actions") or []),
        "usage": {
            "input": turn_usage.get("input_tokens", 0),
            "output": turn_usage.get("output_tokens", 0),
            "total": turn_usage.get("total_tokens", 0),
            "cost": round(turn_usage.get("cost", 0), 6),
        } if turn_usage.get("total_tokens") else None,
    })

    for d in result.get("discovery_notifications", []) or []:
        await ws.send_json({
            "type": "discovery",
            "trace_id": d["trace_id"],
            "layer": d["layer"],
            "layer_name": d.get("layer_name", ""),
            "description": d["description"],
        })

    for kn in result.get("knowledge_notifications", []) or []:
        await ws.send_json({
            "type": "knowledge_added",
            "entry_type": kn.get("entry_type", "fact"),
        })

    # Meter-change + low-integrity notices, rendered as system lines in chat so
    # the player is fully aware of how Integrity / NEXUS Alert / Fragment Decay
    # moved this turn (from → to).
    for note in result.get("system_notices", []) or []:
        if note:
            await ws.send_json({"type": "system_notice", "text": note})

    await ws.send_json({
        "type": "session_update",
        "session": _get_session_data(),
    })

    # Auto-save on normal play turns (every N turns; pruned to a cap).
    if mode == "play" and not game_over and not result.get("is_warning") and _active_session_dir:
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, _maybe_autosave, _active_session_dir
            )
        except Exception:
            pass

    if game_over:
        await ws.send_json({
            "type": "game_over",
            "ending": ending,
            "death_cause": result.get("death_cause"),
            "narrative": narrative,
        })
        if _world_sim_scheduler:
            _world_sim_scheduler.stop()
        return

    if mode == "play" and _world_sim_scheduler:
        _world_sim_scheduler.on_player_input()

    _maybe_schedule_prediction(result, ws)


async def _run_opening(ws: WebSocket, language: str, background: str) -> None:
    """Present a new game's opening scene.

    Serves the persistent opening cache instantly (no LLM) when warm; on a cache
    miss it runs the turn-1 ``resume`` generation once and persists the result so
    every later new game of this ``(language, background)`` is instant.
    """
    import time as _time
    cached = opening_cache.load(language, background)
    if cached:
        result = {
            "narrative": cached["narrative"],
            "suggested_actions": cached.get("suggested_actions") or [],
            "game_over": False,
            "ending": None,
            "is_warning": False,
            "discovery_notifications": [],
            "knowledge_notifications": [],
            "turn_usage": {},
            "elapsed_seconds": 0.0,
        }
        await _finish_turn(ws, result, "resume", _time.time())
        return
    # Miss: generate the opening once and write it through to the cache.
    await _run_turn(ws, mode="resume", opening_key=(language, background))


async def _run_turn(ws: WebSocket, player_input: str | None = None, mode: str = "play",
                    opening_key: tuple[str, str] | None = None):
    """Run a single game turn in a background thread.

    When *opening_key* is set (new-game turn-1 only), the resulting opening scene
    is written to the persistent opening cache so subsequent new games skip it.
    """
    global _game_state

    await ws.send_json({"type": "thinking"})

    import time as _time
    _turn_start = _time.time()

    # A real turn supersedes any pending suggested-action predictions.
    _reset_prediction()

    loop = asyncio.get_event_loop()

    def _invoke():
        global _game_state
        with _game_lock:
            # --- CLI-bypass: single LLM call, pure Python post-processing ---
            # The same fast path is used by both Claude Code CLI and Codex CLI;
            # any LLM exposing _call_claude(system, user) -> str can plug in.
            # Re-check from the live LLM instance to avoid a stale flag.
            from engine.graph import get_llm as _get_current_llm
            _current_llm = _get_current_llm()
            _use_bypass = (
                _is_cli_bypass
                and _active_session_dir
                and hasattr(_current_llm, '_call_claude')
            )
            if _use_bypass:
                return cc_run_turn(
                    session_dir=_active_session_dir,
                    player_input=player_input or "",
                    mode=mode,
                )

            # --- Standard LangGraph path ---
            # Inject any pending world events from background world simulator
            if _world_sim_scheduler and mode == "play":
                pending = _world_sim_scheduler.get_pending_events()
                if pending:
                    world_section = "\n\n".join(pending)
                    _game_state["messages"].append(
                        HumanMessage(content=(
                            f"[SYSTEM: While you were away, the world moved on.]\n{world_section}"
                        ))
                    )
                    _game_state["skip_conversation_log"] = True
                    _game_state["skip_turn_increment"] = True
                    _game_state["skip_validation"] = True
                    result = _game_graph.invoke(_game_state)
                    _game_state = result

            if mode == "resume":
                player = _game_state.get("player", {})
                location = _game_state.get("location", {})
                if player.get("turn", 1) == 1:
                    # Fresh new-game opening — name-agnostic so it can be cached
                    # and reused for every new player of this (language, background).
                    resume_text = (
                        f"[SYSTEM: New game — opening scene. The player is a "
                        f"{player.get('background', '?')} at {location.get('area', '?')} in "
                        f"{location.get('district', '?')}. Turn 1. Write a brief, atmospheric "
                        f"second-person ('you') scene-setting opening. Do NOT use the player's "
                        f"name or alias or invent any proper name for them — this exact opening "
                        f"is shown to every new player of this background.]"
                    )
                else:
                    resume_text = (
                        f"[SYSTEM: Session resumed. The player is {player.get('name', 'unknown')} "
                        f"(alias: {player.get('alias', '?')}), a {player.get('background', '?')}. "
                        f"Currently at {location.get('area', '?')} in {location.get('district', '?')}. "
                        f"Turn {player.get('turn', 1)}. Provide a brief scene-setting narrative.]"
                    )
                _game_state["messages"].append(HumanMessage(content=resume_text))
                _game_state["skip_conversation_log"] = True
                _game_state["skip_turn_increment"] = True
                _game_state["skip_validation"] = True
            else:
                _game_state["messages"].append(HumanMessage(content=player_input))

            result = _game_graph.invoke(_game_state)
            _game_state = result
            return result

    try:
        result = await loop.run_in_executor(None, _invoke)

        # The CLI-bypass engine emits suggested_actions inline (no extra call).
        # The LangGraph path does not, so generate them here as a fallback.
        if (not _is_cli_bypass and not result.get("suggested_actions")
                and not result.get("game_over") and not result.get("is_warning")):
            try:
                feats = read_features(_active_session_dir)
                if feats["suggested_actions"]:
                    suggestions = await loop.run_in_executor(
                        None,
                        lambda: generate_suggested_actions(
                            _game_state,
                            result.get("narrative", ""),
                            _session_language(_active_session_dir),
                            get_fast_llm(),
                            feats["suggested_actions_count"],
                        ),
                    )
                    result["suggested_actions"] = suggestions
            except Exception:
                pass

        # Write-through the freshly generated opening so future new games of this
        # (language, background) are served instantly from cache. The cache is
        # shared across all future players of that combo, so never persist an
        # opening that embedded THIS player's name/alias. The bypass engine
        # already strips identity from the opening prompt; this is a cross-engine
        # safety net (covers the LangGraph path / any residual leak).
        if (opening_key and result.get("narrative")
                and not result.get("game_over") and not result.get("is_warning")):
            ply = (_game_state or {}).get("player", {}) if isinstance(_game_state, dict) else {}
            narr_lower = result["narrative"].lower()
            ident = [str(ply.get("name", "")).strip(), str(ply.get("alias", "")).strip()]
            leaked = any(len(tok) >= 3 and tok.lower() in narr_lower for tok in ident)
            if not leaked:
                try:
                    opening_cache.save(opening_key[0], opening_key[1],
                                       result["narrative"], result.get("suggested_actions") or [])
                except Exception:
                    pass

        await _finish_turn(ws, result, mode, _turn_start)

    except WebSocketDisconnect:
        # Client closed/reloaded the tab mid-turn — not an error. Let the
        # endpoint's disconnect handler do the cleanup (stop world sim, cancel
        # predictions). Don't try to send on the dead socket.
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            await ws.send_json({"type": "error", "message": f"Engine error: {e}"})
        except Exception:
            pass  # socket may already be gone
