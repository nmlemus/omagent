import asyncio
from typing import Any
from omagent.tools.base import Tool


class FlutterCLITool(Tool):
    """Run Flutter CLI commands (create, build, run, test, pub get, etc.)."""

    @property
    def name(self) -> str:
        return "flutter_cli"

    @property
    def description(self) -> str:
        return (
            "Execute Flutter CLI commands. Supports: create, build, run, test, pub get, "
            "pub add, clean, devices, doctor. Use for project creation, building for "
            "Android/iOS, running tests, and managing dependencies."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "Flutter command to run (e.g., 'create my_app', 'build apk', "
                        "'build ios', 'test', 'pub get', 'pub add provider', 'doctor')."
                    ),
                },
                "working_dir": {
                    "type": "string",
                    "description": "Working directory for the command. Defaults to current dir.",
                },
            },
            "required": ["command"],
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        command = input["command"]
        cwd = input.get("working_dir")

        full_cmd = f"flutter {command}"

        try:
            proc = await asyncio.create_subprocess_shell(
                full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            except asyncio.TimeoutError:
                proc.kill()
                return {"error": f"Command timed out after 300s: flutter {command}"}

            result = {
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "returncode": proc.returncode,
            }

            if proc.returncode == 0:
                result["output"] = result["stdout"] or "Command completed successfully"
            else:
                result["error"] = f"flutter {command} failed (exit {proc.returncode})"

            return result
        except FileNotFoundError:
            return {"error": "Flutter CLI not found. Install from https://flutter.dev/docs/get-started/install"}
        except Exception as e:
            return {"error": str(e)}
