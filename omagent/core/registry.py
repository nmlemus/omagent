import logging
from typing import Any
from omagent.tools.base import Tool

logger = logging.getLogger(__name__)


class ToolNotFoundError(Exception):
    pass


class ToolRegistry:
    """
    Central registry for all tools available to the AgentLoop.

    Tools are registered by name. The registry provides:
    - Schema list for passing to LLM (tool definitions)
    - Execution by name
    - Introspection
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool instance. Overwrites if name already exists."""
        if tool.name in self._tools:
            logger.debug("Overwriting tool: %s", tool.name)
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s", tool.name)

    def register_many(self, tools: list[Tool]) -> None:
        for tool in tools:
            self.register(tool)

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise ToolNotFoundError(f"Tool not found: {name!r}")
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def get_schemas(self) -> list[dict]:
        """Return tool schemas in Anthropic format for passing to LLM."""
        return [tool.to_schema() for tool in self._tools.values()]

    async def execute(self, name: str, input: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool by name. Raises ToolNotFoundError if not registered."""
        tool = self.get(name)
        try:
            result = await tool.execute(input)
            return result
        except Exception as e:
            logger.exception("Tool %s raised exception", name)
            return {"error": f"Tool execution failed: {e}"}

    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        return f"ToolRegistry(tools={self.names()})"
