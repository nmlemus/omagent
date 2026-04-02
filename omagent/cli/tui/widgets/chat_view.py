# omagent/cli/tui/widgets/chat_view.py
"""Chat view — displays conversation using structured message widgets."""
import json
from typing import Any

from textual.containers import ScrollableContainer

from omagent.cli.tui.widgets.message_card import MessageCard
from omagent.cli.tui.widgets.tool_card import ToolCard
from omagent.cli.tui.widgets.thinking_indicator import ThinkingIndicator


class ChatView(ScrollableContainer):
    """Scrollable container rendering chat with MessageCards and ToolCards."""

    DEFAULT_CSS = """
    ChatView { height: 1fr; overflow-y: auto; }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_assistant: MessageCard | None = None
        self._thinking: ThinkingIndicator | None = None
        self._current_tool_card: ToolCard | None = None

    def _scroll_to_bottom(self) -> None:
        """Scroll to bottom after render cycle completes."""
        self.call_after_refresh(self.scroll_end, animate=False)

    def add_user_message(self, text: str) -> None:
        """Add a user message card."""
        card = MessageCard(role="user", content=text)
        self.mount(card)
        self._scroll_to_bottom()

    def show_thinking(self, phase: str = "Thinking...") -> None:
        """Show or update the thinking indicator."""
        if self._thinking is not None:
            self._thinking.update_phase(phase)
        else:
            self._thinking = ThinkingIndicator(phase=phase)
            self.mount(self._thinking)
            self._scroll_to_bottom()

    def hide_thinking(self) -> None:
        """Remove the thinking indicator."""
        if self._thinking is not None:
            self._thinking.remove()
            self._thinking = None

    def start_assistant_stream(self) -> None:
        """Create a new assistant message card for streaming."""
        self._current_assistant = MessageCard(role="assistant", content="")
        self.mount(self._current_assistant)

    def update_assistant_stream(self, text: str) -> None:
        """Update the streaming assistant message."""
        if self._current_assistant is None:
            self.start_assistant_stream()
        self._current_assistant.update_content(text)
        self._scroll_to_bottom()

    async def finalize_assistant_message(self, text: str) -> None:
        """Finalize the assistant message with markdown rendering."""
        if self._current_assistant is not None:
            try:
                await self._current_assistant.finalize_with_markdown(text)
            except Exception:
                self._current_assistant.update_content(text)
            self._current_assistant = None
        self._scroll_to_bottom()

    def add_tool_call(self, name: str, inputs: dict) -> ToolCard:
        """Add a tool card and return it for later result update."""
        card = ToolCard(tool_name=name, tool_input=inputs)
        self._current_tool_card = card
        self.mount(card)
        self._scroll_to_bottom()
        return card

    def update_tool_result(
        self, tool_card: ToolCard | None, result: dict, is_error: bool, duration_ms: int | None = None
    ) -> None:
        """Update a tool card with its result."""
        target = tool_card or self._current_tool_card
        if target is not None:
            target.set_result(result, is_error=is_error, duration_ms=duration_ms)
            self._scroll_to_bottom()

    def add_system_message(self, text: str) -> None:
        """Add a system/info message."""
        card = MessageCard(role="system", content=text)
        self.mount(card)
        self._scroll_to_bottom()

    def add_error_message(self, text: str) -> None:
        """Add an error message."""
        card = MessageCard(role="error", content=text)
        self.mount(card)
        self._scroll_to_bottom()

    def add_step_progress(self, step: int, total: int | None, description: str) -> None:
        """Show step progress indicator."""
        from textual.widgets import Static
        total_str = f"/{total}" if total else ""
        widget = Static(
            f"[dim italic]Step {step}{total_str}: {description}[/]",
            classes="step-progress",
        )
        self.mount(widget)
        self._scroll_to_bottom()

    def clear_messages(self) -> None:
        """Remove all message widgets."""
        self._current_assistant = None
        self._thinking = None
        self._current_tool_card = None
        for child in list(self.children):
            child.remove()
