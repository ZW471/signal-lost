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

from engine.graph import compile_graph, set_llm, set_fast_llm, get_llm
from engine.world_sim_scheduler import WorldSimScheduler
from engine.claude_code_engine import run_turn as cc_run_turn
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


_is_claude_code: bool = False


def _setup_fast_llm(provider: str):
    """Set up a fast (haiku-class) LLM for lightweight tasks.

    Uses Anthropic haiku when the main provider has an Anthropic API key.
    Falls back to the main LLM otherwise (claude-code, local, etc.).
    """
    if provider == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
        try:
            fast = create_llm("anthropic", "claude-haiku-4-5-20250620")
            set_fast_llm(fast)
        except Exception:
            pass  # Fall back to main LLM
    # For other providers, fast_llm stays None → get_fast_llm() returns main LLM


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
    global _game_graph, _game_state, _active_session_dir, _is_claude_code

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
                config = msg.get("config", {})
                provider_cfg = msg.get("provider", {})

                provider = provider_cfg.get("provider", "openai")
                model = provider_cfg.get("model", default_model_for(provider))
                temperature = provider_cfg.get("temperature", 0.7)

                api_key = provider_cfg.get("api_key")
                if api_key and provider not in ("claude-code", "local", "lmstudio"):
                    if provider == "anthropic":
                        os.environ["ANTHROPIC_API_KEY"] = api_key
                    elif provider == "openai":
                        os.environ["OPENAI_API_KEY"] = api_key

                extra = {}
                if provider in ("lmstudio", "local"):
                    extra["base_url"] = provider_cfg.get("base_url", "http://localhost:1234/v1")
                if provider != "claude-code":
                    extra["temperature"] = temperature

                try:
                    llm = create_llm(provider, model, **extra)
                    set_llm(llm, zero_cost=provider in ("claude-code", "local", "lmstudio"))
                    _is_claude_code = provider == "claude-code"
                    _setup_fast_llm(provider)
                except Exception as e:
                    await ws.send_json({"type": "error", "message": f"Failed to create LLM: {e}"})
                    continue

                # Save provider config (global)
                with open(os.path.join(SETTINGS_DIR, "provider.json"), "w", encoding="utf-8") as f:
                    json.dump({
                        "provider": provider,
                        "model": model,
                        "temperature": temperature,
                    }, f, indent=2)

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

                await _run_turn(ws, mode="resume")

            elif action == "resume":
                session_name = msg.get("session_name", "")
                if not session_name:
                    await ws.send_json({"type": "error", "message": "No session_name provided."})
                    continue
                sess_path = os.path.join(SESSION_DIR, session_name)
                if not os.path.isdir(sess_path):
                    await ws.send_json({"type": "error", "message": f"Session not found: {session_name}"})
                    continue

                provider_cfg = msg.get("provider", load_provider_config())
                provider = provider_cfg.get("provider", "openai")
                model = provider_cfg.get("model", default_model_for(provider))
                temperature = provider_cfg.get("temperature", 0.7)

                api_key = provider_cfg.get("api_key")
                if api_key and provider not in ("claude-code", "local", "lmstudio"):
                    if provider == "anthropic":
                        os.environ["ANTHROPIC_API_KEY"] = api_key
                    elif provider == "openai":
                        os.environ["OPENAI_API_KEY"] = api_key

                extra = {}
                if provider in ("lmstudio", "local"):
                    extra["base_url"] = provider_cfg.get("base_url", "http://localhost:1234/v1")
                if provider != "claude-code":
                    extra["temperature"] = temperature

                try:
                    llm = create_llm(provider, model, **extra)
                    set_llm(llm, zero_cost=provider in ("claude-code", "local", "lmstudio"))
                    _is_claude_code = provider == "claude-code"
                    _setup_fast_llm(provider)
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
                save_name = msg.get("save_name", "")
                save_path = os.path.join(SAVES_DIR, save_name)
                if not os.path.isdir(save_path):
                    await ws.send_json({"type": "error", "message": f"Save not found: {save_name}"})
                    continue

                provider_cfg = msg.get("provider", load_provider_config())
                provider = provider_cfg.get("provider", "openai")
                model = provider_cfg.get("model", default_model_for(provider))
                temperature = provider_cfg.get("temperature", 0.7)

                api_key = provider_cfg.get("api_key")
                if api_key and provider not in ("claude-code", "local", "lmstudio"):
                    if provider == "anthropic":
                        os.environ["ANTHROPIC_API_KEY"] = api_key
                    elif provider == "openai":
                        os.environ["OPENAI_API_KEY"] = api_key

                extra = {}
                if provider in ("lmstudio", "local"):
                    extra["base_url"] = provider_cfg.get("base_url", "http://localhost:1234/v1")
                if provider != "claude-code":
                    extra["temperature"] = temperature

                try:
                    llm = create_llm(provider, model, **extra)
                    set_llm(llm, zero_cost=provider in ("claude-code", "local", "lmstudio"))
                    _is_claude_code = provider == "claude-code"
                    _setup_fast_llm(provider)
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
                cfg_to_save = {
                    "provider": provider_cfg.get("provider", "openai"),
                    "model": provider_cfg.get("model", default_model_for(provider_cfg.get("provider", "openai"))),
                    "temperature": provider_cfg.get("temperature", 0.7),
                }
                if provider_cfg.get("base_url"):
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
                prov = provider_cfg.get("provider", "openai")
                if api_key and prov not in ("claude-code", "local", "lmstudio"):
                    env_var = "ANTHROPIC_API_KEY" if prov == "anthropic" else "OPENAI_API_KEY"
                    os.environ[env_var] = api_key
                    save_env_key(env_var, api_key)

                langsmith_cfg = msg.get("langsmith")
                if langsmith_cfg:
                    _apply_langsmith(langsmith_cfg)

                await ws.send_json({
                    "type": "provider_saved",
                    "provider": cfg_to_save,
                    "langsmith": _get_langsmith_status(),
                })

    except WebSocketDisconnect:
        if _world_sim_scheduler:
            _world_sim_scheduler.stop()
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


async def _run_turn(ws: WebSocket, player_input: str | None = None, mode: str = "play"):
    """Run a single game turn in a background thread."""
    global _game_state

    await ws.send_json({"type": "thinking"})

    import time as _time
    _turn_start = _time.time()

    loop = asyncio.get_event_loop()

    def _invoke():
        global _game_state
        with _game_lock:
            # --- Claude-code bypass: single LLM call, pure Python post-processing ---
            # Re-check provider from the actual LLM instance to avoid stale flag
            from engine.graph import get_llm as _get_current_llm
            _current_llm = _get_current_llm()
            _actually_claude_code = (
                _is_claude_code
                and _active_session_dir
                and hasattr(_current_llm, '_call_claude')  # ClaudeCodeLLM signature
            )
            if _actually_claude_code:
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

        narrative = result.get("narrative", "")
        game_over = result.get("game_over", False)
        ending = result.get("ending")

        # Determine message role
        if mode == "resume":
            msg_role = "system"
        elif result.get("is_warning"):
            msg_role = "warning"
        else:
            msg_role = "agent"

        turn_usage = result.get("turn_usage") or {}
        elapsed = result.get("elapsed_seconds") or round(_time.time() - _turn_start, 1)
        await ws.send_json({
            "type": "narrative",
            "text": narrative,
            "game_over": game_over,
            "ending": ending,
            "role": msg_role,
            "elapsed_seconds": elapsed,
            "usage": {
                "input": turn_usage.get("input_tokens", 0),
                "output": turn_usage.get("output_tokens", 0),
                "total": turn_usage.get("total_tokens", 0),
                "cost": round(turn_usage.get("cost", 0), 6),
            } if turn_usage.get("total_tokens") else None,
        })

        # Send discovery notifications (ephemeral trace alerts)
        discoveries = result.get("discovery_notifications", [])
        if discoveries:
            for d in discoveries:
                await ws.send_json({
                    "type": "discovery",
                    "trace_id": d["trace_id"],
                    "layer": d["layer"],
                    "layer_name": d.get("layer_name", ""),
                    "description": d["description"],
                })

        # Send knowledge-added notifications (brief bottom-right toast)
        knowledge_notifs = result.get("knowledge_notifications", [])
        for kn in knowledge_notifs:
            await ws.send_json({
                "type": "knowledge_added",
                "entry_type": kn.get("entry_type", "fact"),
            })

        await ws.send_json({
            "type": "session_update",
            "session": _get_session_data(),
        })

        if game_over:
            await ws.send_json({
                "type": "game_over",
                "ending": ending,
                "narrative": narrative,
            })
            # Stop world sim on game over
            if _world_sim_scheduler:
                _world_sim_scheduler.stop()
        elif mode == "play" and _world_sim_scheduler:
            # Schedule background world simulation after player turn
            _world_sim_scheduler.on_player_input()

    except Exception as e:
        import traceback
        traceback.print_exc()
        await ws.send_json({"type": "error", "message": f"Engine error: {e}"})
