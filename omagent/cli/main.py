# omagent/cli/main.py
import asyncio
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv()


def _build_loop(pack_name: str, session_id: str | None = None):
    """Build a configured AgentLoop. Imported lazily to keep CLI startup fast."""
    from omagent.core.loop import AgentLoop
    from omagent.core.registry import ToolRegistry
    from omagent.core.session import Session, SessionStore
    from omagent.core.permissions import PermissionPolicy
    from omagent.core.hooks import HookRunner
    from omagent.providers.litellm_provider import LiteLLMProvider
    from omagent.tools.builtin import ReadFileTool, WriteFileTool, ListDirTool, BashTool

    store = SessionStore()
    registry = ToolRegistry()
    registry.register_many([ReadFileTool(), WriteFileTool(), ListDirTool(), BashTool()])

    policy = PermissionPolicy()
    mcp_servers = []

    # Try to load domain pack if available
    try:
        from omagent.packs.loader import DomainPackLoader
        loader = DomainPackLoader()
        pack = loader.load(pack_name)
        system_prompt = pack.system_prompt
        registry.register_many(pack.tools)
        policy.load_pack_permissions(pack.permissions)
        mcp_servers = pack.mcp_servers
    except Exception:
        system_prompt = f"You are a helpful AI assistant. Pack: {pack_name}."

    session = Session(id=session_id or __import__("uuid").uuid4().hex, pack_name=pack_name)

    loop = AgentLoop(
        session=session,
        registry=registry,
        provider=LiteLLMProvider(),
        policy=policy,
        hooks=HookRunner(),
        system_prompt=system_prompt,
        store=store,
    )
    # Attach mcp_servers list so async callers can connect them
    loop._pending_mcp_servers = mcp_servers
    return loop


async def _connect_mcp(loop) -> None:
    """Connect any MCP servers declared in the pack and register their tools."""
    servers = getattr(loop, "_pending_mcp_servers", [])
    if not servers:
        return
    from omagent.mcp.manager import MCPManager
    manager = MCPManager()
    for server_cfg in servers:
        try:
            await manager.connect_server(server_cfg)
        except Exception:
            pass  # already logged inside connect_server
    await manager.register_tools(loop.registry)
    loop.mcp_manager = manager


@click.group()
def cli():
    """omagent — Oh My Agent. Generic domain-configurable agentic engine."""
    pass


@cli.command()
@click.option("--pack", default=None, envvar="OMAGENT_PACK", help="Domain pack name")
@click.option("--session", "session_id", default=None, help="Resume a session by ID")
def chat(pack: str | None, session_id: str | None):
    """Start an interactive multi-turn chat session."""
    from omagent.cli.repl import run_repl

    pack_name = pack or os.getenv("OMAGENT_PACK", "default")

    async def loop_factory_async(sid=None):
        loop = _build_loop(pack_name, sid or session_id)
        await _connect_mcp(loop)
        return loop

    asyncio.run(run_repl(loop_factory_async, pack_name=pack_name))


@cli.command()
@click.argument("prompt")
@click.option("--pack", default=None, envvar="OMAGENT_PACK", help="Domain pack name")
def run(prompt: str, pack: str | None):
    """Run a single prompt and print the response."""
    from rich.console import Console
    from omagent.core.events import TextDeltaEvent, ErrorEvent

    console = Console()
    pack_name = pack or os.getenv("OMAGENT_PACK", "default")
    agent_loop = _build_loop(pack_name)

    async def _run():
        await _connect_mcp(agent_loop)
        try:
            async for event in agent_loop.run(prompt):
                if isinstance(event, TextDeltaEvent):
                    console.print(event.content, end="")
                elif isinstance(event, ErrorEvent):
                    console.print(f"\n[red]error:[/] {event.message}")
            console.print()  # final newline
        finally:
            if agent_loop.mcp_manager is not None:
                await agent_loop.mcp_manager.disconnect_all()

    asyncio.run(_run())


@cli.command()
@click.option("--host", default=None, envvar="OMAGENT_HOST", help="Bind host")
@click.option("--port", default=None, type=int, envvar="OMAGENT_PORT", help="Bind port")
@click.option("--pack", default=None, envvar="OMAGENT_PACK", help="Default domain pack")
def serve(host: str | None, port: int | None, pack: str | None):
    """Start the FastAPI server."""
    import uvicorn
    from omagent.server.app import create_app

    h = host or os.getenv("OMAGENT_HOST", "0.0.0.0")
    p = port or int(os.getenv("OMAGENT_PORT", "8000"))
    pack_name = pack or os.getenv("OMAGENT_PACK", "default")

    app = create_app(default_pack=pack_name, loop_factory=_build_loop)
    uvicorn.run(app, host=h, port=p)
