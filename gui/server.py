"""
Signal Lost — Browser GUI Backend

FastAPI + WebSocket server that interfaces with the LangGraph game engine.
Serves the static frontend and handles real-time game communication.

Multi-user model (demo-scale, < 10 concurrent players)
------------------------------------------------------
The server keeps ONE shared LLM/provider (configured server-wide — see
``_configure_llm``) but isolates everything else per signed-in user. Each live
WebSocket binds to a :class:`PlayerSession` that owns its own game state, session
directory, turn lock, world-sim scheduler and suggested-action prediction cache,
so concurrent players never touch each other's state. Sessions and saves are
namespaced on disk under ``session/<uid>/`` and ``saves/<uid>/`` (``uid`` comes
from the account store in :mod:`auth`).

One account may only be actively playing from one connection at a time. A second
sign-in is warned ("session_conflict"); if the player confirms, the older
connection is kicked.
"""

from __future__ import annotations

import asyncio
import json
import os
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

import auth
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
    save_user_provider,
    save_user_custom,
    save_env_key,
    _read_json,
    GAME_ROOT,
    SETTINGS_DIR,
    ZERO_COST_PROVIDERS,
    OAUTH_CLI_PROVIDERS,
    BYPASS_PROVIDERS,
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
# Shared server state
# ---------------------------------------------------------------------------
# The LLM/provider is a single server-wide resource (see module docstring). The
# compiled LangGraph is stateless — state flows through invoke() — so one
# instance is shared across all players. Per-player state lives on PlayerSession.

_server_graph = None
_is_cli_bypass: bool = False
_llm_configured: bool = False
_active_provider: tuple | None = None  # (provider, model, base_url) last built
_llm_lock = threading.Lock()  # guards (re)building the shared LLM


def _get_graph():
    """Return the shared, lazily-compiled (stateless) game graph."""
    global _server_graph
    if _server_graph is None:
        _server_graph = compile_graph()
    return _server_graph


# Registry of currently-active player sessions, keyed by username. Mutated only
# from the asyncio event loop (single-threaded), so a plain dict is safe.
_sessions_by_user: "dict[str, PlayerSession]" = {}


class PlayerSession:
    """All per-player runtime state for one live connection.

    Each instance is fully self-contained: its own game state, session dir, turn
    ``lock`` (serializes this player's turns and guards its world-sim writes),
    scheduler, and suggested-action prediction cache. Two PlayerSessions never
    share mutable state, so concurrent players cannot interfere.
    """

    def __init__(self, username: str, uid: str):
        self.username = username
        self.uid = uid
        self.ws: WebSocket | None = None

        self.graph = None
        self.game_state = None
        self.session_dir: str | None = None
        self.scheduler: WorldSimScheduler | None = None

        # Serializes this player's turn execution and world-sim disk writes.
        self.lock = threading.Lock()

        # --- Suggested-action prediction cache (predict_outcome feature) ---
        self.action_cache: dict[str, dict] = {}
        self.action_cache_turn: int | None = None
        self.action_cache_fp: str | None = None
        self.predict_generation: int = 0
        self.predict_task: "asyncio.Task | None" = None
        # Guards the in-memory cache bookkeeping above (microsecond critical
        # sections only — never held across disk/LLM work).
        self.cache_lock = threading.Lock()

        # --- Per-session LLM/bypass snapshot ---
        # (llm, is_cli_bypass) resolved atomically under _llm_lock at game start
        # / provider change, so a concurrent reconfigure by another player can't
        # leave this session's turn running the LLM with a mismatched bypass flag.
        # The engine reads a process-global LLM (engine.graph._llm_instance), so
        # this pair is re-snapshotted atomically at the head of each turn too.
        self.is_cli_bypass: bool = False

        # --- Reconnect resync (init) + state_delta bookkeeping ---
        # Last narrative's suggested actions, stashed when sent so a reconnecting
        # client can be re-fed them without waiting for the next input.
        self.last_suggested_actions: list[dict] = []
        # Last meter/trace/knowledge snapshot, for computing state_delta from→to.
        self.meter_snapshot: dict | None = None

    @property
    def session_root(self) -> str:
        return os.path.join(SESSION_DIR, self.uid)

    @property
    def saves_root(self) -> str:
        return os.path.join(SAVES_DIR, self.uid)


# ---------------------------------------------------------------------------
# LLM configuration (shared, server-wide)
# ---------------------------------------------------------------------------

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


def _configure_llm(provider_cfg: dict, *, persist: bool = True, uid: str | None = None):
    """(Re)build the shared server LLM from a provider config.

    Sets the engine's global LLM + fast LLM and the server-wide bypass flag, and
    (optionally) persists the choice to the *user's* per-user override (never the
    committed template). The built LLM itself is shared server-wide; persistence is
    per-user so a player's choice is remembered without touching the repo template.

    Returns (provider, model, temperature).
    """
    global _is_cli_bypass, _llm_configured, _active_provider

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

    with _llm_lock:
        llm = create_llm(provider, model, **extra)
        set_llm(llm, zero_cost=provider in ZERO_COST_PROVIDERS)
        _is_cli_bypass = provider in BYPASS_PROVIDERS
        _setup_fast_llm(provider)
        _llm_configured = True
        _active_provider = (provider, model, extra.get("base_url"))

    if persist:
        cfg = {"provider": provider, "model": model, "temperature": temperature}
        if provider_cfg.get("base_url") and provider in ("local", "lmstudio", "openrouter"):
            cfg["base_url"] = provider_cfg["base_url"]
        try:
            save_user_provider(uid, cfg)
        except OSError:
            pass

    return provider, model, temperature


def _provider_changed(provider_cfg: dict) -> bool:
    """True if *provider_cfg* selects a different provider/model/base_url than the
    currently-built LLM, or carries a fresh api_key to apply."""
    if _active_provider is None:
        return True
    provider = provider_cfg.get("provider", "openai")
    model = provider_cfg.get("model", default_model_for(provider))
    base_url = provider_cfg.get("base_url")
    if (provider, model, base_url) != _active_provider:
        return True
    return bool(provider_cfg.get("api_key"))  # a newly-entered key must take effect


def _llm_snapshot() -> tuple:
    """Atomically read (llm, is_cli_bypass) under ``_llm_lock``.

    The engine reads a process-global LLM (``engine.graph._llm_instance``) and the
    bypass decision hinges on the module-global ``_is_cli_bypass`` — both are set
    together under ``_llm_lock`` in ``_configure_llm``. Reading them together under
    the same lock guarantees a turn never sees the llm from one provider paired
    with the bypass flag of another (which a concurrent reconfigure could produce).

    Returns ``(llm_or_None, is_cli_bypass)``.
    """
    with _llm_lock:
        try:
            llm = get_llm()
        except Exception:
            llm = None
        return llm, _is_cli_bypass


def _ensure_llm(provider_cfg: dict | None = None, uid: str | None = None):
    """Ensure the shared LLM is built and reflects the requested provider.

    Builds only when needed: on first use, or when *provider_cfg* actually selects
    a different provider/model/base_url (or supplies a new api_key). This keeps the
    common case (every player on the same configured provider) from rebuilding —
    so a second player's new game can't swap the LLM out from under a player who is
    mid-turn — while still letting a provider change in Settings take effect on the
    next game start. *uid* scopes both the fallback provider load and persistence
    to the player's per-user override.
    """
    if provider_cfg is None:
        if not _llm_configured:
            _configure_llm(load_provider_config(uid=uid), persist=False, uid=uid)
        return
    if not _llm_configured or _provider_changed(provider_cfg):
        _configure_llm(provider_cfg, persist=True, uid=uid)


def _bind_session_llm(sess: PlayerSession) -> None:
    """Resolve and store this session's (llm, is_cli_bypass) snapshot atomically.

    Called right after ``_ensure_llm`` at game start / provider change so the
    session's bypass flag matches the LLM it will run with. Re-snapshotted per
    turn as well (belt-and-suspenders against a mid-turn reconfigure)."""
    _, is_bypass = _llm_snapshot()
    sess.is_cli_bypass = is_bypass


# ---------------------------------------------------------------------------
# Session data helpers
# ---------------------------------------------------------------------------

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


def _get_session_data(sess: PlayerSession) -> dict:
    """Read all of *sess*'s session JSON files, filter hidden fields, return dict."""
    sd = sess.session_dir
    if not sd:
        return {}
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
    usage_path = os.path.join(sd, "usage.json")
    if os.path.exists(usage_path):
        try:
            with open(usage_path, "r", encoding="utf-8") as f:
                data["usage"] = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return data


async def _get_session_data_async(sess: PlayerSession) -> dict:
    """Off-event-loop ``_get_session_data`` (reads + parses conversation.jsonl).

    Per-session ordering: the only writers of a session's files are the turn's
    ``_invoke`` (under ``sess.lock``) and the world-sim scheduler (also under
    ``sess.lock``). Every call site here runs *after* the writing turn's
    ``run_in_executor`` has already resolved (``_finish_turn`` / ``game_started``
    are awaited only once the invoke future completes), so an executor read never
    races a same-session write. Distinct sessions touch disjoint dirs."""
    return await asyncio.to_thread(_get_session_data, sess)


def _meter_snapshot_from_data(data: dict) -> dict:
    """Extract the three end-gating meters + discovered-trace / knowledge sets from
    a session-data blob (already spoiler-filtered by ``_get_session_data``).

    Returns plain numbers + id/title sets so consecutive snapshots diff into a
    ``state_delta``. Only *discovered* traces and *present* knowledge entries are
    counted, so nothing undiscovered leaks."""
    player = data.get("player") or {}
    world = data.get("world_state") or {}
    ig = player.get("integrity") or {}
    integ = ig.get("current") if isinstance(ig, dict) else ig
    alert = world.get("nexus_alert") or {}
    decay = world.get("fragment_decay") or {}

    trace_ids: set = set()
    layers = ((data.get("traces") or {}).get("layers") or {})
    if isinstance(layers, dict):
        for layer in layers.values():
            for tid, tr in ((layer or {}).get("traces") or {}).items():
                if isinstance(tr, dict) and tr.get("status") and tr["status"] != "undiscovered":
                    trace_ids.add(tid)

    know_titles: set = set()
    knowledge = data.get("knowledge") or {}
    for bucket in ("facts", "rumors", "evidence", "theories", "connections"):
        for entry in (knowledge.get(bucket) or []):
            if isinstance(entry, dict):
                title = entry.get("description") or entry.get("title") or entry.get("name")
                if title:
                    know_titles.add(str(title))

    return {
        "integrity": integ if isinstance(integ, (int, float)) else None,
        "nexus_alert": alert.get("current") if isinstance(alert, dict) else None,
        "fragment_decay": decay.get("current") if isinstance(decay, dict) else None,
        "trace_ids": trace_ids,
        "know_titles": know_titles,
    }


def _list_saves(saves_root: str) -> list[dict]:
    """List save games under *saves_root*, newest-first by mtime."""
    saves = []
    if os.path.isdir(saves_root):
        for name in os.listdir(saves_root):
            save_path = os.path.join(saves_root, name)
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


def _list_sessions(session_root: str) -> list[dict]:
    """List active sessions under *session_root*."""
    return list_active_sessions(session_root)


def _safe_name(name: str) -> str | None:
    """Reduce a client-supplied save/session name to a single safe path
    component. Returns None if it can't be made safe (prevents traversal into
    another user's namespace via '..' or path separators)."""
    name = (name or "").strip()
    if not name:
        return None
    name = os.path.basename(name)  # strip any directory components
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        return None
    return name


_ORIGIN_MARKER = ".origin"


def _resolve_new_session_dir(session_root: str, original_name: str) -> str | None:
    """Pick a collision-free session directory for a NEW game whose display name
    is *original_name*.

    ``_safe_name`` collapses distinct display names to the same path component
    (e.g. ``Neo!`` and ``Neo?`` → ``Neo_``). If we naively reused the sanitized
    name we'd silently overwrite another game's save. So:

    - Sanitize via ``_safe_name`` (rejecting empty / all-symbol names → None).
    - If the sanitized dir is free, take it and record the original name.
    - If it exists AND was created for the SAME original name, reuse it.
    - Otherwise suffix ``-2``, ``-3``… until a free (or same-origin) slot is found.

    Returns an absolute session dir path, or None if the name can't be made safe
    or carries no alphanumeric content (empty / all-symbol → junk dir).
    """
    base = _safe_name(original_name)
    if base is None:
        return None
    # Reject names with no alphanumeric content (e.g. "   ", "!!!") so we never
    # create junk / all-symbol session dirs. (str.isalnum handles Unicode too, so
    # Chinese display names pass.)
    if not any(ch.isalnum() for ch in base):
        return None

    def _origin_of(path: str) -> str | None:
        marker = os.path.join(path, _ORIGIN_MARKER)
        try:
            with open(marker, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None

    candidate = base
    n = 1
    while True:
        path = os.path.join(session_root, candidate)
        if not os.path.exists(path):
            return path
        # Directory exists — reuse only if it belongs to the same display name.
        # (Legacy dirs with no marker are treated as same-origin so we don't
        # orphan pre-existing saves.)
        origin = _origin_of(path)
        if origin is None or origin == original_name:
            return path
        n += 1
        candidate = f"{base}-{n}"


def _write_origin_marker(session_dir: str, original_name: str) -> None:
    """Record the display name a session dir was created for, so a later
    ``_resolve_new_session_dir`` can distinguish a collision (different display
    name sanitizing to the same path) from a legitimate reuse."""
    try:
        with open(os.path.join(session_dir, _ORIGIN_MARKER), "w", encoding="utf-8") as f:
            f.write(original_name)
    except OSError:
        pass


# --- Autosave (per-user) --------------------------------------------------
AUTOSAVE_PREFIX = "autosave_"
AUTOSAVE_INTERVAL = 5   # turns
AUTOSAVE_MAX = 10       # keep at most this many autosaves per user; prune oldest


def _prune_autosaves(saves_root: str) -> None:
    """Keep at most AUTOSAVE_MAX autosaves under *saves_root*; delete the oldest."""
    try:
        autos = []
        for name in os.listdir(saves_root):
            if name.startswith(AUTOSAVE_PREFIX):
                p = os.path.join(saves_root, name)
                if os.path.isdir(p):
                    autos.append((p, os.path.getmtime(p)))
        autos.sort(key=lambda t: t[1], reverse=True)
        for p, _ in autos[AUTOSAVE_MAX:]:
            shutil.rmtree(p, ignore_errors=True)
    except OSError:
        pass


def _maybe_autosave(session_dir: str, saves_root: str) -> None:
    """Autosave every AUTOSAVE_INTERVAL turns into *saves_root*, then prune.

    Best-effort: never let a save failure break a turn.
    """
    try:
        turn = _player_turn(session_dir)
        if not isinstance(turn, int) or turn % AUTOSAVE_INTERVAL != 0:
            return
        import time as _t
        os.makedirs(saves_root, exist_ok=True)
        name = f"{AUTOSAVE_PREFIX}T{turn:03d}_{_t.strftime('%H%M%S')}"
        save_game_to_slot(session_dir, name, saves_root)
        _prune_autosaves(saves_root)
    except Exception:
        pass


def _status_payload(sess: PlayerSession | None) -> dict:
    """Build the 'status' message — scoped to *sess*'s user, or logged-out.

    Settings/provider reflect the committed templates overlaid with this user's
    own per-user overrides (or just the templates when logged out)."""
    uid = sess.uid if sess is not None else None
    base = {
        "type": "status",
        "settings": load_settings(uid=uid),
        "provider": load_provider_config(uid=uid),
        "langsmith": _get_langsmith_status(),
    }
    if sess is None:
        base.update({"authed": False, "username": None,
                     "has_session": False, "sessions": [], "saves": []})
        return base
    sessions = _list_sessions(sess.session_root)
    saves = _list_saves(sess.saves_root)
    base.update({
        "authed": True,
        "username": sess.username,
        "has_session": bool(sessions),
        "sessions": sessions,
        "saves": saves,
    })
    return base


# ---------------------------------------------------------------------------
# Routes (HTTP)
# ---------------------------------------------------------------------------

@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/status")
async def status():
    # HTTP status is user-agnostic (the authenticated, per-user view comes over
    # the WebSocket 'init' action). Kept for health checks / compatibility.
    return _status_payload(None)


# ---------------------------------------------------------------------------
# Session binding / registry helpers (event-loop thread only)
# ---------------------------------------------------------------------------

def _unbind(sess: PlayerSession | None) -> None:
    """Detach *sess* from the active registry and stop its background work."""
    if sess is None:
        return
    _reset_prediction(sess)
    if _sessions_by_user.get(sess.username) is sess:
        del _sessions_by_user[sess.username]
    if sess.scheduler:
        sess.scheduler.stop()
    sess.ws = None


async def _kick(existing: PlayerSession) -> None:
    """Forcibly disconnect an older session for the same account."""
    old_ws = existing.ws
    _reset_prediction(existing)
    if existing.scheduler:
        existing.scheduler.stop()
    if _sessions_by_user.get(existing.username) is existing:
        del _sessions_by_user[existing.username]
    existing.ws = None
    if old_ws is not None:
        try:
            await old_ws.send_json({"type": "kicked"})
        except Exception:
            pass
        try:
            await old_ws.close()
        except Exception:
            pass


def _on_disconnect(sess: PlayerSession | None, ws: WebSocket) -> None:
    """Clean up when a bound connection drops (only if it's still the live one)."""
    if sess is None:
        return
    _reset_prediction(sess)
    # Only tear down if THIS ws is still the registered owner — a prior kick may
    # have already replaced it with a newer connection.
    if sess.ws is ws and _sessions_by_user.get(sess.username) is sess:
        del _sessions_by_user[sess.username]
        if sess.scheduler:
            sess.scheduler.stop()
        sess.ws = None


# ---------------------------------------------------------------------------
# WebSocket — main game communication
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    sess: PlayerSession | None = None  # this connection's bound player session
    loop = asyncio.get_event_loop()

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                # One malformed frame must not kill the whole connection: reply
                # with a generic bilingual error and keep the receive loop alive
                # (mirrors the companion channel's per-frame guard).
                await ws.send_json({
                    "type": "error",
                    "message": (
                        "Bad request — the message could not be read. / "
                        "请求无效——无法读取该消息。"
                    ),
                })
                continue
            # A syntactically-valid but non-object frame (e.g. `5`, `true`,
            # `"hi"`, `[]`, `null`) parses fine but has no .get — guard it so a
            # stray scalar/array frame can't AttributeError out of the loop and
            # tear down the whole connection.
            if not isinstance(msg, dict):
                await ws.send_json({
                    "type": "error",
                    "message": (
                        "Bad request — the message could not be read. / "
                        "请求无效——无法读取该消息。"
                    ),
                })
                continue
            action = msg.get("action")

            # -------------------- Auth: register / login --------------------
            if action in ("register", "login"):
                username = msg.get("username", "")
                password = msg.get("password", "")
                result = (auth.register(username, password) if action == "register"
                          else auth.login(username, password))
                if result.get("ok"):
                    await ws.send_json({
                        "type": "auth_result", "ok": True, "action": action,
                        "username": result["username"], "token": result["token"],
                    })
                else:
                    await ws.send_json({
                        "type": "auth_result", "ok": False, "action": action,
                        "error": result.get("error", "unknown"),
                    })
                continue

            # -------------------- Bind / refresh status (init) --------------------
            if action == "init":
                token = msg.get("token")
                force = bool(msg.get("force"))
                info = auth.resolve_token(token) if token else None

                if not info:
                    # Unauthenticated (no/expired token) — drop any prior binding
                    # and report the logged-out menu.
                    if sess is not None:
                        _unbind(sess)
                        sess = None
                    await ws.send_json(_status_payload(None))
                    continue

                username, uid = info["username"], info["uid"]

                # Switching identity on the same socket — release the old one.
                if sess is not None and sess.username != username:
                    _unbind(sess)
                    sess = None

                existing = _sessions_by_user.get(username)
                if existing is not None and existing.ws is not ws:
                    if not force:
                        # Another live connection already owns this account.
                        await ws.send_json({"type": "session_conflict", "username": username})
                        continue
                    await _kick(existing)

                if sess is None or sess.username != username:
                    sess = PlayerSession(username, uid)
                sess.ws = ws
                _sessions_by_user[username] = sess
                # Off-thread: _status_payload lists this user's sessions + saves
                # from disk (dir scans + player.json reads). Distinct users touch
                # disjoint namespaces, so no cross-session read/write race.
                await ws.send_json(await asyncio.to_thread(_status_payload, sess))

                # Reconnect resync: if this bound session already holds a live game
                # (same-socket re-init, or a force-kick handover), push a fresh
                # session_update + re-emit the last narrative's suggested actions so
                # the reconnecting client repaints immediately without waiting for the
                # next input. Additive — a client that ignores these loses nothing.
                if sess.game_state is not None and sess.session_dir:
                    await _safe_send(ws, {
                        "type": "session_update",
                        "session": await _get_session_data_async(sess),
                    })
                    if sess.last_suggested_actions:
                        await _safe_send(ws, {
                            "type": "suggested_actions",
                            "suggested_actions": sess.last_suggested_actions,
                        })
                continue

            # -------------------- Logout --------------------
            if action == "logout":
                token = msg.get("token")
                if token:
                    auth.logout(token)
                if sess is not None:
                    _unbind(sess)
                    sess = None
                await ws.send_json(_status_payload(None))
                continue

            # -------------------- Provider/settings (allowed logged-out) --------------------
            if action == "save_provider":
                await _handle_save_provider(ws, sess, msg)
                continue

            # -------------------- Game actions (require auth) --------------------
            if sess is None:
                await ws.send_json({"type": "auth_required"})
                continue

            if action == "new_game":
                await _handle_new_game(ws, sess, msg)

            elif action == "resume":
                await _handle_resume(ws, sess, msg)

            elif action == "load_game":
                await _handle_load_game(ws, sess, msg)

            elif action == "player_input":
                await _handle_player_input(ws, sess, msg, loop)

            elif action == "save_game":
                save_name = _safe_name(msg.get("save_name", "quicksave")) or "quicksave"
                if not sess.session_dir:
                    await ws.send_json({"type": "error", "message": "No active session to save."})
                    continue
                try:
                    os.makedirs(sess.saves_root, exist_ok=True)
                    path = save_game_to_slot(sess.session_dir, save_name, sess.saves_root)
                    await ws.send_json({"type": "saved", "save_name": save_name, "path": path})
                except Exception as e:
                    await ws.send_json({"type": "error", "message": f"Save failed: {e}"})

            elif action == "refresh":
                if sess.session_dir:
                    await ws.send_json({
                        "type": "session_update",
                        "session": await _get_session_data_async(sess),
                    })

    except WebSocketDisconnect:
        _on_disconnect(sess, ws)
    except Exception as e:
        # Log the real error + traceback server-side only; never leak raw
        # exception text to the browser.
        import logging
        import traceback
        traceback.print_exc()
        logging.getLogger(__name__).warning("websocket loop error: %s", e)
        try:
            await ws.send_json({
                "type": "error",
                "message": (
                    "Something went wrong on the server. / 服务器发生了错误。"
                ),
            })
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------

async def _handle_new_game(ws: WebSocket, sess: PlayerSession, msg: dict):
    _reset_prediction(sess)  # cancel/clear any prior game's predictions
    config = msg.get("config", {})
    provider_cfg = msg.get("provider") or load_provider_config(uid=sess.uid)

    try:
        _ensure_llm(provider_cfg, uid=sess.uid)
        _bind_session_llm(sess)
    except Exception as e:
        await ws.send_json({"type": "error", "message": f"Failed to create LLM: {e}"})
        return

    lang = config.get("language", "en")
    diff = config.get("difficulty", "standard")

    save_name = config.get("save_name", config.get("alias", "Unknown"))
    os.makedirs(sess.session_root, exist_ok=True)
    session_dir = _resolve_new_session_dir(sess.session_root, save_name)
    if session_dir is None:
        await ws.send_json({
            "type": "error",
            "message": (
                "Invalid save name — please use letters or numbers. / "
                "存档名无效——请使用字母或数字。"
            ),
        })
        return
    sess.session_dir = session_dir

    await asyncio.to_thread(
        create_new_session,
        session_dir=sess.session_dir,
        name=config.get("name", "Unknown"),
        alias=config.get("alias", "Unknown"),
        background=config.get("background", "street_runner"),
        difficulty=diff,
        language=lang,
    )
    # create_new_session rmtree's the dir, so (re)stamp the origin marker after
    # it so future new-game collision checks can tell this game's display name.
    _write_origin_marker(sess.session_dir, save_name)

    sess.graph = _get_graph()
    sess.game_state = initial_state(sess.session_dir)
    _start_world_sim_scheduler(sess)

    await _send_game_started(sess, ws)
    await _run_opening(sess, ws, lang, config.get("background", "street_runner"))


async def _handle_resume(ws: WebSocket, sess: PlayerSession, msg: dict):
    _reset_prediction(sess)
    session_name = _safe_name(msg.get("session_name", ""))
    if not session_name:
        await ws.send_json({"type": "error", "message": "No session_name provided."})
        return
    sess_path = os.path.join(sess.session_root, session_name)
    if not os.path.isdir(sess_path):
        await ws.send_json({"type": "error", "message": f"Session not found: {session_name}"})
        return

    provider_cfg = msg.get("provider") or load_provider_config(uid=sess.uid)
    try:
        _ensure_llm(provider_cfg, uid=sess.uid)
        _bind_session_llm(sess)
    except Exception as e:
        await ws.send_json({"type": "error", "message": f"Failed to create LLM: {e}"})
        return

    sess.session_dir = sess_path
    sess.graph = _get_graph()
    sess.game_state = initial_state(sess.session_dir)
    _start_world_sim_scheduler(sess)

    await _send_game_started(sess, ws, mode="resume")
    await _run_turn(sess, ws, mode="resume")


async def _handle_load_game(ws: WebSocket, sess: PlayerSession, msg: dict):
    _reset_prediction(sess)
    save_name = _safe_name(msg.get("save_name", ""))
    if not save_name:
        await ws.send_json({"type": "error", "message": "Save not found."})
        return
    save_path = os.path.join(sess.saves_root, save_name)
    if not os.path.isdir(save_path):
        await ws.send_json({"type": "error", "message": f"Save not found: {save_name}"})
        return

    provider_cfg = msg.get("provider") or load_provider_config(uid=sess.uid)
    try:
        _ensure_llm(provider_cfg, uid=sess.uid)
        _bind_session_llm(sess)
    except Exception as e:
        await ws.send_json({"type": "error", "message": f"Failed to create LLM: {e}"})
        return

    os.makedirs(sess.session_root, exist_ok=True)
    sess.session_dir = os.path.join(sess.session_root, save_name)
    await asyncio.to_thread(copy_save_to_session, save_path, sess.session_dir)
    sess.graph = _get_graph()
    sess.game_state = initial_state(sess.session_dir)
    _start_world_sim_scheduler(sess)

    await _send_game_started(sess, ws, mode="resume")
    await _run_turn(sess, ws, mode="resume")


async def _try_autoresume(ws: WebSocket, sess: PlayerSession, msg: dict) -> bool:
    """Rebind to the most-recently-played on-disk session after a reconnect.

    A dropped WebSocket tears down the in-memory PlayerSession (its game_state),
    but the on-disk session under session/<uid>/ is intact. Without this, the
    player's next action on the reconnected socket hit a dead "No active game"
    error even though their game was right there on disk. Returns True if a game
    is now live and the caller may proceed with the turn.
    """
    sessions = await asyncio.to_thread(_list_sessions, sess.session_root)
    if not sessions:
        return False
    name = sessions[0]["name"]  # most-recently-played (list is mtime-sorted)
    sess_path = os.path.join(sess.session_root, name)
    if not os.path.isdir(sess_path):
        return False
    try:
        _ensure_llm(msg.get("provider") or load_provider_config(uid=sess.uid), uid=sess.uid)
        _bind_session_llm(sess)
    except Exception:
        return False
    sess.session_dir = sess_path
    sess.graph = _get_graph()
    sess.game_state = initial_state(sess.session_dir)
    _start_world_sim_scheduler(sess)
    await _send_game_started(sess, ws, mode="resume")
    return True


async def _handle_player_input(ws: WebSocket, sess: PlayerSession, msg: dict, loop):
    text = msg.get("text", "").strip()
    if not text:
        return
    if sess.graph is None or sess.game_state is None:
        # The socket reconnected and lost its in-memory game — transparently
        # rebind to the on-disk session and continue instead of erroring out.
        if not await _try_autoresume(ws, sess, msg):
            await ws.send_json({"type": "error", "message": "No active game. Start or resume first."})
            return

    # Fast path: serve a pre-computed suggested-action outcome. Run the
    # lock-guarded validate+promote off the event loop so a background
    # prediction holding sess.lock can't stall the server.
    import time as _t
    _start = _t.time()
    cached = await loop.run_in_executor(None, _try_serve_cached, sess, text)
    if cached is not None:
        await ws.send_json({"type": "thinking"})
        _reset_prediction(sess)  # the promoted snapshot is now the live turn
        served = {**cached, "elapsed_seconds": round(_t.time() - _start, 1)}
        await _finish_turn(sess, ws, served, "play", _start)
    else:
        await _run_turn(sess, ws, player_input=text)


async def _handle_save_provider(ws: WebSocket, sess: PlayerSession | None, msg: dict):
    """Persist provider/langsmith/feature settings to the player's PER-USER
    override (never the committed templates). Allowed while logged out (writes go
    to the shared ``_local`` override). Per-game parts also apply to the active
    session.

    Does NOT rebuild the shared LLM here — that would swap the provider out from
    under any player currently mid-turn, and could lock in a keyless build. The
    new provider takes effect on the next game start, where ``_ensure_llm`` sees
    the change."""
    uid = sess.uid if sess is not None else None
    provider_cfg = msg.get("provider", {})
    prov = provider_cfg.get("provider", "openai")

    # Persist the provider choice to the per-user override (no rebuild — see docstring).
    cfg_to_save = {
        "provider": prov,
        "model": provider_cfg.get("model", default_model_for(prov)),
        "temperature": provider_cfg.get("temperature", 0.7),
    }
    if provider_cfg.get("base_url") and prov in ("local", "lmstudio", "openrouter"):
        cfg_to_save["base_url"] = provider_cfg["base_url"]

    # Snapshot the session dir once so a concurrent new_game reassignment can't
    # split these writes across two dirs.
    session_dir = sess.session_dir if sess else None
    lang = msg.get("language")
    api_key = provider_cfg.get("api_key")
    langsmith_cfg = msg.get("langsmith")
    features = msg.get("features")

    def _persist() -> None:
        # All blocking disk writes for this settings save, off the event loop. Only
        # touches per-user override files + this session's session_settings.json —
        # never the turn loop's player/knowledge/etc files — so no same-session
        # read/write race with an in-flight turn.
        save_user_provider(uid, cfg_to_save)

        if lang:
            if session_dir:
                ss_path = os.path.join(session_dir, "session_settings.json")
                ss = _read_json(ss_path)
                ss["language"] = lang
                with open(ss_path, "w", encoding="utf-8") as f:
                    json.dump(ss, f, ensure_ascii=False, indent=2)
            save_user_custom(uid, {"language": {"display": lang, "tui": lang}})

        if api_key and prov not in OAUTH_CLI_PROVIDERS and prov not in ("local", "lmstudio"):
            env_var = _env_var_for_provider(prov)
            if env_var:
                os.environ[env_var] = api_key
                save_env_key(env_var, api_key)

        if langsmith_cfg:
            _apply_langsmith(langsmith_cfg)

        if isinstance(features, dict):
            save_user_custom(uid, {"features": features})
            if session_dir:
                ss_path = os.path.join(session_dir, "session_settings.json")
                ss = _read_json(ss_path)
                ss.setdefault("features", {})
                ss["features"].update(features)
                with open(ss_path, "w", encoding="utf-8") as f:
                    json.dump(ss, f, ensure_ascii=False, indent=2)

    await asyncio.to_thread(_persist)

    # _reset_prediction cancels an asyncio task, so it must run on the event loop
    # (not inside the executor thread) once the feature writes have landed.
    if isinstance(features, dict):
        _reset_prediction(sess)

    await ws.send_json({
        "type": "provider_saved",
        "provider": cfg_to_save,
        "langsmith": _get_langsmith_status(),
        "features": await asyncio.to_thread(read_features, session_dir),
    })


# ---------------------------------------------------------------------------
# WebSocket — implant companion (side-channel "ask the implant" Q&A)
# ---------------------------------------------------------------------------

@app.websocket("/ws/companion")
async def companion_endpoint(ws: WebSocket):
    """Side-channel for the player to ask questions without advancing the game.

    Deliberately a SEPARATE socket from ``/ws`` so it runs truly concurrently.
    It is strictly read-only — never takes a turn lock, never mutates session
    state, never advances the turn, and never writes to the conversation log.
    The asking connection identifies its player via the same auth token; the
    answer is drawn from that player's active session only.
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

            token = msg.get("token")
            info = auth.resolve_token(token) if token else None
            sess = _sessions_by_user.get(info["username"]) if info else None
            # Snapshot the session dir ONCE per request into a local. A concurrent
            # new_game on the /ws socket can rmtree+reassign sess.session_dir mid-
            # request; capturing it here (and passing the local, never sess.*, into
            # the executor lambda below) pins this reply to one consistent path.
            session_dir = sess.session_dir if sess else None
            if not session_dir:
                await ws.send_json({"type": "companion_reply", "error": True, "code": "no_session"})
                continue

            try:
                llm = get_llm()
            except Exception:
                llm = None
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
# World-sim scheduler (per player)
# ---------------------------------------------------------------------------

def _start_world_sim_scheduler(sess: PlayerSession):
    """Create or restart the WorldSimScheduler for *sess*."""
    if sess.scheduler is not None:
        sess.scheduler.stop()
    sess.scheduler = WorldSimScheduler(
        session_dir=sess.session_dir,
        llm_getter=get_llm,
        game_lock=sess.lock,
    )


# ---------------------------------------------------------------------------
# Suggested-action prediction cache (predict_outcome feature) — per player
# ---------------------------------------------------------------------------

def _reset_prediction(sess: PlayerSession | None, *, clear_disk: bool = True) -> None:
    """Invalidate any cached or in-flight suggested-action predictions for *sess*."""
    if sess is None:
        return
    with sess.cache_lock:
        sess.predict_generation += 1
        sess.action_cache = {}
        sess.action_cache_turn = None
        sess.action_cache_fp = None
    if sess.predict_task is not None and not sess.predict_task.done():
        sess.predict_task.cancel()
    sess.predict_task = None
    if clear_disk and sess.session_dir:
        action_cache.clear(sess.session_dir)


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


def _maybe_schedule_prediction(sess: PlayerSession, result: dict, ws: WebSocket | None = None) -> None:
    """If predict_outcome is on, speculatively pre-compute each suggested action."""
    session_dir = sess.session_dir
    if not (sess.is_cli_bypass and session_dir) or result.get("game_over"):
        return
    actions = [a.get("text", "") for a in (result.get("suggested_actions") or []) if a.get("text")]
    if not actions or not read_features(session_dir)["predict_outcome"]:
        return
    try:
        sess.predict_task = asyncio.get_event_loop().create_task(
            _predict_outcomes(sess, actions, sess.predict_generation, session_dir, ws)
        )
    except RuntimeError:
        pass  # no running loop


async def _predict_outcomes(sess: PlayerSession, action_texts: list[str], gen: int,
                            session_dir: str, ws: WebSocket | None = None) -> None:
    """Background: speculate the suggested actions, ALL IN PARALLEL.

    The base snapshot is taken once under ``sess.lock`` (so it can't tear against
    a live turn). Each action then branches from that frozen snapshot into its own
    isolated working dir and runs a full speculative turn concurrently. Tool
    context is thread-local, so parallel speculations (and the live turn) never
    interfere. Cancellable via the per-session generation counter.
    """
    if not session_dir:
        return
    loop = asyncio.get_event_loop()

    def _make_base():
        with sess.lock:
            if gen != sess.predict_generation:
                return None
            action_cache.clear(session_dir)
            base = action_cache.make_base(session_dir)
            return base, action_cache.fingerprint(session_dir), _player_turn(session_dir)

    try:
        info = await loop.run_in_executor(None, _make_base)
        if not info:
            return
        base, fp, turn = info
        with sess.cache_lock:
            if gen != sess.predict_generation:
                return
            sess.action_cache_fp, sess.action_cache_turn = fp, turn

        def _spec(text):
            # No sess.lock: operates only on its own copy of the frozen base,
            # and tool context is thread-local. Independent of the live session.
            if gen != sess.predict_generation:
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
            if outcome and gen == sess.predict_generation:
                work_dir, res = outcome
                stored = False
                with sess.cache_lock:
                    if gen == sess.predict_generation:
                        sess.action_cache[action_cache.hash_action(text)] = {
                            "text": text, "state_dir": work_dir, "result": res, "ready": True,
                        }
                        stored = True
                if stored and ws is not None:
                    try:
                        await ws.send_json({"type": "prediction_ready", "text": text})
                    except Exception:
                        pass

        await asyncio.gather(*[_one(t) for t in action_texts])
    except asyncio.CancelledError:
        pass


def _try_serve_cached(sess: PlayerSession, text: str) -> dict | None:
    """Return a pre-computed result for *text* if a valid cache hit exists.

    Confirms (under ``sess.lock``) that the live session still matches the
    snapshot the prediction branched from (same turn + fingerprint), then
    promotes that snapshot to be the live session.
    """
    session_dir = sess.session_dir
    if not (sess.is_cli_bypass and session_dir):
        return None
    if not read_features(session_dir)["predict_outcome"]:
        return None
    with sess.cache_lock:
        entry = sess.action_cache.get(action_cache.hash_action(text))
        exp_turn, exp_fp = sess.action_cache_turn, sess.action_cache_fp
    if not entry or not entry.get("ready"):
        return None
    with sess.lock:
        if _player_turn(session_dir) != exp_turn:
            return None
        if action_cache.fingerprint(session_dir) != exp_fp:
            return None
        action_cache.promote(session_dir, entry["state_dir"])
    with sess.cache_lock:
        sess.predict_generation += 1
    return entry["result"]


# ---------------------------------------------------------------------------
# Turn execution
# ---------------------------------------------------------------------------

def _ws_connected(ws: WebSocket) -> bool:
    """Best-effort check that *ws* is still open before we try to send on it."""
    try:
        from starlette.websockets import WebSocketState
        return (ws.client_state == WebSocketState.CONNECTED
                and ws.application_state == WebSocketState.CONNECTED)
    except Exception:
        # If the state enum isn't available for any reason, assume connected and
        # let the guarded send catch a failure.
        return True


async def _safe_send(ws: WebSocket, payload: dict) -> bool:
    """Send *payload* on *ws*, swallowing failures from a dead/closing socket.

    Returns True if the send succeeded, False otherwise — so a dead socket can
    never crash the turn finalizer (a raw send would bubble up into the WS loop's
    outer handler and tear down the connection).
    """
    if not _ws_connected(ws):
        return False
    try:
        await ws.send_json(payload)
        return True
    except Exception:
        return False


async def _send_game_started(sess: PlayerSession, ws: WebSocket, mode: str = "new") -> None:
    """Send the ``game_started`` blob (session data read off-thread) and seed the
    meter snapshot so the first turn's ``state_delta`` diffs from a real baseline.

    ``mode`` is ``"new"`` for a fresh game and ``"resume"`` for resume / load /
    autoresume. The client uses it to decide whether to wipe the session-scoped
    companion transcript (only on ``"new"``); resuming the SAME session must keep
    the just-restored aside. Additive — old clients ignore the extra field."""
    data = await _get_session_data_async(sess)
    sess.meter_snapshot = _meter_snapshot_from_data(data)
    await ws.send_json({"type": "game_started", "session": data, "mode": mode})


def _build_state_delta(prev: dict | None, cur: dict,
                       reasons: dict | None = None) -> dict | None:
    """Repackage the meter/trace/knowledge diff between two snapshots as numbers.

    Additive companion to ``session_update``; old clients ignore the ``state_delta``
    type. Returns None when there is no prior snapshot to diff against.

    *reasons* (optional) carries the in-world cause the resolver gave for any meter
    that moved, as ``{alert?:{en,zh}, integrity?:{en,zh}, decay?:{en,zh}}``. Only
    reasons whose meter actually changed this turn are forwarded, so a stale/omitted
    reason never mislabels a static meter."""
    if prev is None:
        return None

    def _pair(key):
        return {"from": prev.get(key), "to": cur.get(key)}

    traces_added = sorted((cur.get("trace_ids") or set()) - (prev.get("trace_ids") or set()))
    knowledge_added = sorted((cur.get("know_titles") or set()) - (prev.get("know_titles") or set()))

    delta = {
        "type": "state_delta",
        "integrity": _pair("integrity"),
        "nexus_alert": _pair("nexus_alert"),
        "fragment_decay": _pair("fragment_decay"),
        "traces_added": traces_added,
        "knowledge_added": knowledge_added,
    }

    # Attach reasons only for meters that actually moved (guards against a reason
    # the model supplied for a delta that got clamped to no-op).
    if reasons:
        out_reasons: dict = {}
        _meter_key = {"alert": "nexus_alert", "integrity": "integrity", "decay": "fragment_decay"}
        for meter, payload in reasons.items():
            snap_key = _meter_key.get(meter)
            if not snap_key or not isinstance(payload, dict):
                continue
            pair = delta[snap_key]
            if pair["from"] != pair["to"] and (payload.get("en") or payload.get("zh")):
                out_reasons[meter] = {"en": payload.get("en") or payload.get("zh"),
                                      "zh": payload.get("zh") or payload.get("en")}
        if out_reasons:
            delta["reasons"] = out_reasons

    return delta


async def _finish_turn(sess: PlayerSession, ws: WebSocket, result: dict, mode: str,
                       turn_start: float) -> None:
    """Send a completed turn's result to the client and schedule follow-ups."""
    import time as _time

    # If this session is no longer the live one (the player logged out, was
    # kicked, or disconnected mid-turn), drop the result: don't write to a dead
    # socket or reactivate a torn-down scheduler / prediction for a stale session.
    if sess.ws is not ws or _sessions_by_user.get(sess.username) is not sess:
        return
    # A dead-but-still-registered socket (e.g. cached fast-path where the client
    # went away between frames) must not crash the finalizer — bail before send.
    if not _ws_connected(ws):
        return

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

    # Stash the actions actually shown so a reconnecting client (init resync) can
    # repaint the quick-action buttons without waiting for the next input.
    shown_actions = [] if game_over else (result.get("suggested_actions") or [])
    sess.last_suggested_actions = shown_actions

    # Roll beat: if the resolver used the dice/cipher/signal mechanic tools this
    # turn, surface an additive 'roll' frame BEFORE the narrative so the client can
    # animate the check. Drained per turn from the tools module buffer; in-world
    # safe (only names the skill/method the player just attempted). Old clients
    # ignore the unknown type. Stash the reasons here too (drained together) for the
    # state_delta below.
    turn_reasons: dict = {}
    if sess.session_dir:
        try:
            from engine.tools import drain_rolls, drain_reasons
            rolls = await asyncio.to_thread(drain_rolls, sess.session_dir)
            turn_reasons = await asyncio.to_thread(drain_reasons, sess.session_dir)
            if rolls and not game_over:
                await _safe_send(ws, {"type": "roll", "rolls": rolls})
        except Exception:
            pass

    if not await _safe_send(ws, {
        "type": "narrative",
        "text": narrative,
        "game_over": game_over,
        "ending": ending,
        "role": msg_role,
        "elapsed_seconds": elapsed,
        "suggested_actions": shown_actions,
        "usage": {
            "input": turn_usage.get("input_tokens", 0),
            "output": turn_usage.get("output_tokens", 0),
            "total": turn_usage.get("total_tokens", 0),
            "cost": round(turn_usage.get("cost", 0), 6),
        } if turn_usage.get("total_tokens") else None,
    }):
        # Socket died on the primary send — nothing more to deliver.
        return

    for d in result.get("discovery_notifications", []) or []:
        await _safe_send(ws, {
            "type": "discovery",
            "trace_id": d["trace_id"],
            "layer": d["layer"],
            "layer_name": d.get("layer_name", ""),
            "description": d["description"],
        })

    for kn in result.get("knowledge_notifications", []) or []:
        await _safe_send(ws, {
            "type": "knowledge_added",
            "entry_type": kn.get("entry_type", "fact"),
        })

    # Meter-change + low-integrity notices, rendered as system lines in chat so
    # the player sees how Integrity / NEXUS Alert / Fragment Decay moved this turn.
    for note in result.get("system_notices", []) or []:
        if note:
            await _safe_send(ws, {"type": "system_notice", "text": note})

    session_data = await _get_session_data_async(sess)
    await _safe_send(ws, {
        "type": "session_update",
        "session": session_data,
    })

    # state_delta: repackage the meter/trace/knowledge move as numbers, alongside
    # session_update. Additive — old clients ignore the type. The snapshot always
    # advances (even when the delta is suppressed) so the next turn diffs cleanly.
    cur_snapshot = _meter_snapshot_from_data(session_data)
    if mode != "resume":
        delta = _build_state_delta(sess.meter_snapshot, cur_snapshot, turn_reasons)
        if delta is not None:
            await _safe_send(ws, delta)
    sess.meter_snapshot = cur_snapshot

    # Auto-save on normal play turns (every N turns; pruned to a cap), per user.
    if mode == "play" and not game_over and not result.get("is_warning") and sess.session_dir:
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, _maybe_autosave, sess.session_dir, sess.saves_root
            )
        except Exception:
            pass

    if game_over:
        await _safe_send(ws, {
            "type": "game_over",
            "ending": ending,
            "death_cause": result.get("death_cause"),
            "narrative": narrative,
        })
        if sess.scheduler:
            sess.scheduler.stop()
        return

    if mode == "play" and sess.scheduler:
        sess.scheduler.on_player_input()

    _maybe_schedule_prediction(sess, result, ws)


# Substrings that mark a transient CLI/network stream drop worth retrying (as
# opposed to a content/auth/logic error, which won't get better on a retry).
_TRANSIENT_CLI_MARKERS = (
    "tls handshake eof", "handshake eof", "connection reset", "connection refused",
    "connection aborted", "connection closed", "broken pipe", "reconnecting",
    "timed out", "timeout", "temporarily unavailable", "eof occurred",
    "stream closed", "stream disconnected", "network is unreachable",
    "read timed out", "remote end closed",
)


def _is_transient_cli_error(err: BaseException) -> bool:
    """True if *err* looks like a transient CLI/network stream drop (safe to retry)."""
    msg = str(err).lower()
    return any(marker in msg for marker in _TRANSIENT_CLI_MARKERS)


async def _run_opening(sess: PlayerSession, ws: WebSocket, language: str, background: str) -> None:
    """Present a new game's opening scene (served from the persistent cache when warm)."""
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
        await _finish_turn(sess, ws, result, "resume", _time.time())
        return
    await _run_turn(sess, ws, mode="resume", opening_key=(language, background))


async def _run_turn(sess: PlayerSession, ws: WebSocket, player_input: str | None = None,
                    mode: str = "play", opening_key: tuple[str, str] | None = None):
    """Run a single game turn for *sess* in a background thread."""
    await ws.send_json({"type": "thinking"})

    import time as _time
    _turn_start = _time.time()

    # A real turn supersedes any pending suggested-action predictions.
    _reset_prediction(sess)

    loop = asyncio.get_event_loop()

    def _invoke():
        with sess.lock:
            # --- CLI-bypass: single LLM call, pure Python post-processing ---
            # Snapshot (llm, is_cli_bypass) atomically so a concurrent provider
            # reconfigure by another player can't pair this turn's LLM with a
            # mismatched bypass flag. Refresh the session's flag from the same
            # atomic read (the engine reads a process-global LLM).
            _current_llm, _bypass = _llm_snapshot()
            sess.is_cli_bypass = _bypass
            # The bypass engine uses llm._call_claude when present (CLI providers)
            # and falls back to llm.invoke(system, user) otherwise (e.g. openrouter),
            # so it no longer requires _call_claude — only that this provider is
            # routed to the bypass.
            _use_bypass = bool(_bypass and sess.session_dir and _current_llm)
            if _use_bypass:
                return cc_run_turn(
                    session_dir=sess.session_dir,
                    player_input=player_input or "",
                    mode=mode,
                )

            # --- Standard LangGraph path ---
            # Inject any pending world events from background world simulator
            if sess.scheduler and mode == "play":
                pending = sess.scheduler.get_pending_events()
                if pending:
                    world_section = "\n\n".join(pending)
                    sess.game_state["messages"].append(
                        HumanMessage(content=(
                            f"[SYSTEM: While you were away, the world moved on.]\n{world_section}"
                        ))
                    )
                    sess.game_state["skip_conversation_log"] = True
                    sess.game_state["skip_turn_increment"] = True
                    sess.game_state["skip_validation"] = True
                    result = sess.graph.invoke(sess.game_state)
                    sess.game_state = result

            if mode == "resume":
                player = sess.game_state.get("player", {})
                location = sess.game_state.get("location", {})
                if player.get("turn", 1) == 1:
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
                sess.game_state["messages"].append(HumanMessage(content=resume_text))
                sess.game_state["skip_conversation_log"] = True
                sess.game_state["skip_turn_increment"] = True
                sess.game_state["skip_validation"] = True
            else:
                sess.game_state["messages"].append(HumanMessage(content=player_input))

            result = sess.graph.invoke(sess.game_state)
            sess.game_state = result
            return result

    try:
        # Hard backstop against a wedged turn: if the engine/CLI hangs past this
        # deadline (well beyond a slow-but-normal ~10-min codex turn), abort so the
        # except below surfaces an in-fiction error and the client re-enables input
        # — instead of leaving the player stuck on a dead spinner forever.
        #
        # Transient CLI stream drops (tls handshake eof, connection reset, timeout)
        # shouldn't nuke a turn on the first flake. Retry the invoke up to 3 attempts
        # with a short backoff — but ONLY on the CLI-bypass path, where cc_run_turn
        # reads state from disk and is safe to re-run. The LangGraph path appends the
        # player's HumanMessage into sess.game_state before invoking, so re-running it
        # would duplicate that message; leave it single-shot.
        _attempts = 3
        for _attempt in range(1, _attempts + 1):
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, _invoke), timeout=960)
                break
            except asyncio.TimeoutError:
                # The 960s hard backstop means the turn wedged, not a transient
                # network blip — don't retry (that's up to ~48min of dead spinner).
                raise
            except Exception as _err:
                _retryable = (sess.is_cli_bypass and _attempt < _attempts
                              and _is_transient_cli_error(_err))
                if not _retryable:
                    raise
                import logging as _logging
                _logging.getLogger(__name__).warning(
                    "transient CLI error (attempt %d/%d), retrying: %s",
                    _attempt, _attempts, _err)
                await asyncio.sleep(1.5 * _attempt)

        # The CLI-bypass engine usually emits suggested_actions inline, but some
        # models/turns omit them (or a parse-fallback zeroes them), leaving the
        # quick-action buttons missing for the rest of the game. Generate a
        # fallback whenever they're empty — for the bypass too, not just LangGraph.
        if (not result.get("suggested_actions")
                and not result.get("game_over") and not result.get("is_warning")):
            try:
                feats = read_features(sess.session_dir)
                if feats["suggested_actions"]:
                    suggestions = await loop.run_in_executor(
                        None,
                        lambda: generate_suggested_actions(
                            sess.game_state,
                            result.get("narrative", ""),
                            _session_language(sess.session_dir),
                            get_fast_llm(),
                            feats["suggested_actions_count"],
                        ),
                    )
                    result["suggested_actions"] = suggestions
            except Exception:
                pass

        # Write-through the freshly generated opening so future new games of this
        # (language, background) are served instantly from cache. Never persist
        # an opening that embedded THIS player's name/alias.
        if (opening_key and result.get("narrative")
                and not result.get("game_over") and not result.get("is_warning")):
            ply = (sess.game_state or {}).get("player", {}) if isinstance(sess.game_state, dict) else {}
            narr_lower = result["narrative"].lower()
            ident = [str(ply.get("name", "")).strip(), str(ply.get("alias", "")).strip()]
            leaked = any(len(tok) >= 3 and tok.lower() in narr_lower for tok in ident)
            if not leaked:
                try:
                    opening_cache.save(opening_key[0], opening_key[1],
                                       result["narrative"], result.get("suggested_actions") or [])
                except Exception:
                    pass

        await _finish_turn(sess, ws, result, mode, _turn_start)

    except WebSocketDisconnect:
        # Client closed/reloaded mid-turn — not an error. The endpoint's
        # disconnect handler does the cleanup.
        raise
    except Exception as e:
        import traceback
        import logging
        traceback.print_exc()
        # Never leak raw engine/CLI internals (e.g. "codex CLI exited 1") into the
        # player-facing UI. Show a recoverable, in-fiction message in the player's
        # language and keep the input usable so they can retry the turn.
        lang = _session_language(sess.session_dir) if sess and sess.session_dir else "en"
        in_fiction = (
            "信号一阵刺啦——干扰扭曲了连接。深吸一口气，再试一次。"
            if lang == "zh" else
            "The Signal stutters — interference scrambles the link for a moment. "
            "Steady yourself and try that again."
        )
        logging.getLogger(__name__).warning("turn failed (shown in-fiction): %s", e)
        try:
            await ws.send_json({
                "type": "error", "message": in_fiction, "recoverable": True,
            })
        except Exception:
            pass  # socket may already be gone
