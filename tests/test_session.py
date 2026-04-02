import pytest
import tempfile
from pathlib import Path
from omagent.core.session import Session, SessionStore


@pytest.fixture
def store(tmp_path):
    return SessionStore(db_path=tmp_path / "test.db")


@pytest.mark.asyncio
async def test_create_and_load(store):
    session = await store.create(pack_name="data_science")
    assert session.id
    loaded = await store.load(session.id)
    assert loaded.id == session.id
    assert loaded.pack_name == "data_science"


@pytest.mark.asyncio
async def test_messages_persist(store):
    session = await store.create()
    session.add_user_message("hello")
    session.add_assistant_message("hi there", tool_calls=None)
    await store.save(session)

    loaded = await store.load(session.id)
    assert len(loaded.messages) == 2
    assert loaded.messages[0]["content"] == "hello"


@pytest.mark.asyncio
async def test_tool_result(store):
    session = await store.create()
    session.add_user_message("run code")
    session.add_tool_result("tool-123", {"output": "hello world"})
    await store.save(session)

    loaded = await store.load(session.id)
    assert any(
        m["role"] == "tool" and m["tool_call_id"] == "tool-123"
        for m in loaded.messages
    )


@pytest.mark.asyncio
async def test_list_sessions(store):
    await store.create()
    await store.create()
    sessions = await store.list_sessions()
    assert len(sessions) == 2
