# omagent/core/journal.py
"""Event journal — structured JSONL + human-readable dual logging per session."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class EventJournal:
    """
    Writes structured JSONL events and human-readable logs for a session.

    Each event includes: event_id, timestamp, session_id, round, type, data.
    Writes to:
      - {logs_dir}/events.jsonl (machine-readable)
      - {logs_dir}/run.log (human-readable)
    """

    def __init__(self, session_id: str, logs_dir: Path):
        self.session_id = session_id
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._events_path = logs_dir / "events.jsonl"
        self._run_log_path = logs_dir / "run.log"
        self._event_counter = 0
        self._current_round = 0

    def set_round(self, round_num: int) -> None:
        """Set the current round/iteration number."""
        self._current_round = round_num

    def log(self, event_type: str, data: dict[str, Any] | None = None, summary: str | None = None) -> None:
        """Log a structured event."""
        self._event_counter += 1
        timestamp = datetime.now(timezone.utc).isoformat()

        event = {
            "event_id": self._event_counter,
            "timestamp": timestamp,
            "session_id": self.session_id,
            "round": self._current_round,
            "type": event_type,
            "data": data or {},
        }

        # Write JSONL
        try:
            with open(self._events_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, default=str) + "\n")
        except Exception as e:
            logger.warning("Failed to write event: %s", e)

        # Write human-readable log
        log_summary = summary or self._auto_summary(event_type, data)
        try:
            with open(self._run_log_path, "a", encoding="utf-8") as f:
                time_short = timestamp[11:19]  # HH:MM:SS
                f.write(f"{time_short} | R{self._current_round:02d} | {event_type:20s} | {log_summary}\n")
        except Exception as e:
            logger.warning("Failed to write run log: %s", e)

    def _auto_summary(self, event_type: str, data: dict | None) -> str:
        """Generate a human-readable summary for common event types."""
        if not data:
            return ""

        summaries = {
            "session_start": lambda d: f"Pack: {d.get('pack_name', '?')}, Model: {d.get('model', '?')}",
            "session_end": lambda d: f"Turns: {d.get('turns', '?')}, Cost: ${d.get('total_cost', 0):.4f}",
            "user_message": lambda d: d.get("text", "")[:100],
            "llm_request": lambda d: f"Model: {d.get('model', '?')}, Messages: {d.get('message_count', '?')}",
            "llm_response": lambda d: f"Tokens: {d.get('tokens_in', '?')}/{d.get('tokens_out', '?')}, Latency: {d.get('latency_ms', '?')}ms, Tools: {d.get('tool_calls_count', 0)}",
            "tool_call": lambda d: f"{d.get('tool_name', '?')} — input: {str(d.get('input_summary', ''))[:80]}",
            "tool_result": lambda d: f"{d.get('tool_name', '?')} — {'ERROR' if d.get('is_error') else 'OK'} ({d.get('duration_ms', '?')}ms)",
            "artifact_saved": lambda d: f"{d.get('artifact_type', '?')}: {d.get('path', '?')} ({d.get('size_bytes', '?')} bytes)",
            "code_executed": lambda d: f"{'OK' if d.get('success') else 'ERROR'} ({d.get('execution_time_ms', '?')}ms)",
            "plan_created": lambda d: f"Steps: {d.get('total_steps', '?')} — {d.get('goal', '')[:80]}",
            "plan_step_completed": lambda d: f"Step {d.get('step_num', '?')}: {d.get('description', '')[:80]}",
            "sub_agent_start": lambda d: f"Pack: {d.get('pack_name', '?')}, Task: {d.get('task', '')[:80]}",
            "sub_agent_done": lambda d: f"Pack: {d.get('pack_name', '?')}, {'ERROR' if d.get('is_error') else 'OK'}",
            "memory_summary": lambda d: f"Summarized {d.get('messages_summarized', '?')} messages",
            "error": lambda d: d.get("message", "")[:100],
        }

        fn = summaries.get(event_type)
        if fn:
            try:
                return fn(data)
            except Exception:
                pass
        return str(data)[:100]

    # Convenience methods for common events

    def log_session_start(self, pack_name: str, model: str) -> None:
        self.log("session_start", {"pack_name": pack_name, "model": model})

    def log_session_end(self, turns: int, total_cost: float) -> None:
        self.log("session_end", {"turns": turns, "total_cost": total_cost})

    def log_user_message(self, text: str) -> None:
        self.log("user_message", {"text": text[:500]})

    def log_llm_request(self, model: str, message_count: int) -> None:
        self.log("llm_request", {"model": model, "message_count": message_count})

    def log_llm_response(
        self, tokens_in: int | None, tokens_out: int | None, latency_ms: int | None, tool_calls_count: int = 0
    ) -> None:
        self.log("llm_response", {
            "tokens_in": tokens_in, "tokens_out": tokens_out,
            "latency_ms": latency_ms, "tool_calls_count": tool_calls_count,
        })

    def log_tool_call(self, tool_name: str, input_data: dict) -> None:
        input_summary = str(input_data)[:200]
        self.log("tool_call", {"tool_name": tool_name, "input_summary": input_summary})

    def log_tool_result(self, tool_name: str, is_error: bool, duration_ms: int | None) -> None:
        self.log("tool_result", {"tool_name": tool_name, "is_error": is_error, "duration_ms": duration_ms})

    def log_artifact_saved(self, artifact_type: str, path: str, size_bytes: int) -> None:
        self.log("artifact_saved", {"artifact_type": artifact_type, "path": path, "size_bytes": size_bytes})

    def log_code_executed(self, code: str, success: bool, execution_time_ms: int | None) -> None:
        self.log("code_executed", {"code": code[:500], "success": success, "execution_time_ms": execution_time_ms})

    def log_error(self, message: str, traceback: str | None = None) -> None:
        self.log("error", {"message": message, "traceback": traceback})

    def log_memory_summary(self, messages_summarized: int, summary_text: str) -> None:
        self.log("memory_summary", {"messages_summarized": messages_summarized, "summary_text": summary_text[:500]})

    def log_sub_agent_start(self, agent_id: str, pack_name: str, task: str) -> None:
        self.log("sub_agent_start", {"agent_id": agent_id, "pack_name": pack_name, "task": task[:200]})

    def log_sub_agent_done(self, agent_id: str, pack_name: str, is_error: bool) -> None:
        self.log("sub_agent_done", {"agent_id": agent_id, "pack_name": pack_name, "is_error": is_error})

    def read_events(self, limit: int = 100, event_types: list[str] | None = None) -> list[dict]:
        """Read events from the JSONL file."""
        events = []
        if not self._events_path.exists():
            return events
        try:
            with open(self._events_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    event = json.loads(line)
                    if event_types and event.get("type") not in event_types:
                        continue
                    events.append(event)
        except Exception as e:
            logger.warning("Failed to read events: %s", e)
        # Return last N events
        return events[-limit:]

    def read_run_log(self) -> str:
        """Read the human-readable run log."""
        if self._run_log_path.exists():
            return self._run_log_path.read_text(encoding="utf-8")
        return ""
