# omagent/cli/replay.py
"""Session replay — render a rich timeline from JSONL events."""
import ast
import json
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table


def replay_session(events_path: Path, console: Console | None = None) -> None:
    """Render a rich timeline from a JSONL events file."""
    console = console or Console()

    if not events_path.exists():
        console.print(f"[red]Events file not found:[/] {events_path}")
        return

    events = []
    with open(events_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))

    if not events:
        console.print("[dim]No events found.[/]")
        return

    # Header info
    session_id = events[0].get("session_id", "unknown")
    first_ts = events[0].get("timestamp", "")[:19]
    last_ts = events[-1].get("timestamp", "")[:19]

    # Compute stats
    total_tokens_in = 0
    total_tokens_out = 0
    total_tool_calls = 0
    total_llm_calls = 0
    total_llm_time = 0
    total_tool_time = 0
    errors = 0
    tools_used: dict[str, int] = {}

    for e in events:
        t = e["type"]
        d = e.get("data", {})
        if t == "llm_response":
            total_llm_calls += 1
            total_tokens_in += d.get("tokens_in") or 0
            total_tokens_out += d.get("tokens_out") or 0
            total_llm_time += d.get("latency_ms") or 0
        elif t == "tool_call":
            total_tool_calls += 1
            name = d.get("tool_name", "?")
            tools_used[name] = tools_used.get(name, 0) + 1
        elif t == "tool_result":
            total_tool_time += d.get("duration_ms") or 0
            if d.get("is_error"):
                errors += 1

    # Stats header
    console.print()
    console.print(Rule(f"[bold #80cbc4]Session Replay[/] — {session_id[:12]}…", style="#3a3a50"))
    console.print()

    stats_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    stats_table.add_column(style="dim")
    stats_table.add_column(style="bold")
    stats_table.add_row("Session", session_id)
    stats_table.add_row("Period", f"{first_ts} → {last_ts}")
    stats_table.add_row("LLM Calls", f"{total_llm_calls} ({total_llm_time / 1000:.1f}s)")
    stats_table.add_row("Tool Calls", f"{total_tool_calls} ({total_tool_time / 1000:.1f}s)")
    stats_table.add_row("Tokens", f"{total_tokens_in:,} in / {total_tokens_out:,} out")
    stats_table.add_row("Errors", f"[red]{errors}[/]" if errors else "[green]0[/]")
    if tools_used:
        tools_str = ", ".join(
            f"{k}({v})" for k, v in sorted(tools_used.items(), key=lambda x: -x[1])
        )
        stats_table.add_row("Tools Used", tools_str)
    console.print(stats_table)
    console.print()
    console.print(Rule("Timeline", style="#3a3a50"))
    console.print()

    # Render each event
    current_round = -1
    for e in events:
        ts = e.get("timestamp", "")
        time_short = ts[11:19] if len(ts) >= 19 else ts
        round_num = e.get("round", 0)
        event_type = e["type"]
        data = e.get("data", {})

        # Round separator
        if round_num != current_round:
            current_round = round_num
            console.print(f"  [dim]{'─' * 60}[/]")
            console.print(f"  [bold #a8b4f0]Round {round_num}[/]")
            console.print()

        if event_type == "user_message":
            text = data.get("text", "")
            console.print(Panel(
                text,
                title=f"[bold #a8b4f0]You[/] [dim]{time_short}[/]",
                border_style="#a8b4f0",
                padding=(0, 1),
            ))
            console.print()

        elif event_type == "llm_request":
            model = data.get("model", "?")
            msgs = data.get("message_count", "?")
            console.print(f"  [dim]{time_short}[/]  [#ffe082]→ LLM[/] {model} [dim]({msgs} messages)[/]")

        elif event_type == "llm_response":
            tokens_in = data.get("tokens_in") or 0
            tokens_out = data.get("tokens_out") or 0
            latency = data.get("latency_ms") or 0
            tool_count = data.get("tool_calls_count", 0)
            tools_str = f" → [#ce93d8]{tool_count} tool call{'s' if tool_count != 1 else ''}[/]" if tool_count else ""
            console.print(
                f"  [dim]{time_short}[/]  [#a5d6a7]← LLM[/] "
                f"{tokens_in:,}/{tokens_out:,} tok "
                f"[dim]({latency / 1000:.1f}s)[/]"
                f"{tools_str}"
            )

        elif event_type == "tool_call":
            tool_name = data.get("tool_name", "?")
            input_summary = data.get("input_summary", "")

            # Try to extract code for display in jupyter_execute or bash
            code = None
            lang = "python"
            if input_summary:
                try:
                    parsed = ast.literal_eval(input_summary)
                    if isinstance(parsed, dict):
                        if tool_name == "jupyter_execute" and "code" in parsed:
                            code = parsed["code"]
                            lang = "python"
                        elif tool_name == "bash" and "command" in parsed:
                            code = parsed["command"]
                            lang = "bash"
                        elif tool_name == "write_file" and "content" in parsed:
                            path_hint = parsed.get("path", "")
                            code = parsed["content"][:500]
                            if path_hint.endswith((".py",)):
                                lang = "python"
                            elif path_hint.endswith((".md",)):
                                lang = "markdown"
                            elif path_hint.endswith((".json",)):
                                lang = "json"
                            else:
                                lang = "text"
                except Exception:
                    pass

            if code:
                console.print(f"  [dim]{time_short}[/]  [#ce93d8]⚡ {tool_name}[/]")
                console.print(Syntax(code, lang, theme="monokai", padding=(0, 1), line_numbers=False))
            else:
                summary_display = input_summary[:100] if input_summary else ""
                console.print(
                    f"  [dim]{time_short}[/]  [#ce93d8]⚡ {tool_name}[/] "
                    f"[dim]{summary_display}[/]"
                )

        elif event_type == "tool_result":
            tool_name = data.get("tool_name", "?")
            is_error = data.get("is_error", False)
            duration = data.get("duration_ms")
            dur_str = f" ({duration}ms)" if duration else ""

            if is_error:
                console.print(f"  [dim]{time_short}[/]  [red]✗ {tool_name}{dur_str}[/]")
            else:
                console.print(f"  [dim]{time_short}[/]  [#a5d6a7]✓ {tool_name}{dur_str}[/]")

        elif event_type == "artifact_saved":
            path = data.get("path", "?")
            size = data.get("size_bytes", 0)
            console.print(f"  [dim]{time_short}[/]  [#80cbc4]📄 Artifact:[/] {path} [dim]({size:,} bytes)[/]")

        elif event_type == "session_start":
            pack = data.get("pack_name", "?")
            model = data.get("model", "?")
            console.print(f"  [dim]{time_short}[/]  [#ffe082]▶ Session start[/] — pack: {pack}, model: {model}")

        elif event_type == "session_end":
            turns = data.get("turns", "?")
            cost = data.get("total_cost", 0)
            cost_str = f"${cost:.4f}" if cost else "—"
            console.print(f"  [dim]{time_short}[/]  [#a5d6a7]■ Session end[/] — {turns} turns, cost: {cost_str}")

        elif event_type == "error":
            msg = data.get("message", "")
            console.print(f"  [dim]{time_short}[/]  [red]❌ Error:[/] {msg[:120]}")

        elif event_type == "memory_summary":
            count = data.get("messages_summarized", "?")
            console.print(f"  [dim]{time_short}[/]  [#ffe082]📝 Summarized {count} messages[/]")

        elif event_type == "sub_agent_start":
            pack = data.get("pack_name", "?")
            task = data.get("task", "")[:80]
            console.print(f"  [dim]{time_short}[/]  [#ce93d8]🔀 Sub-agent:[/] {pack} — {task}")

        elif event_type == "sub_agent_done":
            pack = data.get("pack_name", "?")
            is_err = data.get("is_error", False)
            status = "[red]ERROR[/]" if is_err else "[#a5d6a7]OK[/]"
            console.print(f"  [dim]{time_short}[/]  [#a5d6a7]🔀 Sub-agent done:[/] {pack} — {status}")

        elif event_type == "plan_created":
            steps = data.get("total_steps", "?")
            goal = data.get("goal", "")[:80]
            console.print(f"  [dim]{time_short}[/]  [#ffe082]📋 Plan:[/] {steps} steps — {goal}")

        elif event_type == "plan_step_completed":
            step = data.get("step_num", "?")
            desc = data.get("description", "")[:80]
            console.print(f"  [dim]{time_short}[/]  [#a5d6a7]✓ Step {step}:[/] {desc}")

        elif event_type == "code_executed":
            success = data.get("success", True)
            exec_time = data.get("execution_time_ms")
            dur_str = f" ({exec_time}ms)" if exec_time else ""
            status = "[#a5d6a7]✓[/]" if success else "[red]✗[/]"
            console.print(f"  [dim]{time_short}[/]  {status} code_executed{dur_str}")

    console.print()
    console.print(Rule(style="#3a3a50"))

    # Show workspace artifacts and notebook summary
    ws_root = events_path.parent.parent
    artifacts_dir = ws_root / "artifacts"
    notebook_path = ws_root / "notebooks" / "session.ipynb"

    has_artifacts = artifacts_dir.exists() and any(artifacts_dir.iterdir())
    has_notebook = notebook_path.exists()

    if has_artifacts or has_notebook:
        console.print()

    if has_artifacts:
        console.print("[bold #80cbc4]Artifacts[/]")
        for f in sorted(artifacts_dir.iterdir()):
            size = f.stat().st_size
            size_str = f"{size / 1024:.1f} KB" if size >= 1024 else f"{size} B"
            console.print(f"  [#80cbc4]●[/] {f.name} [dim]({size_str})[/]")

    if has_notebook:
        nb = json.loads(notebook_path.read_text(encoding="utf-8"))
        cell_count = len(nb.get("cells", []))
        console.print(f"\n[bold #80cbc4]Notebook[/] — {cell_count} cells")
        console.print(f"  [dim]{notebook_path}[/]")

    console.print()
