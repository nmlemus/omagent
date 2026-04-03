# omagent/cli/tui/widgets/input_area.py
"""Message input widget with persistent history and command autocomplete."""
from pathlib import Path

from textual.widgets import Input
from textual.message import Message
from textual.events import Key


# Built-in commands available for autocomplete
BUILTIN_COMMANDS = [
    "/help",
    "/tools",
    "/skills",
    "/stop",
    "/session new",
    "/session list",
    "/session resume ",
    "/pack ",
    "/model",
    "/clear",
    "/quit",
]

MAX_HISTORY = 500
HISTORY_FILE = Path.home() / ".omagent" / "history"


def _load_history() -> list[str]:
    """Load command history from disk."""
    if not HISTORY_FILE.exists():
        return []
    try:
        lines = HISTORY_FILE.read_text(encoding="utf-8").splitlines()
        # Return last MAX_HISTORY entries
        return lines[-MAX_HISTORY:]
    except Exception:
        return []


def _save_history(history: list[str]) -> None:
    """Persist command history to disk."""
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Keep only last MAX_HISTORY entries
        to_save = history[-MAX_HISTORY:]
        HISTORY_FILE.write_text("\n".join(to_save) + "\n", encoding="utf-8")
    except Exception:
        pass


class MessageInput(Input):
    """Input widget with submit-on-Enter, Up/Down history, and Tab autocomplete."""

    class UserSubmitted(Message):
        """Posted when the user presses Enter."""
        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._history: list[str] = _load_history()
        self._history_index: int = -1  # -1 means not navigating
        self._saved_input: str = ""  # preserve current input when navigating
        self._extra_completions: list[str] = []  # skill commands added at runtime
        self._tab_matches: list[str] = []
        self._tab_index: int = 0

    def set_skill_commands(self, names: list[str]) -> None:
        """Register skill names for autocomplete (e.g., ["discuss", "plan"])."""
        self._extra_completions = [f"/{name}" for name in names]

    async def action_submit(self) -> None:
        """Override submit action to post our custom message and save history."""
        value = self.value
        if value.strip():
            # Don't add duplicates of the last entry
            if not self._history or self._history[-1] != value:
                self._history.append(value)
                if len(self._history) > MAX_HISTORY:
                    self._history = self._history[-MAX_HISTORY:]
                _save_history(self._history)
        # Reset navigation state
        self._history_index = -1
        self._saved_input = ""
        self._tab_matches = []
        self.post_message(MessageInput.UserSubmitted(value))

    async def _on_key(self, event: Key) -> None:
        if event.key == "up":
            event.prevent_default()
            event.stop()
            self._navigate_history(-1)
        elif event.key == "down":
            event.prevent_default()
            event.stop()
            self._navigate_history(1)
        elif event.key == "tab":
            event.prevent_default()
            event.stop()
            self._autocomplete()
        else:
            # Any other key resets tab completion state
            self._tab_matches = []
            self._tab_index = 0

    def _navigate_history(self, direction: int) -> None:
        """Navigate through command history. direction: -1=older, +1=newer."""
        if not self._history:
            return

        if self._history_index == -1:
            # Starting navigation — save current input
            self._saved_input = self.value
            if direction == -1:
                self._history_index = len(self._history) - 1
            else:
                return  # already at newest, nothing to do
        else:
            new_index = self._history_index + direction
            if new_index < 0:
                # Already at oldest
                return
            if new_index >= len(self._history):
                # Back to current input
                self._history_index = -1
                self.value = self._saved_input
                self.cursor_position = len(self.value)
                return
            self._history_index = new_index

        self.value = self._history[self._history_index]
        self.cursor_position = len(self.value)

    def _autocomplete(self) -> None:
        """Tab-complete commands starting with /."""
        current = self.value

        if not current.startswith("/"):
            return

        # If we already have matches from a previous Tab, cycle through them
        if self._tab_matches:
            self._tab_index = (self._tab_index + 1) % len(self._tab_matches)
            self.value = self._tab_matches[self._tab_index]
            self.cursor_position = len(self.value)
            return

        # Build completion candidates
        all_commands = BUILTIN_COMMANDS + self._extra_completions
        # Also add history entries that start with /
        for h in self._history:
            if h.startswith("/") and h not in all_commands:
                all_commands.append(h)

        # Find matches
        prefix = current.lower()
        matches = [cmd for cmd in all_commands if cmd.lower().startswith(prefix) and cmd.lower() != prefix]

        if not matches:
            return

        if len(matches) == 1:
            self.value = matches[0]
            self.cursor_position = len(self.value)
        else:
            # Multiple matches — store for cycling
            self._tab_matches = sorted(set(matches))
            self._tab_index = 0
            self.value = self._tab_matches[0]
            self.cursor_position = len(self.value)
