from pathlib import Path
from typing import Any
from omagent.tools.base import Tool


class ListDirTool(Tool):
    @property
    def name(self) -> str:
        return "list_dir"

    @property
    def description(self) -> str:
        return "List the contents of a directory. Returns file names, types, and sizes."

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the directory to list. Defaults to current directory.",
                }
            },
            "required": [],
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        path = Path(input.get("path", ".")).expanduser()
        try:
            entries = []
            for entry in sorted(path.iterdir()):
                stat = entry.stat()
                entries.append({
                    "name": entry.name,
                    "type": "dir" if entry.is_dir() else "file",
                    "size": stat.st_size if entry.is_file() else None,
                })
            return {"output": entries, "path": str(path)}
        except FileNotFoundError:
            return {"error": f"Directory not found: {path}"}
        except PermissionError:
            return {"error": f"Permission denied: {path}"}
        except Exception as e:
            return {"error": str(e)}
