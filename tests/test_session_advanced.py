import pytest
import json
from omagent.core.session import Session, SessionStore


@pytest.fixture
def store(tmp_path):
    return SessionStore(db_path=tmp_path / "test.db")


def test_fork_session():
    session = Session(id="original", pack_name="data_science")
    session.add_user_message("hello")
    session.add_assistant_message("hi there")

    forked = session.fork()
    assert forked.id != session.id
    assert len(forked.messages) == 2
    assert forked.pack_name == "data_science"
    # Verify deep copy
    forked.add_user_message("new message")
    assert len(forked.messages) == 3
    assert len(session.messages) == 2


def test_export_json():
    session = Session(id="test-export", pack_name="default")
    session.add_user_message("hello")

    exported = session.export_json()
    data = json.loads(exported)
    assert data["id"] == "test-export"
    assert len(data["messages"]) == 1


def test_export_markdown():
    session = Session(id="test-md", pack_name="data_science")
    session.add_user_message("analyze this data")
    session.add_assistant_message("Here are the results")

    md = session.export_markdown()
    assert "# Session:" in md
    assert "### User" in md
    assert "analyze this data" in md
    assert "### Assistant" in md


def test_import_json():
    original = Session(id="orig", pack_name="flutter_dev")
    original.add_user_message("create a project")

    exported = original.export_json()
    imported = Session.import_json(exported)

    assert imported.id != original.id  # New ID
    assert imported.pack_name == "flutter_dev"
    assert len(imported.messages) == 1


@pytest.mark.asyncio
async def test_fork_and_save(store):
    session = await store.create(pack_name="data_science")
    session.add_user_message("test")
    await store.save(session)

    forked = session.fork()
    await store.save(forked)

    loaded = await store.load(forked.id)
    assert loaded is not None
    assert loaded.id == forked.id
    assert len(loaded.messages) == 1
