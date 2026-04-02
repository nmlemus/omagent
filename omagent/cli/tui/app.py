# omagent/cli/tui/app.py
"""omagent TUI — Rich terminal interface for the agentic engine."""
import asyncio
import uuid
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


class OmagentApp(App):
    """The omagent Terminal UI Application."""

    CSS_PATH = "styles.tcss"

    TITLE = "omagent"
    SUB_TITLE = "Oh My Agent"

    BINDINGS = [
        Binding("ctrl+n", "new_session", "New Session"),
        Binding("ctrl+t", "toggle_sidebar", "Toggle Sidebar"),
        Binding("ctrl+l", "list_sessions", "Sessions"),
        Binding("ctrl+q", "quit_app", "Quit"),
        Binding("escape", "focus_input", "Focus Input", show=False),
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
                yield MessageInput(id="message-input", placeholder="Type a message... (/ for commands)")
            yield Sidebar(id="sidebar", pack_name=self.pack_name)
        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize on mount."""
        self._init_loop()
        self.query_one("#message-input", MessageInput).focus()
        chat = self.query_one("#chat-view", ChatView)
        chat.add_system_message(
            f"Welcome to [bold]omagent[/bold] — Oh My Agent\n\n"
            f"Pack: [cyan]{self.pack_name}[/cyan] | Session: [cyan]{self._agent_loop.session.id[:8]}…[/cyan]\n\n"
            f"Type a message to start. Use [bold]/help[/bold] for commands."
        )
        self._update_sidebar()

    def _init_loop(self) -> None:
        """Create a new agent loop."""
        self._agent_loop = self.loop_factory(self.pack_name, self._session_id)
        self._session_id = self._agent_loop.session.id

    async def on_message_input_user_submitted(self, event: MessageInput.UserSubmitted) -> None:
        """Handle message submission from input."""
        message = event.value.strip()
        if not message:
            return

        # Clear input
        input_widget = self.query_one("#message-input", MessageInput)
        input_widget.value = ""

        # Handle slash commands
        if message.startswith("/"):
            await self._handle_command(message)
            return

        if self._is_processing:
            return

        # Show user message
        chat = self.query_one("#chat-view", ChatView)
        chat.add_user_message(message)

        # Process with agent
        self._is_processing = True
        self._update_status("thinking...")
        self._run_agent(message)

    @work(thread=False)
    async def _run_agent(self, message: str) -> None:
        """Run the agent loop in background."""
        chat = self.query_one("#chat-view", ChatView)

        assistant_text = ""
        tool_calls_this_turn = 0

        try:
            async for event in self._agent_loop.run(message):
                if isinstance(event, TextDeltaEvent):
                    assistant_text += event.content
                    chat.update_assistant_stream(assistant_text)
                    self._update_status("generating...")

                elif isinstance(event, ToolCallEvent):
                    tool_calls_this_turn += 1
                    self._tool_calls_count += 1
                    chat.add_tool_call(event.name, event.input)
                    self._update_status(f"running tool: {event.name}")

                elif isinstance(event, ToolResultEvent):
                    chat.add_tool_result(event.tool_name, event.result, event.is_error)
                    self._update_status("processing results...")

                elif isinstance(event, PermissionPromptEvent):
                    chat.add_system_message(f"[yellow]⚠[/yellow] Permission needed: [cyan]{event.tool_name}[/cyan]")

                elif isinstance(event, PermissionDeniedEvent):
                    chat.add_system_message(f"[red]✗[/red] Permission denied: [cyan]{event.tool_name}[/cyan]")

                elif isinstance(event, ErrorEvent):
                    chat.add_error_message(event.message)

                elif isinstance(event, SubAgentStartEvent):
                    chat.add_system_message(f"[green]→[/green] Sub-agent started: [cyan]{event.pack_name}[/cyan] — {event.task[:100]}")

                elif isinstance(event, SubAgentDoneEvent):
                    chat.add_system_message(f"[green]←[/green] Sub-agent done: [cyan]{event.pack_name}[/cyan]")

                elif isinstance(event, DoneEvent):
                    if assistant_text:
                        chat.finalize_assistant_message(assistant_text)
                    self._turn_count += 1

        except Exception as e:
            chat.add_error_message(f"Error: {e}")
        finally:
            self._is_processing = False
            self._update_status("ready")
            self._update_sidebar()

    async def _handle_command(self, command: str) -> None:
        """Handle slash commands."""
        chat = self.query_one("#chat-view", ChatView)
        parts = command.split()
        cmd = parts[0].lower()

        if cmd == "/help":
            chat.add_system_message(
                "[bold]Commands:[/bold]\n"
                "  [cyan]/help[/cyan]         — Show this help\n"
                "  [cyan]/tools[/cyan]        — List available tools\n"
                "  [cyan]/session new[/cyan]  — Start new session\n"
                "  [cyan]/session list[/cyan] — List sessions\n"
                "  [cyan]/pack <name>[/cyan]  — Switch domain pack\n"
                "  [cyan]/model[/cyan]        — Show current model\n"
                "  [cyan]/clear[/cyan]        — Clear chat\n"
                "  [cyan]/quit[/cyan]         — Exit\n\n"
                "[dim]Shortcuts: Ctrl+N New Session | Ctrl+T Toggle Sidebar | Ctrl+Q Quit[/dim]"
            )
        elif cmd == "/tools":
            schemas = self._agent_loop.registry.get_schemas()
            if schemas:
                lines = ["[bold]Available Tools:[/bold]\n"]
                for s in schemas:
                    lines.append(f"  [cyan]•[/cyan] [bold]{s['name']}[/bold] — {s.get('description', '')[:80]}")
                chat.add_system_message("\n".join(lines))
            else:
                chat.add_system_message("No tools registered.")
        elif cmd == "/session":
            if len(parts) > 1 and parts[1] == "new":
                self._session_id = None
                self._init_loop()
                self._turn_count = 0
                self._tool_calls_count = 0
                chat.clear_messages()
                chat.add_system_message(f"New session started: [cyan]{self._agent_loop.session.id[:8]}…[/cyan]")
                self._update_sidebar()
            elif len(parts) > 1 and parts[1] == "list":
                if self._agent_loop.store:
                    sessions = await self._agent_loop.store.list_sessions()
                    if sessions:
                        lines = ["[bold]Recent Sessions:[/bold]\n"]
                        for s in sessions[:10]:
                            lines.append(f"  [cyan]{s['id'][:12]}…[/cyan] — {s['pack_name']} ({s['updated_at'][:16]})")
                        chat.add_system_message("\n".join(lines))
                    else:
                        chat.add_system_message("No sessions found.")
        elif cmd == "/pack" and len(parts) > 1:
            self.pack_name = parts[1]
            self._session_id = None
            self._init_loop()
            chat.clear_messages()
            chat.add_system_message(f"Switched to pack: [cyan]{self.pack_name}[/cyan]")
            self._update_sidebar()
        elif cmd == "/model":
            model = self._agent_loop.provider.model if hasattr(self._agent_loop.provider, "model") else "unknown"
            chat.add_system_message(f"Model: [cyan]{model}[/cyan]")
        elif cmd == "/clear":
            chat.clear_messages()
        elif cmd == "/quit":
            self.exit()
        else:
            chat.add_system_message(f"Unknown command: [cyan]{cmd}[/cyan]. Type [bold]/help[/bold] for commands.")

    def _update_status(self, status: str) -> None:
        try:
            bar = self.query_one("#status-bar", StatusBar)
            bar.update_status(status)
        except NoMatches:
            pass

    def _update_sidebar(self) -> None:
        try:
            sidebar = self.query_one("#sidebar", Sidebar)
            sidebar.update_info(
                session_id=self._agent_loop.session.id[:12] + "…",
                pack_name=self.pack_name,
                model=self._agent_loop.provider.model if hasattr(self._agent_loop.provider, "model") else "unknown",
                turns=self._turn_count,
                tool_calls=self._tool_calls_count,
                tools=self._agent_loop.registry.names(),
            )
        except NoMatches:
            pass

    def action_new_session(self) -> None:
        self._session_id = None
        self._init_loop()
        self._turn_count = 0
        self._tool_calls_count = 0
        chat = self.query_one("#chat-view", ChatView)
        chat.clear_messages()
        chat.add_system_message(f"New session: [cyan]{self._agent_loop.session.id[:8]}…[/cyan]")
        self._update_sidebar()

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar", Sidebar)
        sidebar.toggle_class("hidden")

    def action_list_sessions(self) -> None:
        pass  # TODO: modal dialog

    def action_quit_app(self) -> None:
        self.exit()

    def action_focus_input(self) -> None:
        self.query_one("#message-input", MessageInput).focus()
