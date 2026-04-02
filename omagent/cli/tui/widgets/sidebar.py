# omagent/cli/tui/widgets/sidebar.py
"""Sidebar widget — session info, plan progress, and tool list."""
from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import ScrollableContainer


class Sidebar(ScrollableContainer):
    """Right-hand sidebar showing session info, plan, and tools."""

    DEFAULT_CSS = """
    Sidebar {
        width: 35;
        overflow-y: auto;
    }
    """

    def __init__(self, pack_name: str = "default", **kwargs):
        super().__init__(**kwargs)
        self.pack_name = pack_name

    def compose(self) -> ComposeResult:
        yield Static("[bold #a8b4f0]Session Info[/]", classes="sidebar-title")
        yield Static("Loading…", classes="sidebar-value", id="sidebar-info")
        yield Static("\n[bold #a8b4f0]Plan[/]", classes="sidebar-title")
        yield Static("[dim]No plan yet[/]", classes="sidebar-value", id="sidebar-plan")
        yield Static("\n[bold #a8b4f0]Tools[/]", classes="sidebar-title")
        yield Static("Loading…", classes="sidebar-tool-item", id="sidebar-tools")

    def update_info(
        self,
        session_id: str,
        pack_name: str,
        model: str,
        turns: int,
        tool_calls: int,
        tools: list[str],
        workspace_path: str | None = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost: float = 0.0,
    ) -> None:
        model_short = model.split("/")[-1] if "/" in model else model

        info_text = (
            f"[dim]Session:[/]  {session_id}\n"
            f"[dim]Pack:[/]     {pack_name}\n"
            f"[dim]Model:[/]    {model_short}\n"
            f"[dim]Turns:[/]    {turns}\n"
            f"[dim]Tools:[/]    {tool_calls} calls\n"
            f"[dim]Tokens:[/]   {tokens_in:,}/{tokens_out:,}\n"
            f"[dim]Cost:[/]     ${cost:.4f}"
        )
        if workspace_path:
            ws_short = workspace_path.split("/")[-1][:16] + "\u2026"
            info_text += f"\n[dim]Workspace:[/] {ws_short}"

        tools_text = "\n".join(f"  [#80cbc4]\u2022[/] {t}" for t in tools) or "[dim]none[/]"

        try:
            self.query_one("#sidebar-info", Static).update(info_text)
            self.query_one("#sidebar-tools", Static).update(tools_text)
        except Exception:
            pass

    def update_plan(self, plan_data: dict | None) -> None:
        """Update the plan section with step checklist."""
        try:
            plan_widget = self.query_one("#sidebar-plan", Static)
        except Exception:
            return

        if not plan_data or not plan_data.get("steps"):
            plan_widget.update("[dim]No plan yet[/]")
            return

        lines = []
        goal = plan_data.get("goal", "")
        if goal:
            lines.append(f"[bold]{goal[:40]}[/]")
            lines.append("")

        for step in plan_data["steps"]:
            status = step.get("status", "pending")
            desc = step.get("description", "")[:35]
            if status == "completed":
                icon = "[#a5d6a7]\u2713[/]"
            elif status == "in_progress":
                icon = "[#ffe082]\u25cb[/]"
            elif status == "failed":
                icon = "[#ef9a9a]\u2717[/]"
            else:
                icon = "[dim]\u25cb[/]"
            lines.append(f"  {icon} {desc}")

        progress = plan_data.get("progress", "")
        if progress:
            lines.append(f"\n[dim]Progress: {progress}[/]")

        plan_widget.update("\n".join(lines))
