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
from collections import deque
from contextlib import contextmanager

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


@app.on_event("shutdown")
async def _shutdown_cleanup() -> None:
    """Reap background work on graceful shutdown (Ctrl+C / SIGTERM / deploy).

    Two leaks this closes:

    - **World-sim schedulers**: stop every live PlayerSession's scheduler thread
      so no background tick fires while uvicorn is tearing down.
    - **Orphaned CLI children**: the claude/codex wrappers spawn ``claude -p`` /
      ``codex exec`` in their OWN process group (``start_new_session=True``, so a
      timeout can kill the whole tree) — which also means a dying server never
      signals them. An in-flight CLI call at shutdown would be re-parented to
      init/launchd and keep consuming CPU/tokens forever (observed live: two
      orphaned ``codex exec`` PIDs after ``pkill run_gui.py``). Killing them
      here also unblocks any executor thread parked in ``communicate()``, which
      the interpreter would otherwise wait on before it can exit.
    """
    for sess in list(_sessions_by_user.values()):
        try:
            if sess.scheduler:
                sess.scheduler.stop()
        except Exception:
            pass
    try:
        from tests.scripts import cli_process_registry
        killed = cli_process_registry.kill_all()
        if killed:
            import logging
            logging.getLogger(__name__).info(
                "shutdown: killed %d in-flight CLI child process group(s)", killed)
    except Exception:
        # Cleanup must never turn a graceful shutdown into a crash.
        pass

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

# One turn lock PER ACCOUNT (uid), shared by every PlayerSession ever bound to
# that account. A force-kick / reconnect creates a brand-new PlayerSession for
# the SAME on-disk session directory while the old session's turn thread may
# still be running in the executor (nothing joins it) and writing
# player.json/knowledge.json/... — a per-instance lock gave that abandoned
# thread and the new session's turn two DIFFERENT locks, i.e. zero mutual
# exclusion over the same files (torn/lost writes). Keying the lock by uid
# means old and new sessions of one account serialize on the same object,
# while distinct accounts (disjoint session/<uid>/ namespaces) stay fully
# independent. Entries are tiny and bounded by the number of accounts, so the
# registry is never pruned. Guarded because PlayerSessions can be constructed
# while executor threads exist (cheap, uncontended).
_turn_locks: "dict[str, threading.Lock]" = {}
_turn_locks_guard = threading.Lock()


def _turn_lock_for(uid: str) -> threading.Lock:
    """Return the account-wide turn lock for *uid*, creating it on first use."""
    with _turn_locks_guard:
        lock = _turn_locks.get(uid)
        if lock is None:
            lock = _turn_locks[uid] = threading.Lock()
        return lock


# ---------------------------------------------------------------------------
# Player-turn priority over background lock holders (world-sim, predictions)
# ---------------------------------------------------------------------------
# The account turn lock is shared between PLAYER-VISIBLE turns (input / resume /
# load) and BACKGROUND work — most notably the WorldSimScheduler tick, whose
# single LLM call through a CLI provider can legally take many minutes (codex:
# up to 3 attempts x 300s). Wave 6 handed the scheduler the account lock
# verbatim, so a tick that fired around a resume could grab the lock first and
# the player's turn queued behind it INVISIBLY (phase frames are only emitted
# once the turn body holds the lock). Live incident: u18/波醒w1 resume, 8+ min
# of silence behind a world-sim holder.
#
# Fix: (1) player-visible turns register themselves in ``_player_waiting`` for
# the duration of their lock acquire + hold; (2) the scheduler no longer gets
# the raw lock but a ``_BackgroundSimLock`` facade that REFUSES to start a tick
# while a player turn is pending/running and only try-acquires with a short
# timeout — contended ⇒ the tick is skipped and the scheduler's own loop
# reschedules it; (3) a player turn that still finds the lock held (a tick
# already in its LLM call cannot be preempted) tells the client immediately
# instead of waiting in silence (see ``_notify_sim_wait`` in ``_run_turn``).

_player_waiting: "dict[str, int]" = {}
_player_waiting_guard = threading.Lock()


def _player_turn_pending(uid: str) -> bool:
    """True while any player-visible turn for *uid* is waiting for or holding
    the account turn lock. Probed by background work before slow LLM calls."""
    with _player_waiting_guard:
        return _player_waiting.get(uid, 0) > 0


class _note_player_waiting:
    """Context manager marking a player-visible lock acquire/hold for *uid*.

    A plain counter (not a bool) so overlapping waiters — e.g. an abandoned
    kicked turn plus its replacement — can't clear each other's mark early.
    """

    def __init__(self, uid: str):
        self._uid = uid

    def __enter__(self):
        with _player_waiting_guard:
            _player_waiting[self._uid] = _player_waiting.get(self._uid, 0) + 1
        return self

    def __exit__(self, *exc):
        with _player_waiting_guard:
            n = _player_waiting.get(self._uid, 1) - 1
            if n > 0:
                _player_waiting[self._uid] = n
            else:
                _player_waiting.pop(self._uid, None)
        return False


class _WorldSimSkipped(Exception):
    """Raised by _BackgroundSimLock to make the world-sim scheduler skip this
    tick (its _run_sim catches it non-fatally and its loop reschedules)."""


# How long a background world-sim tick may wait for the account turn lock
# before skipping. Deliberately short: background work must never queue.
_SIM_LOCK_TIMEOUT = 0.25


class _BackgroundSimLock:
    """Context-manager lock facade handed to the WorldSimScheduler.

    Player-visible turns have PRIORITY on the account turn lock. ``__enter__``:

    * refuses outright when a player turn is pending/running for this account
      (the 'player turn pending' check before the sim's slow LLM call);
    * otherwise try-acquires the real lock with a short timeout — contended
      means someone is doing real work, so the tick skips rather than queues;
    * re-checks the pending flag after acquiring (a player turn may have
      arrived during the bounded wait) and backs off if so.

    A skip raises :class:`_WorldSimSkipped`, which the scheduler's ``_run_sim``
    already treats as a non-fatal tick failure; its timer loop reschedules the
    next tick at the normal interval, so skipped work is retried later.
    """

    def __init__(self, real_lock: threading.Lock, uid: str):
        self._real = real_lock
        self._uid = uid

    def __enter__(self):
        if _player_turn_pending(self._uid):
            raise _WorldSimSkipped(
                "player turn pending — world-sim tick skipped (will retry next interval)")
        if not self._real.acquire(timeout=_SIM_LOCK_TIMEOUT):
            raise _WorldSimSkipped(
                "account turn lock contended — world-sim tick skipped (will retry next interval)")
        if _player_turn_pending(self._uid):
            self._real.release()
            raise _WorldSimSkipped(
                "player turn arrived during acquire — world-sim tick skipped")
        return self

    def __exit__(self, *exc):
        self._real.release()
        return False


# Bilingual notice shown when a player turn finds the account lock held by an
# unpreemptable background holder (a world-sim tick already inside its LLM
# call). Sent IMMEDIATELY so the wait is never silent.
_SIM_WAIT_MSG = (
    "The world kept moving while you were away — wrapping up a background "
    "simulation, your turn starts right after… / "
    "你离开时世界仍在运转——正在完成后台模拟，你的回合马上开始…"
)


@contextmanager
def _player_priority_lock(sess: "PlayerSession", notify_wait=None):
    """Acquire the account turn lock for a PLAYER-VISIBLE turn, with priority.

    * Registers in ``_player_waiting`` for the whole acquire+hold, so no NEW
      background tick will start (see :class:`_BackgroundSimLock`).
    * Fast path: uncontended non-blocking acquire — the common case.
    * Contended (an already-running background tick, or a superseded session's
      abandoned turn, cannot be preempted): call *notify_wait* ONCE so the
      client immediately learns why nothing is happening, then block. The
      holder is finite (CLI wrappers own hard subprocess timeouts and
      ``_run_turn`` has its 960s backstop), so the wait is bounded.
    """
    with _note_player_waiting(sess.uid):
        if not sess.lock.acquire(blocking=False):
            if notify_wait is not None:
                try:
                    notify_wait()
                except Exception:
                    pass  # notification is best-effort; never blocks the turn
            sess.lock.acquire()
        try:
            yield
        finally:
            sess.lock.release()


class PlayerSession:
    """All per-player runtime state for one live connection.

    Each instance owns its game state, session dir, scheduler, and
    suggested-action prediction cache — two PlayerSessions never share those,
    so concurrent players cannot interfere. The turn ``lock`` is the one
    deliberate exception: it is the ACCOUNT-wide lock from ``_turn_lock_for``,
    so a superseded session's still-running turn thread and its replacement
    session (same uid, same on-disk dir) can never write session files
    concurrently.
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
        # Account-wide (shared with any prior/kicked session of the same uid)
        # so an abandoned in-flight turn can never interleave file writes with
        # this session's turns — see _turn_lock_for.
        self.lock = _turn_lock_for(uid)

        # Frames received by the mid-turn reader (see _read_frames_during_turn)
        # that are NOT cancel_turn: replayed by the endpoint's main loop, in
        # arrival order, once the in-flight turn returns.
        self.pending_frames: "deque[str]" = deque()

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

        # --- Turn cancel (heartbeat / abort) -----------------------------
        # Set by the {action:'cancel_turn'} WS frame; checked at phase
        # boundaries inside the turn's executor thread. Abort is only honoured
        # BEFORE state_writer has committed — once state is written the turn
        # finishes normally and the flag is ignored (a half-written turn must
        # never persist). Reset at the head of every turn so it can't bleed.
        self.cancel_requested: bool = False

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
    """List save games under *saves_root*, newest-first by mtime.

    Each entry carries ``mtime`` (epoch seconds) so the client can render a
    relative timestamp ("2h ago"). ``day``/``location`` are added when cheaply
    readable from the save's already-open player.json / a single location.json
    read — never a full multi-file parse. All extras are best-effort: a missing
    or malformed file just omits that field (defensive dict.get everywhere) so a
    partial save still lists.
    """
    saves = []
    if os.path.isdir(saves_root):
        for name in os.listdir(saves_root):
            save_path = os.path.join(saves_root, name)
            if os.path.isdir(save_path):
                player = _read_json(os.path.join(save_path, "player.json"))
                player_file = os.path.join(save_path, "player.json")
                mtime = os.path.getmtime(player_file) if os.path.isfile(player_file) else os.path.getmtime(save_path)
                entry = {
                    "name": name,
                    "player_name": player.get("name", "Unknown"),
                    "turn": player.get("turn", "?"),
                    "mtime": mtime,
                }
                # In-fiction time-of-day period (player.json.time) is already in
                # hand — surface it as "day" without an extra read.
                day = player.get("time")
                if day:
                    entry["day"] = day
                # One extra cheap read for a human-readable place ("area · district").
                # Skipped silently if location.json is absent/unparseable.
                loc = _read_json(os.path.join(save_path, "location.json"))
                area = loc.get("area")
                district = loc.get("district")
                place = " · ".join(p for p in (area, district) if p)
                if place:
                    entry["location"] = place
                saves.append(entry)
    saves.sort(key=lambda s: s["mtime"], reverse=True)
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


# --- Endings history (per-user meta-progression) --------------------------
# The roguelike remembers which of the game's designed endings each ACCOUNT has
# ever reached, across every playthrough. One file per user at
# ``session/<uid>/endings_discovered.json`` holding a de-duplicated list of
# {id, turn, day, timestamp} — one entry per DISTINCT ending id, first reach
# wins (turn/day/timestamp of the first time that ending fired). The gallery the
# client renders only ever names endings the player ACTUALLY reached; unreached
# ones are sealed '???' slots the client draws from the count alone, so this file
# is the sole source of "which endings are unlocked". The generic multi-cause
# "death" failure state is not one of the nine designed endings, so it is stored
# for completeness but never resolved into a named gallery slot.
_ENDINGS_FILE = "endings_discovered.json"

# The nine designed endings, id → {name, name_zh}, resolved once from game_data
# so the payload never has to import ENDINGS at call time. NEVER expanded with
# ad-hoc ids (e.g. "death"): only these nine can occupy a named gallery slot.
from engine.game_data import ENDINGS as _ENDINGS_DEFS

_DESIGNED_ENDINGS: "dict[str, dict]" = {
    e["id"]: {"name": e.get("name", e["id"]), "name_zh": e.get("name_zh", e.get("name", e["id"]))}
    for e in _ENDINGS_DEFS
}
ENDINGS_TOTAL = len(_DESIGNED_ENDINGS)  # 9 — the size of the gallery


def _endings_path(session_root: str) -> str:
    return os.path.join(session_root, _ENDINGS_FILE)


def _read_endings_history(session_root: str) -> list[dict]:
    """Read the raw endings-history list for a user (``[]`` if absent/corrupt)."""
    data = _read_json(_endings_path(session_root))
    if isinstance(data, dict):  # tolerate a wrapped {"endings": [...]} shape
        data = data.get("endings")
    return [e for e in data if isinstance(e, dict)] if isinstance(data, list) else []


def _record_ending(session_root: str, ending_id: str, turn, day) -> None:
    """Append a reached ending to the user's history, once per DISTINCT id.

    Atomic (temp file + ``os.replace``) so a crash mid-write can never leave a
    truncated JSON that would wipe the whole gallery. First-reach wins: if the id
    is already present we do nothing (don't overwrite the original turn/day). Meant
    to run in an executor thread — it does blocking disk I/O. Best-effort: any OS
    error is swallowed so a history write can never break the game-over path.
    """
    if not ending_id:
        return
    import time as _t
    try:
        os.makedirs(session_root, exist_ok=True)
        history = _read_endings_history(session_root)
        if any(e.get("id") == ending_id for e in history):
            return  # already unlocked — keep the first-reach record
        history.append({
            "id": ending_id,
            "turn": turn if isinstance(turn, int) else None,
            "day": day,
            "timestamp": int(_t.time()),
        })
        path = _endings_path(session_root)
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)  # atomic on POSIX + Windows
    except OSError:
        pass


def _endings_discovered_payload(session_root: str) -> list[dict]:
    """Resolve the user's reached endings into the spoiler-safe gallery payload.

    Returns ``[{id, name, name_zh, turn}]`` for ONLY the nine designed endings the
    user has actually reached (a stored "death" or any unknown id is dropped — it
    is not a gallery slot). Never emits an id/name for an UNREACHED ending, so no
    ending the player hasn't seen can leak through this channel."""
    out = []
    for e in _read_endings_history(session_root):
        eid = e.get("id")
        meta = _DESIGNED_ENDINGS.get(eid)
        if not meta:
            continue  # "death" / unknown → not one of the nine named slots
        out.append({
            "id": eid,
            "name": meta["name"],
            "name_zh": meta["name_zh"],
            "turn": e.get("turn"),
        })
    return out


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
        # Logged out: still advertise the gallery SIZE (so the menu can show
        # sealed slots) but reveal no reached endings — there is no user to scope
        # them to.
        base.update({"authed": False, "username": None,
                     "has_session": False, "sessions": [], "saves": [],
                     "endings_discovered": [], "endings_total": ENDINGS_TOTAL})
        return base
    sessions = _list_sessions(sess.session_root)
    saves = _list_saves(sess.saves_root)
    base.update({
        "authed": True,
        "username": sess.username,
        "has_session": bool(sessions),
        "sessions": sessions,
        "saves": saves,
        # Meta-progression: which of the nine designed endings this ACCOUNT has
        # ever reached (names only for reached ones) + the gallery size.
        "endings_discovered": _endings_discovered_payload(sess.session_root),
        "endings_total": ENDINGS_TOTAL,
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
    # If the old connection has a turn in flight, ask it to abort at the next
    # pre-commit seam: its result has no audience anymore, and the sooner it
    # releases the shared per-account turn lock the sooner the replacement
    # session's resume/turn can proceed. A post-commit turn ignores the flag
    # and finishes its writes normally (never tear a half-written turn).
    existing.cancel_requested = True
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


async def _report_ws_loop_error(ws: WebSocket, e: Exception) -> None:
    """Handle an unexpected websocket-loop error: log the real error + traceback
    server-side only (never leak raw exception text to the browser) and send the
    client a generic bilingual error, tolerating a dead socket."""
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
# WebSocket — main game communication
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    sess: PlayerSession | None = None  # this connection's bound player session
    loop = asyncio.get_event_loop()

    try:
        while True:
            if sess is not None and sess.pending_frames:
                # Frames that arrived while a turn was in flight were drained by
                # the turn's concurrent receiver (_read_frames_during_turn) —
                # cancel_turn was acted on there; everything else was requeued.
                # Replay them in arrival order before blocking on the socket.
                raw = sess.pending_frames.popleft()
            else:
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

            elif action == "delete_save":
                await _handle_delete_save(ws, sess, msg)

            elif action == "cancel_turn":
                # Mid-turn cancels are consumed by the turn's concurrent reader
                # (_read_frames_during_turn) — this receive loop is suspended
                # inside the turn await and only sees frames between turns. So
                # a cancel landing HERE means no turn is in flight: flip the
                # flag anyway (harmless; reset at the head of every turn) so a
                # cancel racing the turn's very first frames isn't lost.
                sess.cancel_requested = True

            elif action == "refresh":
                if sess.session_dir:
                    await ws.send_json({
                        "type": "session_update",
                        "session": await _get_session_data_async(sess),
                    })

    except WebSocketDisconnect:
        _on_disconnect(sess, ws)
    except RuntimeError as e:
        # A client close racing a server send never surfaces here as
        # WebSocketDisconnect: the failing send raises WebSocketDisconnect(1006)
        # INSIDE _safe_send (which swallows it by design), starlette flips
        # application_state to DISCONNECTED, and the endpoint's next
        # receive_text() then raises a bare RuntimeError ("WebSocket is not
        # connected..."). Routing that through the generic branch used to leak
        # the whole session: PlayerSession stayed registered in
        # _sessions_by_user (forcing session_conflict on reconnect) and its
        # WorldSimScheduler thread kept firing world-sim ticks with no client.
        # Treat any RuntimeError on a no-longer-connected socket as the
        # disconnect it really is; only a RuntimeError on a live socket is a
        # genuine server error.
        if not _ws_connected(ws):
            _on_disconnect(sess, ws)
        else:
            await _report_ws_loop_error(ws, e)
    except Exception as e:
        await _report_ws_loop_error(ws, e)


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

    def _create_locked():
        # Under the ACCOUNT turn lock: _resolve_new_session_dir may legally
        # REUSE a same-origin dir, and create_new_session rmtree's it — without
        # the lock a superseded session's still-running turn could be mid-write
        # in that very dir (see _turn_lock_for). Bounded acquire so a wedged
        # abandoned turn yields an error instead of a hang. Marked player-
        # visible so background world-sim ticks defer instead of contending.
        with _note_player_waiting(sess.uid):
            if not sess.lock.acquire(timeout=_BIND_LOCK_TIMEOUT):
                return None
            try:
                create_new_session(
                    session_dir=sess.session_dir,
                    name=config.get("name", "Unknown"),
                    alias=config.get("alias", "Unknown"),
                    background=config.get("background", "street_runner"),
                    difficulty=diff,
                    language=lang,
                )
                # create_new_session rmtree's the dir, so (re)stamp the origin
                # marker after it so future new-game collision checks can tell
                # this game's display name.
                _write_origin_marker(sess.session_dir, save_name)
                return initial_state(sess.session_dir)
            finally:
                sess.lock.release()

    state = await asyncio.to_thread(_create_locked)
    if state is None:
        await ws.send_json({"type": "error", "message": _PREV_TURN_BUSY_MSG})
        return

    sess.graph = _get_graph()
    sess.game_state = state
    _start_world_sim_scheduler(sess)

    await _send_game_started(sess, ws)
    await _run_opening(sess, ws, lang, config.get("background", "street_runner"))


# How long a resume/load may wait for the account turn lock before giving up.
# Long enough to ride out a kicked turn finishing its post-commit writes (or
# aborting at the next pre-commit seam via the cancel flag _kick sets); short
# enough that a truly wedged abandoned turn yields an actionable error instead
# of a resume that hangs forever.
_BIND_LOCK_TIMEOUT = 60.0

_PREV_TURN_BUSY_MSG = (
    "A previous turn is still finishing on the server — try again in a moment. / "
    "上一回合仍在服务器上收尾——请稍后再试。"
)


def _load_state_locked(sess: PlayerSession, *, copy_from: str | None = None):
    """Read (and for load-game, first restore) the on-disk session under the
    ACCOUNT turn lock, so a superseded session's still-running turn thread can't
    be mid-write while we copy/read the files (torn reads → silent empty state).
    Runs in a worker thread (blocking acquire). Returns the initial GameState,
    or None if the lock couldn't be acquired within _BIND_LOCK_TIMEOUT.

    Marked player-visible (``_note_player_waiting``) for the whole acquire+hold,
    so a world-sim tick firing mid-resume defers to us instead of stealing the
    lock between this read and the resume turn itself.
    """
    with _note_player_waiting(sess.uid):
        if not sess.lock.acquire(timeout=_BIND_LOCK_TIMEOUT):
            return None
        try:
            if copy_from:
                copy_save_to_session(copy_from, sess.session_dir)
            return initial_state(sess.session_dir)
        finally:
            sess.lock.release()


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
    state = await asyncio.to_thread(_load_state_locked, sess)
    if state is None:
        await ws.send_json({"type": "error", "message": _PREV_TURN_BUSY_MSG})
        return
    sess.game_state = state
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
    sess.graph = _get_graph()
    state = await asyncio.to_thread(_load_state_locked, sess, copy_from=save_path)
    if state is None:
        await ws.send_json({"type": "error", "message": _PREV_TURN_BUSY_MSG})
        return
    sess.game_state = state
    _start_world_sim_scheduler(sess)

    await _send_game_started(sess, ws, mode="resume")
    await _run_turn(sess, ws, mode="resume")


async def _handle_delete_save(ws: WebSocket, sess: PlayerSession, msg: dict) -> None:
    """Delete a save directory under the player's own ``saves/<uid>/`` namespace.

    Hardened against path traversal and self-deletion:
    * ``_safe_name`` collapses the client name to a single path component (no
      ``..`` / separators), then we re-verify the resolved target is contained
      inside ``sess.saves_root`` (belt-and-suspenders against symlink/edge cases).
    * We REFUSE to delete a save whose resolved path is the player's ACTIVE
      session directory (compared via ``os.path.realpath``), so a player can't
      nuke the game they're currently in from under the running turn loop.

    Replies ``{type:'save_deleted', save_name, saves:[...]}`` with a freshly
    listed saves array; all errors are bilingual EN/中文.
    """
    save_name = _safe_name(msg.get("save_name", ""))
    if not save_name:
        await ws.send_json({
            "type": "error",
            "message": (
                "Invalid save name. / 存档名无效。"
            ),
        })
        return

    saves_root = sess.saves_root
    save_path = os.path.join(saves_root, save_name)

    # Resolve real paths so a traversal / symlink can't escape saves_root.
    real_root = os.path.realpath(saves_root)
    real_save = os.path.realpath(save_path)
    contained = (real_save == real_root  # never (root itself) but guard anyway
                 or real_save.startswith(real_root + os.sep))
    if not contained or not os.path.isdir(real_save):
        await ws.send_json({
            "type": "error",
            "message": (
                f"Save not found: {save_name} / 未找到存档：{save_name}"
            ),
        })
        return

    # Refuse to delete the currently-active session dir (compare resolved paths).
    if sess.session_dir and os.path.realpath(sess.session_dir) == real_save:
        await ws.send_json({
            "type": "error",
            "message": (
                "Can't delete the game you're currently playing. / "
                "无法删除你正在进行的游戏存档。"
            ),
        })
        return

    try:
        await asyncio.to_thread(shutil.rmtree, real_save)
    except Exception:
        import logging
        logging.getLogger(__name__).warning("delete_save failed for %r", save_name)
        await ws.send_json({
            "type": "error",
            "message": (
                "Delete failed — try again. / 删除失败——请重试。"
            ),
        })
        return

    saves = await asyncio.to_thread(_list_saves, saves_root)
    await ws.send_json({
        "type": "save_deleted",
        "save_name": save_name,
        "saves": saves,
    })


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
    state = await asyncio.to_thread(_load_state_locked, sess)
    if state is None:
        return False
    sess.game_state = state
    _start_world_sim_scheduler(sess)
    await _send_game_started(sess, ws, mode="resume")
    return True


async def _handle_player_input(ws: WebSocket, sess: PlayerSession, msg: dict, loop):
    text = msg.get("text", "").strip()
    if not text:
        return
    # Clear any stale cancel from a prior turn so it can't abort this new input
    # (belt-and-suspenders: _run_turn also resets at its head, but the cached
    # fast path below bypasses _run_turn and completes instantly).
    sess.cancel_requested = False
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
    """Create or restart the WorldSimScheduler for *sess*.

    The scheduler gets the account turn lock only through the
    :class:`_BackgroundSimLock` facade: a tick that would contend with a
    player-visible turn (pending, running, or arriving mid-acquire) SKIPS
    instead of queueing, so a slow world-sim LLM call can never starve the
    player's resume/input turn (the u18/波醒w1 incident). Data safety is
    unchanged — when a tick does run it holds the same account-wide lock.
    """
    if sess.scheduler is not None:
        sess.scheduler.stop()
    sess.scheduler = WorldSimScheduler(
        session_dir=sess.session_dir,
        llm_getter=get_llm,
        game_lock=_BackgroundSimLock(sess.lock, sess.uid),
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
        # Bounded acquire: predictions are best-effort BACKGROUND work — never
        # let one queue for minutes behind a world-sim tick / abandoned turn
        # holding the account lock (it would pin an executor thread and then
        # snapshot a stale base anyway). Contended ⇒ skip this prediction round.
        if not sess.lock.acquire(timeout=5.0):
            return None
        try:
            if gen != sess.predict_generation:
                return None
            action_cache.clear(session_dir)
            base = action_cache.make_base(session_dir)
            return base, action_cache.fingerprint(session_dir), _player_turn(session_dir)
        finally:
            sess.lock.release()

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
            # Capture the speculative turn's roll beats + meter reasons NOW: they
            # were buffered under work_dir, which _finish_turn never drains (it
            # drains the LIVE session dir). Stashing them in the cache entry both
            # surfaces them when the prediction is served (_try_serve_cached
            # requeues them onto the live dir) and stops the module-level buffers
            # leaking work_dir keys for predictions that are never clicked.
            from engine.tools import drain_rolls, drain_reasons
            return work_dir, res, drain_rolls(work_dir), drain_reasons(work_dir)

        async def _one(text):
            try:
                outcome = await loop.run_in_executor(None, _spec, text)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("prediction failed for %r: %s", text, e)
                return
            if outcome and gen == sess.predict_generation:
                work_dir, res, rolls, reasons = outcome
                stored = False
                with sess.cache_lock:
                    if gen == sess.predict_generation:
                        sess.action_cache[action_cache.hash_action(text)] = {
                            "text": text, "state_dir": work_dir, "result": res, "ready": True,
                            "rolls": rolls, "reasons": reasons,
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
    # Bounded acquire: the turn lock is account-wide, so a superseded session's
    # still-running turn may hold it for minutes. This fast path has no timeout
    # backstop of its own — degrade to a cache miss (the normal turn path has
    # both the 960s backstop and the cancel seam) instead of blocking unboundedly.
    # Marked player-visible: this IS the player's action, so a world-sim tick
    # must defer to it rather than start mid-click and force a cache miss.
    with _note_player_waiting(sess.uid):
        if not sess.lock.acquire(timeout=5.0):
            return None
        try:
            if _player_turn(session_dir) != exp_turn:
                return None
            if action_cache.fingerprint(session_dir) != exp_fp:
                return None
            action_cache.promote(session_dir, entry["state_dir"])
        finally:
            sess.lock.release()
    with sess.cache_lock:
        sess.predict_generation += 1
    # The speculative turn's roll beats + meter reasons were drained from the
    # work dir at speculate time (see _spec). Requeue them onto the LIVE session
    # dir so _finish_turn's normal drain surfaces them — otherwise the wave-4
    # roll chip and meter-why silently no-op on every prediction hit.
    from engine.tools import requeue_rolls, requeue_reasons
    requeue_rolls(session_dir, entry.get("rolls"))
    requeue_reasons(session_dir, entry.get("reasons"))
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


# F2 — ambient meter-change reasons. When a meter MOVES this turn but the
# resolver volunteered no in-world cause, the meter still changed for a reason;
# surfacing "(rose|fell)" with no "why" reads as a bug to the player. So we
# attach a generic AMBIENT default, keyed by (meter, direction).
#
# The design track is adding ambient variants to game_data's cause labels. We
# read those defensively (getattr / dict.get with fallbacks) so this code works
# whether or not their commit has landed: if game_data exposes an ambient label
# set we prefer it, otherwise we fall back to the hardcoded bilingual defaults
# below. Never a spoiler — these name only the meter and its direction, nothing
# undiscovered.
_AMBIENT_REASON_FALLBACK: dict[tuple[str, str], dict] = {
    ("alert", "up"): {
        "en": "the city's watch grows warier",
        "zh": "城市的监控愈发警觉"},
    ("alert", "down"): {
        "en": "the heat around you cools a little",
        "zh": "针对你的搜查稍稍缓和"},
    ("integrity", "up"): {
        "en": "your neural link steadies",
        "zh": "你的神经链路趋于稳定"},
    ("integrity", "down"): {
        "en": "the strain frays your neural link",
        "zh": "压力侵蚀着你的神经链路"},
    ("decay", "up"): {
        "en": "the Signal frays a little further",
        "zh": "信号进一步衰减"},
    ("decay", "down"): {
        "en": "the Signal settles for now",
        "zh": "信号暂时稳定下来"},
}


def _ambient_reason(meter: str, direction: str) -> dict | None:
    """Return an ``{en, zh}`` ambient default for *meter* moving *direction*.

    Reads game_data's ambient cause labels if the design track has added them
    (tried under several plausible names), else falls back to the hardcoded map.
    Fully defensive: any import/shape surprise degrades to the fallback (or None
    if even that is missing), never raising into the turn finalizer."""
    try:
        from engine import game_data as _gd
    except Exception:
        _gd = None

    if _gd is not None:
        # The design track hasn't fixed a name yet; probe the plausible ones and
        # accept the first that yields a bilingual {en|zh} dict for this key.
        for attr in ("AMBIENT_CAUSE_LABELS", "AMBIENT_METER_REASONS",
                     "METER_AMBIENT_LABELS", "AMBIENT_REASONS"):
            table = getattr(_gd, attr, None)
            if not isinstance(table, dict):
                continue
            # Accept whatever shape the track settles on, tried in order:
            #   flat tuple key {(meter, dir): {...}}
            #   flat string key {"meter_dir": {...}}
            #   nested         {meter: {dir: {...}}}
            cand = table.get((meter, direction)) or table.get(f"{meter}_{direction}")
            if not isinstance(cand, dict):
                nested = table.get(meter)
                if isinstance(nested, dict):
                    cand = nested.get(direction)
            if isinstance(cand, dict) and (cand.get("en") or cand.get("zh")):
                return {"en": cand.get("en") or cand.get("zh"),
                        "zh": cand.get("zh") or cand.get("en")}
        # Some tracks may fold ambient variants into the existing alert table
        # under a reserved key (e.g. ALERT_CAUSE_LABELS["ambient_up"]).
        if meter == "alert":
            alert_tbl = getattr(_gd, "ALERT_CAUSE_LABELS", None)
            if isinstance(alert_tbl, dict):
                cand = alert_tbl.get(f"ambient_{direction}") or alert_tbl.get("ambient")
                if isinstance(cand, dict) and (cand.get("en") or cand.get("zh")):
                    return {"en": cand.get("en") or cand.get("zh"),
                            "zh": cand.get("zh") or cand.get("en")}

    return _AMBIENT_REASON_FALLBACK.get((meter, direction))


def _build_state_delta(prev: dict | None, cur: dict,
                       reasons: dict | None = None) -> dict | None:
    """Repackage the meter/trace/knowledge diff between two snapshots as numbers.

    Additive companion to ``session_update``; old clients ignore the ``state_delta``
    type. Returns None when there is no prior snapshot to diff against.

    *reasons* (optional) carries the in-world cause the resolver gave for any meter
    that moved, as ``{alert?:{en,zh}, integrity?:{en,zh}, decay?:{en,zh}}``. Only
    reasons whose meter actually changed this turn are forwarded, so a stale/omitted
    reason never mislabels a static meter. For a meter that moved but carries NO
    supplied reason, we attach an AMBIENT default (see ``_ambient_reason``) so the
    player always gets a "why" alongside the number."""
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

    # Attach a reason for every meter that actually MOVED this turn: the resolver's
    # supplied cause when present, else an ambient default. A supplied reason for a
    # meter that did NOT move is dropped (guards against a reason the model gave for
    # a delta that got clamped to no-op).
    reasons = reasons or {}
    out_reasons: dict = {}
    _meter_key = {"alert": "nexus_alert", "integrity": "integrity", "decay": "fragment_decay"}
    for meter, snap_key in _meter_key.items():
        pair = delta[snap_key]
        frm, to = pair["from"], pair["to"]
        if frm == to:
            continue  # meter static this turn — no reason at all
        payload = reasons.get(meter)
        if isinstance(payload, dict) and (payload.get("en") or payload.get("zh")):
            out_reasons[meter] = {"en": payload.get("en") or payload.get("zh"),
                                  "zh": payload.get("zh") or payload.get("en")}
            continue
        # Moved but unexplained → ambient default, chosen by direction. A missing/
        # non-numeric endpoint means we can't tell direction; skip rather than guess.
        try:
            direction = "up" if float(to) > float(frm) else "down"
        except (TypeError, ValueError):
            continue
        ambient = _ambient_reason(meter, direction)
        if ambient:
            out_reasons[meter] = ambient

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
        # Meta-progression: persist the reached ending to this ACCOUNT's history
        # (once per distinct id) BEFORE the game_over frame, so the fresh gallery
        # we ship with it already reflects this run. The in-fiction turn/day come
        # from the spoiler-filtered session_data we already read this turn. All
        # off the event loop; best-effort — a history-write failure must never
        # swallow the game_over the client is waiting on.
        endings_discovered = _endings_discovered_payload(sess.session_root) if sess.session_dir else []
        if ending and sess.session_dir:
            _plr = session_data.get("player") or {}
            _wt = (session_data.get("world_state") or {}).get("time") or {}
            try:
                await asyncio.to_thread(
                    _record_ending, sess.session_root, ending,
                    _plr.get("turn"), _wt.get("day"),
                )
                endings_discovered = await asyncio.to_thread(
                    _endings_discovered_payload, sess.session_root)
            except Exception:
                pass
        await _safe_send(ws, {
            "type": "game_over",
            "ending": ending,
            "death_cause": result.get("death_cause"),
            "narrative": narrative,
            # The refreshed per-account gallery so the end-screen can light up the
            # ending just earned (and any previously unlocked) without a round-trip.
            # Names only for REACHED designed endings; sealed slots come from the
            # total. A "death" or unknown id contributes no named slot.
            "endings_discovered": endings_discovered,
            "endings_total": ENDINGS_TOTAL,
        })
        if sess.scheduler:
            sess.scheduler.stop()
        return

    if mode == "play" and sess.scheduler:
        sess.scheduler.on_player_input()

    _maybe_schedule_prediction(sess, result, ws)


# Substrings that mark a transient CLI/network stream drop worth retrying (as
# opposed to a content/auth/logic error, which won't get better on a retry).
# CONNECTION-phase errors only: the bare "timeout"/"timed out" markers are
# deliberately absent (wave 4 review) — they matched subprocess.TimeoutExpired
# from a CLI turn that already burned its full multi-minute budget (plus the
# wrapper's own internal retries), so the server re-ran it up to 3x for a
# worst case of ~45 minutes of dead spinner on a merely slow/hung model.
# "read timed out" stays: it is a socket read dropping mid-stream, not a
# completed wait.
_TRANSIENT_CLI_MARKERS = (
    "tls handshake eof", "handshake eof", "connection reset", "connection refused",
    "connection aborted", "connection closed", "broken pipe", "reconnecting",
    "temporarily unavailable", "eof occurred",
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


# ---------------------------------------------------------------------------
# Turn progress heartbeat (phase frames) + cancel
# ---------------------------------------------------------------------------
# A turn can run for minutes (a slow model, a multi-step tool loop). Rather than
# leave the client on an opaque spinner, the server emits additive
# ``{type:'phase', phase, ts}`` frames as the turn crosses coarse boundaries.
# Frames are best-effort and additive — a client that ignores them loses nothing,
# and the flavor ticker on the client stays as the fallback when none arrive.

# LangGraph node name → coarse phase. Nodes not listed (input_gate,
# input_blocked_handler) don't emit a phase — they're instantaneous pure-Python
# gates whose progress the player doesn't need to see.
_NODE_PHASES = {
    "input_validator": "validating",
    "resolver": "resolving",
    "tool_executor": "resolving",
    "output_language_checker": "resolving",
    "state_writer": "writing",
    "location_updater": "world",
    "world_ticker": "world",
    "world_simulator": "world",
    "trace_checker": "checking",
    "consequence": "checking",
}

# The turn is only safely abortable BEFORE this node commits state to disk. A
# node whose phase is one of these has not yet written durable state, so a cancel
# observed up to (and including) their completion aborts cleanly. Once
# ``state_writer`` runs, the turn finishes normally and cancel is ignored.
_PRE_COMMIT_PHASES = frozenset({"validating", "resolving"})

# Sentinel returned by the turn body when a cancel aborted it before any state
# write. Distinct object so ``_run_turn`` can tell an abort from a real result.
_TURN_ABORTED = object()


def _make_phase_emitter(loop, ws: WebSocket):
    """Return a thread-safe ``emit(phase)`` callable for use inside the turn's
    executor thread.

    The turn body runs off the event loop (``run_in_executor``), but WS sends
    must happen on the loop. This schedules a best-effort ``_safe_send`` of a
    ``phase`` frame via ``call_soon_threadsafe`` and de-dupes consecutive
    identical phases so the resolver/tool loop doesn't spam ``resolving``.
    """
    import time as _time
    state = {"last": None}

    def emit(phase: str) -> None:
        if not phase or phase == state["last"]:
            return
        state["last"] = phase
        payload = {"type": "phase", "phase": phase, "ts": _time.time()}
        try:
            loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(_safe_send(ws, payload))
            )
        except RuntimeError:
            pass  # loop gone — client is away; nothing to deliver

    return emit


def _stream_graph_turn(graph, state: dict, emit, is_cancelled):
    """Run one LangGraph turn via streaming, emitting phase frames and honouring
    a cooperative cancel, and return the SAME final state ``invoke()`` would.

    LangGraph contract (verified against langgraph 1.1.3): with
    ``stream_mode=["updates","values"]`` the ``updates`` chunks name the node(s)
    that just ran (in execution order) and each ``values`` chunk is the full
    accumulated state after that super-step — the LAST ``values`` chunk is
    byte-for-byte identical to ``graph.invoke(state)``. So streaming here changes
    nothing about the state we extract; it only adds visibility + a cancel seam.

    Cancel semantics: after each node completes we map it to a coarse phase and
    emit it. If a cancel was requested AND we are still in a pre-commit phase
    (before ``state_writer`` writes durable state), we stop consuming the stream
    and return ``_TURN_ABORTED`` — no state has been persisted, so the abort is
    clean. Once ``state_writer`` has run we ignore cancel and finish the turn
    normally (a half-written turn must never be surfaced).
    """
    last_values = None
    aborted = False
    committed = False  # True once a node at/after state_writer has run

    for mode, chunk in graph.stream(state, stream_mode=["updates", "values"]):
        if mode == "updates":
            # chunk maps {node_name: partial_update}; usually one key.
            for node in chunk:
                phase = _NODE_PHASES.get(node)
                if phase is not None:
                    emit(phase)
                if phase not in _PRE_COMMIT_PHASES and phase is not None:
                    committed = True
            # Cooperative abort: only before any durable write.
            if not committed and is_cancelled():
                aborted = True
                break
        elif mode == "values":
            last_values = chunk

    if aborted:
        return _TURN_ABORTED
    return last_values


async def _read_frames_during_turn(ws: WebSocket, sess: PlayerSession, rx_state: dict) -> None:
    """Concurrently drain WS frames while a turn is in flight.

    The endpoint's single receive loop is parked awaiting the turn coroutine,
    so without this task a mid-turn ``{action:'cancel_turn'}`` frame would sit
    unread in the socket buffer until the turn finished on its own — making the
    CANCEL button a pure no-op. This task lives only for the duration of one
    turn's executor await (created/cancelled by ``_run_turn``):

    * ``cancel_turn``   → flips ``sess.cancel_requested`` immediately, so the
      executor thread's ``is_cancelled()`` probe can abort at the next
      pre-commit seam;
    * any other frame   → requeued verbatim onto ``sess.pending_frames``; the
      endpoint's main loop replays them in arrival order after the turn (the
      same net behaviour as the old socket-buffer queueing);
    * client disconnect → recorded in *rx_state* (``_run_turn`` re-raises it so
      the endpoint's normal WebSocketDisconnect cleanup runs) and treated as an
      implicit cancel — nobody is listening, so don't burn out the rest of a
      still-pre-commit model run.
    """
    try:
        while True:
            raw = await ws.receive_text()
            action = None
            try:
                frame = json.loads(raw)
                if isinstance(frame, dict):
                    action = frame.get("action")
            except (json.JSONDecodeError, TypeError):
                pass  # malformed frame — requeue; the main loop owns the error reply
            if action == "cancel_turn":
                sess.cancel_requested = True
            else:
                sess.pending_frames.append(raw)
    except WebSocketDisconnect:
        rx_state["disconnected"] = True
        sess.cancel_requested = True
    except Exception:
        # Receive machinery failed some other way — stop reading; the main
        # loop's own receive will surface the real condition after the turn.
        pass


async def _run_turn(sess: PlayerSession, ws: WebSocket, player_input: str | None = None,
                    mode: str = "play", opening_key: tuple[str, str] | None = None):
    """Run a single game turn for *sess* in a background thread."""
    await ws.send_json({"type": "thinking"})

    import time as _time
    _turn_start = _time.time()

    # Fresh turn: clear any stale cancel request so it can't abort this turn
    # before the player even asked.
    sess.cancel_requested = False

    # A real turn supersedes any pending suggested-action predictions.
    _reset_prediction(sess)

    loop = asyncio.get_event_loop()

    # Thread-safe phase emitter + a snapshot-free cancel probe. Both are read
    # from inside the executor thread; the emitter marshals sends back onto the
    # loop, and ``_cancelled`` just reads the session flag the WS handler sets.
    _emit_phase = _make_phase_emitter(loop, ws)
    def _cancelled() -> bool:
        return sess.cancel_requested

    def _notify_sim_wait():
        # The account lock is held by an unpreemptable background holder
        # (world-sim tick mid-LLM-call). Surface an immediate 'world' phase +
        # bilingual system notice so the queued turn is never silent. Runs in
        # the executor thread — marshal the send onto the loop, best-effort.
        _emit_phase("world")
        payload = {"type": "system_notice", "text": _SIM_WAIT_MSG}
        try:
            loop.call_soon_threadsafe(
                lambda: asyncio.ensure_future(_safe_send(ws, payload))
            )
        except RuntimeError:
            pass  # loop gone — client is away; nothing to deliver

    def _invoke():
        with _player_priority_lock(sess, _notify_sim_wait):
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
                # The bypass is a single opaque CLI/LLM call in engine (read-only
                # to us), so we can only bracket it with COARSE phases at the
                # visible call boundary: 'resolving' while the model runs, then
                # 'writing' as pure-Python post-processing commits state. A cancel
                # requested BEFORE the call aborts cleanly (nothing ran yet); once
                # cc_run_turn is entered we cannot interrupt the in-flight CLI
                # from here (the wrapper owns its own subprocess/hung-CLI kill via
                # its timeout), so a mid-call cancel lands at this next boundary —
                # i.e. it takes effect on the following turn, not this one.
                if _cancelled():
                    return _TURN_ABORTED
                _emit_phase("resolving")
                res = cc_run_turn(
                    session_dir=sess.session_dir,
                    player_input=player_input or "",
                    mode=mode,
                )
                _emit_phase("writing")
                return res

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

            # The turn's HumanMessage is appended IN PLACE to the live
            # sess.game_state below, before streaming. Keep a handle to it so a
            # pre-commit cancel can revert the append — otherwise the rejected
            # input would linger as a dangling, unanswered user turn and leak
            # into the next turn's LLM context (the graph streams over its own
            # internal copy, so it never removes it for us on abort).
            _turn_msg = None
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
                _turn_msg = HumanMessage(content=resume_text)
                sess.game_state["messages"].append(_turn_msg)
                sess.game_state["skip_conversation_log"] = True
                sess.game_state["skip_turn_increment"] = True
                sess.game_state["skip_validation"] = True
            else:
                _turn_msg = HumanMessage(content=player_input)
                sess.game_state["messages"].append(_turn_msg)

            # Stream the turn so we can emit phase frames and honour a cancel,
            # while extracting the exact same final state ``invoke`` would return
            # (see _stream_graph_turn for the verified LangGraph contract).
            result = _stream_graph_turn(
                sess.graph, sess.game_state, _emit_phase, _cancelled,
            )
            if result is _TURN_ABORTED:
                # Aborted before state_writer — nothing durable was persisted
                # (the streamed state was local to the graph). But the append
                # above DID mutate the live sess.game_state["messages"], so
                # revert it: pop the exact HumanMessage we appended, restoring
                # the pre-turn state. Without this the cancelled input would be
                # replayed as context on the next turn (and, on the blocked-
                # input path, the stripping RemoveMessage never ran either).
                msgs = sess.game_state.get("messages")
                if msgs and _turn_msg is not None and msgs[-1] is _turn_msg:
                    msgs.pop()
                return _TURN_ABORTED
            sess.game_state = result
            return result

    try:
        # Hard backstop against a wedged turn: if the engine/CLI hangs past this
        # deadline (well beyond a slow-but-normal ~10-min codex turn), abort so the
        # except below surfaces an in-fiction error and the client re-enables input
        # — instead of leaving the player stuck on a dead spinner forever.
        #
        # Transient CLI stream drops (tls handshake eof, connection reset — NOT a
        # completed multi-minute model timeout, see _TRANSIENT_CLI_MARKERS)
        # shouldn't nuke a turn on the first flake. Retry the invoke up to 3 attempts
        # with a short backoff — but ONLY on the CLI-bypass path, where cc_run_turn
        # reads state from disk and is safe to re-run. The LangGraph path appends the
        # player's HumanMessage into sess.game_state before invoking, so re-running it
        # would duplicate that message; leave it single-shot.
        # While the invoke is parked in the executor this coroutine is
        # suspended, so the endpoint's single receive loop can't see incoming
        # frames — a mid-turn cancel_turn would otherwise sit unread in the
        # socket buffer until the turn ended by itself. Run a concurrent
        # receiver for exactly the duration of the invoke: it acts on
        # cancel_turn immediately and requeues everything else for the main
        # loop (see _read_frames_during_turn).
        _rx_state = {"disconnected": False}
        _reader = asyncio.create_task(_read_frames_during_turn(ws, sess, _rx_state))

        _attempts = 3
        try:
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
        finally:
            # The reader must never outlive the invoke: once we're back on the
            # main loop, IT owns ws.receive_text() again (never two concurrent
            # readers on one socket).
            _reader.cancel()
            try:
                await _reader
            except (asyncio.CancelledError, Exception):
                pass
            if _rx_state["disconnected"]:
                # Client vanished mid-turn. Whatever the turn committed is
                # safely on disk, but nobody is listening for the result (or
                # for a turn error — hence raising from finally, deliberately
                # superseding any in-flight exception: the reader already
                # consumed the socket's disconnect message, so the endpoint's
                # next receive would raise RuntimeError and MISS its disconnect
                # cleanup). Re-raise as the normal disconnect path so the
                # endpoint unbinds this session.
                raise WebSocketDisconnect(1006)

        # Turn was cancelled cleanly before any state write (see
        # _stream_graph_turn / the bypass pre-call check). Nothing was persisted
        # and no meter/session snapshot advanced, so we just tell the client the
        # turn is cancelled and unlock — no narrative, no state_delta, no autosave.
        if result is _TURN_ABORTED:
            sess.cancel_requested = False
            await _safe_send(ws, {"type": "turn_cancelled"})
            return

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

        # A cancel that arrived after state_writer committed is honoured as a
        # no-op (the turn finishes normally); clear it here so it can't leak into
        # the next turn's abort check. The head-of-turn reset covers the same
        # bleed, but clearing on completion keeps the flag tightly scoped.
        sess.cancel_requested = False

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
            "信号一阵刺啦——干扰扭曲了链路。深吸一口气，再试一次。"
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
