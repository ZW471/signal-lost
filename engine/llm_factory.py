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


def load_settings(settings_dir: str | None = None) -> dict:
    """Load merged settings (default + custom)."""
    sd = settings_dir or SETTINGS_DIR
    default = _read_json(os.path.join(sd, "default.json"))
    custom = _read_json(os.path.join(sd, "custom.json"))
    merged = {**default}
    for k, v in custom.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = {**merged[k], **v}
        else:
            merged[k] = v
    return merged


def load_provider_config(settings_dir: str | None = None) -> dict:
    """Load provider configuration."""
    sd = settings_dir or SETTINGS_DIR
    return _read_json(os.path.join(sd, "provider.json"))


# ---------------------------------------------------------------------------
# LLM creation
# ---------------------------------------------------------------------------

def create_llm(provider: str, model: str, **kwargs: Any):
    """Create an LLM instance for the given provider.

    Supported providers: anthropic, openai, lmstudio, claude-code.
    """
    if provider == "claude-code":
        from tests.scripts.claude_llm import ClaudeCodeLLM
        return ClaudeCodeLLM(model_name=model)
    elif provider == "anthropic":
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
