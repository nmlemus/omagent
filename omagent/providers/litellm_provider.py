import os
import json
from typing import AsyncGenerator

import litellm  # noqa: F401
from litellm import acompletion

from omagent.core.events import (
    AgentEvent, TextDeltaEvent, ToolCallEvent, ErrorEvent, DoneEvent
)

import logging

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "anthropic/claude-sonnet-4-6"


def _sanitize_messages(messages: list[dict]) -> list[dict]:
    """Sanitize messages for provider compatibility.

    Enforces constraints required by Vertex AI / Gemini (and safe for other
    providers):

    1. Remove orphaned tool-result messages (no matching tool_call).
    2. Remove empty assistant messages (no text, no tool_calls).
    3. Strip ``function_call: None`` from assistant messages.
    4. Ensure first non-system message is a user message.
    5. Prevent consecutive same-role messages (merge user messages,
       ensure tool results follow their tool calls).
    """
    # --- Pass 1: Remove orphaned tool results and empty assistant messages ---
    valid_tool_call_ids: set[str] = set()
    for msg in messages:
        if msg.get("role") == "assistant":
            for tc in msg.get("tool_calls") or []:
                tc_id = tc.get("id") or ""
                if tc_id:
                    valid_tool_call_ids.add(tc_id)

    cleaned: list[dict] = []
    removed = 0
    for msg in messages:
        role = msg.get("role", "")

        # Drop orphaned tool results
        if role == "tool":
            tc_id = msg.get("tool_call_id", "")
            if tc_id not in valid_tool_call_ids:
                removed += 1
                continue

        # Drop empty assistant messages (no text, no tool_calls)
        if role == "assistant":
            content = msg.get("content")
            has_text = bool(content) if isinstance(content, str) else bool(content)
            has_tools = bool(msg.get("tool_calls"))
            if not has_text and not has_tools:
                removed += 1
                continue
            # Strip function_call: None (causes Vertex AI rejection)
            if "function_call" in msg and msg["function_call"] is None:
                msg = {k: v for k, v in msg.items() if k != "function_call"}

        cleaned.append(msg)

    # --- Pass 2: Ensure first non-system message is user role ---
    first_non_system = None
    for i, msg in enumerate(cleaned):
        if msg.get("role") != "system":
            first_non_system = i
            break

    if first_non_system is not None and cleaned[first_non_system].get("role") != "user":
        # Insert a synthetic user message to satisfy Gemini's first-turn rule
        cleaned.insert(first_non_system, {
            "role": "user",
            "content": "Continue.",
        })
        removed -= 1  # we added one

    # --- Pass 3: Merge consecutive same-role user messages ---
    merged: list[dict] = []
    for msg in cleaned:
        role = msg.get("role", "")
        if (
            merged
            and role == "user"
            and merged[-1].get("role") == "user"
            # Don't merge if either has non-string content (e.g., multimodal)
            and isinstance(msg.get("content"), str)
            and isinstance(merged[-1].get("content"), str)
        ):
            merged[-1] = {
                "role": "user",
                "content": merged[-1]["content"] + "\n" + msg["content"],
            }
            removed += 1
        else:
            merged.append(msg)

    if removed:
        logger.info("Sanitized messages: %d fixes applied", abs(removed))

    return merged


def get_model() -> str:
    return os.getenv("OMAGENT_MODEL", DEFAULT_MODEL)


class LiteLLMProvider:
    """Wraps litellm.acompletion with structured streaming events."""

    def __init__(self, model: str | None = None):
        self.model = model or get_model()
        self._last_usage: dict | None = None

    @property
    def last_usage(self) -> dict | None:
        return self._last_usage

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
        full_messages = _sanitize_messages(list(messages))
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
                stream_options={"include_usage": True},
                **kwargs,
            )

            # Track accumulation state
            current_text = ""
            # tool_calls_acc: dict[index -> {id, name, arguments}]
            tool_calls_acc: dict[int, dict] = {}
            last_chunk = None

            async for chunk in response:
                last_chunk = chunk
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

            # Extract usage from last chunk
            self._last_usage = None
            if last_chunk:
                try:
                    usage = getattr(last_chunk, "usage", None)
                    if usage:
                        self._last_usage = {
                            "tokens_in": getattr(usage, "prompt_tokens", None),
                            "tokens_out": getattr(usage, "completion_tokens", None),
                        }
                except Exception:
                    pass

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
            logger.error("LLM provider error: %s: %s", type(e).__name__, e)
            yield ErrorEvent(message=f"{type(e).__name__}: {e}")
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
