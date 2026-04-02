# omagent/cli/repl.py
import asyncio
import os
from typing import TYPE_CHECKING

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.text import Text
from rich.live import Live
from rich.panel import Panel
from rich import print as rprint
from pathlib import Path

from omagent.core.events import (
    TextDeltaEvent, ToolCallEvent, ToolResultEvent,
    PermissionDeniedEvent, PermissionPromptEvent, ErrorEvent, DoneEvent
)

console = Console()

PROMPT_STYLE = Style.from_dict({
    "pack": "#00aaff bold",
    "prompt": "#ffffff",
})

HISTORY_PATH = Path.home() / ".omagent" / "history"
HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)


def print_welcome(pack_name: str) -> None:
    console.print(Panel(
        f"[bold cyan]omagent[/] — Oh My Agent\n"
        f"Pack: [green]{pack_name}[/]  |  "
        f"Type [dim]/help[/] for commands, [dim]Ctrl+D[/] to exit",
        border_style="dim",
    ))


def print_help() -> None:
    console.print("""
[bold]Slash commands:[/]
  [cyan]/tools[/]           List available tools
  [cyan]/session new[/]     Start a new session
  [cyan]/session list[/]    List recent sessions
  [cyan]/pack <name>[/]     Switch domain pack
  [cyan]/help[/]            Show this help
  [cyan]/exit[/]            Quit
""")


async def run_repl(loop_factory, pack_name: str = "default") -> None:
    """
    loop_factory: callable(session_id=None) -> AgentLoop
    Called once per session to create a fresh AgentLoop.
    """
    print_welcome(pack_name)

    prompt_session = PromptSession(
        history=FileHistory(str(HISTORY_PATH)),
        auto_suggest=AutoSuggestFromHistory(),
        style=PROMPT_STYLE,
    )

    agent_loop = loop_factory()

    while True:
        try:
            prompt_text = [
                ("class:pack", f"[{pack_name}]"),
                ("class:prompt", " > "),
            ]
            user_input = await prompt_session.prompt_async(
                prompt_text,
                multiline=False,
            )
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        # Handle slash commands
        if user_input.startswith("/"):
            parts = user_input.split()
            cmd = parts[0].lower()

            if cmd == "/exit":
                console.print("[dim]Goodbye.[/]")
                break
            elif cmd == "/help":
                print_help()
            elif cmd == "/tools":
                schemas = agent_loop.registry.get_schemas()
                if not schemas:
                    console.print("[dim]No tools registered.[/]")
                else:
                    for s in schemas:
                        console.print(f"  [cyan]{s['name']}[/] — {s.get('description', '')}")
            elif cmd == "/session" and len(parts) > 1:
                subcmd = parts[1].lower()
                if subcmd == "new":
                    agent_loop = loop_factory()
                    console.print("[dim]New session started.[/]")
                elif subcmd == "list":
                    if agent_loop.store:
                        sessions = await agent_loop.store.list_sessions()
                        for s in sessions:
                            console.print(f"  [dim]{s['id'][:8]}…[/] {s['pack_name']} — {s['updated_at'][:19]}")
                    else:
                        console.print("[dim]No session store configured.[/]")
            elif cmd == "/pack" and len(parts) > 1:
                console.print(f"[dim]Pack switching not yet implemented. Restart with --pack {parts[1]}[/]")
            else:
                console.print(f"[red]Unknown command:[/] {cmd}. Type /help for commands.")
            continue

        # Run the agent loop and stream output
        await stream_response(agent_loop, user_input)


async def stream_response(agent_loop, user_input: str) -> None:
    """Stream the agent response to terminal."""
    accumulated_text = ""

    with Live(console=console, refresh_per_second=20) as live:
        async for event in agent_loop.run(user_input):
            if isinstance(event, TextDeltaEvent):
                accumulated_text += event.content
                live.update(Text(accumulated_text))

            elif isinstance(event, ToolCallEvent):
                # Show tool call dimmed above the text
                console.print(
                    f"[dim]→ tool:[/] [cyan]{event.name}[/] [dim]{event.input}[/]",
                    highlight=False,
                )

            elif isinstance(event, ToolResultEvent):
                result_str = str(event.result)
                if len(result_str) > 200:
                    result_str = result_str[:200] + "…"
                console.print(
                    f"[dim]← result:[/] {result_str}",
                    highlight=False,
                )

            elif isinstance(event, PermissionDeniedEvent):
                console.print(f"[red]✗ denied:[/] {event.tool_name}")

            elif isinstance(event, PermissionPromptEvent):
                console.print(f"[yellow]? permission:[/] {event.tool_name}")

            elif isinstance(event, ErrorEvent):
                console.print(f"[red]error:[/] {event.message}")

            elif isinstance(event, DoneEvent):
                # Final render
                if accumulated_text:
                    live.update(Text(accumulated_text))
