"""
Async httpx-based tests for all omagent server endpoints.

Uses ASGITransport so no real server is needed, and mocks the LLM provider
so no API keys are required.
"""
import json
import os
import uuid

import pytest
import httpx
from unittest.mock import MagicMock

from omagent.server.app import create_app
from omagent.core.loop import AgentLoop
from omagent.core.registry import ToolRegistry
from omagent.core.session import Session, SessionStore
from omagent.core.permissions import PermissionPolicy
from omagent.core.hooks import HookRunner
from omagent.core.events import TextDeltaEvent, DoneEvent
from omagent.providers.litellm_provider import LiteLLMProvider
from omagent.tools.builtin.read_file import ReadFileTool
from omagent.tools.builtin.list_dir import ListDirTool


# ---------------------------------------------------------------------------
# Mock LLM stream
# ---------------------------------------------------------------------------

async def mock_stream(messages, tools, system, **kwargs):
    """Mock provider stream: yields one text delta then done."""
    yield TextDeltaEvent(content="Hello from omagent!")
    yield DoneEvent()


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------

def make_mock_factory(db_path):
    """Return a loop_factory that uses a temp SQLite DB and a mock provider."""

    def factory(pack_name: str = "default", session_id: str | None = None):
        store = SessionStore(db_path=db_path)
        registry = ToolRegistry()
        registry.register_many([ReadFileTool(), ListDirTool()])
        policy = PermissionPolicy()
        hooks = HookRunner()

        real_provider = LiteLLMProvider.__new__(LiteLLMProvider)
        provider = MagicMock(spec=LiteLLMProvider)
        provider.stream = mock_stream
        provider.build_assistant_message = real_provider.build_assistant_message

        session = Session(
            id=session_id or uuid.uuid4().hex,
            pack_name=pack_name,
        )

        return AgentLoop(
            session=session,
            registry=registry,
            provider=provider,
            policy=policy,
            hooks=hooks,
            system_prompt=f"Test assistant. Pack: {pack_name}",
            store=store,
        )

    return factory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


@pytest.fixture
def app(db_path, monkeypatch):
    # Point SessionStore default path (used inside routes.py) to the temp DB
    monkeypatch.setenv("OMAGENT_DB_PATH", str(db_path))
    factory = make_mock_factory(db_path)
    return create_app(default_pack="default", loop_factory=factory)


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_chat_returns_response(client):
    resp = await client.post("/chat", json={"message": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert "response" in data
    assert "Hello from omagent!" in data["response"]
    assert isinstance(data["tool_calls"], list)


@pytest.mark.asyncio
async def test_chat_uses_provided_session_id(client):
    sid = uuid.uuid4().hex
    resp = await client.post("/chat", json={"message": "hello", "session_id": sid})
    assert resp.status_code == 200
    assert resp.json()["session_id"] == sid


@pytest.mark.asyncio
async def test_chat_creates_new_session_when_none_given(client):
    resp1 = await client.post("/chat", json={"message": "hello"})
    resp2 = await client.post("/chat", json={"message": "hello"})
    sid1 = resp1.json()["session_id"]
    sid2 = resp2.json()["session_id"]
    assert sid1 != sid2


def _parse_sse(text: str) -> list[dict]:
    """Parse SSE response body into a list of event dicts.

    Handles both legacy single-line ``data: {...}`` chunks and the new
    multi-field format with ``id:``, ``event:``, and ``data:`` lines.
    """
    events = []
    for chunk in text.strip().split("\n\n"):
        for line in chunk.strip().splitlines():
            line = line.strip()
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
                break
    return events


@pytest.mark.asyncio
async def test_stream_returns_sse(client):
    resp = await client.post("/stream", json={"message": "hello"})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = _parse_sse(resp.text)
    types = [e.get("type") for e in events]
    assert "text_delta" in types
    assert "done" in types


@pytest.mark.asyncio
async def test_stream_text_delta_has_content(client):
    resp = await client.post("/stream", json={"message": "hello"})
    events = _parse_sse(resp.text)

    text_events = [e for e in events if e.get("type") == "text_delta"]
    assert len(text_events) >= 1
    combined = "".join(e.get("content", "") for e in text_events)
    assert "Hello from omagent!" in combined


@pytest.mark.asyncio
async def test_stream_events_have_session_id(client):
    resp = await client.post("/stream", json={"message": "hi"})
    events = _parse_sse(resp.text)

    for event in events:
        assert "session_id" in event


@pytest.mark.asyncio
async def test_list_sessions_empty_initially(client):
    resp = await client.get("/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert "sessions" in data
    assert isinstance(data["sessions"], list)


@pytest.mark.asyncio
async def test_list_sessions_after_chat(client):
    await client.post("/chat", json={"message": "hello"})
    resp = await client.get("/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["sessions"]) >= 1


@pytest.mark.asyncio
async def test_get_session_found(client):
    chat_resp = await client.post("/chat", json={"message": "hello"})
    session_id = chat_resp.json()["session_id"]

    resp = await client.get(f"/sessions/{session_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == session_id
    assert "messages" in data


@pytest.mark.asyncio
async def test_get_session_not_found(client):
    resp = await client.get("/sessions/nonexistent-id-that-does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_session_success(client):
    chat_resp = await client.post("/chat", json={"message": "hello"})
    session_id = chat_resp.json()["session_id"]

    del_resp = await client.delete(f"/sessions/{session_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True


@pytest.mark.asyncio
async def test_delete_session_then_get_returns_404(client):
    chat_resp = await client.post("/chat", json={"message": "hello"})
    session_id = chat_resp.json()["session_id"]

    await client.delete(f"/sessions/{session_id}")

    get_resp = await client.get(f"/sessions/{session_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_session(client):
    resp = await client.delete("/sessions/ghost-session-id")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is False


@pytest.mark.asyncio
async def test_list_tools(client):
    resp = await client.get("/tools")
    assert resp.status_code == 200
    data = resp.json()
    assert "tools" in data
    assert "pack" in data
    tool_names = [t["name"] for t in data["tools"]]
    assert "read_file" in tool_names
    assert "list_dir" in tool_names


@pytest.mark.asyncio
async def test_list_tools_schema_format(client):
    resp = await client.get("/tools")
    data = resp.json()
    for tool in data["tools"]:
        assert "name" in tool
        assert "description" in tool
        assert "input_schema" in tool


@pytest.mark.asyncio
async def test_list_tools_for_specific_pack(client):
    resp = await client.get("/tools?pack=default")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pack"] == "default"


@pytest.mark.asyncio
async def test_list_packs(client):
    resp = await client.get("/packs")
    assert resp.status_code == 200
    data = resp.json()
    assert "packs" in data
    assert isinstance(data["packs"], list)
