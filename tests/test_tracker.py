import pytest
from pathlib import Path
from omagent.core.tracker import ActivityTracker, EventType


@pytest.fixture
def tracker(tmp_path):
    return ActivityTracker(db_path=tmp_path / "test.db")


@pytest.mark.asyncio
async def test_log_and_get_timeline(tracker):
    await tracker.log_event("sess-1", EventType.SESSION_START, summary="Session started")
    await tracker.log_tool_call("sess-1", "read_file", {"path": "test.txt"}, {"output": "hello"}, 50)

    timeline = await tracker.get_timeline("sess-1")
    assert len(timeline) == 2
    assert timeline[0]["event_type"] == "session_start"
    assert timeline[1]["event_type"] == "tool_call"


@pytest.mark.asyncio
async def test_log_llm_call(tracker):
    await tracker.log_llm_call("sess-1", "anthropic/claude-sonnet-4-6", tokens_in=500, tokens_out=200, duration_ms=1500)

    timeline = await tracker.get_timeline("sess-1")
    assert len(timeline) == 1
    assert timeline[0]["data"]["model"] == "anthropic/claude-sonnet-4-6"
    assert timeline[0]["data"]["cost_estimate"] is not None


@pytest.mark.asyncio
async def test_daily_report(tracker):
    await tracker.log_milestone("sess-1", "Session started")
    await tracker.log_tool_call("sess-1", "bash", {"command": "ls"}, {"stdout": "files"}, 100)
    await tracker.log_llm_call("sess-1", "anthropic/claude-sonnet-4-6", tokens_in=1000, tokens_out=500, duration_ms=2000)

    report = await tracker.get_daily_report()
    assert report["sessions"] == 1
    assert report["tokens"]["in"] == 1000
    assert report["tokens"]["out"] == 500
    assert len(report["milestones"]) == 1


@pytest.mark.asyncio
async def test_format_daily_report(tracker):
    await tracker.log_milestone("sess-1", "Started data analysis")
    text = await tracker.format_daily_report()
    assert "Activity Report" in text
    assert "Started data analysis" in text


@pytest.mark.asyncio
async def test_filter_by_event_type(tracker):
    await tracker.log_milestone("sess-1", "start")
    await tracker.log_tool_call("sess-1", "bash", {}, {}, 10)

    milestones = await tracker.get_timeline("sess-1", event_types=["milestone"])
    assert len(milestones) == 1
    assert milestones[0]["event_type"] == "milestone"
