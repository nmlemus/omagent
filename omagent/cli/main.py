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
    from omagent.core.skill_loader import SkillRegistry
    skill_registry = SkillRegistry()

    try:
        from omagent.packs.loader import DomainPackLoader
        loader = DomainPackLoader()
        pack = loader.load(pack_name)
        system_prompt = pack.system_prompt
        registry.register_many(pack.tools)
        policy.load_pack_permissions(pack.permissions)
        mcp_servers = pack.mcp_servers

        # Discover skills from pack directory
        if pack.pack_dir:
            pack_skills_dir = pack.pack_dir / "skills"
            if pack_skills_dir.is_dir():
                skill_registry.discover([pack_skills_dir], source="pack")
    except Exception:
        system_prompt = f"You are a helpful AI assistant. Pack: {pack_name}."

    # Discover from standard paths + walk-up
    skill_registry.discover([
        Path.cwd() / ".omagent" / "skills",
        Path.home() / ".omagent" / "skills",
        Path.home() / ".claude" / "skills",
    ], source="user")
    skill_registry.discover_walk_up()

    # Add <available_skills> XML to system prompt
    xml_prompt = skill_registry.get_prompt_xml()
    if xml_prompt:
        system_prompt += f"\n\n{xml_prompt}"

    skills_loaded = skill_registry.names()

    from omagent.tools.builtin.skill_tool import SkillTool
    registry.register(SkillTool(skill_registry))

    from omagent.core.tracker import ActivityTracker
    from omagent.core.workspace import Workspace
    from omagent.core.journal import EventJournal
    from omagent.core.memory import ConversationSummarizer, MemoryStore
    from omagent.core.planner import PlanStore
    from omagent.tools.builtin.remember import RememberTool
    from omagent.tools.builtin.summarize import SummarizeTool

    sid = session_id or __import__("uuid").uuid4().hex
    session = Session(id=sid, pack_name=pack_name)

    workspace = Workspace(sid)
    journal = EventJournal(sid, workspace.logs_dir)
    summarizer = ConversationSummarizer()
    memory_store = MemoryStore()
    plan_store = PlanStore()

    session.workspace_path = str(workspace.root)

    # Log pack loading to journal
    journal.log("pack_loaded", {
        "pack_name": pack_name,
        "tools": registry.names(),
        "skills": skills_loaded,
        "workspace": str(workspace.root),
    })
    journal.log_session_start(pack_name, LiteLLMProvider().model)

    # Register cross-cutting tools (transversal — available in ALL packs)
    remember_tool = RememberTool(memory_store=memory_store, session_id=sid)
    summarize_tool = SummarizeTool(summarizer=summarizer, session=session)
    registry.register(remember_tool)
    registry.register(summarize_tool)

    # Inject workspace into tools that support it
    for tool_name in registry.names():
        tool = registry.get(tool_name)
        if hasattr(tool, '_workspace') and tool._workspace is None:
            tool._workspace = workspace

    # Tell the LLM where to save artifacts
    workspace_instruction = (
        f"\n\n[Workspace]\n"
        f"Save all generated files (charts, CSVs, reports, notebooks) to: {workspace.artifacts_dir}\n"
        f"Example: plt.savefig('{workspace.artifacts_dir}/chart.png')\n"
        f"Example: df.to_csv('{workspace.artifacts_dir}/cleaned_data.csv')\n"
    )
    system_prompt += workspace_instruction

    loop = AgentLoop(
        session=session,
        registry=registry,
        provider=LiteLLMProvider(),
        policy=policy,
        hooks=HookRunner(),
        system_prompt=system_prompt,
        store=store,
        tracker=ActivityTracker(),
        workspace=workspace,
        journal=journal,
        summarizer=summarizer,
        memory_store=memory_store,
        plan_store=plan_store,
        skill_registry=skill_registry,
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
    from omagent.core.config import setup_logging
    setup_logging()


@cli.command()
@click.option("--pack", default=None, envvar="OMAGENT_PACK", help="Domain pack name")
@click.option("--session", "session_id", default=None, help="Resume a session by ID")
@click.option("--classic", is_flag=True, default=False, help="Use classic REPL instead of TUI")
def chat(pack: str | None, session_id: str | None, classic: bool):
    """Start an interactive multi-turn chat session (TUI by default)."""
    pack_name = pack or os.getenv("OMAGENT_PACK", "default")

    if classic:
        from omagent.cli.repl import run_repl

        async def loop_factory_async(sid=None):
            loop = _build_loop(pack_name, sid or session_id)
            await _connect_mcp(loop)
            return loop

        asyncio.run(run_repl(loop_factory_async, pack_name=pack_name))
    else:
        from omagent.cli.tui.app import OmagentApp

        def loop_factory(pn=None, sid=None):
            return _build_loop(pn or pack_name, sid or session_id)

        app = OmagentApp(loop_factory=loop_factory, pack_name=pack_name, session_id=session_id)
        app.run()


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


@cli.command("config")
def show_config():
    """Show active configuration."""
    from omagent.core.config import get_config
    from rich.console import Console
    from rich.table import Table

    config = get_config()
    console = Console()
    table = Table(title="omagent Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    for field_name, value in config.model_dump().items():
        # Mask API key
        display = "****" if field_name == "api_key" and value else str(value)
        table.add_row(field_name, display)

    console.print(table)


@cli.command()
@click.argument("when", default="today")
def activity(when: str):
    """Show activity report. Usage: omagent activity [today|yesterday|2026-04-01]"""
    from omagent.core.tracker import ActivityTracker
    from datetime import datetime, timezone, timedelta

    tracker = ActivityTracker()
    _today = datetime.now(timezone.utc).date()
    if when == "today":
        target = _today.isoformat()
    elif when == "yesterday":
        target = (_today - timedelta(days=1)).isoformat()
    else:
        target = when

    async def _show():
        report = await tracker.format_daily_report(target)
        from rich.console import Console
        Console().print(report)

    import asyncio
    asyncio.run(_show())


@cli.command()
@click.argument("session_id", default="last")
def replay(session_id: str):
    """Replay a session — show rich timeline of what the agent did.

    SESSION_ID can be a full or partial workspace ID, or 'last' for the most recent session.
    """
    from omagent.cli.replay import replay_session
    from omagent.core.workspace import get_workspaces_dir
    from rich.console import Console

    console = Console()
    ws_dir = get_workspaces_dir()

    if not ws_dir.exists() or not any(ws_dir.iterdir()):
        console.print("[red]No workspaces found.[/]")
        console.print("[dim]Run a session first with 'omagent chat' or 'omagent run'.[/]")
        return

    if session_id == "last":
        dirs = [d for d in ws_dir.iterdir() if d.is_dir()]
        if not dirs:
            console.print("[red]No workspaces found.[/]")
            return
        target = sorted(dirs, key=lambda d: d.stat().st_mtime, reverse=True)[0]
    else:
        matches = [d for d in ws_dir.iterdir() if d.is_dir() and d.name.startswith(session_id)]
        if not matches:
            console.print(f"[red]No workspace found for:[/] {session_id}")
            console.print("[dim]Use 'omagent workspace list' to see available sessions.[/]")
            return
        target = matches[0]

    events_path = target / "logs" / "events.jsonl"
    replay_session(events_path, console)


@cli.group()
def session():
    """Manage sessions."""
    pass


@session.command("export")
@click.argument("session_id")
@click.option("--format", "fmt", type=click.Choice(["json", "markdown"]), default="json")
@click.option("--output", "-o", default=None, help="Output file path")
def session_export(session_id: str, fmt: str, output: str | None):
    """Export a session to JSON or Markdown."""
    from omagent.core.session import SessionStore
    from rich.console import Console

    console = Console()
    store = SessionStore()

    async def _export():
        s = await store.load(session_id)
        if s is None:
            console.print(f"[red]Session not found:[/] {session_id}")
            return
        if fmt == "markdown":
            content = s.export_markdown()
        else:
            content = s.export_json()

        if output:
            from pathlib import Path
            Path(output).write_text(content)
            console.print(f"[green]Exported to {output}[/]")
        else:
            console.print(content)

    asyncio.run(_export())


@session.command("list")
def session_list():
    """List recent sessions."""
    from omagent.core.session import SessionStore
    from rich.console import Console
    from rich.table import Table

    console = Console()
    store = SessionStore()

    async def _list():
        sessions = await store.list_sessions()
        if not sessions:
            console.print("[dim]No sessions found.[/]")
            return
        table = Table(title="Sessions")
        table.add_column("ID", style="cyan")
        table.add_column("Pack")
        table.add_column("Updated")
        for s in sessions:
            table.add_row(s["id"][:12] + "…", s["pack_name"], s["updated_at"][:19])
        console.print(table)

    asyncio.run(_list())


@cli.group()
def workspace():
    """Manage workspaces."""
    pass


@workspace.command("list")
def workspace_list():
    """List session workspaces."""
    from omagent.core.workspace import get_workspaces_dir
    from rich.console import Console
    from rich.table import Table

    console = Console()
    ws_dir = get_workspaces_dir()
    if not ws_dir.exists():
        console.print("[dim]No workspaces found.[/]")
        return

    table = Table(title="Workspaces")
    table.add_column("Session ID", style="cyan")
    table.add_column("Artifacts")
    table.add_column("Notebook")
    table.add_column("Size")

    for d in sorted(ws_dir.iterdir(), reverse=True):
        if d.is_dir():
            artifacts = len(list((d / "artifacts").iterdir())) if (d / "artifacts").exists() else 0
            has_nb = "Yes" if (d / "notebooks" / "session.ipynb").exists() else "No"
            size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            size_str = f"{size/1024:.1f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
            table.add_row(d.name[:16] + "…", str(artifacts), has_nb, size_str)

    console.print(table)


@workspace.command("open")
@click.argument("session_id")
def workspace_open(session_id: str):
    """Show workspace contents."""
    from omagent.core.workspace import get_workspaces_dir
    from rich.console import Console
    from rich.tree import Tree

    console = Console()
    ws_dir = get_workspaces_dir()

    # Find matching workspace
    matches = [d for d in ws_dir.iterdir() if d.name.startswith(session_id)]
    if not matches:
        console.print(f"[red]No workspace found for: {session_id}[/]")
        return

    ws_path = matches[0]
    tree = Tree(f"[bold cyan]{ws_path.name}[/]")
    for subdir in sorted(ws_path.iterdir()):
        if subdir.is_dir():
            branch = tree.add(f"[bold]{subdir.name}/[/]")
            for f in sorted(subdir.iterdir()):
                size = f.stat().st_size
                branch.add(f"{f.name} [dim]({size} bytes)[/]")

    console.print(tree)


@workspace.command("clean")
@click.option("--older-than", default=7, type=int, help="Remove workspaces older than N days (default: 7)")
@click.option("--dry-run", is_flag=True, default=False, help="Show what would be deleted without deleting")
@click.option("--force", is_flag=True, default=False, help="Skip confirmation")
def workspace_clean(older_than: int, dry_run: bool, force: bool):
    """Remove old workspaces to free disk space."""
    import shutil
    from datetime import datetime, timezone, timedelta
    from omagent.core.workspace import get_workspaces_dir
    from rich.console import Console

    console = Console()
    ws_dir = get_workspaces_dir()
    if not ws_dir.exists():
        console.print("[dim]No workspaces found.[/]")
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than)
    to_remove = []
    total_size = 0

    for d in ws_dir.iterdir():
        if not d.is_dir():
            continue
        mtime = datetime.fromtimestamp(d.stat().st_mtime, timezone.utc)
        if mtime < cutoff:
            size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            to_remove.append((d, size, mtime))
            total_size += size

    if not to_remove:
        console.print(f"[dim]No workspaces older than {older_than} days.[/]")
        return

    size_str = f"{total_size/1024:.1f}KB" if total_size < 1024*1024 else f"{total_size/1024/1024:.1f}MB"
    console.print(f"Found [bold]{len(to_remove)}[/] workspaces older than {older_than} days ({size_str}):\n")
    for d, size, mtime in to_remove:
        s = f"{size/1024:.1f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
        console.print(f"  [cyan]{d.name[:16]}…[/] [dim]{mtime.strftime('%Y-%m-%d')}[/] {s}")

    if dry_run:
        console.print(f"\n[dim]Dry run — nothing deleted. Would free {size_str}.[/]")
        return

    if not force:
        confirm = click.confirm(f"\nDelete {len(to_remove)} workspaces?")
        if not confirm:
            console.print("[dim]Cancelled.[/]")
            return

    deleted = 0
    for d, _, _ in to_remove:
        try:
            shutil.rmtree(d)
            deleted += 1
        except Exception as e:
            console.print(f"[red]Failed to delete {d.name}: {e}[/]")

    console.print(f"\n[green]Deleted {deleted} workspaces, freed {size_str}.[/]")


@cli.group("pack")
def pack_group():
    """Manage domain packs."""
    pass


@pack_group.command("list")
def pack_list():
    """List available domain packs."""
    from omagent.packs.loader import DomainPackLoader
    from rich.console import Console
    from rich.table import Table

    console = Console()
    loader = DomainPackLoader()
    packs = loader.list_packs()

    if not packs:
        console.print("[dim]No packs found.[/]")
        return

    table = Table(title="Domain Packs")
    table.add_column("Name", style="cyan")
    table.add_column("Version")
    table.add_column("Description")

    for name in packs:
        try:
            p = loader.load(name)
            table.add_row(name, p.version, p.description[:60] or "[dim]—[/]")
        except Exception:
            table.add_row(name, "?", "[red]failed to load[/]")

    console.print(table)


@pack_group.command("init")
@click.argument("name")
@click.option("--dir", "target_dir", default=None, help="Target directory (default: ~/.omagent/packs/<name>)")
def pack_init(name: str, target_dir: str | None):
    """Scaffold a new domain pack."""
    from rich.console import Console

    console = Console()
    if target_dir:
        pack_dir = Path(target_dir) / name
    else:
        pack_dir = Path.home() / ".omagent" / "packs" / name

    if pack_dir.exists():
        console.print(f"[red]Pack directory already exists:[/] {pack_dir}")
        return

    pack_dir.mkdir(parents=True)
    (pack_dir / "tools").mkdir()
    (pack_dir / "skills").mkdir()
    (pack_dir / "tools" / "__init__.py").write_text("")

    pack_yaml = f"""name: {name}
version: "0.1.0"
description: "{name} domain pack"

system_prompt: |
  You are an AI assistant specialized in {name}.
  Help the user with tasks related to {name}.

tools:
  - omagent.tools.builtin.read_file:ReadFileTool
  - omagent.tools.builtin.write_file:WriteFileTool
  - omagent.tools.builtin.list_dir:ListDirTool
  - omagent.tools.builtin.bash:BashTool

permissions:
  read_file: auto
  list_dir: auto
  write_file: prompt
  bash: prompt
"""
    (pack_dir / "pack.yaml").write_text(pack_yaml)

    console.print(f"[green]Created pack:[/] [bold]{name}[/] at {pack_dir}")
    console.print(f"\n  [dim]pack.yaml[/]     — Pack configuration")
    console.print(f"  [dim]tools/[/]        — Custom tool modules")
    console.print(f"  [dim]skills/[/]       — SKILL.md files")
    console.print(f"\n  Use: [bold]omagent chat --pack {name}[/]")


@pack_group.command("validate")
@click.argument("name")
def pack_validate(name: str):
    """Validate a domain pack configuration."""
    from omagent.packs.loader import DomainPackLoader
    from rich.console import Console

    console = Console()
    loader = DomainPackLoader()
    errors = []

    try:
        pack = loader.load(name)
    except FileNotFoundError:
        console.print(f"[red]Pack not found:[/] {name}")
        return
    except Exception as e:
        console.print(f"[red]Failed to load pack:[/] {e}")
        return

    # Validate fields
    if not pack.name:
        errors.append("Missing 'name' field")
    if not pack.system_prompt or pack.system_prompt == "You are a helpful AI assistant.":
        errors.append("Using default system_prompt — consider customizing it")
    if not pack.tools:
        errors.append("No tools loaded — check tool paths in pack.yaml")

    # Check tool names match permissions
    tool_names = {t.name for t in pack.tools}
    for perm_tool in pack.permissions:
        if perm_tool not in tool_names:
            errors.append(f"Permission for unknown tool: '{perm_tool}'")

    # Check skills directory
    if pack.pack_dir:
        skills_dir = pack.pack_dir / "skills"
        if skills_dir.is_dir():
            skill_count = sum(1 for d in skills_dir.iterdir() if (d / "SKILL.md").exists())
            console.print(f"  [dim]Skills:[/] {skill_count} found")
        else:
            console.print(f"  [dim]Skills:[/] no skills/ directory")

    console.print(f"\n[bold]Validating pack:[/] {pack.name} v{pack.version}")
    console.print(f"  [dim]Description:[/] {pack.description or '(none)'}")
    console.print(f"  [dim]Tools:[/] {len(pack.tools)} ({', '.join(t.name for t in pack.tools)})")
    console.print(f"  [dim]Permissions:[/] {len(pack.permissions)} rules")
    console.print(f"  [dim]MCP servers:[/] {len(pack.mcp_servers)}")

    if errors:
        console.print(f"\n[yellow]Warnings ({len(errors)}):[/]")
        for e in errors:
            console.print(f"  [yellow]![/] {e}")
    else:
        console.print(f"\n[green]Pack is valid.[/]")


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
