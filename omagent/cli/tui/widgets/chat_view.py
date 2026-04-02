# omagent/cli/tui/widgets/chat_view.py
"""Chat view widget — displays conversation messages."""
import json
from typing import Any

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Markdown, Static
from textual.containers import ScrollableContainer


class ChatView(ScrollableContainer):
    """Scrollable container that renders chat messages."""

    DEFAULT_CSS = """
    ChatView {
        height: 1fr;
        overflow-y: auto;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._assistant_widget: Static | None = None

    def compose(self) -> ComposeResult:
        return iter([])

    def add_user_message(self, text: str) -> None:
        """Add a user message bubble."""
        widget = Static(f"[bold cyan]You[/bold cyan]\n{text}", classes="user-message")
        self.mount(widget)
        self.scroll_end(animate=False)

    def update_assistant_stream(self, text: str) -> None:
        """Update (or create) the current streaming assistant message."""
        if self._assistant_widget is None:
            self._assistant_widget = Static(
                f"[bold green]Assistant[/bold green]\n{text}",
                classes="assistant-message",
            )
            self.mount(self._assistant_widget)
        else:
            self._assistant_widget.update(f"[bold green]Assistant[/bold green]\n{text}")
        self.scroll_end(animate=False)

    def finalize_assistant_message(self, text: str) -> None:
        """Finalize the streaming assistant message."""
        if self._assistant_widget is not None:
            self._assistant_widget.update(f"[bold green]Assistant[/bold green]\n{text}")
            self._assistant_widget = None
        self.scroll_end(animate=False)

    def add_tool_call(self, name: str, inputs: dict) -> None:
        """Add a tool call display."""
        args_str = json.dumps(inputs, indent=2) if inputs else "{}"
        widget = Static(
            f"[bold yellow]→ Tool:[/bold yellow] [cyan]{name}[/cyan]\n[dim]{args_str[:200]}[/dim]",
            classes="tool-call",
        )
        self.mount(widget)
        self.scroll_end(animate=False)

    def add_tool_result(self, tool_name: str, result: Any, is_error: bool = False) -> None:
        """Add a tool result display."""
        result_str = json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
        css_class = "tool-result-error" if is_error else "tool-result"
        prefix = "[red]✗[/red]" if is_error else "[green]✓[/green]"
        widget = Static(
            f"{prefix} [dim]{tool_name}:[/dim] {result_str[:300]}",
            classes=css_class,
        )
        self.mount(widget)
        self.scroll_end(animate=False)

    def add_system_message(self, text: str) -> None:
        """Add a system/info message."""
        widget = Static(text, markup=True, classes="system-message")
        self.mount(widget)
        self.scroll_end(animate=False)

    def add_error_message(self, text: str) -> None:
        """Add an error message."""
        widget = Static(f"[bold red]Error:[/bold red] {text}", classes="error-message")
        self.mount(widget)
        self.scroll_end(animate=False)

    def clear_messages(self) -> None:
        """Remove all message widgets."""
        self._assistant_widget = None
        for child in list(self.children):
            child.remove()
