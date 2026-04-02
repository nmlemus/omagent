# omagent/cli/tui/widgets/input_area.py
"""Message input widget with submit-on-Enter."""
from textual.widgets import Input
from textual.message import Message


class MessageInput(Input):
    """Input widget that fires a Submitted message on Enter."""

    class Submitted(Message):
        """Posted when the user presses Enter."""
        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Intercept the built-in Input.Submitted and re-post as MessageInput.Submitted."""
        event.stop()
        self.post_message(MessageInput.Submitted(event.value))
