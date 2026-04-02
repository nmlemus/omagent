# omagent/cli/tui/widgets/input_area.py
"""Message input widget with submit-on-Enter."""
from textual.widgets import Input
from textual.message import Message


class MessageInput(Input):
    """Input widget that posts a UserSubmitted message on Enter."""

    class UserSubmitted(Message):
        """Posted when the user presses Enter."""
        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    async def action_submit(self) -> None:
        """Override submit action to post our custom message instead."""
        value = self.value
        self.post_message(MessageInput.UserSubmitted(value))
