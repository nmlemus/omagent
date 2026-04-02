import os
import json
from typing import AsyncGenerator

import litellm  # noqa: F401
from litellm import acompletion

from omagent.core.events import (
    AgentEvent, TextDeltaEvent, ToolCallEvent, ErrorEvent, DoneEvent
)

DEFAULT_MODEL = "anthropic/claude-sonnet-4-6"


def get_model() -> str:
    return os.getenv("OMAGENT_MODEL", DEFAULT_MODEL)


class LiteLLMProvider:
    """Wraps litellm.acompletion with structured streaming events."""

    def __init__(self, model: str | None = None):
        self.model = model or get_model()

    async def stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
        **kwargs,
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Stream a completion. Yields AgentEvent instances.
        After the stream ends, also yields a DoneEvent.
        The caller should collect TextDeltaEvent.content chunks and
        ToolCallEvent instances to reconstruct the assistant message.
        """
        # Prepend system message if provided and not already present
        full_messages = list(messages)
        if system and (not full_messages or full_messages[0].get("role") != "system"):
            full_messages = [{"role": "system", "content": system}] + full_messages

        # Convert tool schemas to litellm format
        litellm_tools = None
        if tools:
            litellm_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("input_schema", {}),
                    },
                }
                for t in tools
            ]

        try:
            response = await acompletion(
                model=self.model,
                messages=full_messages,
                tools=litellm_tools,
                stream=True,
                **kwargs,
            )

            # Track accumulation state
            current_text = ""
            # tool_calls_acc: dict[index -> {id, name, arguments}]
            tool_calls_acc: dict[int, dict] = {}

            async for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                # Text delta
                if delta.content:
                    current_text += delta.content
                    yield TextDeltaEvent(content=delta.content)

                # Tool call deltas
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_calls_acc:
                            tool_calls_acc[idx] = {
                                "id": "",
                                "name": "",
                                "arguments": "",
                            }
                        acc = tool_calls_acc[idx]
                        if tc_delta.id:
                            acc["id"] += tc_delta.id
                        if tc_delta.function and tc_delta.function.name:
                            acc["name"] += tc_delta.function.name
                        if tc_delta.function and tc_delta.function.arguments:
                            acc["arguments"] += tc_delta.function.arguments

            # Emit complete tool calls
            for idx in sorted(tool_calls_acc.keys()):
                acc = tool_calls_acc[idx]
                try:
                    parsed_input = json.loads(acc["arguments"]) if acc["arguments"] else {}
                except json.JSONDecodeError:
                    parsed_input = {"_raw": acc["arguments"]}

                yield ToolCallEvent(
                    id=acc["id"],
                    name=acc["name"],
                    input=parsed_input,
                )

            yield DoneEvent()

        except Exception as e:
            yield ErrorEvent(message=str(e))
            yield DoneEvent()

    def build_assistant_message(
        self, text: str, tool_calls: list[ToolCallEvent]
    ) -> dict:
        """
        Build the assistant message dict in OpenAI format (for LiteLLM).
        """
        msg: dict = {"role": "assistant", "content": text or None}
        if tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.input),
                    },
                }
                for tc in tool_calls
            ]
        return msg
