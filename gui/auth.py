"""
Signal Lost — Local Account Store & Authentication

A tiny, dependency-free auth layer for the browser GUI so multiple players can
share one backend without stepping on each other. Accounts live in a local
JSON file (``auth/accounts.json``) that is git-ignored — credentials never leave
this machine and are never committed.

Design (demo-scale, < 10 concurrent players):
- Passwords are salted + PBKDF2-HMAC-SHA256 hashed; the plaintext is never stored.
- Usernames are unique (case-insensitive) and map to a stable, filesystem-safe
  ``uid`` (``u1``, ``u2``, …) used to namespace each player's session/save dirs.
- Session tokens are random, in-memory only (lost on server restart — players
  simply sign in again). This keeps the demo stateless and avoids persisting
  anything sensitive to disk beyond the password hash.

All public functions are thread-safe (a single module lock guards the file and
the in-memory token table). File I/O is small and fast, so callers may invoke
these inline from the request handler.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import threading
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

_GUI_DIR = os.path.dirname(os.path.abspath(__file__))
_GAME_ROOT = os.path.abspath(os.path.join(_GUI_DIR, ".."))
AUTH_DIR = os.path.join(_GAME_ROOT, "auth")
ACCOUNTS_PATH = os.path.join(AUTH_DIR, "accounts.json")

_PBKDF2_ITERATIONS = 200_000
_USERNAME_MAX = 32
_PASSWORD_MIN = 4

# Reject control characters and the path separators that could escape a uid dir.
_BAD_USERNAME_CHARS = re.compile(r"[\x00-\x1f\x7f/\\]")

_TOKEN_TTL_DAYS = 30  # auto-login tokens are valid this long

_lock = threading.RLock()

# token -> {"username": str, "created": iso}. Persisted to AUTH_DIR/tokens.json so
# a signed-in session survives a server restart (enables auto-login on refresh).
_tokens: dict[str, dict] = {}


def _tokens_path() -> str:
    return os.path.join(AUTH_DIR, "tokens.json")


def _save_tokens() -> None:
    """Persist the token table to disk (best-effort, atomic)."""
    try:
        os.makedirs(AUTH_DIR, exist_ok=True)
        tmp = _tokens_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_tokens, f)
        os.replace(tmp, _tokens_path())
    except OSError:
        pass


def _token_expired(meta: dict, now: datetime | None = None) -> bool:
    try:
        created = datetime.fromisoformat(meta["created"])
    except (KeyError, ValueError, TypeError):
        return True
    now = now or datetime.now(timezone.utc)
    return (now - created).days >= _TOKEN_TTL_DAYS


def _load_tokens() -> dict:
    """Load persisted tokens, dropping malformed or expired ones."""
    try:
        with open(_tokens_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    now = datetime.now(timezone.utc)
    return {t: m for t, m in data.items()
            if isinstance(m, dict) and m.get("username") and not _token_expired(m, now)}


# Restore persisted tokens at import so sign-ins survive a server restart.
_tokens = _load_tokens()


# ---------------------------------------------------------------------------
# Store I/O
# ---------------------------------------------------------------------------

def _load() -> dict:
    """Load the accounts store, returning a fresh skeleton on any error."""
    try:
        with open(ACCOUNTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        data = {}
    data.setdefault("meta", {})
    data["meta"].setdefault("next_uid", 1)
    data.setdefault("users", {})
    return data


def _save(data: dict) -> None:
    os.makedirs(AUTH_DIR, exist_ok=True)
    tmp = ACCOUNTS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ACCOUNTS_PATH)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def _hash_password(password: str, salt_hex: str, iterations: int = _PBKDF2_ITERATIONS) -> str:
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), iterations
    )
    return dk.hex()


def _verify_password(password: str, record: dict) -> bool:
    try:
        expected = record["hash"]
        salt_hex = record["salt"]
        iterations = int(record.get("iterations", _PBKDF2_ITERATIONS))
    except (KeyError, ValueError, TypeError):
        return False
    actual = _hash_password(password, salt_hex, iterations)
    return hmac.compare_digest(actual, expected)


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def _find_user(data: dict, username: str) -> tuple[str | None, dict | None]:
    """Case-insensitive lookup. Returns (stored_key, record) or (None, None)."""
    target = username.strip().casefold()
    for key, rec in data.get("users", {}).items():
        if key.casefold() == target:
            return key, rec
    return None, None


def _validate_username(username: str) -> str | None:
    """Return an error code, or None if the username is acceptable."""
    if not username or not username.strip():
        return "username_required"
    name = username.strip()
    if len(name) > _USERNAME_MAX:
        return "username_too_long"
    if _BAD_USERNAME_CHARS.search(name):
        return "username_invalid"
    return None


def _issue_token(username: str) -> str:
    token = secrets.token_urlsafe(32)
    with _lock:
        _tokens[token] = {
            "username": username,
            "created": datetime.now(timezone.utc).isoformat(),
        }
        _save_tokens()
    return token


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def register(username: str, password: str) -> dict:
    """Create a new account. Returns {ok, error?, username, uid, token}.

    On success the user is auto-signed-in (a token is issued).
    """
    username = (username or "").strip()
    password = password or ""

    err = _validate_username(username)
    if err:
        return {"ok": False, "error": err}
    if len(password) < _PASSWORD_MIN:
        return {"ok": False, "error": "password_too_short"}

    with _lock:
        data = _load()
        existing_key, _ = _find_user(data, username)
        if existing_key is not None:
            return {"ok": False, "error": "username_taken"}

        uid = f"u{data['meta']['next_uid']}"
        data["meta"]["next_uid"] += 1
        salt_hex = secrets.token_bytes(16).hex()
        data["users"][username] = {
            "uid": uid,
            "salt": salt_hex,
            "hash": _hash_password(password, salt_hex),
            "iterations": _PBKDF2_ITERATIONS,
            "created": datetime.now(timezone.utc).isoformat(),
        }
        _save(data)

    token = _issue_token(username)
    return {"ok": True, "username": username, "uid": uid, "token": token}


def login(username: str, password: str) -> dict:
    """Verify credentials. Returns {ok, error?, username, uid, token}."""
    username = (username or "").strip()
    password = password or ""
    if not username:
        return {"ok": False, "error": "username_required"}

    with _lock:
        data = _load()
        key, rec = _find_user(data, username)
        if rec is None or not _verify_password(password, rec):
            return {"ok": False, "error": "invalid_credentials"}
        uid = rec.get("uid", "")
        display = key  # canonical stored form

    token = _issue_token(display)
    return {"ok": True, "username": display, "uid": uid, "token": token}


def logout(token: str) -> None:
    """Invalidate a session token (no-op if unknown)."""
    if not token:
        return
    with _lock:
        if _tokens.pop(token, None) is not None:
            _save_tokens()


def username_for_token(token: str) -> str | None:
    """Return the username a token authenticates, or None (and drop it if expired)."""
    if not token:
        return None
    with _lock:
        meta = _tokens.get(token)
        if not meta:
            return None
        if _token_expired(meta):
            _tokens.pop(token, None)
            _save_tokens()
            return None
        return meta.get("username")


def uid_for_username(username: str) -> str | None:
    """Return the stable filesystem uid for a username, or None."""
    if not username:
        return None
    with _lock:
        data = _load()
        _, rec = _find_user(data, username)
        return rec.get("uid") if rec else None


def resolve_token(token: str) -> dict | None:
    """Resolve a token to {username, uid}, or None if invalid."""
    username = username_for_token(token)
    if not username:
        return None
    uid = uid_for_username(username)
    if not uid:
        return None
    return {"username": username, "uid": uid}
