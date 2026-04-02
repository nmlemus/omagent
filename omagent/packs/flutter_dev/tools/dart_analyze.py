import asyncio
from typing import Any
from omagent.tools.base import Tool


class DartAnalyzeTool(Tool):
    """Run Dart analysis on a Flutter project and parse issues."""

    @property
    def name(self) -> str:
        return "dart_analyze"

    @property
    def description(self) -> str:
        return (
            "Run 'dart analyze' on a Flutter/Dart project. Returns structured issues "
            "with severity, file, line, and message. Use to find code quality issues, "
            "unused imports, type errors, and potential bugs."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "Path to the Flutter/Dart project root.",
                },
            },
            "required": ["project_path"],
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        project_path = input["project_path"]

        try:
            proc = await asyncio.create_subprocess_shell(
                "dart analyze --format=machine .",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_path,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            output = stdout.decode("utf-8", errors="replace")

            issues = []
            for line in output.strip().split("\n"):
                if not line.strip():
                    continue
                # Machine format: SEVERITY|TYPE|LINT_CODE|FILE|LINE|COL|LENGTH|MESSAGE
                parts = line.split("|")
                if len(parts) >= 8:
                    issues.append({
                        "severity": parts[0],
                        "type": parts[1],
                        "code": parts[2],
                        "file": parts[3],
                        "line": int(parts[4]) if parts[4].isdigit() else parts[4],
                        "column": int(parts[5]) if parts[5].isdigit() else parts[5],
                        "message": parts[7],
                    })

            summary = {
                "errors": sum(1 for i in issues if i["severity"] == "ERROR"),
                "warnings": sum(1 for i in issues if i["severity"] == "WARNING"),
                "infos": sum(1 for i in issues if i["severity"] == "INFO"),
            }

            return {
                "output": f"Analysis complete: {summary['errors']} errors, {summary['warnings']} warnings, {summary['infos']} info",
                "issues": issues[:50],  # Cap at 50
                "summary": summary,
                "total_issues": len(issues),
            }
        except FileNotFoundError:
            return {"error": "Dart SDK not found. Install Flutter SDK which includes Dart."}
        except asyncio.TimeoutError:
            return {"error": "Analysis timed out after 120s"}
        except Exception as e:
            return {"error": f"Analysis failed: {e}"}
