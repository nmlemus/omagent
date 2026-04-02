# omagent/cli/tui/widgets/thinking_indicator.py
"""Animated thinking indicator."""
from textual.widget import Widget
from textual.widgets import Static
from textual.app import ComposeResult


DOTS = ["⠋ ", "⠙ ", "⠹ ", "⠸ ", "⠼ ", "⠴ ", "⠦ ", "⠧ ", "⠇ ", "⠏ "]


class ThinkingIndicator(Widget):
    """Animated spinner with phase label. Mounted/removed dynamically."""

    DEFAULT_CSS = """
    ThinkingIndicator { height: auto; }
    """

    def __init__(self, phase: str = "Thinking...", **kwargs):
        super().__init__(**kwargs)
        self.phase = phase
        self._frame = 0
        self._label: Static | None = None
        self.add_class("thinking-indicator")

    def compose(self) -> ComposeResult:
        self._label = Static(f"{DOTS[0]}[italic #ffe082]{self.phase}[/]")
        yield self._label

    def on_mount(self) -> None:
        self.set_interval(0.1, self._tick)

    def _tick(self) -> None:
        self._frame = (self._frame + 1) % len(DOTS)
        if self._label:
            self._label.update(f"{DOTS[self._frame]}[italic #ffe082]{self.phase}[/]")

    def update_phase(self, phase: str) -> None:
        """Change the displayed phase text."""
        self.phase = phase
