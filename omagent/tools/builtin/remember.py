from typing import Any
from omagent.tools.base import Tool


class RememberTool(Tool):
    """Store facts in persistent memory. Available in all packs."""

    def __init__(self, memory_store=None, session_id: str = ""):
        self._store = memory_store
        self._session_id = session_id

    @property
    def name(self) -> str:
        return "remember"

    @property
    def description(self) -> str:
        return (
            "Store a fact or finding in persistent memory. "
            "Memories persist across conversation turns and can be recalled later. "
            "Use to save important findings, user preferences, or project context."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "A descriptive key for the memory (e.g., 'dataset_shape', 'user_preference').",
                },
                "value": {
                    "type": "string",
                    "description": "The fact or information to remember.",
                },
            },
            "required": ["key", "value"],
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        if not self._store:
            return {"error": "Memory store not configured"}

        try:
            await self._store.set(self._session_id, input["key"], input["value"])
            return {"output": f"Remembered: {input['key']} = {input['value'][:100]}"}
        except Exception as e:
            return {"error": f"Failed to store memory: {e}"}
