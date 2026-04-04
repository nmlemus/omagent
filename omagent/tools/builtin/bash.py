import asyncio
import logging
import re
from typing import Any
from omagent.tools.base import Tool

logger = logging.getLogger(__name__)

TIMEOUT = 120  # seconds

# Patterns that are too dangerous for automated execution
_BLOCKED_PATTERNS = [
    re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f\b.*\s+/\s*$"),  # rm -rf /
    re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f\b.*\s+/\w+\s*$"),  # rm -rf /usr etc (top-level)
    re.compile(r"\bmkfs\b"),
    re.compile(r"\bdd\s+.*of=/dev/"),
    re.compile(r"\bcurl\b.*\|\s*sh\b"),
    re.compile(r"\bcurl\b.*\|\s*bash\b"),
    re.compile(r"\bwget\b.*\|\s*sh\b"),
    re.compile(r"\bwget\b.*\|\s*bash\b"),
    re.compile(r">\s*/etc/"),
    re.compile(r"\bchmod\s+777\s+/"),
    re.compile(r"\b:()\s*\{"),  # fork bomb
]


def _is_blocked(command: str) -> str | None:
    """Return reason if command matches a blocked pattern, else None."""
    for pattern in _BLOCKED_PATTERNS:
        if pattern.search(command):
            return f"Blocked dangerous pattern: {pattern.pattern}"
    return None


class BashTool(Tool):
    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return (
            "Run a bash shell command and return stdout and stderr. "
            "Use for running scripts, installing packages, or any shell operation. "
            "Commands must be non-interactive (no prompts for user input). "
            "Use flags like --yes, -y, or pipe from /dev/null when needed. "
            f"Timeout: {TIMEOUT}s."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute. Must be non-interactive.",
                }
            },
            "required": ["command"],
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        command = input["command"]
        logger.info("bash: %s", command[:200])
        blocked = _is_blocked(command)
        if blocked:
            logger.warning("bash blocked: %s — %s", command[:100], blocked)
            return {"error": blocked, "command": command}
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=TIMEOUT
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return {"error": f"Command timed out after {TIMEOUT}s", "command": command}
            finally:
                # Close transport to prevent "Event loop is closed" warnings
                # during garbage collection after the event loop shuts down.
                if hasattr(proc, "_transport") and proc._transport:
                    proc._transport.close()

            return {
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "returncode": proc.returncode,
            }
        except Exception as e:
            return {"error": str(e)}
