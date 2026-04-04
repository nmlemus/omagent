# omagent/core/tracker.py
import json
import time
import os
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any
from enum import Enum
import aiosqlite

from omagent.core.session import get_db_path, _connect_wal


class EventType(str, Enum):
    TOOL_CALL = "tool_call"
    LLM_CALL = "llm_call"
    MILESTONE = "milestone"
    AGENT_SWITCH = "agent_switch"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    ERROR = "error"


class ActivityTracker:
    """Records everything the agent does as a temporal journal."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or get_db_path()
        self._pending_llm_start: float | None = None
        self._schema_initialized = False

    async def _ensure_schema(self, db: aiosqlite.Connection) -> None:
        if self._schema_initialized:
            return
        await db.execute("""
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                duration_ms INTEGER,
                data TEXT NOT NULL DEFAULT '{}',
                summary TEXT
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_session
            ON activity(session_id, timestamp)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_activity_date
            ON activity(timestamp)
        """)
        await db.commit()
        self._schema_initialized = True

    async def log_event(
        self,
        session_id: str,
        event_type: EventType | str,
        data: dict[str, Any] | None = None,
        duration_ms: int | None = None,
        summary: str | None = None,
    ) -> None:
        """Log an activity event."""
        async with _connect_wal(self.db_path) as db:
            await self._ensure_schema(db)
            await db.execute(
                """
                INSERT INTO activity (session_id, event_type, timestamp, duration_ms, data, summary)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    event_type if isinstance(event_type, str) else event_type.value,
                    datetime.now(timezone.utc).isoformat(),
                    duration_ms,
                    json.dumps(data or {}),
                    summary,
                ),
            )
            await db.commit()

    async def log_tool_call(
        self,
        session_id: str,
        tool_name: str,
        input_data: dict,
        result: dict,
        duration_ms: int,
    ) -> None:
        """Log a tool execution with timing."""
        is_error = "error" in result
        # Truncate large values for the summary
        input_summary = str(input_data)[:200]
        result_summary = str(result.get("output", result.get("error", "")))[:200]

        await self.log_event(
            session_id=session_id,
            event_type=EventType.TOOL_CALL,
            data={
                "tool_name": tool_name,
                "input": input_data,
                "is_error": is_error,
            },
            duration_ms=duration_ms,
            summary=f"{'ERROR ' if is_error else ''}{tool_name}: {input_summary} -> {result_summary}",
        )

    async def log_llm_call(
        self,
        session_id: str,
        model: str,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        duration_ms: int | None = None,
        tool_calls_count: int = 0,
    ) -> None:
        """Log an LLM API call with token counts."""
        cost = None
        if tokens_in is not None and tokens_out is not None:
            # Rough cost estimates (per 1M tokens)
            cost_rates = {
                "anthropic/claude-sonnet-4-6": {"in": 3.0, "out": 15.0},
                "anthropic/claude-opus-4-6": {"in": 15.0, "out": 75.0},
                "openai/gpt-4o": {"in": 2.5, "out": 10.0},
            }
            rate = cost_rates.get(model, {"in": 3.0, "out": 15.0})
            cost = (tokens_in * rate["in"] + tokens_out * rate["out"]) / 1_000_000

        await self.log_event(
            session_id=session_id,
            event_type=EventType.LLM_CALL,
            data={
                "model": model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_estimate": round(cost, 6) if cost else None,
                "tool_calls_count": tool_calls_count,
            },
            duration_ms=duration_ms,
            summary=f"LLM {model}: {tokens_in or '?'}->{tokens_out or '?'} tokens, {tool_calls_count} tools",
        )

    async def log_milestone(
        self, session_id: str, milestone: str, details: dict | None = None
    ) -> None:
        """Log a milestone event (session start, pack switch, etc.)."""
        await self.log_event(
            session_id=session_id,
            event_type=EventType.MILESTONE,
            data=details or {},
            summary=milestone,
        )

    async def get_timeline(
        self,
        session_id: str,
        limit: int = 100,
        event_types: list[str] | None = None,
    ) -> list[dict]:
        """Get chronological activity for a session."""
        async with _connect_wal(self.db_path) as db:
            await self._ensure_schema(db)
            query = "SELECT id, session_id, event_type, timestamp, duration_ms, data, summary FROM activity WHERE session_id = ?"
            params: list[Any] = [session_id]
            if event_types:
                placeholders = ",".join("?" for _ in event_types)
                query += f" AND event_type IN ({placeholders})"
                params.extend(event_types)
            query += " ORDER BY timestamp ASC LIMIT ?"
            params.append(limit)

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "id": r[0],
                        "session_id": r[1],
                        "event_type": r[2],
                        "timestamp": r[3],
                        "duration_ms": r[4],
                        "data": json.loads(r[5]),
                        "summary": r[6],
                    }
                    for r in rows
                ]

    async def get_daily_report(self, target_date: str | None = None) -> dict:
        """Get activity summary for a specific day (default: today).

        Args:
            target_date: ISO date string like '2026-04-01'. Defaults to today.
        """
        if target_date is None:
            target_date = datetime.now(timezone.utc).date().isoformat()

        date_prefix = target_date  # SQLite LIKE on ISO timestamps

        async with _connect_wal(self.db_path) as db:
            await self._ensure_schema(db)

            # Count events by type
            async with db.execute(
                "SELECT event_type, COUNT(*) FROM activity WHERE timestamp LIKE ? GROUP BY event_type",
                (f"{date_prefix}%",),
            ) as cursor:
                type_counts = {r[0]: r[1] async for r in cursor}

            # Get unique sessions
            async with db.execute(
                "SELECT DISTINCT session_id FROM activity WHERE timestamp LIKE ?",
                (f"{date_prefix}%",),
            ) as cursor:
                sessions = [r[0] async for r in cursor]

            # Get total tokens and cost
            async with db.execute(
                "SELECT data FROM activity WHERE timestamp LIKE ? AND event_type = 'llm_call'",
                (f"{date_prefix}%",),
            ) as cursor:
                total_tokens_in = 0
                total_tokens_out = 0
                total_cost = 0.0
                async for (data_str,) in cursor:
                    data = json.loads(data_str)
                    total_tokens_in += data.get("tokens_in") or 0
                    total_tokens_out += data.get("tokens_out") or 0
                    total_cost += data.get("cost_estimate") or 0.0

            # Get milestones
            async with db.execute(
                "SELECT timestamp, summary FROM activity WHERE timestamp LIKE ? AND event_type = 'milestone' ORDER BY timestamp",
                (f"{date_prefix}%",),
            ) as cursor:
                milestones = [{"time": r[0][11:19], "event": r[1]} async for r in cursor]

            # Get tool usage
            async with db.execute(
                "SELECT json_extract(data, '$.tool_name'), COUNT(*) FROM activity WHERE timestamp LIKE ? AND event_type = 'tool_call' GROUP BY json_extract(data, '$.tool_name') ORDER BY COUNT(*) DESC",
                (f"{date_prefix}%",),
            ) as cursor:
                tool_usage = {r[0]: r[1] async for r in cursor}

            return {
                "date": target_date,
                "sessions": len(sessions),
                "session_ids": sessions,
                "events": type_counts,
                "tokens": {"in": total_tokens_in, "out": total_tokens_out},
                "cost_estimate": round(total_cost, 4),
                "milestones": milestones,
                "tool_usage": tool_usage,
            }

    async def format_daily_report(self, target_date: str | None = None) -> str:
        """Get a human-readable daily activity report."""
        report = await self.get_daily_report(target_date)

        lines = [
            f"# Activity Report — {report['date']}",
            f"",
            f"**Sessions:** {report['sessions']}",
            f"**Tokens:** {report['tokens']['in']:,} in / {report['tokens']['out']:,} out",
            f"**Est. Cost:** ${report['cost_estimate']:.4f}",
            f"",
        ]

        if report["milestones"]:
            lines.append("## Milestones")
            for m in report["milestones"]:
                lines.append(f"  {m['time']} — {m['event']}")
            lines.append("")

        if report["tool_usage"]:
            lines.append("## Tool Usage")
            for tool, count in report["tool_usage"].items():
                lines.append(f"  {tool}: {count}x")
            lines.append("")

        if report["events"]:
            lines.append("## Events")
            for evt, count in report["events"].items():
                lines.append(f"  {evt}: {count}")

        return "\n".join(lines)
