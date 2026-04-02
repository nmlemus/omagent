# omagent/cli/tui/widgets/status_bar.py
"""Multi-segment status bar with live metrics."""
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static


class StatusBar(Widget):
    """Eight-segment status bar showing real-time agent metrics."""

    def compose(self) -> ComposeResult:
        yield Static("[#a5d6a7]●[/]", id="status-indicator", classes="status-segment")
        yield Static("ready", id="status-text", classes="status-segment")
        yield Static("", id="status-model", classes="status-segment")
        yield Static("", id="status-pack", classes="status-segment")
        yield Static("[dim]--/-- tok[/]", id="status-tokens", classes="status-segment")
        yield Static("[dim]$0.00[/]", id="status-cost", classes="status-segment")
        yield Static("[dim]T:0[/]", id="status-turns", classes="status-segment")
        yield Static("", id="status-elapsed", classes="status-segment")

    def update_status(self, text: str) -> None:
        """Update status text and indicator."""
        try:
            self.query_one("#status-text", Static).update(text)
            indicator = self.query_one("#status-indicator", Static)
            if text == "ready":
                indicator.update("[#a5d6a7]●[/]")
            else:
                indicator.update("[#ffe082]●[/]")
        except Exception:
            pass

    def set_model(self, model: str) -> None:
        try:
            # Shorten model name
            short = model.split("/")[-1] if "/" in model else model
            self.query_one("#status-model", Static).update(f"[dim]{short}[/]")
        except Exception:
            pass

    def set_pack(self, pack: str) -> None:
        try:
            self.query_one("#status-pack", Static).update(f"[#a8b4f0]{pack}[/]")
        except Exception:
            pass

    def set_tokens(self, tokens_in: int, tokens_out: int) -> None:
        try:
            tin = f"{tokens_in/1000:.1f}k" if tokens_in >= 1000 else str(tokens_in)
            tout = f"{tokens_out/1000:.1f}k" if tokens_out >= 1000 else str(tokens_out)
            self.query_one("#status-tokens", Static).update(f"{tin}/{tout} tok")
        except Exception:
            pass

    def set_cost(self, cost: float) -> None:
        try:
            self.query_one("#status-cost", Static).update(f"${cost:.4f}")
        except Exception:
            pass

    def set_turns(self, turns: int) -> None:
        try:
            self.query_one("#status-turns", Static).update(f"T:{turns}")
        except Exception:
            pass

    def set_elapsed(self, elapsed_s: float) -> None:
        try:
            self.query_one("#status-elapsed", Static).update(f"[dim]{elapsed_s:.1f}s[/]")
        except Exception:
            pass

    def clear_elapsed(self) -> None:
        try:
            self.query_one("#status-elapsed", Static).update("")
        except Exception:
            pass
