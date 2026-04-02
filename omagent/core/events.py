from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class EventType(str, Enum):
    TEXT_DELTA = "text_delta"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PERMISSION_DENIED = "permission_denied"
    PERMISSION_PROMPT = "permission_prompt"
    ERROR = "error"
    DONE = "done"


@dataclass
class TextDeltaEvent:
    type: EventType = field(default=EventType.TEXT_DELTA, init=False)
    content: str = ""


@dataclass
class ToolCallEvent:
    type: EventType = field(default=EventType.TOOL_CALL, init=False)
    id: str = ""
    name: str = ""
    input: dict = field(default_factory=dict)


@dataclass
class ToolResultEvent:
    type: EventType = field(default=EventType.TOOL_RESULT, init=False)
    tool_use_id: str = ""
    tool_name: str = ""
    result: dict = field(default_factory=dict)
    is_error: bool = False


@dataclass
class PermissionDeniedEvent:
    type: EventType = field(default=EventType.PERMISSION_DENIED, init=False)
    tool_name: str = ""
    reason: str = ""


@dataclass
class PermissionPromptEvent:
    type: EventType = field(default=EventType.PERMISSION_PROMPT, init=False)
    tool_name: str = ""
    input: dict = field(default_factory=dict)


@dataclass
class ErrorEvent:
    type: EventType = field(default=EventType.ERROR, init=False)
    message: str = ""


@dataclass
class DoneEvent:
    type: EventType = field(default=EventType.DONE, init=False)


AgentEvent = (
    TextDeltaEvent
    | ToolCallEvent
    | ToolResultEvent
    | PermissionDeniedEvent
    | PermissionPromptEvent
    | ErrorEvent
    | DoneEvent
)
