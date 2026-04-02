# omagent/cli/tui/widgets/status_bar.py
"""Status bar widget — one-line status at the bottom."""
from textual.widget import Widget
from textual.widgets import Static
from textual.app import ComposeResult


class StatusBar(Widget):
    """Single-line status bar docked at the bottom."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        dock: bottom;
        background: $primary-darken-2;
        color: $text;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("ready", id="status-text")

    def update_status(self, text: str) -> None:
        """Update the status text."""
        try:
            self.query_one("#status-text", Static).update(f"[dim]●[/dim] {text}")
        except Exception:
            pass
