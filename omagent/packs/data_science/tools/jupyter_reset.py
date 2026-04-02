from typing import Any
from omagent.tools.base import Tool


class JupyterResetTool(Tool):
    """Reset the Jupyter kernel, clearing all state."""

    def __init__(self, execute_tool=None):
        self._execute_tool = execute_tool

    @property
    def name(self) -> str:
        return "jupyter_reset"

    @property
    def description(self) -> str:
        return "Reset the Jupyter kernel, clearing all variables and state. Use when you want a clean environment."

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        if self._execute_tool and hasattr(self._execute_tool, "shutdown"):
            await self._execute_tool.shutdown()
            return {"output": "Jupyter kernel has been reset. All variables cleared."}
        return {"error": "No Jupyter kernel to reset"}
