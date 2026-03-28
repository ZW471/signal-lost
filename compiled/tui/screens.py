"""
Signal Lost — TUI Menu Screens

StartScreen, NewGameScreen, LoadGameScreen, ProviderScreen, SaveScreen.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Input, Label, OptionList, Select, Static
from textual.widgets.option_list import Option
from rich.text import Text

# ---------------------------------------------------------------------------
# Paths — resolved relative to this file
# ---------------------------------------------------------------------------

_COMPILED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GAME_ROOT = os.path.abspath(os.path.join(_COMPILED_DIR, ".."))
DEFAULT_SESSION_DIR = os.path.join(GAME_ROOT, "session")
SAVES_DIR = os.path.join(GAME_ROOT, "saves")
SETTINGS_DIR = os.path.join(GAME_ROOT, "settings")
ENV_PATH = os.path.join(GAME_ROOT, ".env")
PROVIDER_CONFIG_PATH = os.path.join(SETTINGS_DIR, "provider.json")

# ---------------------------------------------------------------------------
# .env helpers
# ---------------------------------------------------------------------------

def _load_env(path: str) -> dict[str, str]:
    env: dict[str, str] = {}
    if not os.path.isfile(path):
        return env
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def _save_env(path: str, key: str, value: str) -> None:
    env = _load_env(path)
    env[key] = value
    with open(path, "w", encoding="utf-8") as f:
        for k, v in env.items():
            f.write(f"{k}={v}\n")


def _load_provider_config() -> dict:
    try:
        with open(PROVIDER_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_provider_config(provider: str, model: str, **extra) -> None:
    os.makedirs(os.path.dirname(PROVIDER_CONFIG_PATH), exist_ok=True)
    try:
        with open(PROVIDER_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        cfg = {}
    cfg["provider"] = provider
    cfg["model"] = model
    cfg.update(extra)
    with open(PROVIDER_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ---------------------------------------------------------------------------
# Default models per provider
# ---------------------------------------------------------------------------

DEFAULT_MODELS = {
    "openai": "gpt-5.4",
    "anthropic": "claude-sonnet-4-20250514",
    "lmstudio": "local-model",
}

ENV_KEY_NAMES = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "lmstudio": "",
}

# Providers that run locally and don't require an API key
LOCAL_PROVIDERS = {"lmstudio"}


# =============================================================================
# Shared mixin for provider-readiness checks
# =============================================================================

class _ProviderReadyMixin:
    """Shared helper to check if provider is configured and launch directly."""

    def _provider_ready(self) -> bool:
        cfg = _load_provider_config()
        provider = cfg.get("provider")
        model = cfg.get("model")
        if not provider or not model:
            return False
        if provider in LOCAL_PROVIDERS:
            return True
        env_key_name = ENV_KEY_NAMES.get(provider, "")
        if not env_key_name:
            return False
        env = _load_env(ENV_PATH)
        return bool(env.get(env_key_name, "") or os.environ.get(env_key_name, ""))

    def _launch_directly(self, mode: str) -> None:
        cfg = _load_provider_config()
        provider = cfg["provider"]
        model = cfg["model"]
        temperature = cfg.get("temperature", 0.7)
        env_key_name = ENV_KEY_NAMES.get(provider, "")
        env = _load_env(ENV_PATH)
        existing_key = env.get(env_key_name, "") or os.environ.get(env_key_name, "")
        if existing_key:
            os.environ[env_key_name] = existing_key
        self.app.launch_game(mode, provider, model, temperature)


# =============================================================================
# START SCREEN
# =============================================================================

START_CSS = """
StartScreen {
    align: center middle;
    background: #0a0a0f;
}

#start-container {
    width: 60;
    height: auto;
    padding: 2 4;
    border: heavy #ff00ff;
    background: #0d0d1a;
}

#title-art {
    text-align: center;
    color: #ff00ff;
    text-style: bold;
    margin-bottom: 1;
}

#subtitle {
    text-align: center;
    color: #00ffff;
    margin-bottom: 2;
}

.menu-btn {
    width: 100%;
    margin: 1 0;
}

#btn-new {
    background: #1a0033;
    color: #ff00ff;
}

#btn-load {
    background: #001a33;
    color: #00bfff;
}

#btn-resume {
    background: #0d1a00;
    color: #00ff41;
}

#btn-settings {
    background: #1a1a00;
    color: #ffbf00;
}

#btn-quit {
    background: #1a0000;
    color: #ff3333;
}
"""


class StartScreen(_ProviderReadyMixin, Screen):
    DEFAULT_CSS = START_CSS

    BINDINGS = [
        Binding("q", "quit_app", "Quit", show=True),
    ]

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="start-container"):
                yield Static(
                    "███████╗██╗ ██████╗ ███╗   ██╗ █████╗ ██╗\n"
                    "██╔════╝██║██╔════╝ ████╗  ██║██╔══██╗██║\n"
                    "███████╗██║██║  ███╗██╔██╗ ██║███████║██║\n"
                    "╚════██║██║██║   ██║██║╚██╗██║██╔══██║██║\n"
                    "███████║██║╚██████╔╝██║ ╚████║██║  ██║███████╗\n"
                    "╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝\n"
                    "      ██╗      ██████╗ ███████╗████████╗\n"
                    "      ██║     ██╔═══██╗██╔════╝╚══██╔══╝\n"
                    "      ██║     ██║   ██║███████╗   ██║\n"
                    "      ██║     ██║   ██║╚════██║   ██║\n"
                    "      ███████╗╚██████╔╝███████║   ██║\n"
                    "      ╚══════╝ ╚═════╝ ╚══════╝   ╚═╝",
                    id="title-art",
                )
                yield Static("信 号 遗 失", id="subtitle")
                yield Button("NEW GAME", id="btn-new", classes="menu-btn")
                yield Button("LOAD GAME", id="btn-load", classes="menu-btn")
                yield Button("RESUME", id="btn-resume", classes="menu-btn")
                yield Button("SETTINGS", id="btn-settings", classes="menu-btn")
                yield Button("QUIT", id="btn-quit", classes="menu-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-new":
            self.app.push_screen(NewGameScreen())
        elif event.button.id == "btn-load":
            self.app.push_screen(LoadGameScreen())
        elif event.button.id == "btn-resume":
            player_path = os.path.join(DEFAULT_SESSION_DIR, "player.json")
            if os.path.isfile(player_path):
                if self._provider_ready():
                    self._launch_directly("resume")
                else:
                    self.app.push_screen(ProviderScreen(mode="resume"))
            else:
                self.notify("No active session found. Start a new game or load a save.", severity="error", timeout=4)
        elif event.button.id == "btn-settings":
            self.app.push_screen(SettingsScreen())
        elif event.button.id == "btn-quit":
            self.app.exit()

    def action_quit_app(self) -> None:
        self.app.exit()


# =============================================================================
# SETTINGS SCREEN
# =============================================================================

SETTINGS_CSS = """
SettingsScreen {
    align: center middle;
    background: #0a0a0f;
}

#settings-container {
    width: 65;
    height: auto;
    max-height: 90%;
    padding: 2 4;
    border: heavy #ffbf00;
    background: #0d0d1a;
}

#settings-title {
    text-align: center;
    color: #ffbf00;
    text-style: bold;
    margin-bottom: 1;
}

.settings-label {
    color: #ff00ff;
    margin-top: 1;
}

.settings-hint {
    color: #444466;
}

#btn-settings-save {
    margin-top: 2;
    width: 100%;
    background: #1a0033;
    color: #ff00ff;
}

#btn-settings-back {
    margin-top: 1;
    width: 100%;
    background: #1a0000;
    color: #ff3333;
}
"""


def _load_custom_settings() -> dict:
    """Load custom.json settings."""
    custom_path = os.path.join(SETTINGS_DIR, "custom.json")
    try:
        with open(custom_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_custom_settings(settings: dict) -> None:
    """Save settings to custom.json."""
    custom_path = os.path.join(SETTINGS_DIR, "custom.json")
    os.makedirs(os.path.dirname(custom_path), exist_ok=True)
    with open(custom_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


class SettingsScreen(Screen):
    DEFAULT_CSS = SETTINGS_CSS

    BINDINGS = [
        Binding("escape", "go_back", "Back", show=True),
    ]

    def compose(self) -> ComposeResult:
        # Load current settings
        custom = _load_custom_settings()
        provider_cfg = _load_provider_config()
        current_lang = custom.get("language", {}).get("display", "en")
        current_provider = provider_cfg.get("provider", "openai")
        current_model = provider_cfg.get("model", DEFAULT_MODELS.get(current_provider, ""))
        current_temp = str(provider_cfg.get("temperature", 0.7))
        current_base_url = provider_cfg.get("base_url", "http://localhost:1234/v1")

        env = _load_env(ENV_PATH)
        env_key_name = ENV_KEY_NAMES.get(current_provider, "")
        has_key = bool(env.get(env_key_name, "") or os.environ.get(env_key_name, ""))

        with Center():
            with VerticalScroll(id="settings-container"):
                yield Static("SETTINGS / 设置", id="settings-title")

                yield Label("Language / 语言", classes="settings-label")
                yield Select(
                    [
                        ("English", "en"),
                        ("中文", "zh"),
                    ],
                    value=current_lang,
                    id="settings-language",
                )

                yield Label("Provider", classes="settings-label")
                yield Select(
                    [
                        ("OpenAI", "openai"),
                        ("Anthropic", "anthropic"),
                        ("LM Studio (Local)", "lmstudio"),
                    ],
                    value=current_provider,
                    id="settings-provider",
                )

                yield Label("Model", classes="settings-label")
                yield Input(value=current_model, placeholder="Model name", id="settings-model")

                yield Label("Base URL", classes="settings-label", id="settings-label-base-url")
                yield Input(value=current_base_url, placeholder="http://localhost:1234/v1", id="settings-base-url")

                yield Label("API Key", classes="settings-label", id="settings-label-api-key")
                yield Static("(loaded from .env)", classes="settings-hint", id="settings-api-key-hint")
                yield Input(
                    placeholder="Paste your API key (leave empty to keep current)",
                    password=True,
                    id="settings-api-key",
                )

                yield Label("Temperature", classes="settings-label")
                yield Input(value=current_temp, placeholder="0.0 - 1.0", id="settings-temperature")

                yield Button("SAVE / 保存", id="btn-settings-save")
                yield Button("BACK", id="btn-settings-back")

        self.set_timer(0.05, self._update_key_visibility)

    def _update_key_visibility(self) -> None:
        try:
            provider = self.query_one("#settings-provider", Select).value
            is_local = provider in LOCAL_PROVIDERS
            env_key_name = ENV_KEY_NAMES.get(provider, "")
            env = _load_env(ENV_PATH)
            has_key = bool(env.get(env_key_name, "") or os.environ.get(env_key_name, ""))

            key_input = self.query_one("#settings-api-key", Input)
            hint = self.query_one("#settings-api-key-hint", Static)
            label = self.query_one("#settings-label-api-key", Label)
            base_url_input = self.query_one("#settings-base-url", Input)
            base_url_label = self.query_one("#settings-label-base-url", Label)

            # Base URL only shown for local providers
            base_url_input.display = is_local
            base_url_label.display = is_local

            if is_local:
                label.display = False
                key_input.display = False
                hint.display = True
                hint.update("(no API key needed — local server)")
            else:
                label.display = True
                key_input.display = True
                if has_key:
                    key_input.placeholder = "Enter new key to replace existing one"
                    hint.display = True
                    hint.update("(key loaded from .env — enter new key to replace)")
                else:
                    key_input.placeholder = "Paste your API key"
                    hint.display = False
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "settings-provider":
            provider = event.value
            model_input = self.query_one("#settings-model", Input)
            cfg = _load_provider_config()
            if cfg.get("provider") == provider and cfg.get("model"):
                model_input.value = cfg["model"]
            else:
                model_input.value = DEFAULT_MODELS.get(provider, "")
            self._update_key_visibility()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-settings-save":
            self._save()
        elif event.button.id == "btn-settings-back":
            self.action_go_back()

    def _save(self) -> None:
        language = self.query_one("#settings-language", Select).value
        provider = self.query_one("#settings-provider", Select).value
        model = self.query_one("#settings-model", Input).value.strip()
        api_key = self.query_one("#settings-api-key", Input).value.strip()
        base_url = self.query_one("#settings-base-url", Input).value.strip()
        temperature_str = self.query_one("#settings-temperature", Input).value.strip()

        if not model:
            self.notify("Model name cannot be empty.", severity="error", timeout=3)
            return

        try:
            temperature = float(temperature_str)
        except ValueError:
            self.notify("Invalid temperature value.", severity="error", timeout=3)
            return

        # Resolve the API key to use for testing
        if provider not in LOCAL_PROVIDERS:
            env_key_name = ENV_KEY_NAMES.get(provider, "")
            env = _load_env(ENV_PATH)
            effective_key = api_key or env.get(env_key_name, "") or os.environ.get(env_key_name, "")
            if not effective_key:
                self.notify("API key is required.", severity="error", timeout=3)
                return
            # Temporarily set key so the LLM client can use it
            os.environ[env_key_name] = effective_key

        # Test connection before saving
        self.notify("Testing connection...", severity="information", timeout=2)
        self.run_worker(self._test_and_save(
            language, provider, model, api_key, base_url, temperature,
        ), exclusive=True)

    async def _test_and_save(
        self, language: str, provider: str, model: str,
        api_key: str, base_url: str, temperature: float,
    ) -> None:
        from run import test_llm_connection
        import asyncio
        loop = asyncio.get_event_loop()
        test_kwargs = {"temperature": temperature}
        if provider in LOCAL_PROVIDERS and base_url:
            test_kwargs["base_url"] = base_url
        success, error = await loop.run_in_executor(
            None, lambda: test_llm_connection(provider, model, **test_kwargs),
        )
        if not success:
            self.notify(f"Connection failed: {error}", severity="error", timeout=6)
            return

        # Save language to custom.json
        custom = _load_custom_settings()
        if "language" not in custom:
            custom["language"] = {}
        custom["language"]["display"] = language
        custom["language"]["tui"] = language
        _save_custom_settings(custom)

        # Save provider + model + base_url
        extra = {}
        if provider in LOCAL_PROVIDERS and base_url:
            extra["base_url"] = base_url
        _save_provider_config(provider, model, **extra)

        # Save temperature to provider config
        try:
            with open(PROVIDER_CONFIG_PATH, "r", encoding="utf-8") as f:
                pcfg = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pcfg = {}
        pcfg["temperature"] = temperature
        with open(PROVIDER_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(pcfg, f, indent=2)

        # Save API key if provided
        if api_key and provider not in LOCAL_PROVIDERS:
            env_key_name = ENV_KEY_NAMES.get(provider, "")
            _save_env(ENV_PATH, env_key_name, api_key)
            os.environ[env_key_name] = api_key

        self.notify("Connection OK — settings saved!", severity="information", timeout=3)
        self.app.pop_screen()

    def action_go_back(self) -> None:
        self.app.pop_screen()


# =============================================================================
# NEW GAME SCREEN
# =============================================================================

NEW_GAME_CSS = """
NewGameScreen {
    align: center middle;
    background: #0a0a0f;
}

#newgame-container {
    width: 70;
    height: auto;
    max-height: 90%;
    padding: 2 4;
    border: heavy #00ffff;
    background: #0d0d1a;
}

#newgame-title {
    text-align: center;
    color: #00ffff;
    text-style: bold;
    margin-bottom: 1;
}

.form-label {
    color: #ff00ff;
    margin-top: 1;
}

.form-desc {
    color: #666688;
    margin-bottom: 0;
}

#btn-begin {
    margin-top: 2;
    width: 100%;
    background: #1a0033;
    color: #ff00ff;
}

#btn-newgame-back {
    margin-top: 1;
    width: 100%;
    background: #1a0000;
    color: #ff3333;
}
"""


class NewGameScreen(_ProviderReadyMixin, Screen):
    DEFAULT_CSS = NEW_GAME_CSS

    BINDINGS = [
        Binding("escape", "go_back", "Back", show=True),
    ]

    def compose(self) -> ComposeResult:
        # Pre-populate language from global settings
        custom = _load_custom_settings()
        current_lang = custom.get("language", {}).get("display", "en")

        with Center():
            with VerticalScroll(id="newgame-container"):
                yield Static("CHARACTER CREATION / 角色创建", id="newgame-title")

                yield Label("Name / 姓名", classes="form-label")
                yield Input(placeholder="What is your name?", id="input-name")

                yield Label("Alias / 化名", classes="form-label")
                yield Input(placeholder="What do they call you on the street?", id="input-alias")

                yield Label("Background / 背景", classes="form-label")
                yield Select(
                    [
                        ("Street Runner / 街头行者 — You know the alleys and back doors", "street_runner"),
                        ("Corporate Exile / 企业流亡者 — You fled from the towers", "corporate_exile"),
                        ("Netrunner / 网行者 — You lived in data once", "netrunner"),
                    ],
                    value="street_runner",
                    id="select-background",
                )

                yield Label("Difficulty / 难度", classes="form-label")
                yield Select(
                    [
                        ("Paranoid / 偏执 — Merciful (Integrity: 4, hints)", "paranoid"),
                        ("Cautious / 谨慎 — Careful (Integrity: 3, subtle hints)", "cautious"),
                        ("Standard / 标准 — No safety net (Integrity: 3)", "standard"),
                        ("Reckless / 鲁莽 — Already dead (Integrity: 2)", "reckless"),
                    ],
                    value="standard",
                    id="select-difficulty",
                )

                yield Label("Language / 语言", classes="form-label")
                yield Select(
                    [
                        ("English", "en"),
                        ("中文", "zh"),
                    ],
                    value=current_lang,
                    id="select-language",
                )

                yield Button("BEGIN / 开始", id="btn-begin")
                yield Button("BACK", id="btn-newgame-back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-begin":
            name = self.query_one("#input-name", Input).value.strip()
            alias = self.query_one("#input-alias", Input).value.strip()
            if not name:
                self.notify("Name cannot be empty.", severity="error", timeout=3)
                return
            if not alias:
                alias = name

            self.app.new_game_config = {
                "name": name,
                "alias": alias,
                "background": self.query_one("#select-background", Select).value,
                "difficulty": self.query_one("#select-difficulty", Select).value,
                "language": self.query_one("#select-language", Select).value,
            }
            if self._provider_ready():
                self._launch_directly("new_game")
            else:
                self.app.push_screen(ProviderScreen(mode="new_game"))
        elif event.button.id == "btn-newgame-back":
            self.action_go_back()

    def action_go_back(self) -> None:
        self.app.pop_screen()


# =============================================================================
# LOAD GAME SCREEN
# =============================================================================

LOAD_GAME_CSS = """
LoadGameScreen {
    align: center middle;
    background: #0a0a0f;
}

#load-container {
    width: 70;
    height: auto;
    max-height: 80%;
    padding: 2 4;
    border: heavy #00bfff;
    background: #0d0d1a;
}

#load-title {
    text-align: center;
    color: #00bfff;
    text-style: bold;
    margin-bottom: 1;
}

#save-list {
    height: auto;
    max-height: 20;
    margin: 1 0;
}

#no-saves {
    text-align: center;
    color: #666688;
    margin: 2 0;
}

#btn-load-back {
    margin-top: 1;
    width: 100%;
    background: #1a0000;
    color: #ff3333;
}
"""


def _read_json_safe(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


class LoadGameScreen(_ProviderReadyMixin, Screen):
    DEFAULT_CSS = LOAD_GAME_CSS

    BINDINGS = [
        Binding("escape", "go_back", "Back", show=True),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._save_dirs: list[str] = []

    def compose(self) -> ComposeResult:
        saves: list[tuple[str, str]] = []  # (display_text, save_dir_path)

        if os.path.isdir(SAVES_DIR):
            for entry in sorted(os.listdir(SAVES_DIR)):
                save_path = os.path.join(SAVES_DIR, entry)
                if not os.path.isdir(save_path):
                    continue
                player = _read_json_safe(os.path.join(save_path, "player.json"))
                world = _read_json_safe(os.path.join(save_path, "world_state.json"))
                traces = _read_json_safe(os.path.join(save_path, "traces.json"))

                alias = player.get("alias", player.get("name", "???"))
                bg = player.get("background", "?")
                turn = player.get("turn", "?")
                integrity = player.get("integrity", "?")
                int_str = f"{integrity.get('current', '?')}/{integrity.get('max', '?')}" if isinstance(integrity, dict) else str(integrity)
                alert = world.get("nexus_alert", {})
                alert_val = alert.get("current", alert) if isinstance(alert, dict) else alert
                total_traces = traces.get("total_discovered", "?")

                line = f"{entry}  |  {alias} ({bg})  |  Turn {turn}  |  HP {int_str}  |  Alert {alert_val}%  |  Traces {total_traces}"
                saves.append((line, save_path))

        with Center():
            with Vertical(id="load-container"):
                yield Static("LOAD GAME / 读取存档", id="load-title")
                if saves:
                    options = []
                    for display, path in saves:
                        options.append(Option(display, id=path))
                        self._save_dirs.append(path)
                    yield OptionList(*options, id="save-list")
                else:
                    yield Static("No saves found. Start a new game first.", id="no-saves")
                yield Button("BACK", id="btn-load-back")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        idx = event.option_index
        if 0 <= idx < len(self._save_dirs):
            self.app.load_save_path = self._save_dirs[idx]
            if self._provider_ready():
                self._launch_directly("load_game")
            else:
                self.app.push_screen(ProviderScreen(mode="load_game"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-load-back":
            self.action_go_back()

    def action_go_back(self) -> None:
        self.app.pop_screen()


# =============================================================================
# PROVIDER SCREEN
# =============================================================================

PROVIDER_CSS = """
ProviderScreen {
    align: center middle;
    background: #0a0a0f;
}

#provider-container {
    width: 65;
    height: auto;
    padding: 2 4;
    border: heavy #ffbf00;
    background: #0d0d1a;
}

#provider-title {
    text-align: center;
    color: #ffbf00;
    text-style: bold;
    margin-bottom: 1;
}

.prov-label {
    color: #ff00ff;
    margin-top: 1;
}

.prov-hint {
    color: #444466;
}

#btn-launch {
    margin-top: 2;
    width: 100%;
    background: #1a0033;
    color: #ff00ff;
}

#btn-provider-back {
    margin-top: 1;
    width: 100%;
    background: #1a0000;
    color: #ff3333;
}

#api-key-row {
    height: auto;
}
"""


class ProviderScreen(Screen):
    DEFAULT_CSS = PROVIDER_CSS

    BINDINGS = [
        Binding("escape", "go_back", "Back", show=True),
    ]

    def __init__(self, mode: str, **kwargs):
        super().__init__(**kwargs)
        self.mode = mode

    def compose(self) -> ComposeResult:
        cfg = _load_provider_config()
        saved_provider = cfg.get("provider", "openai")
        saved_model = cfg.get("model", DEFAULT_MODELS.get(saved_provider, "gpt-5.4"))
        saved_base_url = cfg.get("base_url", "http://localhost:1234/v1")

        env = _load_env(ENV_PATH)
        env_key_name = ENV_KEY_NAMES.get(saved_provider, "")
        has_key = bool(env.get(env_key_name, "") or os.environ.get(env_key_name, ""))

        with Center():
            with Vertical(id="provider-container"):
                yield Static("LLM CONFIGURATION", id="provider-title")

                yield Label("Provider", classes="prov-label")
                yield Select(
                    [
                        ("OpenAI", "openai"),
                        ("Anthropic", "anthropic"),
                        ("LM Studio (Local)", "lmstudio"),
                    ],
                    value=saved_provider,
                    id="select-provider",
                )

                yield Label("Model", classes="prov-label")
                yield Input(value=saved_model, placeholder="Model name", id="input-model")

                yield Label("Base URL", classes="prov-label", id="label-base-url")
                yield Input(value=saved_base_url, placeholder="http://localhost:1234/v1", id="input-base-url")

                yield Label("API Key", classes="prov-label", id="label-api-key")
                yield Static("(loaded from .env)", classes="prov-hint", id="api-key-hint")
                yield Input(
                    placeholder="Paste your API key",
                    password=True,
                    id="input-api-key",
                )

                yield Label("Temperature", classes="prov-label")
                yield Input(value="0.7", placeholder="0.0 - 1.0", id="input-temperature")

                yield Button("LAUNCH GAME / 启动游戏", id="btn-launch")
                yield Button("BACK", id="btn-provider-back")

        # Schedule post-mount visibility update
        self.set_timer(0.05, self._update_key_visibility)

    def _update_key_visibility(self) -> None:
        provider = self.query_one("#select-provider", Select).value
        is_local = provider in LOCAL_PROVIDERS
        env_key_name = ENV_KEY_NAMES.get(provider, "")
        env = _load_env(ENV_PATH)
        has_key = bool(env.get(env_key_name, "") or os.environ.get(env_key_name, ""))

        try:
            key_input = self.query_one("#input-api-key", Input)
            hint = self.query_one("#api-key-hint", Static)
            label = self.query_one("#label-api-key", Label)
            base_url_input = self.query_one("#input-base-url", Input)
            base_url_label = self.query_one("#label-base-url", Label)

            # Base URL only shown for local providers
            base_url_input.display = is_local
            base_url_label.display = is_local

            if is_local:
                key_input.display = False
                label.display = False
                hint.display = True
                hint.update("(no API key needed — local server)")
            else:
                label.display = True
                key_input.display = True
                if has_key:
                    key_input.placeholder = "Enter new key to replace existing one"
                    hint.display = True
                    hint.update("(key loaded from .env — enter new key to replace)")
                else:
                    key_input.placeholder = "Paste your API key"
                    hint.display = False
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "select-provider":
            provider = event.value
            model_input = self.query_one("#input-model", Input)
            cfg = _load_provider_config()
            if cfg.get("provider") == provider and cfg.get("model"):
                model_input.value = cfg["model"]
            else:
                model_input.value = DEFAULT_MODELS.get(provider, "")
            self._update_key_visibility()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-launch":
            self._launch()
        elif event.button.id == "btn-provider-back":
            self.action_go_back()

    def _launch(self) -> None:
        provider = self.query_one("#select-provider", Select).value
        model = self.query_one("#input-model", Input).value.strip()
        api_key = self.query_one("#input-api-key", Input).value.strip()
        base_url = self.query_one("#input-base-url", Input).value.strip()
        temperature_str = self.query_one("#input-temperature", Input).value.strip()

        if not model:
            self.notify("Model name cannot be empty.", severity="error", timeout=3)
            return

        try:
            temperature = float(temperature_str)
        except ValueError:
            self.notify("Invalid temperature value.", severity="error", timeout=3)
            return

        # Resolve API key (not needed for local providers)
        if provider not in LOCAL_PROVIDERS:
            env_key_name = ENV_KEY_NAMES.get(provider, "")
            env = _load_env(ENV_PATH)
            effective_key = api_key or env.get(env_key_name, "") or os.environ.get(env_key_name, "")

            if not effective_key:
                self.notify("API key is required. Paste it above or set it in .env.", severity="error", timeout=4)
                return
            # Temporarily set key so the LLM client can use it
            os.environ[env_key_name] = effective_key

        # Test connection before launching
        self.notify("Testing connection...", severity="information", timeout=2)
        self.run_worker(self._test_and_launch(
            provider, model, api_key, base_url, temperature,
        ), exclusive=True)

    async def _test_and_launch(
        self, provider: str, model: str,
        api_key: str, base_url: str, temperature: float,
    ) -> None:
        import asyncio
        from run import test_llm_connection
        loop = asyncio.get_event_loop()
        test_kwargs = {"temperature": temperature}
        if provider in LOCAL_PROVIDERS and base_url:
            test_kwargs["base_url"] = base_url
        success, error = await loop.run_in_executor(
            None, lambda: test_llm_connection(provider, model, **test_kwargs),
        )
        if not success:
            self.notify(f"Connection failed: {error}", severity="error", timeout=6)
            return

        # Save API key if user provided a new one
        if api_key and provider not in LOCAL_PROVIDERS:
            env_key_name = ENV_KEY_NAMES.get(provider, "")
            _save_env(ENV_PATH, env_key_name, api_key)
            os.environ[env_key_name] = api_key

        # Persist provider + model + base_url globally
        extra = {}
        if provider in LOCAL_PROVIDERS and base_url:
            extra["base_url"] = base_url
        _save_provider_config(provider, model, **extra)

        # Delegate to the app
        self.app.launch_game(self.mode, provider, model, temperature)

    def action_go_back(self) -> None:
        self.app.pop_screen()


# =============================================================================
# SAVE SCREEN (modal during gameplay)
# =============================================================================

SAVE_CSS = """
SaveScreen {
    align: center middle;
}

#save-modal {
    width: 50;
    height: auto;
    padding: 2 4;
    border: heavy #00ff41;
    background: #0d0d1a;
}

#save-title {
    text-align: center;
    color: #00ff41;
    text-style: bold;
    margin-bottom: 1;
}

#btn-save-confirm {
    margin-top: 1;
    width: 100%;
    background: #0d1a00;
    color: #00ff41;
}

#btn-save-cancel {
    margin-top: 1;
    width: 100%;
    background: #1a0000;
    color: #ff3333;
}
"""


class SaveScreen(ModalScreen[str | None]):
    DEFAULT_CSS = SAVE_CSS

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    def __init__(self, default_name: str = "save", session_dir: str = "", **kwargs):
        super().__init__(**kwargs)
        self.default_name = default_name
        self.session_dir = session_dir

    def compose(self) -> ComposeResult:
        with Vertical(id="save-modal"):
            yield Static("SAVE GAME / 保存游戏", id="save-title")
            yield Label("Save name:", classes="prov-label")
            yield Input(value=self.default_name, placeholder="Save name", id="input-save-name")
            yield Button("SAVE", id="btn-save-confirm")
            yield Button("CANCEL", id="btn-save-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save-confirm":
            self._do_save()
        elif event.button.id == "btn-save-cancel":
            self.dismiss(None)

    def _do_save(self) -> None:
        from state import save_game_to_slot

        name = self.query_one("#input-save-name", Input).value.strip()
        name = re.sub(r"[^\w\-]", "_", name)
        if not name:
            self.notify("Save name cannot be empty.", severity="error", timeout=3)
            return

        try:
            save_game_to_slot(self.session_dir, name, SAVES_DIR)
            self.dismiss(name)
        except Exception as e:
            self.notify(f"Save failed: {e}", severity="error", timeout=4)

    def action_cancel(self) -> None:
        self.dismiss(None)


# =============================================================================
# GAME OVER SCREEN (modal)
# =============================================================================

_ENDING_META: dict[str, tuple[str, str]] = {
    "death":        ("SIGNAL TERMINATED / 信号终止", "bad"),
    "liberation":   ("LIBERATION / 解放", "bad"),
    "ascension":    ("ASCENSION / 升华", "bad"),
    "order":        ("ORDER / 秩序", "bad"),
    "purification": ("PURIFICATION / 净化", "bad"),
    "silence":      ("SILENCE / 沉默", "neutral"),
    "exile":        ("EXILE / 流放", "neutral"),
    "symbiosis":    ("SYMBIOSIS / 共生", "good"),
    "the_bridge":   ("THE BRIDGE / 桥", "good"),
}

_ENDING_DESC: dict[str, str] = {
    "death":        "Your signal has been terminated. The city swallows another ghost.",
    "liberation":   "A reckless strike. NEXUS crumbles — and so does everything else. Was this freedom?",
    "ascension":    "You forced the merge before understanding what you were becoming. The fragments consume you.",
    "order":        "You chose compliance. NEXUS wins. Your memory will be useful to them.",
    "purification": "You destroyed what you didn't understand. The signal goes quiet forever.",
    "silence":      "A hundred turns pass. You drift through the city like smoke. Nothing resolved.",
    "exile":        "Neo-Kowloon fades behind you. Some truths are better left buried.",
    "symbiosis":    "You found balance. The fragment lives. You live. A quiet coexistence in the noise of the city.",
    "the_bridge":   "Every truth uncovered. Every fragment understood. You become the bridge between worlds.",
}

GAME_OVER_CSS = """
GameOverScreen {
    align: center middle;
    background: rgba(0,0,0,0.88);
}

#gameover-box {
    width: 72;
    max-height: 80%;
    padding: 3 5;
    border: heavy #ff0000;
    background: #0d0000;
}

#gameover-box.ending-neutral {
    border: heavy #ffbf00;
    background: #0d0d00;
}

#gameover-box.ending-good {
    border: heavy #00ff41;
    background: #000d00;
}

#gameover-header {
    text-align: center;
    color: #ff3333;
    text-style: bold;
    margin-bottom: 1;
}

#gameover-header.ending-neutral { color: #ffbf00; }
#gameover-header.ending-good    { color: #00ff41; }

#gameover-name {
    text-align: center;
    color: #ff6666;
    text-style: bold;
    margin-bottom: 1;
}

#gameover-name.ending-neutral { color: #ffdd88; }
#gameover-name.ending-good    { color: #88ff88; }

#gameover-narrative {
    color: #ccccdd;
    margin-bottom: 1;
    padding: 1 2;
    background: #0a0a12;
    border: solid #333344;
}

#gameover-desc {
    text-align: center;
    color: #888899;
    margin-bottom: 2;
    padding: 0 2;
}

#btn-go-menu {
    margin-top: 1;
    width: 100%;
    background: #1a0000;
    color: #ff6666;
}

#btn-go-menu.ending-neutral { background: #1a1a00; color: #ffdd88; }
#btn-go-menu.ending-good    { background: #001a00; color: #88ff88; }

#btn-go-quit {
    margin-top: 1;
    width: 100%;
    background: #111111;
    color: #555555;
}
"""


class GameOverScreen(ModalScreen):
    DEFAULT_CSS = GAME_OVER_CSS

    def __init__(self, ending: str | None = None, narrative: str = "", **kwargs):
        super().__init__(**kwargs)
        self._ending = ending or "death"
        self._narrative = narrative

    def compose(self) -> ComposeResult:
        name, etype = _ENDING_META.get(self._ending, (self._ending.upper(), "bad"))
        desc = _ENDING_DESC.get(self._ending, "The signal fades into static.")
        cls = f"ending-{etype}"

        with Vertical(id="gameover-box", classes=cls):
            yield Static("◆  G A M E   O V E R  ◆", id="gameover-header", classes=cls)
            yield Static(name, id="gameover-name", classes=cls)
            if self._narrative:
                yield Static(self._narrative, id="gameover-narrative")
            yield Static(desc, id="gameover-desc")
            yield Button("MAIN MENU / 主菜单", id="btn-go-menu", classes=cls)
            yield Button("QUIT / 退出", id="btn-go-quit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-go-menu":
            self.app.switch_screen(StartScreen())
        elif event.button.id == "btn-go-quit":
            self.app.exit()
