# omagent/cli/tui/widgets/splash.py
"""Splash screen with ASCII logo shown on first launch."""
from textual.widget import Widget
from textual.widgets import Static
from textual.app import ComposeResult

LOGO = """
[#a8b4f0]
  ██████╗ ███╗   ███╗ █████╗  ██████╗ ███████╗███╗   ██╗████████╗
 ██╔═══██╗████╗ ████║██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
 ██║   ██║██╔████╔██║███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║
 ██║   ██║██║╚██╔╝██║██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║
 ╚██████╔╝██║ ╚═╝ ██║██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║
  ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝
[/]
[#80cbc4]           Oh My Agent — Your AI, Your Rules[/]

[dim]  Domain-configurable agentic engine with swappable intelligence.
  Swap a pack, change the expert. Data science today, Flutter tomorrow.[/]
"""


class SplashScreen(Widget):
    """ASCII art splash displayed on first launch."""

    DEFAULT_CSS = """
    SplashScreen {
        height: auto;
        content-align: center middle;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(LOGO, id="splash-logo")
