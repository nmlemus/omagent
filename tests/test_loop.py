import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from omagent.core.loop import AgentLoop
from omagent.core.registry import ToolRegistry
from omagent.core.session import Session
from omagent.core.permissions import PermissionPolicy
from omagent.core.hooks import HookRunner
from omagent.core.events import TextDeltaEvent, DoneEvent, ToolCallEvent, ToolResultEvent
from omagent.providers.litellm_provider import LiteLLMProvider
from omagent.tools.builtin import ListDirTool


async def text_only_stream(*args, **kwargs):
    """Mock provider that returns only text, no tool calls."""
    yield TextDeltaEvent(content="Hello ")
    yield TextDeltaEvent(content="world")
    yield DoneEvent()


@pytest.mark.asyncio
async def test_text_only_response(tmp_path):
    session = Session(id="test-1")
    registry = ToolRegistry()
    policy = PermissionPolicy()
    hooks = HookRunner()

    real_provider = LiteLLMProvider.__new__(LiteLLMProvider)
    provider = MagicMock(spec=LiteLLMProvider)
    provider.stream = text_only_stream
    provider.build_assistant_message = real_provider.build_assistant_message

    loop = AgentLoop(
        session=session,
        registry=registry,
        provider=provider,
        policy=policy,
        hooks=hooks,
    )

    events = []
    async for event in loop.run("say hello"):
        events.append(event)

    text_events = [e for e in events if isinstance(e, TextDeltaEvent)]
    assert "".join(e.content for e in text_events) == "Hello world"
    done_events = [e for e in events if isinstance(e, DoneEvent)]
    assert len(done_events) == 1


@pytest.mark.asyncio
async def test_tool_call_then_done(tmp_path):
    """Loop should execute a tool call and continue."""
    session = Session(id="test-2")
    registry = ToolRegistry()
    registry.register(ListDirTool())
    policy = PermissionPolicy()
    hooks = HookRunner()

    call_count = 0

    async def tool_then_text_stream(messages, tools, system, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call: return a tool use
            yield ToolCallEvent(id="tc-1", name="list_dir", input={"path": str(tmp_path)})
            yield DoneEvent()
        else:
            # Second call: return text
            yield TextDeltaEvent(content="Done listing.")
            yield DoneEvent()

    real_provider = LiteLLMProvider.__new__(LiteLLMProvider)
    provider = MagicMock(spec=LiteLLMProvider)
    provider.stream = tool_then_text_stream
    provider.build_assistant_message = real_provider.build_assistant_message

    loop = AgentLoop(
        session=session, registry=registry, provider=provider,
        policy=policy, hooks=hooks,
    )

    events = []
    async for event in loop.run("list the directory"):
        events.append(event)

    tool_results = [e for e in events if isinstance(e, ToolResultEvent)]
    assert len(tool_results) == 1
    assert tool_results[0].tool_name == "list_dir"
