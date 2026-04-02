import pytest
import httpx
from unittest.mock import MagicMock, patch
from omagent.server.app import create_app
from omagent.core.loop import AgentLoop
from omagent.core.registry import ToolRegistry
from omagent.core.session import Session, SessionStore
from omagent.core.permissions import PermissionPolicy
from omagent.core.hooks import HookRunner
from omagent.core.events import TextDeltaEvent, DoneEvent
from omagent.providers.litellm_provider import LiteLLMProvider


async def mock_stream(messages, tools, system, **kwargs):
    yield TextDeltaEvent(content="hello")
    yield DoneEvent()


def make_factory(tmp_path):
    def factory(pack_name="default", session_id=None):
        import uuid
        store = SessionStore(db_path=tmp_path / "test.db")
        registry = ToolRegistry()
        provider = MagicMock(spec=LiteLLMProvider)
        provider.stream = mock_stream
        provider.build_assistant_message = LiteLLMProvider.__new__(LiteLLMProvider).build_assistant_message
        return AgentLoop(
            session=Session(id=session_id or uuid.uuid4().hex),
            registry=registry, provider=provider,
            policy=PermissionPolicy(), hooks=HookRunner(),
            store=store,
        )
    return factory


@pytest.mark.asyncio
async def test_health_no_auth_needed(tmp_path, monkeypatch):
    """Health endpoint should work even with auth enabled."""
    monkeypatch.setenv("OMAGENT_API_KEY", "secret123")
    from omagent.core.config import get_config
    get_config.cache_clear()

    app = create_app(loop_factory=make_factory(tmp_path))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200

    get_config.cache_clear()


@pytest.mark.asyncio
async def test_chat_requires_auth(tmp_path, monkeypatch):
    """Chat should fail without auth when API key is set."""
    monkeypatch.setenv("OMAGENT_API_KEY", "secret123")
    from omagent.core.config import get_config
    get_config.cache_clear()

    app = create_app(loop_factory=make_factory(tmp_path))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/chat", json={"message": "hi"})
        assert resp.status_code == 401

    get_config.cache_clear()


@pytest.mark.asyncio
async def test_chat_with_valid_auth(tmp_path, monkeypatch):
    """Chat should work with valid bearer token."""
    monkeypatch.setenv("OMAGENT_API_KEY", "secret123")
    monkeypatch.setenv("OMAGENT_DB_PATH", str(tmp_path / "test.db"))
    from omagent.core.config import get_config
    get_config.cache_clear()

    app = create_app(loop_factory=make_factory(tmp_path))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/chat",
            json={"message": "hi"},
            headers={"Authorization": "Bearer secret123"},
        )
        assert resp.status_code == 200

    get_config.cache_clear()


@pytest.mark.asyncio
async def test_no_auth_when_key_not_set(tmp_path, monkeypatch):
    """Without API key set, everything should work without auth."""
    monkeypatch.delenv("OMAGENT_API_KEY", raising=False)
    monkeypatch.setenv("OMAGENT_DB_PATH", str(tmp_path / "test.db"))
    from omagent.core.config import get_config
    get_config.cache_clear()

    app = create_app(loop_factory=make_factory(tmp_path))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/chat", json={"message": "hi"})
        assert resp.status_code == 200

    get_config.cache_clear()
