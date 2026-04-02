import asyncio
from typing import Any
from omagent.tools.base import Tool

TIMEOUT = 30  # seconds


class BashTool(Tool):
    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return (
            "Run a bash shell command and return stdout and stderr. "
            "Use for running scripts, installing packages, or any shell operation. "
            f"Timeout: {TIMEOUT}s."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute.",
                }
            },
            "required": ["command"],
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        command = input["command"]
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=TIMEOUT
                )
            except asyncio.TimeoutError:
                proc.kill()
                return {"error": f"Command timed out after {TIMEOUT}s", "command": command}

            return {
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "returncode": proc.returncode,
            }
        except Exception as e:
            return {"error": str(e)}
