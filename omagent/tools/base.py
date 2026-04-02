from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Base class for all omagent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name used in registry and LLM tool calls."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description shown to the LLM."""
        ...

    @property
    @abstractmethod
    def input_schema(self) -> dict:
        """JSON Schema for the tool's input parameters."""
        ...

    @abstractmethod
    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the tool with the given input.
        Returns a dict with at minimum {"output": ...}.
        On error, returns {"error": "message"}.
        """
        ...

    def to_schema(self) -> dict:
        """Return the LLM-compatible tool schema (Anthropic format)."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
