# omagent/cli/tui/widgets/sidebar.py
"""Sidebar widget — session info and tool list."""
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from textual.containers import ScrollableContainer


class Sidebar(ScrollableContainer):
    """Right-hand sidebar showing session info and registered tools."""

    DEFAULT_CSS = """
    Sidebar {
        width: 35;
        overflow-y: auto;
    }
    """

    def __init__(self, pack_name: str = "default", **kwargs):
        super().__init__(**kwargs)
        self.pack_name = pack_name
        self._info_widget: Static | None = None
        self._tools_widget: Static | None = None

    def compose(self) -> ComposeResult:
        yield Static("[bold cyan]Session Info[/bold cyan]", classes="sidebar-title")
        self._info_widget = Static("Loading…", classes="sidebar-value")
        yield self._info_widget
        yield Static("\n[bold cyan]Tools[/bold cyan]", classes="sidebar-title")
        self._tools_widget = Static("Loading…", classes="sidebar-tool-item")
        yield self._tools_widget

    def on_mount(self) -> None:
        self._info_widget = self.query_one(".sidebar-value", Static)
        self._tools_widget = self.query_one(".sidebar-tool-item", Static)

    def update_info(
        self,
        session_id: str,
        pack_name: str,
        model: str,
        turns: int,
        tool_calls: int,
        tools: list[str],
    ) -> None:
        """Refresh sidebar content."""
        info_text = (
            f"[dim]Session:[/dim] {session_id}\n"
            f"[dim]Pack:[/dim] {pack_name}\n"
            f"[dim]Model:[/dim] {model}\n"
            f"[dim]Turns:[/dim] {turns}\n"
            f"[dim]Tool calls:[/dim] {tool_calls}"
        )
        tools_text = "\n".join(f"  [cyan]•[/cyan] {t}" for t in tools) or "[dim]none[/dim]"

        try:
            info_w = self.query(".sidebar-value")[0]
            info_w.update(info_text)
            tool_w = self.query(".sidebar-tool-item")[0]
            tool_w.update(tools_text)
        except Exception:
            pass
