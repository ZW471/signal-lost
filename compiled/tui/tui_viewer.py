#!/usr/bin/env python3
"""
Signal Lost — Compiled TUI Game Screen

Extends the original TUI by replacing the PTY terminal with a ConversationWidget
that communicates directly with the LangGraph agent.

The right-side panels (Identity, Knowledge, Traces, District, etc.) are
inherited unchanged from the original TUI — they still poll session/*.json files.

Refactored from App to Screen so it can be managed by the main SignalLostApp.
"""

from __future__ import annotations

import os
import re
import sys
import threading
from pathlib import Path
from queue import Queue

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Footer, Input, Static, TabbedContent, TabPane
from rich.console import Group
from rich.text import Text

from langchain_core.messages import HumanMessage

# Add parent tui directory to path so we can import original panels
_GAME_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_PARENT_TUI = os.path.join(_GAME_ROOT, "tui")
_COMPILED_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PARENT_TUI not in sys.path:
    sys.path.insert(0, _PARENT_TUI)
if _COMPILED_DIR not in sys.path:
    sys.path.insert(0, _COMPILED_DIR)

# Import all panel widgets and parser from the original TUI
from tui_viewer import (  # noqa: E402
    SessionParser,
    StatusBar,
    IdentityPanel,
    KnowledgePanel,
    TracesPanel,
    DistrictPanel,
    InventoryPanel,
    NetworkPanel,
    WorldPanel,
    LogPanel,
    ConversationPanel as OrigConversationPanel,
    LABELS,
    make_css,
)


# =============================================================================
# CONVERSATION WIDGET (replaces PtyTerminal)
# =============================================================================

CHAT_CSS = """
#chat-panel {
    height: 100%;
    background: #0a0a0f;
}

#chat-messages {
    height: 1fr;
    background: #0a0a0f;
    padding: 1;
    overflow-y: auto;
}

#chat-input {
    dock: bottom;
    margin: 0 1;
}

.msg-player {
    color: #00ffff;
    margin-bottom: 1;
}

.msg-agent {
    color: #e0e0e0;
    margin-bottom: 1;
}

.msg-system {
    color: #ffbf00;
    margin-bottom: 1;
}
"""


class ChatMessage(Static):
    """A single message in the chat."""

    def __init__(self, role: str, content: str, **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.msg_content = content

    def render(self):
        if self.role == "user":
            prefix = Text("\u25b6 YOU: ", style="bold #00ffff")
            body = Text(self.msg_content, style="#00ffff")
        elif self.role == "assistant":
            prefix = Text("\u25c6 SIGNAL LOST: ", style="bold #ff00ff")
            body = Text(self.msg_content, style="#e0e0e0")
        else:
            prefix = Text("\u25cf SYSTEM: ", style="bold #ffbf00")
            body = Text(self.msg_content, style="#ffbf00")

        return Group(prefix + body)


class ThinkingIndicator(Static):
    """Animated thinking indicator shown while the agent is processing."""

    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._frame = 0
        self._timer = None

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.1, self._tick)

    def _tick(self) -> None:
        self._frame = (self._frame + 1) % len(self.SPINNER_FRAMES)
        self.refresh()

    def render(self):
        spinner = self.SPINNER_FRAMES[self._frame]
        return Text(f"  {spinner} decrypting signal...", style="bold #ff00ff")

    def on_unmount(self) -> None:
        if self._timer:
            self._timer.stop()


class StreamingMessage(Static):
    """A message that streams its content character by character."""

    class Done(Message):
        """Posted when streaming is complete."""
        pass

    def __init__(self, role: str, full_content: str, chars_per_tick: int = 3, **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.full_content = full_content
        self._revealed = 0
        self._chars_per_tick = chars_per_tick
        self._timer = None

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.03, self._stream_tick)

    def _stream_tick(self) -> None:
        if self._revealed < len(self.full_content):
            self._revealed = min(self._revealed + self._chars_per_tick, len(self.full_content))
            self.refresh(layout=True)
            # Auto-scroll parent container
            try:
                parent = self.parent
                if isinstance(parent, VerticalScroll):
                    parent.scroll_end(animate=False)
            except Exception:
                pass
        else:
            if self._timer:
                self._timer.stop()
                self._timer = None
            self.post_message(self.Done())

    def render(self):
        visible = self.full_content[:self._revealed]
        if self.role == "assistant":
            prefix = Text("\u25c6 SIGNAL LOST: ", style="bold #ff00ff")
            body = Text(visible, style="#e0e0e0")
        elif self.role == "user":
            prefix = Text("\u25b6 YOU: ", style="bold #00ffff")
            body = Text(visible, style="#00ffff")
        else:
            prefix = Text("\u25cf SYSTEM: ", style="bold #ffbf00")
            body = Text(visible, style="#ffbf00")
        cursor = Text("▌", style="bold #ff00ff") if self._revealed < len(self.full_content) else Text("")
        return Group(prefix + body + cursor)

    def on_unmount(self) -> None:
        if self._timer:
            self._timer.stop()


class AgentResponse(Message):
    """Message posted when the agent produces a response.

    role: "assistant" for normal gameplay turns, "system" for system-event
          turns (resume recap, load context, etc.) — displayed with different styling.
    """

    def __init__(
        self,
        content: str,
        game_over: bool = False,
        ending: str | None = None,
        role: str = "assistant",
        narrative: str = "",
    ):
        super().__init__()
        self.content = content
        self.game_over = game_over
        self.ending = ending
        self.role = role
        self.narrative = narrative


class ChatPanel(Vertical):
    """Chat panel that replaces the PTY terminal."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.message_queue: Queue = Queue()
        self._thinking: ThinkingIndicator | None = None
        self._streaming: StreamingMessage | None = None

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="chat-messages"):
            yield ChatMessage(
                "system",
                "Signal Lost \u2014 Compiled Engine. Type your actions below.",
                classes="msg-system",
            )
        yield Input(
            placeholder="What do you do?",
            id="chat-input",
        )

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the chat display (instant, no streaming)."""
        css_class = f"msg-{role}" if role in ("player", "agent", "system") else "msg-agent"
        actual_role = "user" if role == "player" else role
        msg_widget = ChatMessage(actual_role, content, classes=css_class)
        container = self.query_one("#chat-messages", VerticalScroll)
        container.mount(msg_widget)
        container.scroll_end(animate=False)

    def show_thinking(self) -> None:
        """Show an animated thinking indicator."""
        self.hide_thinking()
        container = self.query_one("#chat-messages", VerticalScroll)
        self._thinking = ThinkingIndicator(classes="msg-system")
        container.mount(self._thinking)
        container.scroll_end(animate=False)

    def hide_thinking(self) -> None:
        """Remove the thinking indicator."""
        if self._thinking is not None:
            self._thinking.remove()
            self._thinking = None

    def add_streaming_message(self, role: str, content: str) -> None:
        """Add a message that streams in character by character."""
        css_class = f"msg-{role}" if role in ("player", "agent", "system") else "msg-agent"
        actual_role = "user" if role == "player" else role
        container = self.query_one("#chat-messages", VerticalScroll)
        self._streaming = StreamingMessage(actual_role, content, classes=css_class)
        container.mount(self._streaming)
        container.scroll_end(animate=False)


# =============================================================================
# GAME SCREEN (was GameTUI App, now a Screen)
# =============================================================================

class GameScreen(Screen):
    """Signal Lost TUI game screen with embedded LangGraph agent."""

    DEFAULT_CSS = make_css(True) + "\n" + CHAT_CSS

    BINDINGS = [
        Binding("ctrl+s", "save_game", "Save", show=True, priority=True),
        Binding("r", "refresh", "Refresh", show=True, priority=False),
        Binding("t", "focus_chat", "Chat", show=True, priority=False),
        Binding("1", "tab_1", "1", show=False),
        Binding("2", "tab_2", "2", show=False),
        Binding("3", "tab_3", "3", show=False),
        Binding("4", "tab_4", "4", show=False),
        Binding("5", "tab_5", "5", show=False),
        Binding("6", "tab_6", "6", show=False),
        Binding("7", "tab_7", "7", show=False),
        Binding("8", "tab_8", "8", show=False),
        Binding("9", "tab_9", "9", show=False),
    ]

    def __init__(
        self,
        session_dir: str,
        graph,
        state: dict,
        refresh_interval: int = 5,
        mode: str = "new_game",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.game_dir = Path(os.path.dirname(session_dir))
        self.session_dir = session_dir
        self.graph = graph
        self.game_state = state
        self.refresh_interval = refresh_interval
        self.mode = mode
        self.parser = SessionParser(self.game_dir)
        self.session_data: dict = {}
        self.lang = "en"
        self._agent_thread: threading.Thread | None = None
        self._pending_game_over: bool = False
        self._pending_ending: str | None = None
        self._game_over: bool = False

        # Load language setting
        settings = self.parser.parse_settings()
        self.lang = settings.get("language", {}).get("tui", "en")
        if self.lang not in LABELS:
            self.lang = "en"

    @property
    def L(self) -> dict:
        return LABELS[self.lang]

    def compose(self) -> ComposeResult:
        yield StatusBar(self.session_data, self.lang, id="status-bar")
        with Horizontal(id="main-container"):
            # Left: Chat panel (replaces PTY)
            with Vertical(id="terminal-panel"):
                yield ChatPanel(id="chat-panel")
            # Right: Game state panels (unchanged from original)
            with Vertical(id="content-panel"):
                L = self.L
                with TabbedContent(
                    L["tab_identity"],
                    L["tab_knowledge"],
                    L["tab_traces"],
                    L["tab_district"],
                    L["tab_inventory"],
                    L["tab_network"],
                    L["tab_world"],
                    L["tab_log"],
                    L["tab_conversations"],
                    id="tabs",
                ):
                    with TabPane(L["tab_identity"], id="tab-identity"):
                        with VerticalScroll():
                            yield IdentityPanel(self.session_data, self.lang, id="panel-identity")
                    with TabPane(L["tab_knowledge"], id="tab-knowledge"):
                        with VerticalScroll():
                            yield KnowledgePanel(self.session_data, self.lang, id="panel-knowledge")
                    with TabPane(L["tab_traces"], id="tab-traces"):
                        with VerticalScroll():
                            yield TracesPanel(self.session_data, self.lang, id="panel-traces")
                    with TabPane(L["tab_district"], id="tab-district"):
                        with VerticalScroll():
                            yield DistrictPanel(self.session_data, self.lang, id="panel-district")
                    with TabPane(L["tab_inventory"], id="tab-inventory"):
                        with VerticalScroll():
                            yield InventoryPanel(self.session_data, self.lang, id="panel-inventory")
                    with TabPane(L["tab_network"], id="tab-network"):
                        with VerticalScroll():
                            yield NetworkPanel(self.session_data, self.lang, id="panel-network")
                    with TabPane(L["tab_world"], id="tab-world"):
                        with VerticalScroll():
                            yield WorldPanel(self.session_data, self.lang, id="panel-world")
                    with TabPane(L["tab_log"], id="tab-log"):
                        with VerticalScroll():
                            yield LogPanel(self.session_data, self.lang, id="panel-log")
                    with TabPane(L["tab_conversations"], id="tab-conversations"):
                        with VerticalScroll(id="conversations-scroll"):
                            yield OrigConversationPanel(self.session_data, self.lang, id="panel-conversations")
        yield Footer()

    def on_mount(self) -> None:
        self._load_data()
        self._update_all_panels()

        if self.refresh_interval > 0:
            self.set_interval(self.refresh_interval, self._periodic_refresh)

        # Focus chat input
        try:
            chat_input = self.query_one("#chat-input", Input)
            chat_input.focus()
        except NoMatches:
            pass

        # Auto-send initial prompt for resume/load modes
        if self.mode in ("resume", "load_game"):
            self._send_resume_prompt()

    def _load_data(self) -> None:
        self.session_data = self.parser.parse_all()

    def _update_all_panels(self) -> None:
        panel_ids = [
            "#status-bar", "#panel-identity", "#panel-knowledge", "#panel-traces",
            "#panel-district", "#panel-inventory", "#panel-network", "#panel-world",
            "#panel-log", "#panel-conversations",
        ]
        for widget_id in panel_ids:
            try:
                widget = self.query_one(widget_id)
                widget.data = self.session_data
                widget.lang = self.lang
                widget.refresh(layout=True)
            except NoMatches:
                pass


    def action_refresh(self) -> None:
        self._load_data()
        self._update_all_panels()
        self.notify("Refreshed", timeout=1.5)

    def _periodic_refresh(self) -> None:
        self._load_data()
        self._update_all_panels()

    def action_focus_chat(self) -> None:
        try:
            self.query_one("#chat-input", Input).focus()
        except NoMatches:
            pass

    def _switch_tab(self, index: int) -> None:
        try:
            tabs = self.query_one("#tabs", TabbedContent)
            tab_ids = [
                "tab-identity", "tab-knowledge", "tab-traces",
                "tab-district", "tab-inventory", "tab-network",
                "tab-world", "tab-log", "tab-conversations",
            ]
            if 0 <= index < len(tab_ids):
                tabs.active = tab_ids[index]
        except NoMatches:
            pass

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Scroll conversation panel to bottom when its tab is selected."""
        if event.pane and event.pane.id == "tab-conversations":
            try:
                self.query_one("#conversations-scroll", VerticalScroll).scroll_end(animate=False)
            except NoMatches:
                pass

    # Tab shortcuts
    def action_tab_1(self): self._switch_tab(0)
    def action_tab_2(self): self._switch_tab(1)
    def action_tab_3(self): self._switch_tab(2)
    def action_tab_4(self): self._switch_tab(3)
    def action_tab_5(self): self._switch_tab(4)
    def action_tab_6(self): self._switch_tab(5)
    def action_tab_7(self): self._switch_tab(6)
    def action_tab_8(self): self._switch_tab(7)
    def action_tab_9(self): self._switch_tab(8)

    # -------------------------------------------------------------------------
    # Save game
    # -------------------------------------------------------------------------

    def action_save_game(self) -> None:
        if self._agent_thread and self._agent_thread.is_alive():
            self.notify("Cannot save while the agent is thinking.", severity="warning", timeout=3)
            return

        from tui.screens import SaveScreen

        alias = self.game_state.get("player", {}).get("alias", "save")
        default_name = re.sub(r"[^\w\-]", "_", alias).lower()
        self.app.push_screen(
            SaveScreen(default_name=default_name, session_dir=self.session_dir),
            callback=self._on_save_result,
        )

    def _on_save_result(self, save_name: str | None) -> None:
        if save_name:
            self.notify(f"Game saved as '{save_name}'", timeout=3)

    # -------------------------------------------------------------------------
    # Resume / Load initial prompt
    # -------------------------------------------------------------------------

    def _build_resume_context(self) -> str:
        """Build a brief context summary from current session state for the resume prompt."""
        player = self.game_state.get("player", {})
        location = self.game_state.get("location", {})
        log = self.game_state.get("log", {})
        traces = self.game_state.get("traces", {})
        world_state = self.game_state.get("world_state", {})

        alias = player.get("alias", "Unknown")
        background = player.get("background", "Unknown")
        district = location.get("district", "Unknown")
        turn = player.get("turn", 1)
        time_of_day = player.get("time", "Unknown")
        integrity = player.get("integrity", {})
        integrity_str = f"{integrity.get('current', '?')}/{integrity.get('max', '?')}" if isinstance(integrity, dict) else str(integrity)

        nexus_alert = world_state.get("nexus_alert", {})
        alert_str = f"{nexus_alert.get('current', 0)}%" if isinstance(nexus_alert, dict) else str(nexus_alert)
        fragment_decay = world_state.get("fragment_decay", {})
        decay_str = f"{fragment_decay.get('current', 0)}%" if isinstance(fragment_decay, dict) else str(fragment_decay)

        discovered = traces.get("total_discovered", "0 / 16")

        # Last log entry
        entries = log.get("entries", [])
        last_event = entries[-1].get("title", "None") if entries else "None"

        # Current scene description
        scene = location.get("description", "")
        area = location.get("area", "")

        return (
            f"Alias: {alias} | Background: {background}\n"
            f"District: {district} | Area: {area}\n"
            f"Turn: {turn} | Time: {time_of_day}\n"
            f"Integrity: {integrity_str} | NEXUS Alert: {alert_str} | Fragment Decay: {decay_str}\n"
            f"Traces: {discovered}\n"
            f"Last event: {last_event}\n"
            f"Scene: {scene}"
        )

    def _send_resume_prompt(self) -> None:
        """Auto-send a prompt to the agent to provide a context recap on resume/load."""
        context = self._build_resume_context()
        resume_instruction = (
            "[RESUMING SESSION] The player is returning to a previously saved game. "
            "Provide a brief atmospheric status recap of their current situation: "
            "who they are, where they are, what was happening, and what they were doing. "
            "Then invite them to take their next action.\n"
            f"Current state summary:\n{context}"
        )

        # Show system message in chat
        try:
            chat = self.query_one("#chat-panel", ChatPanel)
            chat.add_message("system", "Restoring session... loading previous context.")
            chat.show_thinking()
        except NoMatches:
            return

        # Disable input while agent processes
        try:
            self.query_one("#chat-input", Input).disabled = True
        except NoMatches:
            pass

        # Run agent in background thread with the resume prompt
        self._agent_thread = threading.Thread(
            target=self._run_resume_agent, args=(resume_instruction,), daemon=True
        )
        self._agent_thread.start()

    def _run_resume_agent(self, resume_instruction: str) -> None:
        """Run the LangGraph agent with a resume prompt (called in background thread).

        This is a system-event turn — not player input.  It bypasses input_validator,
        is never logged to conversation.jsonl, does not advance the turn counter, and
        its messages are removed from graph state after the turn so they never appear
        in the player's 5-turn history window.
        """
        try:
            self.game_state["messages"].append(HumanMessage(content=resume_instruction))
            self.game_state["skip_conversation_log"] = True
            self.game_state["skip_turn_increment"] = True
            self.game_state["skip_validation"] = True   # System event — bypass validator
            result = self.graph.invoke(self.game_state)
            self.game_state = result

            narrative = result.get("narrative", "")
            game_over = result.get("game_over", False)
            ending = result.get("ending")

            self.post_message(AgentResponse(
                content=narrative or "(No response)",
                game_over=game_over,
                ending=ending,
                role="system",  # Resume recap shown with system styling, not as a game turn
            ))
        except Exception as e:
            self.post_message(AgentResponse(
                content=f"[Engine error: {e}]",
                game_over=False,
                ending=None,
                role="system",
            ))

    # -------------------------------------------------------------------------
    # Agent interaction
    # -------------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input from chat."""
        if event.input.id == "chat-input":
            self._handle_chat_input(event.value)
            event.input.value = ""

    def _handle_chat_input(self, text: str) -> None:
        """Send player input to the LangGraph agent."""
        text = text.strip()
        if not text:
            return
        if self._game_over:
            return

        # Display player message
        try:
            chat = self.query_one("#chat-panel", ChatPanel)
            chat.add_message("player", text)
            chat.show_thinking()
        except NoMatches:
            return

        # Disable input while agent is running
        try:
            self.query_one("#chat-input", Input).disabled = True
        except NoMatches:
            pass

        # Run agent in background thread
        self._agent_thread = threading.Thread(
            target=self._run_agent, args=(text,), daemon=True
        )
        self._agent_thread.start()

    def _run_agent(self, user_input: str) -> None:
        """Run the LangGraph agent (called in background thread)."""
        try:
            self.game_state["messages"].append(HumanMessage(content=user_input))
            result = self.graph.invoke(self.game_state)
            self.game_state = result

            narrative = result.get("narrative", "")
            game_over = result.get("game_over", False)
            ending = result.get("ending")

            self.post_message(AgentResponse(
                content=narrative or "(No response)",
                game_over=game_over,
                ending=ending,
            ))
        except Exception as e:
            self.post_message(AgentResponse(
                content=f"[Engine error: {e}]",
                game_over=False,
                ending=None,
            ))

    def on_agent_response(self, message: AgentResponse) -> None:
        """Handle agent response (posted from background thread)."""
        self._pending_game_over = message.game_over
        self._pending_ending = message.ending
        self._pending_narrative = message.content

        try:
            chat = self.query_one("#chat-panel", ChatPanel)
            chat.hide_thinking()
            # System-event responses (resume/load recap) stream with "system" styling
            chat.add_streaming_message(message.role, message.content)
        except NoMatches:
            # Fallback: re-enable input immediately if chat panel not found
            self._finish_response()

    def on_streaming_message_done(self, message: StreamingMessage.Done) -> None:
        """Called when the streaming text animation completes."""
        self._finish_response()

    def _finish_response(self) -> None:
        """Re-enable input and handle game-over after streaming completes."""
        # Refresh panels after agent turn
        self._load_data()
        self._update_all_panels()

        if getattr(self, "_pending_game_over", False):
            self._game_over = True
            ending = getattr(self, "_pending_ending", None)
            narrative = getattr(self, "_pending_narrative", "")
            # Input stays disabled — game is over; show dedicated screen with final narrative
            from tui.screens import GameOverScreen
            self.app.push_screen(GameOverScreen(ending=ending, narrative=narrative))
        else:
            # Re-enable input only when game is still running
            try:
                self.query_one("#chat-input", Input).disabled = False
                self.query_one("#chat-input", Input).focus()
            except NoMatches:
                pass



# Backward-compatible alias
GameTUI = GameScreen
