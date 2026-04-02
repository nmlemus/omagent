# omagent/cli/tui/widgets/tool_card.py
"""Tool card widget — collapsible display for tool calls and results."""
import json
from typing import Any
from datetime import datetime
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from textual.reactive import reactive


SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class ToolCard(Widget, can_focus=False):
    """Expandable card showing tool name, input, spinner, output, duration."""

    DEFAULT_CSS = """
    ToolCard { height: auto; }
    """

    is_expanded = reactive(True)

    def __init__(
        self,
        tool_name: str,
        tool_input: dict,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.tool_result: dict | None = None
        self.is_error = False
        self.duration_ms: int | None = None
        self._header_widget: Static | None = None
        self._input_widget: Static | None = None
        self._output_widget: Static | None = None
        self._spinner_idx = 0
        self._spinner_timer = None
        self.add_class("tool-card")

    def compose(self) -> ComposeResult:
        # Header: toggle + tool name + spinner/duration (uses markup)
        spinner = SPINNER_FRAMES[0]
        self._header_widget = Static(
            f"[bold #ffe082]{spinner}[/] [bold]{self.tool_name}[/]",
            classes="tool-card-header",
        )
        yield self._header_widget

        # Input section — NO markup (code contains [ ] characters)
        input_display = self._format_input_plain()
        self._input_widget = Static(input_display, classes="tool-card-input", markup=False)
        yield self._input_widget

        # Output section — NO markup (output contains [ ] characters)
        self._output_widget = Static("", classes="tool-card-output", markup=False)
        yield self._output_widget

    def on_mount(self) -> None:
        """Start spinner animation."""
        self._spinner_timer = self.set_interval(0.1, self._animate_spinner)

    def _animate_spinner(self) -> None:
        """Cycle spinner frames."""
        if self.tool_result is not None:
            return
        self._spinner_idx = (self._spinner_idx + 1) % len(SPINNER_FRAMES)
        frame = SPINNER_FRAMES[self._spinner_idx]
        if self._header_widget:
            self._header_widget.update(
                f"[bold #ffe082]{frame}[/] [bold]{self.tool_name}[/] [dim italic]running...[/]"
            )

    def _format_input_plain(self) -> str:
        """Format tool input as plain text (no Rich markup — content has brackets)."""
        if self.tool_name in ("jupyter_execute",) and "code" in self.tool_input:
            code = self.tool_input["code"]
            return f">>> Python:\n{code}"

        if self.tool_name == "bash" and "command" in self.tool_input:
            return f"$ {self.tool_input['command']}"

        if self.tool_name == "read_file" and "path" in self.tool_input:
            return f"Reading: {self.tool_input['path']}"

        if self.tool_name == "write_file" and "path" in self.tool_input:
            content = self.tool_input.get("content", "")
            preview = content[:300] + "…" if len(content) > 300 else content
            return f"Writing: {self.tool_input['path']}\n{preview}"

        if self.tool_name == "sql_query" and "query" in self.tool_input:
            return f"SQL:\n{self.tool_input['query']}"

        if self.tool_name == "dataset_profile" and "path" in self.tool_input:
            return f"Profiling: {self.tool_input['path']}"

        if self.tool_name == "list_dir":
            return f"Listing: {self.tool_input.get('path', '.')}"

        # Generic: show JSON
        formatted = json.dumps(self.tool_input, indent=2)
        if len(formatted) > 500:
            formatted = formatted[:500] + "\n…"
        return formatted

    def set_result(self, result: dict, is_error: bool = False, duration_ms: int | None = None) -> None:
        """Update the card with the tool result."""
        self.tool_result = result
        self.is_error = is_error
        self.duration_ms = duration_ms

        # Stop spinner
        if self._spinner_timer:
            self._spinner_timer.stop()

        # Update header with duration badge
        duration_str = f" [{duration_ms}ms]" if duration_ms else ""
        status = "[#ef9a9a]✗[/]" if is_error else "[#a5d6a7]✓[/]"
        if self._header_widget:
            self._header_widget.update(
                f"{status} [bold]{self.tool_name}[/] [dim]{duration_str}[/]"
            )

        if is_error:
            self.add_class("tool-card-error")

        # Update output
        if self._output_widget:
            output_text = self._format_output(result)
            self._output_widget.update(output_text)

    def _format_output(self, result: dict) -> str:
        """Format tool result as plain text (no Rich markup)."""
        parts = []

        # Show stdout
        stdout = result.get("stdout", "")
        if stdout:
            parts.append(f"stdout:\n{stdout[:1000]}")

        # Show stderr
        stderr = result.get("stderr", "")
        if stderr:
            parts.append(f"stderr:\n{stderr[:500]}")

        # Show output
        output = result.get("output", "")
        if output and isinstance(output, str):
            parts.append(f"Output: {output[:500]}")
        elif output and isinstance(output, list):
            for item in output[:10]:
                if isinstance(item, dict):
                    parts.append(json.dumps(item))
                else:
                    parts.append(str(item))

        # Show outputs array (Jupyter)
        outputs = result.get("outputs", [])
        for out in outputs:
            if isinstance(out, dict):
                if "text" in out:
                    parts.append(out["text"])
                if "image_base64" in out:
                    parts.append("[image saved to workspace]")
                if "html" in out:
                    parts.append("[HTML output]")

        # Show error
        error = result.get("error", "")
        if error:
            if isinstance(error, dict):
                tb = "\n".join(str(line) for line in error.get("traceback", []))
                parts.append(f"ERROR: {error.get('ename', 'Error')}: {error.get('evalue', '')}\n{tb}")
            elif isinstance(error, str):
                parts.append(f"ERROR: {error}")

        # Show metrics
        metrics = result.get("metrics", {})
        if metrics:
            parts.append("Metrics:")
            for k, v in metrics.items():
                parts.append(f"  {k}: {v}")

        return "\n".join(parts) if parts else "No output"

    def on_click(self) -> None:
        """Toggle expanded/collapsed."""
        self.is_expanded = not self.is_expanded
        if self._input_widget:
            self._input_widget.display = self.is_expanded
        if self._output_widget:
            self._output_widget.display = self.is_expanded
