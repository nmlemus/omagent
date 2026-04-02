from typing import Any
from omagent.tools.base import Tool
from omagent.core.orchestrator import AgentOrchestrator


class DelegateTool(Tool):
    """Delegate a task to a sub-agent using a specific domain pack."""

    def __init__(self, orchestrator: AgentOrchestrator):
        self._orchestrator = orchestrator

    @property
    def name(self) -> str:
        return "delegate"

    @property
    def description(self) -> str:
        return (
            "Delegate a task to a sub-agent with a specific domain pack. "
            "The sub-agent runs independently with its own tools and returns results. "
            "Use to leverage specialized agents: 'data_science' for analysis, "
            "'flutter_dev' for mobile development, etc."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pack": {
                    "type": "string",
                    "description": "Domain pack for the sub-agent (e.g., 'data_science', 'flutter_dev').",
                },
                "task": {
                    "type": "string",
                    "description": "The task or prompt for the sub-agent.",
                },
                "context": {
                    "type": "string",
                    "description": "Brief context or background for the sub-agent.",
                },
            },
            "required": ["pack", "task"],
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        result = await self._orchestrator.spawn_agent(
            pack_name=input["pack"],
            task=input["task"],
            context_summary=input.get("context", ""),
        )
        return result
