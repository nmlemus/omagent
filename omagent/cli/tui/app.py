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
        self._skill_registry = getattr(self._agent_loop, 'skill_registry', None)

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
        round_count = 0
        turn_start = time.monotonic()

        # Show thinking immediately
        chat.show_thinking("Thinking...")
        self._update_status("thinking...")
        if activity:
            activity.add_entry("LLM call started")

        # Start elapsed timer
        elapsed_timer = self.set_interval(0.5, lambda: self._update_elapsed(turn_start))

        def _update_live_metrics():
            """Push real-time metrics to status bar and sidebar."""
            try:
                bar = self.query_one("#status-bar", StatusBar)
                bar.set_tokens(
                    getattr(self._agent_loop.session, 'total_tokens_in', 0),
                    getattr(self._agent_loop.session, 'total_tokens_out', 0),
                )
                bar.set_cost(getattr(self._agent_loop.session, 'total_cost', 0.0))
                bar.set_turns(round_count)
            except NoMatches:
                pass

        try:
            async for event in self._agent_loop.run(message):
                if isinstance(event, TextDeltaEvent):
                    if not assistant_text:
                        # New round of text — show round separator
                        round_count += 1
                        chat.hide_thinking()
                        chat.add_round_separator(round_count)
                        chat.start_assistant_stream()
                        self._update_status(f"R{round_count} generating...")
                        _update_live_metrics()
                        if activity:
                            activity.add_entry(f"Round {round_count} — LLM streaming")
                    assistant_text += event.content
                    chat.update_assistant_stream(assistant_text)

                elif isinstance(event, ToolCallEvent):
                    tool_calls_this_turn += 1
                    self._tool_calls_count += 1

                    # Finalize any streaming text before showing tool card
                    if assistant_text:
                        await chat.finalize_assistant_message(assistant_text)
                        assistant_text = ""

                    chat.hide_thinking()
                    current_tool_card = chat.add_tool_call(event.name, event.input)
                    chat.show_thinking(f"Running {event.name}...")
                    self._update_status(f"R{round_count} ⚡ {event.name}")
                    _update_live_metrics()

                    if activity:
                        activity.add_entry(f"⚡ {event.name}")

                elif isinstance(event, ToolResultEvent):
                    chat.hide_thinking()
                    chat.update_tool_result(current_tool_card, event.result, event.is_error)
                    self._update_status(f"R{round_count} processing...")
                    _update_live_metrics()

                    if activity:
                        status = "❌" if event.is_error else "✓"
                        dur = event.result.get("duration_ms") if isinstance(event.result, dict) else None
                        dur_str = f" ({dur}ms)" if dur else ""
                        activity.add_entry(f"{status} {event.tool_name}{dur_str}")

                elif isinstance(event, PermissionPromptEvent):
                    chat.add_system_message(f"[#ffe082]⚠ Permission needed:[/] `{event.tool_name}`")
                    if activity:
                        activity.add_entry(f"⚠ Permission: {event.tool_name}")

                elif isinstance(event, PermissionDeniedEvent):
                    chat.add_error_message(f"Permission denied: {event.tool_name}")
                    if activity:
                        activity.add_entry(f"✗ Denied: {event.tool_name}")

                elif isinstance(event, ErrorEvent):
                    chat.add_error_message(event.message)
                    if activity:
                        activity.add_entry(f"❌ {event.message[:80]}")

                elif isinstance(event, SubAgentStartEvent):
                    chat.add_system_message(
                        f"[#ce93d8]→ Sub-agent:[/] `{event.pack_name}` — {event.task[:100]}"
                    )
                    if activity:
                        activity.add_entry(f"→ Sub-agent: {event.pack_name}")

                elif isinstance(event, SubAgentDoneEvent):
                    chat.add_system_message(f"[#a5d6a7]← Sub-agent done:[/] `{event.pack_name}`")
                    if activity:
                        activity.add_entry(f"← Sub-agent done: {event.pack_name}")

                elif isinstance(event, DoneEvent):
                    if assistant_text:
                        await chat.finalize_assistant_message(assistant_text)
                        assistant_text = ""
                    self._turn_count += 1
                    _update_live_metrics()
                    if activity:
                        elapsed = time.monotonic() - turn_start
                        activity.add_entry(
                            f"Done — {round_count} rounds, "
                            f"{self._agent_loop.session.total_tokens_in:,}/"
                            f"{self._agent_loop.session.total_tokens_out:,} tok "
                            f"({elapsed:.1f}s)"
                        )

        except Exception as e:
            chat.add_error_message(f"Error: {e}")
            if activity:
                activity.add_entry(f"❌ {e}")
        finally:
            chat.hide_thinking()
            elapsed_timer.stop()
            self._is_processing = False
            self._update_status("ready")

            try:
                bar = self.query_one("#status-bar", StatusBar)
                bar.set_turns(round_count)
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
                workspace_path=getattr(self._agent_loop.session, 'workspace_path', None),
                tokens_in=getattr(self._agent_loop.session, 'total_tokens_in', 0),
                tokens_out=getattr(self._agent_loop.session, 'total_tokens_out', 0),
                cost=getattr(self._agent_loop.session, 'total_cost', 0.0),
            )
            # Update plan if available
            self._update_plan_sidebar()
        except NoMatches:
            pass

    @work(thread=False)
    async def _update_plan_sidebar(self) -> None:
        """Load plan from store and update sidebar."""
        if not hasattr(self._agent_loop, 'plan_store') or not self._agent_loop.plan_store:
            return
        try:
            plan = await self._agent_loop.plan_store.load(self._agent_loop.session.id)
            if plan:
                plan_data = plan.to_dict()
                plan_data["progress"] = plan.progress
                sidebar = self.query_one("#sidebar", Sidebar)
                sidebar.update_plan(plan_data)
        except Exception:
            pass

    async def _handle_command(self, command: str) -> None:
        chat = self.query_one("#chat-view", ChatView)
        parts = command.split()
        cmd = parts[0].lower()

        if cmd == "/help":
            help_text = (
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
            if hasattr(self, '_skill_registry') and self._skill_registry:
                invocable = self._skill_registry.get_user_invocable()
                if invocable:
                    help_text += "\n\n[bold]Skills:[/]\n"
                    for s in invocable:
                        help_text += f"  [#a8b4f0]/{s.name}[/] — {s.description[:50]}\n"
            chat.add_system_message(help_text)
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
        elif cmd == "/skills":
            if self._skill_registry:
                skills = self._skill_registry.list_all()
                if skills:
                    lines = ["[bold]Available Skills:[/]\n"]
                    for s in skills:
                        lines.append(f"  [#a8b4f0]/{s['name']}[/] — {s['description'][:50]} [dim]({s['source']})[/]")
                    chat.add_system_message("\n".join(lines))
                else:
                    chat.add_system_message("[dim]No skills found.[/]")
            return
        else:
            # Check if it's a skill command
            activity = self._get_activity_log()
            if hasattr(self, '_skill_registry') and self._skill_registry:
                skill = self._skill_registry.get_by_name(cmd.lstrip("/"))
                if skill:
                    content = self._skill_registry.get_full_content(skill.name)
                    if content:
                        chat.add_system_message(f"[#a8b4f0]Loaded skill:[/] `{skill.name}` — {skill.description[:60]}")
                        # Inject into the loop's system prompt
                        self._agent_loop.system_prompt += f"\n\n[Skill: {skill.name}]\n{content}"
                        if activity:
                            activity.add_entry(f"Skill loaded: {skill.name}")
                    return
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
