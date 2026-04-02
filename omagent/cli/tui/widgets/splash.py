# omagent/cli/tui/widgets/splash.py
"""Splash screen with 2-column welcome box inspired by Claurst."""
from textual.widget import Widget
from textual.widgets import Static
from textual.containers import Horizontal, Vertical
from textual.app import ComposeResult


# Unicode block-art mascot (3 rows) — friendly robot
MASCOT_DEFAULT = """[bold #a8b4f0] ▐▛█▀█▜▌
▝▜█████▛▘
  ▘▘ ▝▝[/]"""

MASCOT_THINKING = """[bold #ffe082] ▐▛█▀█▜▌
▝▜█████▛▘
  ▘▘ ▝▝[/]"""

# Bold slanted title — ANSI Shadow style for visibility
TITLE = """[bold #a8b4f0]  ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
  █ ▄▄▄▄▄ █▄ ▄▄▄ █  ▄▄▄  █ ▄▄▄▄ █ ▄▄▄ █▄ ▄▄▄ █▄▄▄
  ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀[/]
[bold #80cbc4]   ██████╗ ███╗   ███╗ █████╗  ██████╗ ███████╗███╗   ██╗████████╗
  ██╔═══██╗████╗ ████║██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝
  ██║   ██║██╔████╔██║███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║
  ██║   ██║██║╚██╔╝██║██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║
  ╚██████╔╝██║ ╚═╝ ██║██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║
   ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝[/]"""


class SplashScreen(Widget):
    """2-column welcome box displayed on first launch."""

    DEFAULT_CSS = """
    SplashScreen {
        height: auto;
        padding: 0;
        margin: 0 1 1 1;
    }

    #splash-box {
        height: auto;
        border: round #3a3a50;
        background: #1e1e36;
    }

    #splash-title-row {
        height: auto;
        padding: 1 2 0 2;
    }

    #splash-columns {
        height: auto;
        padding: 0;
    }

    #splash-left {
        width: 1fr;
        height: auto;
        padding: 1 2;
        border-right: solid #3a3a50;
    }

    #splash-right {
        width: 1fr;
        height: auto;
        padding: 1 2;
    }

    .splash-section-title {
        color: #a8b4f0;
        text-style: bold;
        margin-bottom: 1;
    }

    .splash-info {
        color: #9898a8;
        height: auto;
    }

    .splash-tip {
        color: #e0e0e6;
        height: auto;
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        pack_name: str = "default",
        model: str = "unknown",
        session_id: str = "",
        recent_sessions: list[dict] | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.pack_name = pack_name
        self.model = model
        self.session_id = session_id
        self.recent_sessions = recent_sessions or []

    def compose(self) -> ComposeResult:
        with Vertical(id="splash-box"):
            # Title row
            yield Static(TITLE, id="splash-title-row")

            # Two-column layout
            with Horizontal(id="splash-columns"):
                # Left: mascot + info
                with Vertical(id="splash-left"):
                    yield Static(MASCOT_DEFAULT, classes="splash-info")
                    session_suffix = (self.session_id[:12] + "…") if self.session_id else "none"
                    model_short = self.model.split("/")[-1] if self.model else "unknown"
                    yield Static(
                        f"[#80cbc4]Oh My Agent[/] [dim]— Your AI, Your Rules[/]\n\n"
                        f"[dim]Pack:[/]    [#a8b4f0]{self.pack_name}[/]\n"
                        f"[dim]Model:[/]   [#80cbc4]{model_short}[/]\n"
                        f"[dim]Session:[/] [dim]{session_suffix}[/]",
                        classes="splash-info",
                    )

                # Right: tips + recent
                with Vertical(id="splash-right"):
                    yield Static("[#a8b4f0]Getting Started[/]", classes="splash-section-title")
                    yield Static(
                        "[#e0e0e6]●[/] Type a message to chat with the agent\n"
                        "[#e0e0e6]●[/] Use [bold]/tools[/] to see available tools\n"
                        "[#e0e0e6]●[/] Use [bold]/pack <name>[/] to switch packs\n"
                        "[#e0e0e6]●[/] Press [bold]Ctrl+E[/] for event log\n"
                        "[#e0e0e6]●[/] Press [bold]Ctrl+T[/] to toggle sidebar",
                        classes="splash-tip",
                    )
                    yield Static("[#a8b4f0]Recent Sessions[/]", classes="splash-section-title")
                    if self.recent_sessions:
                        lines = []
                        for s in self.recent_sessions[:5]:
                            lines.append(
                                f"[#80cbc4]{s['id'][:8]}…[/] "
                                f"{s['pack_name']} "
                                f"[dim]{s.get('updated_at', '')[:16]}[/]"
                            )
                        yield Static("\n".join(lines), classes="splash-info")
                    else:
                        yield Static("[dim]No recent sessions[/]", classes="splash-info")
