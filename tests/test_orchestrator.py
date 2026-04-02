import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from omagent.core.orchestrator import AgentOrchestrator
from omagent.core.session import SessionStore
from omagent.tools.builtin.delegate import DelegateTool


@pytest.fixture
def orchestrator(tmp_path):
    store = SessionStore(db_path=tmp_path / "test.db")
    return AgentOrchestrator(store=store)


@pytest.mark.asyncio
async def test_delegate_tool_schema():
    orch = AgentOrchestrator()
    tool = DelegateTool(orch)
    schema = tool.to_schema()
    assert schema["name"] == "delegate"
    assert "pack" in schema["input_schema"]["properties"]
    assert "task" in schema["input_schema"]["properties"]


@pytest.mark.asyncio
async def test_orchestrator_active_count(orchestrator):
    assert orchestrator.active_count == 0
