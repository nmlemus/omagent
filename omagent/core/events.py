from dataclasses import dataclass, field
from typing import Any
from enum import Enum
import json


class EventType(str, Enum):
    TEXT_DELTA = "text_delta"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PERMISSION_DENIED = "permission_denied"
    PERMISSION_PROMPT = "permission_prompt"
    ERROR = "error"
    DONE = "done"
    SUB_AGENT_START = "sub_agent_start"
    SUB_AGENT_DONE = "sub_agent_done"


@dataclass
class TextDeltaEvent:
    type: EventType = field(default=EventType.TEXT_DELTA, init=False)
    content: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict for SSE/WebSocket."""
        return {"type": "text_delta", "content": self.content}


@dataclass
class ToolCallEvent:
    type: EventType = field(default=EventType.TOOL_CALL, init=False)
    id: str = ""
    name: str = ""
    input: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dict for SSE/WebSocket."""
        return {"type": "tool_call", "tool_call": {"id": self.id, "name": self.name, "input": self.input}}


@dataclass
class ToolResultEvent:
    type: EventType = field(default=EventType.TOOL_RESULT, init=False)
    tool_use_id: str = ""
    tool_name: str = ""
    result: dict = field(default_factory=dict)
    is_error: bool = False

    def to_dict(self) -> dict:
        """Serialize to dict for SSE/WebSocket."""
        return {
            "type": "tool_result",
            "tool_result": {
                "id": self.tool_use_id,
                "name": self.tool_name,
                "result": self.result,
                "is_error": self.is_error,
            },
        }


@dataclass
class PermissionDeniedEvent:
    type: EventType = field(default=EventType.PERMISSION_DENIED, init=False)
    tool_name: str = ""
    reason: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict for SSE/WebSocket."""
        return {"type": "permission_denied", "tool_name": self.tool_name, "reason": self.reason}


@dataclass
class PermissionPromptEvent:
    type: EventType = field(default=EventType.PERMISSION_PROMPT, init=False)
    tool_name: str = ""
    input: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dict for SSE/WebSocket."""
        return {"type": "permission_prompt", "tool_name": self.tool_name, "input": self.input}


@dataclass
class ErrorEvent:
    type: EventType = field(default=EventType.ERROR, init=False)
    message: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict for SSE/WebSocket."""
        return {"type": "error", "message": self.message}


@dataclass
class DoneEvent:
    type: EventType = field(default=EventType.DONE, init=False)

    def to_dict(self) -> dict:
        """Serialize to dict for SSE/WebSocket."""
        return {"type": "done"}


@dataclass
class SubAgentStartEvent:
    type: EventType = field(default=EventType.SUB_AGENT_START, init=False)
    agent_id: str = ""
    pack_name: str = ""
    task: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict for SSE/WebSocket."""
        return {
            "type": "sub_agent_start",
            "agent_id": self.agent_id,
            "pack_name": self.pack_name,
            "task": self.task,
        }


@dataclass
class SubAgentDoneEvent:
    type: EventType = field(default=EventType.SUB_AGENT_DONE, init=False)
    agent_id: str = ""
    pack_name: str = ""
    result: str = ""
    is_error: bool = False

    def to_dict(self) -> dict:
        """Serialize to dict for SSE/WebSocket."""
        return {
            "type": "sub_agent_done",
            "agent_id": self.agent_id,
            "pack_name": self.pack_name,
            "result": self.result,
            "is_error": self.is_error,
        }


AgentEvent = (
    TextDeltaEvent
    | ToolCallEvent
    | ToolResultEvent
    | PermissionDeniedEvent
    | PermissionPromptEvent
    | ErrorEvent
    | DoneEvent
    | SubAgentStartEvent
    | SubAgentDoneEvent
)
