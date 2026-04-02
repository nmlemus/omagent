# omagent/cli/tui/widgets/message_card.py
"""Message card widget — structured message display with markdown support."""
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
        self._finalized = False

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

        # Always use Static for initial render (streaming compatible)
        self._content_widget = Static(self.content, classes="message-content")
        yield self._content_widget

        self.add_class(f"message-card-{self.role}")
        self.add_class("message-card")

    def update_content(self, new_content: str) -> None:
        """Update the content (used for streaming assistant messages)."""
        self.content = new_content
        if self._content_widget is not None:
            self._content_widget.update(new_content)

    async def finalize_with_markdown(self, content: str) -> None:
        """Replace Static with Markdown widget for final rendered content."""
        self.content = content
        if self._content_widget is not None and self.role == "assistant":
            try:
                md_widget = Markdown(content, classes="message-content-md")
                await self._content_widget.mount_after(md_widget)
                self._content_widget.remove()
                self._content_widget = None
                self._finalized = True
            except Exception:
                # Fallback: just update the static
                self._content_widget.update(content)
