import logging
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

HookFn = Callable[..., Awaitable[None]]


class HookRunner:
    """
    Lightweight async hook system.

    Supported events:
    - pre_tool(tool_name, input)   — before a tool executes
    - post_tool(tool_name, result) — after a tool executes
    - on_text(content)             — when LLM emits a text delta
    - on_error(error)              — on any loop error
    """

    def __init__(self) -> None:
        self._hooks: dict[str, list[HookFn]] = {
            "pre_tool": [],
            "post_tool": [],
            "on_text": [],
            "on_error": [],
        }

    def register(self, event: str, fn: HookFn) -> None:
        """Register a hook function for an event."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(fn)

    async def pre_tool(self, tool_name: str, input: dict[str, Any]) -> None:
        for fn in self._hooks.get("pre_tool", []):
            try:
                await fn(tool_name, input)
            except Exception as e:
                logger.warning("pre_tool hook error: %s", e)

    async def post_tool(self, tool_name: str, result: dict[str, Any]) -> None:
        for fn in self._hooks.get("post_tool", []):
            try:
                await fn(tool_name, result)
            except Exception as e:
                logger.warning("post_tool hook error: %s", e)

    async def on_text(self, content: str) -> None:
        for fn in self._hooks.get("on_text", []):
            try:
                await fn(content)
            except Exception as e:
                logger.warning("on_text hook error: %s", e)

    async def on_error(self, error: Exception) -> None:
        for fn in self._hooks.get("on_error", []):
            try:
                await fn(error)
            except Exception as e:
                logger.warning("on_error hook error: %s", e)
