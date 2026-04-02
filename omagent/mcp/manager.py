import logging
from omagent.mcp.client import MCPClient
from omagent.mcp.bridge import MCPToolBridge
from omagent.core.registry import ToolRegistry

logger = logging.getLogger(__name__)


class MCPManager:
    """Manages multiple MCP server connections and registers their tools."""

    def __init__(self):
        self._clients: dict[str, MCPClient] = {}

    async def connect_server(self, config: dict) -> MCPClient:
        """Connect to an MCP server from a config dict.

        Config format:
            {"name": "fs", "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]}
        """
        name = config["name"]
        client = MCPClient(
            name=name,
            command=config["command"],
            args=config.get("args", []),
            env=config.get("env"),
        )
        try:
            await client.connect()
            self._clients[name] = client
            logger.info("Connected MCP server: %s", name)
        except Exception as e:
            logger.error("Failed to connect MCP server '%s': %s", name, e)
            raise
        return client

    async def register_tools(self, registry: ToolRegistry) -> int:
        """Discover tools from all connected MCP servers and register them."""
        total = 0
        for name, client in self._clients.items():
            try:
                tools = await client.list_tools()
                for tool_schema in tools:
                    bridge = MCPToolBridge(client, tool_schema)
                    registry.register(bridge)
                    total += 1
                logger.info("Registered %d tools from MCP server '%s'", len(tools), name)
            except Exception as e:
                logger.warning("Failed to list tools from MCP '%s': %s", name, e)
        return total

    async def disconnect_all(self) -> None:
        """Disconnect all MCP servers."""
        for name, client in list(self._clients.items()):
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning("Error disconnecting MCP '%s': %s", name, e)
        self._clients.clear()

    @property
    def connected_servers(self) -> list[str]:
        return list(self._clients.keys())
