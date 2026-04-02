# omagent/cli/tui/widgets/activity_log.py
"""Activity log panel — timestamped event stream."""
from datetime import datetime
from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import ScrollableContainer


class ActivityLog(ScrollableContainer):
    """Optional bottom panel showing timestamped event stream."""

    DEFAULT_CSS = """
    ActivityLog { height: 8; overflow-y: auto; }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._entry_count = 0

    def compose(self) -> ComposeResult:
        yield Static("[dim]Event log (Ctrl+E to toggle)[/]", classes="activity-entry")

    def add_entry(self, detail: str) -> None:
        """Add a timestamped entry."""
        self._entry_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Color-code by event type keywords
        if "error" in detail.lower():
            colored = f"[#ef9a9a]{detail}[/]"
        elif "tool" in detail.lower():
            colored = f"[#ce93d8]{detail}[/]"
        elif "llm" in detail.lower() or "thinking" in detail.lower():
            colored = f"[#ffe082]{detail}[/]"
        elif "done" in detail.lower() or "complete" in detail.lower():
            colored = f"[#a5d6a7]{detail}[/]"
        else:
            colored = f"[dim]{detail}[/]"

        entry = Static(
            f"[dim]{timestamp}[/]  {colored}",
            classes="activity-entry",
        )
        self.mount(entry)
        self.scroll_end(animate=False)

        # Cap entries to prevent memory bloat
        if self._entry_count > 200:
            children = list(self.children)
            if children:
                children[0].remove()
                self._entry_count -= 1
