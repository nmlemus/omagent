# omagent/cli/tui/app.py
"""omagent TUI — Rich terminal interface for the agentic engine."""
import time
from typing import Callable

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual import work

from omagent.core.events import (
    TextDeltaEvent, ToolCallEvent, ToolResultEvent,
    PermissionDeniedEvent, PermissionPromptEvent, ErrorEvent, DoneEvent,
    SubAgentStartEvent, SubAgentDoneEvent,
)
from omagent.cli.tui.widgets.chat_view import ChatView
from omagent.cli.tui.widgets.sidebar import Sidebar
from omagent.cli.tui.widgets.status_bar import StatusBar
from omagent.cli.tui.widgets.input_area import MessageInput
from omagent.cli.tui.widgets.activity_log import ActivityLog


class OmagentApp(App):
    """The omagent Terminal UI Application."""

    CSS_PATH = "styles.tcss"
    TITLE = "omagent"
    SUB_TITLE = "Oh My Agent"

    BINDINGS = [
        Binding("ctrl+n", "new_session", "New Session"),
        Binding("ctrl+t", "toggle_sidebar", "Sidebar"),
        Binding("ctrl+e", "toggle_activity_log", "Events"),
        Binding("ctrl+q", "quit_app", "Quit"),
        Binding("escape", "focus_input", "Input", show=False),
    ]

    def __init__(
        self,
        loop_factory: Callable,
        pack_name: str = "default",
        session_id: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.loop_factory = loop_factory
        self.pack_name = pack_name
        self._session_id = session_id
        self._agent_loop = None
        self._is_processing = False
        self._total_tokens_in = 0
        self._total_tokens_out = 0
        self._total_cost = 0.0
        self._tool_calls_count = 0
        self._turn_count = 0

    def compose(self) -> ComposeResult:
        from textual.widgets import Header, Footer
        yield Header()
        with Horizontal(id="main-container"):
            with Vertical(id="chat-panel"):
                yield ChatView(id="chat-view")
                yield ActivityLog(id="activity-log", classes="hidden")
                yield MessageInput(id="message-input", placeholder="Type a message... (/ for commands)")
            yield Sidebar(id="sidebar", pack_name=self.pack_name)
        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._init_loop()
        self.query_one("#message-input", MessageInput).focus()
        self._update_sidebar()
        self._update_status_bar_meta()
        self._mount_splash()

    @work(thread=False)
    async def _mount_splash(self) -> None:
        from omagent.cli.tui.widgets.splash import SplashScreen
        chat = self.query_one("#chat-view", ChatView)

        # Load recent sessions
        recent = []
        if self._agent_loop.store:
            try:
                recent = await self._agent_loop.store.list_sessions(limit=5)
            except Exception:
                pass

        splash = SplashScreen(
            pack_name=self.pack_name,
            model=getattr(self._agent_loop.provider, 'model', 'unknown'),
            session_id=self._agent_loop.session.id,
            recent_sessions=recent,
        )
        await chat.mount(splash)

    def _init_loop(self) -> None:
        self._agent_loop = self.loop_factory(self.pack_name, self._session_id)
        self._session_id = self._agent_loop.session.id

    def _update_status_bar_meta(self) -> None:
        """Set static status bar info (model, pack)."""
        try:
            bar = self.query_one("#status-bar", StatusBar)
            bar.set_model(getattr(self._agent_loop.provider, 'model', 'unknown'))
            bar.set_pack(self.pack_name)
            bar.set_turns(self._turn_count)
        except NoMatches:
            pass

    async def on_message_input_user_submitted(self, event: MessageInput.UserSubmitted) -> None:
        message = event.value.strip()
        if not message:
            return

        input_widget = self.query_one("#message-input", MessageInput)
        input_widget.value = ""

        if message.startswith("/"):
            await self._handle_command(message)
            return

        if self._is_processing:
            return

        chat = self.query_one("#chat-view", ChatView)
        chat.add_user_message(message)

        self._is_processing = True
        self._run_agent(message)

    @work(thread=False)
    async def _run_agent(self, message: str) -> None:
        chat = self.query_one("#chat-view", ChatView)
        activity = self._get_activity_log()

        assistant_text = ""
        tool_calls_this_turn = 0
        current_tool_card = None
        turn_start = time.monotonic()

        # Show thinking immediately
        chat.show_thinking("Thinking...")
        self._update_status("thinking...")
        if activity:
            activity.add_entry("LLM call started")

        # Start elapsed timer
        elapsed_timer = self.set_interval(0.5, lambda: self._update_elapsed(turn_start))

        try:
            async for event in self._agent_loop.run(message):
                if isinstance(event, TextDeltaEvent):
                    if not assistant_text:
                        chat.hide_thinking()
                        chat.start_assistant_stream()
                    assistant_text += event.content
                    chat.update_assistant_stream(assistant_text)
                    self._update_status("generating...")

                elif isinstance(event, ToolCallEvent):
                    tool_calls_this_turn += 1
                    self._tool_calls_count += 1

                    # If there was streaming text, finalize it before the tool card
                    if assistant_text:
                        await chat.finalize_assistant_message(assistant_text)
                        assistant_text = ""

                    chat.hide_thinking()
                    chat.add_step_progress(tool_calls_this_turn, None, event.name)
                    current_tool_card = chat.add_tool_call(event.name, event.input)
                    chat.show_thinking(f"Running {event.name}...")
                    self._update_status(f"tool: {event.name}")

                    if activity:
                        activity.add_entry(f"Tool call: {event.name}")

                elif isinstance(event, ToolResultEvent):
                    chat.hide_thinking()
                    chat.update_tool_result(current_tool_card, event.result, event.is_error)
                    self._update_status("processing...")

                    if activity:
                        status = "error" if event.is_error else "ok"
                        activity.add_entry(f"Tool result: {event.tool_name} ({status})")

                elif isinstance(event, PermissionPromptEvent):
                    chat.add_system_message(f"[#ffe082]Permission needed:[/] `{event.tool_name}`")
                    if activity:
                        activity.add_entry(f"Permission prompt: {event.tool_name}")

                elif isinstance(event, PermissionDeniedEvent):
                    chat.add_error_message(f"Permission denied: {event.tool_name}")
                    if activity:
                        activity.add_entry(f"Permission denied: {event.tool_name}")

                elif isinstance(event, ErrorEvent):
                    chat.add_error_message(event.message)
                    if activity:
                        activity.add_entry(f"Error: {event.message[:80]}")

                elif isinstance(event, SubAgentStartEvent):
                    chat.add_system_message(
                        f"[#ce93d8]Sub-agent started:[/] `{event.pack_name}` — {event.task[:100]}"
                    )
                    if activity:
                        activity.add_entry(f"Sub-agent: {event.pack_name}")

                elif isinstance(event, SubAgentDoneEvent):
                    chat.add_system_message(f"[#a5d6a7]Sub-agent done:[/] `{event.pack_name}`")
                    if activity:
                        activity.add_entry(f"Sub-agent done: {event.pack_name}")

                elif isinstance(event, DoneEvent):
                    if assistant_text:
                        await chat.finalize_assistant_message(assistant_text)
                        assistant_text = ""
                    self._turn_count += 1
                    if activity:
                        elapsed = time.monotonic() - turn_start
                        activity.add_entry(f"Turn {self._turn_count} complete ({elapsed:.1f}s)")

        except Exception as e:
            chat.add_error_message(f"Error: {e}")
            if activity:
                activity.add_entry(f"Error: {e}")
        finally:
            chat.hide_thinking()
            elapsed_timer.stop()
            self._is_processing = False
            self._update_status("ready")

            # Update status bar metrics
            try:
                bar = self.query_one("#status-bar", StatusBar)
                bar.set_turns(self._turn_count)
                bar.clear_elapsed()
            except NoMatches:
                pass
            self._update_sidebar()

    def _update_elapsed(self, start: float) -> None:
        """Update elapsed time in status bar."""
        try:
            bar = self.query_one("#status-bar", StatusBar)
            bar.set_elapsed(time.monotonic() - start)
        except NoMatches:
            pass

    def _update_status(self, status: str) -> None:
        try:
            self.query_one("#status-bar", StatusBar).update_status(status)
        except NoMatches:
            pass

    def _get_activity_log(self) -> ActivityLog | None:
        try:
            return self.query_one("#activity-log", ActivityLog)
        except NoMatches:
            return None

    def _update_sidebar(self) -> None:
        try:
            sidebar = self.query_one("#sidebar", Sidebar)
            sidebar.update_info(
                session_id=self._agent_loop.session.id[:12] + "…",
                pack_name=self.pack_name,
                model=getattr(self._agent_loop.provider, 'model', 'unknown'),
                turns=self._turn_count,
                tool_calls=self._tool_calls_count,
                tools=self._agent_loop.registry.names(),
            )
        except NoMatches:
            pass

    async def _handle_command(self, command: str) -> None:
        chat = self.query_one("#chat-view", ChatView)
        parts = command.split()
        cmd = parts[0].lower()

        if cmd == "/help":
            chat.add_system_message(
                "[bold]Commands:[/]\n"
                "  [#a8b4f0]/help[/]           — Show this help\n"
                "  [#a8b4f0]/tools[/]          — List available tools\n"
                "  [#a8b4f0]/session new[/]    — Start new session\n"
                "  [#a8b4f0]/session list[/]   — List sessions\n"
                "  [#a8b4f0]/pack <name>[/]    — Switch domain pack\n"
                "  [#a8b4f0]/model[/]          — Show current model\n"
                "  [#a8b4f0]/clear[/]          — Clear chat\n"
                "  [#a8b4f0]/quit[/]           — Exit\n\n"
                "[dim]Shortcuts:[/] Ctrl+N New | Ctrl+T Sidebar | Ctrl+E Events | Ctrl+Q Quit"
            )
        elif cmd == "/tools":
            schemas = self._agent_loop.registry.get_schemas()
            if schemas:
                lines = ["[bold]Available Tools:[/]\n"]
                for s in schemas:
                    lines.append(f"  [#80cbc4]●[/] [bold]{s['name']}[/] — [dim]{s.get('description', '')[:60]}[/]")
                chat.add_system_message("\n".join(lines))
            else:
                chat.add_system_message("[dim]No tools registered.[/]")
        elif cmd == "/session":
            if len(parts) > 1 and parts[1] == "new":
                self._session_id = None
                self._init_loop()
                self._turn_count = 0
                self._tool_calls_count = 0
                chat.clear_messages()
                chat.add_system_message(f"New session: [#80cbc4]{self._agent_loop.session.id[:8]}…[/]")
                self._update_sidebar()
                self._update_status_bar_meta()
            elif len(parts) > 1 and parts[1] == "list":
                if self._agent_loop.store:
                    sessions = await self._agent_loop.store.list_sessions()
                    if sessions:
                        lines = ["[bold]Recent Sessions:[/]\n"]
                        for s in sessions[:10]:
                            lines.append(f"  [#80cbc4]{s['id'][:12]}…[/] {s['pack_name']} [dim]({s['updated_at'][:16]})[/]")
                        chat.add_system_message("\n".join(lines))
                    else:
                        chat.add_system_message("[dim]No sessions found.[/]")
        elif cmd == "/pack" and len(parts) > 1:
            self.pack_name = parts[1]
            self._session_id = None
            self._init_loop()
            self._turn_count = 0
            self._tool_calls_count = 0
            chat.clear_messages()
            chat.add_system_message(f"Switched to pack: [#a8b4f0]{self.pack_name}[/]")
            self._update_sidebar()
            self._update_status_bar_meta()
        elif cmd == "/model":
            model = getattr(self._agent_loop.provider, 'model', 'unknown')
            chat.add_system_message(f"Model: [bold]{model}[/]")
        elif cmd == "/clear":
            chat.clear_messages()
        elif cmd == "/quit":
            self.exit()
        else:
            chat.add_system_message(f"[#ef9a9a]Unknown command:[/] {cmd}. Type [bold]/help[/]")

    def action_new_session(self) -> None:
        self._session_id = None
        self._init_loop()
        self._turn_count = 0
        self._tool_calls_count = 0
        chat = self.query_one("#chat-view", ChatView)
        chat.clear_messages()
        chat.add_system_message(f"New session: [#80cbc4]{self._agent_loop.session.id[:8]}…[/]")
        self._update_sidebar()
        self._update_status_bar_meta()

    def action_toggle_sidebar(self) -> None:
        self.query_one("#sidebar", Sidebar).toggle_class("hidden")

    def action_toggle_activity_log(self) -> None:
        self.query_one("#activity-log", ActivityLog).toggle_class("hidden")

    def action_quit_app(self) -> None:
        self.exit()

    def action_focus_input(self) -> None:
        self.query_one("#message-input", MessageInput).focus()
