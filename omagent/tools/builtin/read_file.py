from pathlib import Path
from typing import Any
from omagent.tools.base import Tool
from omagent.tools.builtin._path_guard import check_path


class ReadFileTool(Tool):
    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file at the given path. Returns the file content as text."

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file to read.",
                }
            },
            "required": ["path"],
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        path = Path(input["path"]).expanduser().resolve()
        error = check_path(path)
        if error:
            return {"error": error}
        try:
            content = path.read_text(encoding="utf-8")
            return {"output": content, "path": str(path)}
        except FileNotFoundError:
            return {"error": f"File not found: {path}"}
        except PermissionError:
            return {"error": f"Permission denied: {path}"}
        except Exception as e:
            return {"error": str(e)}
