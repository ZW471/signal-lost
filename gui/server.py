"""
Signal Lost — Browser GUI Backend

FastAPI + WebSocket server that interfaces with the LangGraph game engine.
Serves the static frontend and handles real-time game communication.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# Path setup — mirror what compiled/ modules expect
# ---------------------------------------------------------------------------

_GUI_DIR = os.path.dirname(os.path.abspath(__file__))
_GAME_ROOT = os.path.abspath(os.path.join(_GUI_DIR, ".."))
_COMPILED_DIR = os.path.join(_GAME_ROOT, "compiled")
_PARENT_TUI = os.path.join(_GAME_ROOT, "tui")

for p in (_COMPILED_DIR, _PARENT_TUI):
    if p not in sys.path:
        sys.path.insert(0, p)

# Load .env
_env_path = os.path.join(_GAME_ROOT, ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                if key not in os.environ:
                    os.environ[key] = val

from langchain_core.messages import HumanMessage  # noqa: E402

from graph import compile_graph, set_llm  # noqa: E402
from state import (  # noqa: E402
    create_new_session,
    copy_save_to_session,
    initial_state,
    load_session,
    save_game_to_slot,
    _read_json,
)

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------

def _save_env_key(key: str, value: str) -> None:
    """Persist an env var to the .env file."""
    lines = []
    found = False
    if os.path.exists(_env_path):
        with open(_env_path, "r") as f:
            for line in f:
                if line.strip().startswith(key + "="):
                    lines.append(f'{key}={value}\n')
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f'{key}={value}\n')
    with open(_env_path, "w") as f:
        f.writelines(lines)


SESSION_DIR = os.path.join(_GAME_ROOT, "session")
SAVES_DIR = os.path.join(_GAME_ROOT, "saves")
SETTINGS_DIR = os.path.join(_GAME_ROOT, "settings")
STATIC_DIR = os.path.join(_GUI_DIR, "static")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Signal Lost")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ---------------------------------------------------------------------------
# Game engine state (per-server singleton for now)
# ---------------------------------------------------------------------------

_game_graph = None
_game_state = None
_game_lock = threading.Lock()


def _create_llm(provider: str, model: str, **kwargs):
    """Create an LLM instance based on provider."""
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, **kwargs)
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, **kwargs)
    elif provider == "lmstudio":
        from langchain_openai import ChatOpenAI
        base_url = kwargs.pop("base_url", "http://localhost:1234/v1")
        return ChatOpenAI(model=model, base_url=base_url, api_key="lm-studio", **kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _load_settings() -> dict:
    """Load merged settings (default + custom)."""
    default = _read_json(os.path.join(SETTINGS_DIR, "default.json"))
    custom = _read_json(os.path.join(SETTINGS_DIR, "custom.json"))
    # Shallow merge
    merged = {**default}
    for k, v in custom.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = {**merged[k], **v}
        else:
            merged[k] = v
    return merged


def _load_provider_config() -> dict:
    """Load provider configuration."""
    return _read_json(os.path.join(SETTINGS_DIR, "provider.json"))


def _filter_hidden(obj):
    """Recursively remove any dict that contains 'hidden': True (matches TUI filter_hidden)."""
    if isinstance(obj, dict):
        if obj.get("hidden") is True:
            return None
        return {k: v for k, v in ((k, _filter_hidden(v)) for k, v in obj.items()
                                   if not k.startswith("_")) if v is not None}
    if isinstance(obj, list):
        return [v for v in ((_filter_hidden(x) for x in obj)) if v is not None]
    return obj


def _get_session_data() -> dict:
    """Read all session JSON files, filter hidden fields, and return as a dict."""
    data = load_session(SESSION_DIR)
    # Filter hidden fields (same as TUI's filter_hidden)
    data = _filter_hidden(data)
    # Also read conversation.jsonl
    conv_path = os.path.join(SESSION_DIR, "conversation.jsonl")
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
    return data


def _list_saves() -> list[dict]:
    """List available save games."""
    saves = []
    if os.path.isdir(SAVES_DIR):
        for name in sorted(os.listdir(SAVES_DIR)):
            save_path = os.path.join(SAVES_DIR, name)
            if os.path.isdir(save_path):
                player = _read_json(os.path.join(save_path, "player.json"))
                saves.append({
                    "name": name,
                    "player_name": player.get("name", "Unknown"),
                    "turn": player.get("turn", "?"),
                })
    return saves


def _has_session() -> bool:
    """Check if a resumable session exists."""
    return os.path.isfile(os.path.join(SESSION_DIR, "player.json"))


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
        "saves": _list_saves(),
        "settings": _load_settings(),
        "provider": _load_provider_config(),
    }


@app.get("/api/session")
async def session_data():
    if not _has_session():
        return {"error": "No active session"}
    return _get_session_data()


# ---------------------------------------------------------------------------
# WebSocket — main game communication
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    global _game_graph, _game_state

    await ws.accept()

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            action = msg.get("action")

            if action == "init":
                # Send initial status
                await ws.send_json({
                    "type": "status",
                    "has_session": _has_session(),
                    "saves": _list_saves(),
                    "settings": _load_settings(),
                    "provider": _load_provider_config(),
                })

            elif action == "new_game":
                # Start a new game
                config = msg.get("config", {})
                provider_cfg = msg.get("provider", {})

                provider = provider_cfg.get("provider", "openai")
                model = provider_cfg.get("model", "gpt-4o")
                temperature = provider_cfg.get("temperature", 0.7)

                # Set API key if provided
                api_key = provider_cfg.get("api_key")
                if api_key:
                    if provider == "anthropic":
                        os.environ["ANTHROPIC_API_KEY"] = api_key
                    elif provider == "openai":
                        os.environ["OPENAI_API_KEY"] = api_key

                # Create LLM
                extra = {}
                if provider == "lmstudio":
                    extra["base_url"] = provider_cfg.get("base_url", "http://localhost:1234/v1")

                try:
                    llm = _create_llm(provider, model, temperature=temperature, **extra)
                    set_llm(llm)
                except Exception as e:
                    await ws.send_json({"type": "error", "message": f"Failed to create LLM: {e}"})
                    continue

                # Update settings
                custom_path = os.path.join(SETTINGS_DIR, "custom.json")
                lang = config.get("language", "en")
                diff = config.get("difficulty", "standard")
                os.makedirs(SETTINGS_DIR, exist_ok=True)
                with open(custom_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "language": {"display": lang, "tui": lang},
                        "difficulty": {"mode": diff},
                    }, f, ensure_ascii=False, indent=2)

                # Save provider config
                with open(os.path.join(SETTINGS_DIR, "provider.json"), "w", encoding="utf-8") as f:
                    json.dump({
                        "provider": provider,
                        "model": model,
                        "temperature": temperature,
                    }, f, indent=2)

                # Create session
                create_new_session(
                    session_dir=SESSION_DIR,
                    name=config.get("name", "Unknown"),
                    alias=config.get("alias", "Unknown"),
                    background=config.get("background", "street_runner"),
                    difficulty=diff,
                    language=lang,
                )

                # Compile graph
                _game_graph = compile_graph()
                _game_state = initial_state(SESSION_DIR)

                # Send game started + initial state
                await ws.send_json({
                    "type": "game_started",
                    "session": _get_session_data(),
                })

                # Run resume prompt to get opening narrative
                await _run_turn(ws, mode="resume")

            elif action == "resume":
                provider_cfg = msg.get("provider", _load_provider_config())
                provider = provider_cfg.get("provider", "openai")
                model = provider_cfg.get("model", "gpt-4o")
                temperature = provider_cfg.get("temperature", 0.7)

                api_key = provider_cfg.get("api_key")
                if api_key:
                    if provider == "anthropic":
                        os.environ["ANTHROPIC_API_KEY"] = api_key
                    elif provider == "openai":
                        os.environ["OPENAI_API_KEY"] = api_key

                extra = {}
                if provider == "lmstudio":
                    extra["base_url"] = provider_cfg.get("base_url", "http://localhost:1234/v1")

                try:
                    llm = _create_llm(provider, model, temperature=temperature, **extra)
                    set_llm(llm)
                except Exception as e:
                    await ws.send_json({"type": "error", "message": f"Failed to create LLM: {e}"})
                    continue

                _game_graph = compile_graph()
                _game_state = initial_state(SESSION_DIR)

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

                provider_cfg = msg.get("provider", _load_provider_config())
                provider = provider_cfg.get("provider", "openai")
                model = provider_cfg.get("model", "gpt-4o")
                temperature = provider_cfg.get("temperature", 0.7)

                api_key = provider_cfg.get("api_key")
                if api_key:
                    if provider == "anthropic":
                        os.environ["ANTHROPIC_API_KEY"] = api_key
                    elif provider == "openai":
                        os.environ["OPENAI_API_KEY"] = api_key

                extra = {}
                if provider == "lmstudio":
                    extra["base_url"] = provider_cfg.get("base_url", "http://localhost:1234/v1")

                try:
                    llm = _create_llm(provider, model, temperature=temperature, **extra)
                    set_llm(llm)
                except Exception as e:
                    await ws.send_json({"type": "error", "message": f"Failed to create LLM: {e}"})
                    continue

                copy_save_to_session(save_path, SESSION_DIR)
                _game_graph = compile_graph()
                _game_state = initial_state(SESSION_DIR)

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
                try:
                    path = save_game_to_slot(SESSION_DIR, save_name, SAVES_DIR)
                    await ws.send_json({"type": "saved", "save_name": save_name, "path": path})
                except Exception as e:
                    await ws.send_json({"type": "error", "message": f"Save failed: {e}"})

            elif action == "refresh":
                if _has_session():
                    await ws.send_json({
                        "type": "session_update",
                        "session": _get_session_data(),
                    })

            elif action == "save_provider":
                # Save provider settings without starting a game
                provider_cfg = msg.get("provider", {})
                os.makedirs(SETTINGS_DIR, exist_ok=True)
                cfg_to_save = {
                    "provider": provider_cfg.get("provider", "openai"),
                    "model": provider_cfg.get("model", "gpt-4o"),
                    "temperature": provider_cfg.get("temperature", 0.7),
                }
                if provider_cfg.get("base_url"):
                    cfg_to_save["base_url"] = provider_cfg["base_url"]
                with open(os.path.join(SETTINGS_DIR, "provider.json"), "w", encoding="utf-8") as f:
                    json.dump(cfg_to_save, f, indent=2)

                # Save language setting to custom.json
                lang = msg.get("language")
                if lang:
                    custom_path = os.path.join(SETTINGS_DIR, "custom.json")
                    custom = _read_json(custom_path)
                    custom.setdefault("language", {})
                    custom["language"]["display"] = lang
                    custom["language"]["tui"] = lang
                    with open(custom_path, "w", encoding="utf-8") as f:
                        json.dump(custom, f, ensure_ascii=False, indent=2)

                # Set API key in env + .env file if provided
                api_key = provider_cfg.get("api_key")
                if api_key:
                    prov = provider_cfg.get("provider", "openai")
                    env_var = "ANTHROPIC_API_KEY" if prov == "anthropic" else "OPENAI_API_KEY"
                    os.environ[env_var] = api_key
                    _save_env_key(env_var, api_key)

                await ws.send_json({
                    "type": "provider_saved",
                    "provider": cfg_to_save,
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


async def _run_turn(ws: WebSocket, player_input: str | None = None, mode: str = "play"):
    """Run a single game turn in a background thread."""
    global _game_state

    await ws.send_json({"type": "thinking"})

    loop = asyncio.get_event_loop()

    def _invoke():
        global _game_state
        with _game_lock:
            if mode == "resume":
                # Build resume context
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

        await ws.send_json({
            "type": "narrative",
            "text": narrative,
            "game_over": game_over,
            "ending": ending,
            "role": "system" if mode == "resume" else "agent",
        })

        # Send updated session data
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

    except Exception as e:
        import traceback
        traceback.print_exc()
        await ws.send_json({"type": "error", "message": f"Engine error: {e}"})
