"""
Signal Lost — Shared LLM Factory & Configuration

Centralizes LLM creation, .env loading, and settings management.
Previously duplicated across compiled/run.py, compiled/play_headless.py, and gui/server.py.
"""

from __future__ import annotations

import json
import os
from typing import Any


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

GAME_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SETTINGS_DIR = os.path.join(GAME_ROOT, "settings")
# Per-user setting overrides live here (gitignored). The files under SETTINGS_DIR
# itself (default.json / custom.json / provider.json) are read-only TEMPLATES that
# ship with the repo; a player's own changes are written per-user under this dir so
# they never modify the committed templates or show up as git changes.
USER_SETTINGS_DIR = os.path.join(SETTINGS_DIR, "users")
ENV_PATH = os.path.join(GAME_ROOT, ".env")


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def load_env(env_path: str | None = None) -> None:
    """Parse a .env file and set missing keys in os.environ."""
    path = env_path or ENV_PATH
    if not os.path.exists(path):
        return
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip()
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            if key not in os.environ:
                os.environ[key] = val


def save_env_key(key: str, value: str, env_path: str | None = None) -> None:
    """Persist an env var to the .env file."""
    path = env_path or ENV_PATH
    lines: list[str] = []
    found = False
    if os.path.exists(path):
        with open(path, "r") as f:
            for line in f:
                if line.strip().startswith(key + "="):
                    lines.append(f"{key}={value}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        lines.append(f"{key}={value}\n")
    with open(path, "w") as f:
        f.writelines(lines)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def _read_json(path: str) -> dict:
    """Read a JSON file, returning {} if missing or invalid."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _deep_merge(base: dict, override: dict) -> dict:
    """Return base with override layered on top (one level deep on nested dicts)."""
    merged = {**base}
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = {**merged[k], **v}
        else:
            merged[k] = v
    return merged


def _safe_uid(uid: str | None) -> str:
    """A filesystem-safe per-user key (no path separators / traversal)."""
    if uid and all(c.isalnum() or c in ("-", "_") for c in uid):
        return uid
    return "_local"


def user_settings_dir(uid: str | None) -> str:
    """Directory holding a single user's setting overrides (gitignored).

    Logged-out / no-uid contexts share ``_local`` so the committed templates are
    still never overwritten."""
    return os.path.join(USER_SETTINGS_DIR, _safe_uid(uid))


def save_user_provider(uid: str | None, cfg: dict) -> None:
    """Persist a user's provider choice to their per-user override file."""
    d = user_settings_dir(uid)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "provider.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def save_user_custom(uid: str | None, updates: dict) -> dict:
    """Deep-merge *updates* into a user's per-user custom-settings override and
    persist it. Returns the merged per-user override."""
    d = user_settings_dir(uid)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "custom.json")
    merged = _deep_merge(_read_json(path), updates)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged


def load_settings(settings_dir: str | None = None, uid: str | None = None) -> dict:
    """Load merged settings: committed default + custom templates, then (when a
    *uid* is given) that user's per-user override layered on top."""
    sd = settings_dir or SETTINGS_DIR
    merged = _deep_merge(
        _read_json(os.path.join(sd, "default.json")),
        _read_json(os.path.join(sd, "custom.json")),
    )
    if uid is not None:
        merged = _deep_merge(
            merged, _read_json(os.path.join(user_settings_dir(uid), "custom.json")),
        )
    return merged


def load_provider_config(settings_dir: str | None = None, uid: str | None = None) -> dict:
    """Load the provider config: committed template, then (when a *uid* is given)
    that user's per-user provider override layered on top."""
    sd = settings_dir or SETTINGS_DIR
    cfg = _read_json(os.path.join(sd, "provider.json"))
    if uid is not None:
        override = _read_json(os.path.join(user_settings_dir(uid), "provider.json"))
        if override:
            cfg = {**cfg, **override}
    return cfg


# Default model per provider — used when provider.json omits "model".
DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-6-20250514",
    "claude-code": "sonnet",
    "codex": "gpt-5.5",
    "openai": "gpt-5.4",
    "openrouter": "openai/gpt-5.4",
    "local": "[model]",
    "lmstudio": "[model]",
}


def default_model_for(provider: str) -> str:
    """Return the default model name for *provider*."""
    return DEFAULT_MODELS.get(provider, "gpt-5.4")


# Providers that hit a local CLI or a local server — no API spend at the
# OpenAI/Anthropic gateway, so the cost tracker should treat them as zero-cost.
ZERO_COST_PROVIDERS: set[str] = {"claude-code", "codex", "local", "lmstudio"}


# Providers that authenticate via a CLI's own OAuth flow rather than an
# API key set in the GUI — the API-key form field is hidden for these.
OAUTH_CLI_PROVIDERS: set[str] = {"claude-code", "codex"}


# Providers that run on the single-call BYPASS engine (engine/claude_code_engine.py)
# rather than the full LangGraph pipeline. Only the OAuth CLI backends bypass: they
# expose `_call_claude` and a single CLI invocation per turn is the whole point of
# using them. Every API provider (openrouter, openai, anthropic, local) runs the
# full 11-node LangGraph pipeline with tool-calling.
BYPASS_PROVIDERS: set[str] = set(OAUTH_CLI_PROVIDERS)


# ---------------------------------------------------------------------------
# LLM creation
# ---------------------------------------------------------------------------

def create_llm(provider: str, model: str, **kwargs: Any):
    """Create an LLM instance for the given provider.

    Supported providers:
        - anthropic           (API key)
        - claude-code         (Claude Code CLI, OAuth via `claude /login`)
        - codex               (OpenAI Codex CLI, OAuth via `codex login`)
        - openai              (API key)
        - openrouter          (API key, openrouter.ai gateway)
        - local / lmstudio    (LM Studio / Ollama / vLLM at base_url)
    """
    if provider == "claude-code":
        from tests.scripts.claude_llm import ClaudeCodeLLM
        return ClaudeCodeLLM(model_name=model)
    elif provider == "codex":
        from tests.scripts.codex_llm import CodexCLILLM
        # Codex CLI does not accept a temperature flag, so silently drop it.
        kwargs.pop("temperature", None)
        return CodexCLILLM(model_name=model, **kwargs)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, **kwargs)
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model, **kwargs)
    elif provider == "openrouter":
        from langchain_openai import ChatOpenAI
        # OpenRouter is OpenAI-API-compatible — point ChatOpenAI at the
        # OpenRouter gateway and pass OPENROUTER_API_KEY (falling back to
        # OPENAI_API_KEY for backwards compat).
        base_url = kwargs.pop("base_url", "https://openrouter.ai/api/v1")
        api_key = kwargs.pop("api_key", None) \
            or os.environ.get("OPENROUTER_API_KEY") \
            or os.environ.get("OPENAI_API_KEY") \
            or "not-needed"
        # Bound each call so a hung/stalled openrouter request can't wedge a turn
        # for many minutes (observed ~28-min hangs on weak models with no timeout).
        kwargs.setdefault("timeout", 300)
        kwargs.setdefault("max_retries", 2)
        return ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
            **kwargs,
        )
    elif provider in ("local", "lmstudio"):
        from langchain_openai import ChatOpenAI
        base_url = kwargs.pop("base_url", "http://localhost:1234/v1")
        return ChatOpenAI(model=model, base_url=base_url, api_key="not-needed", **kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")
