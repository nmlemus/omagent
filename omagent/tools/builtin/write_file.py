from pathlib import Path
from typing import Any
from omagent.tools.base import Tool


class WriteFileTool(Tool):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file. Creates the file and any parent directories if they don't exist."

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write.",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file.",
                },
            },
            "required": ["path", "content"],
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        path = Path(input["path"]).expanduser()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(input["content"], encoding="utf-8")
            return {"output": f"Written {len(input['content'])} characters to {path}"}
        except PermissionError:
            return {"error": f"Permission denied: {path}"}
        except Exception as e:
            return {"error": str(e)}
