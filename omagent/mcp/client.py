import asyncio
import logging
from typing import Any
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPClient:
    """Connects to an MCP server and provides tool discovery and execution."""

    def __init__(self, name: str, command: str, args: list[str] | None = None, env: dict[str, str] | None = None):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env
        self._session: ClientSession | None = None
        self._exit_stack = AsyncExitStack()
        self._tools_cache: list[dict] | None = None

    async def connect(self) -> None:
        """Connect to the MCP server via stdio."""
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env,
        )
        stdio_transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read_stream, write_stream = stdio_transport
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self._session.initialize()
        logger.info("MCP client '%s' connected to: %s %s", self.name, self.command, " ".join(self.args))

    async def list_tools(self) -> list[dict]:
        """List available tools from the MCP server."""
        if not self._session:
            raise RuntimeError(f"MCP client '{self.name}' not connected")

        result = await self._session.list_tools()
        tools = []
        for tool in result.tools:
            tools.append({
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema if hasattr(tool, 'inputSchema') else {},
            })
        self._tools_cache = tools
        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        if not self._session:
            raise RuntimeError(f"MCP client '{self.name}' not connected")

        result = await self._session.call_tool(name, arguments)
        # Extract content from MCP result
        if result.content:
            # Combine text content
            texts = []
            for block in result.content:
                if hasattr(block, 'text'):
                    texts.append(block.text)
            return {"output": "\n".join(texts) if texts else str(result.content)}
        return {"output": "Tool executed successfully (no output)"}

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        await self._exit_stack.aclose()
        self._session = None
        self._tools_cache = None
        logger.info("MCP client '%s' disconnected", self.name)

    @property
    def is_connected(self) -> bool:
        return self._session is not None
