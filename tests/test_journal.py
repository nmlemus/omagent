import pytest
import json
from pathlib import Path
from omagent.core.journal import EventJournal


@pytest.fixture
def journal(tmp_path):
    return EventJournal(session_id="test-j", logs_dir=tmp_path / "logs")


def test_log_creates_files(journal):
    journal.log("test_event", {"key": "value"})
    assert journal._events_path.exists()
    assert journal._run_log_path.exists()


def test_jsonl_format(journal):
    journal.log("user_message", {"text": "hello"})
    journal.log("tool_call", {"tool_name": "bash", "input_summary": "ls"})

    events = journal.read_events()
    assert len(events) == 2
    assert events[0]["type"] == "user_message"
    assert events[1]["type"] == "tool_call"
    assert events[0]["event_id"] == 1
    assert events[1]["event_id"] == 2


def test_round_tracking(journal):
    journal.set_round(1)
    journal.log("llm_request", {"model": "test", "message_count": 5})
    events = journal.read_events()
    assert events[0]["round"] == 1


def test_convenience_methods(journal):
    journal.log_session_start("data_science", "claude-sonnet")
    journal.log_user_message("analyze data")
    journal.log_tool_call("jupyter_execute", {"code": "print(1)"})
    journal.log_tool_result("jupyter_execute", is_error=False, duration_ms=150)
    journal.log_error("something broke")

    events = journal.read_events()
    assert len(events) == 5
    types = [e["type"] for e in events]
    assert "session_start" in types
    assert "error" in types


def test_read_run_log(journal):
    journal.log_session_start("default", "test-model")
    log = journal.read_run_log()
    assert "session_start" in log
    assert "default" in log


def test_filter_by_type(journal):
    journal.log("user_message", {"text": "hi"})
    journal.log("tool_call", {"tool_name": "bash"})
    journal.log("user_message", {"text": "bye"})

    filtered = journal.read_events(event_types=["user_message"])
    assert len(filtered) == 2
