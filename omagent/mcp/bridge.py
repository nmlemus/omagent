from typing import Any
from omagent.tools.base import Tool
from omagent.mcp.client import MCPClient


class MCPToolBridge(Tool):
    """
    Bridges an MCP server tool into the omagent Tool interface.
    Each instance wraps one tool from one MCP server.
    """

    def __init__(self, mcp_client: MCPClient, mcp_schema: dict):
        self._client = mcp_client
        self._schema = mcp_schema
        self._tool_name = mcp_schema["name"]

    @property
    def name(self) -> str:
        # Prefix with MCP server name to avoid collisions
        return f"mcp_{self._client.name}_{self._tool_name}"

    @property
    def description(self) -> str:
        return self._schema.get("description", f"MCP tool: {self._tool_name}")

    @property
    def input_schema(self) -> dict:
        return self._schema.get("input_schema", {"type": "object", "properties": {}})

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        try:
            result = await self._client.call_tool(self._tool_name, input)
            return result
        except Exception as e:
            return {"error": f"MCP tool '{self._tool_name}' failed: {e}"}
