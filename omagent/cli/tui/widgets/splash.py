# omagent/cli/tui/widgets/splash.py
"""Splash screen with slanted ASCII logo shown on first launch."""
from textual.widget import Widget
from textual.widgets import Static
from textual.app import ComposeResult

# FIGlet "slant" style logo
LOGO = """
[#a8b4f0]
               ____ ___  ____ _____ ____ ____  / /_
              / __ `__ \\/ __ `/ __ `/ _ \\/ __ \\/ __/
             / / / / / / /_/ / /_/ /  __/ / / / /_
            /_/ /_/ /_/\\__,_/\\__, /\\___/_/ /_/\\__/
                            /____/
[/]
[#80cbc4]          ╭──────────────────────────────────────╮
          │[/]  [bold #e0e0e6]Oh My Agent[/] [dim]—[/] [italic #ffe082]Your AI, Your Rules[/]  [#80cbc4]│
          ╰──────────────────────────────────────╯[/]

[dim]    Swap a pack, change the expert.
    Data science today, Flutter tomorrow.[/]
"""


class SplashScreen(Widget):
    """Slanted ASCII art splash displayed on first launch."""

    DEFAULT_CSS = """
    SplashScreen {
        height: auto;
        content-align: center middle;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(LOGO, id="splash-logo")
