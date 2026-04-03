# omagent/tools/builtin/skill_tool.py
"""Skill tool — LLM calls this to load skill instructions on demand."""
from typing import Any
from omagent.tools.base import Tool


class SkillTool(Tool):
    """Load a local skill definition and its instructions.

    The LLM calls this tool when it decides it needs a skill's instructions.
    Returns the full SKILL.md content as a tool result (not injected into system prompt).
    Pattern from claw-code-parity tools/src/lib.rs Skill tool.
    """

    def __init__(self, skill_registry=None):
        self._registry = skill_registry

    @property
    def name(self) -> str:
        return "Skill"

    @property
    def description(self) -> str:
        return (
            "Load a local skill definition and its instructions. "
            "Call this when you need detailed workflow guidance for a specific task. "
            "The available skills are listed in <available_skills> in your system prompt."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "skill": {
                    "type": "string",
                    "description": "Name of the skill to load (e.g., 'eda', 'modeling', 'cleaning').",
                },
                "args": {
                    "type": "string",
                    "description": "Optional arguments for the skill.",
                },
            },
            "required": ["skill"],
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        if not self._registry:
            return {"error": "Skill registry not configured"}

        skill_name = input["skill"]
        skill = self._registry.get_by_name(skill_name)

        if not skill:
            available = self._registry.names()
            return {
                "error": f"Unknown skill: {skill_name}",
                "available_skills": available,
            }

        content = self._registry.get_full_content(skill_name)
        if not content:
            return {"error": f"Could not read skill content: {skill_name}"}

        return {
            "skill": skill.name,
            "path": str(skill.path) if skill.path else None,
            "args": input.get("args"),
            "description": skill.description,
            "prompt": content,
        }
