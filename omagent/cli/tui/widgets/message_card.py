# omagent/cli/tui/widgets/message_card.py
"""Message card widget — structured message display for all roles."""
import json
from datetime import datetime
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static, Markdown


class MessageCard(Widget):
    """A single message in the chat. Renders differently based on role."""

    DEFAULT_CSS = """
    MessageCard { height: auto; }
    """

    def __init__(self, role: str, content: str = "", **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.content = content
        self.timestamp = datetime.now().strftime("%H:%M:%S")
        self._label_widget: Static | None = None
        self._content_widget: Static | None = None

    def compose(self) -> ComposeResult:
        role_labels = {
            "user": "[bold #a8b4f0]You[/]",
            "assistant": "[bold #80cbc4]Assistant[/]",
            "system": "[dim italic]System[/]",
            "error": "[bold #ef9a9a]Error[/]",
        }
        label = role_labels.get(self.role, f"[bold]{self.role}[/]")
        time_str = f"[dim]{self.timestamp}[/]"

        self._label_widget = Static(f"{label} {time_str}", classes="message-label")
        yield self._label_widget

        self._content_widget = Static(self.content, classes="message-content")
        yield self._content_widget

        # Set card class based on role
        self.add_class(f"message-card-{self.role}")
        self.add_class("message-card")

    def update_content(self, new_content: str) -> None:
        """Update the content (used for streaming assistant messages)."""
        self.content = new_content
        if self._content_widget:
            self._content_widget.update(new_content)
