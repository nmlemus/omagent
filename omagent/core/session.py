# omagent/core/session.py
import uuid
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import aiosqlite


DEFAULT_DB_PATH = Path.home() / ".omagent" / "sessions.db"


def get_db_path() -> Path:
    env = os.getenv("OMAGENT_DB_PATH")
    path = Path(env).expanduser() if env else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class Session:
    """Holds conversation state for a single agent session."""

    def __init__(self, id: str, pack_name: str = "default"):
        self.id = id
        self.pack_name = pack_name
        self.messages: list[dict] = []
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at
        self.workspace_path: str | None = None
        self.status: str = "active"
        self.title: str | None = None
        self.goal: str | None = None
        self.total_tokens_in: int = 0
        self.total_tokens_out: int = 0
        self.total_cost: float = 0.0
        self.summary: str | None = None

    def add_user_message(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})
        self._touch()

    def add_assistant_message(self, content: str | None, tool_calls: list[dict] | None = None) -> None:
        """Add an assistant message in OpenAI format.

        Args:
            content: Text content (can be None if only tool calls).
            tool_calls: List of tool call dicts in OpenAI format.
        """
        msg: dict = {"role": "assistant", "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.messages.append(msg)
        self._touch()

    def add_tool_result(self, tool_use_id: str, result: dict, is_error: bool = False) -> None:
        """Append a tool result as a tool message (OpenAI format for LiteLLM)."""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_use_id,
            "content": json.dumps(result),
        })
        self._touch()

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pack_name": self.pack_name,
            "messages": self.messages,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "workspace_path": self.workspace_path,
            "status": self.status,
            "title": self.title,
            "goal": self.goal,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_cost": self.total_cost,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        s = cls(id=data["id"], pack_name=data.get("pack_name", "default"))
        s.messages = data.get("messages", [])
        s.created_at = data.get("created_at", s.created_at)
        s.updated_at = data.get("updated_at", s.updated_at)
        s.workspace_path = data.get("workspace_path")
        s.status = data.get("status", "active")
        s.title = data.get("title")
        s.goal = data.get("goal")
        s.total_tokens_in = int(data.get("total_tokens_in") or 0)
        s.total_tokens_out = int(data.get("total_tokens_out") or 0)
        s.total_cost = float(data.get("total_cost") or 0.0)
        s.summary = data.get("summary")
        return s

    def fork(self, new_id: str | None = None) -> "Session":
        """Create a deep copy of this session with a new ID."""
        import copy
        forked = Session(
            id=new_id or str(uuid.uuid4()),
            pack_name=self.pack_name,
        )
        forked.messages = copy.deepcopy(self.messages)
        forked.created_at = datetime.now(timezone.utc).isoformat()
        forked.updated_at = forked.created_at
        return forked

    def export_json(self) -> str:
        """Export session as a self-contained JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def export_markdown(self) -> str:
        """Export session as a human-readable Markdown transcript."""
        lines = [
            f"# Session: {self.id[:8]}…",
            f"**Pack:** {self.pack_name}",
            f"**Created:** {self.created_at}",
            f"**Updated:** {self.updated_at}",
            f"**Messages:** {len(self.messages)}",
            "",
            "---",
            "",
        ]
        for i, msg in enumerate(self.messages):
            role = msg["role"].upper()
            content = msg.get("content", "")

            if role == "TOOL":
                tool_id = msg.get("tool_call_id", "unknown")
                lines.append(f"### Tool Result (call: {tool_id[:12]}…)")
                content_str = str(content)
                if len(content_str) > 500:
                    content_str = content_str[:500] + "…"
                lines.append(f"```json\n{content_str}\n```")
            elif role == "ASSISTANT":
                lines.append("### Assistant")
                if isinstance(content, str):
                    lines.append(content)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                lines.append(block.get("text", ""))
                            elif block.get("type") == "tool_use":
                                lines.append(f"**Tool call:** `{block.get('name')}` -> `{json.dumps(block.get('input', {}))[:200]}`")
                elif content is None:
                    tool_calls = msg.get("tool_calls", [])
                    for tc in tool_calls:
                        func = tc.get("function", {})
                        lines.append(f"**Tool call:** `{func.get('name')}` -> `{func.get('arguments', '')[:200]}`")
            elif role == "USER":
                lines.append("### User")
                if isinstance(content, str):
                    lines.append(content)
                elif isinstance(content, list):
                    lines.append(str(content)[:500])
            else:
                lines.append(f"### {role}")
                lines.append(str(content)[:500])

            lines.append("")

        return "\n".join(lines)

    @classmethod
    def import_json(cls, json_str: str) -> "Session":
        """Import a session from a JSON string. Creates with a new ID."""
        data = json.loads(json_str)
        new_id = str(uuid.uuid4())
        s = cls(id=new_id, pack_name=data.get("pack_name", "default"))
        s.messages = data.get("messages", [])
        s.created_at = data.get("created_at", s.created_at)
        s.updated_at = datetime.now(timezone.utc).isoformat()
        return s


class SessionStore:
    """Async SQLite-backed store for Session objects."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or get_db_path()

    async def _ensure_schema(self, db: aiosqlite.Connection) -> None:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                pack_name TEXT NOT NULL DEFAULT 'default',
                messages TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        # Migration: add new columns if they don't exist
        for col, default in [
            ("workspace_path", "NULL"),
            ("status", "'active'"),
            ("title", "NULL"),
            ("goal", "NULL"),
            ("total_tokens_in", "0"),
            ("total_tokens_out", "0"),
            ("total_cost", "0.0"),
            ("summary", "NULL"),
        ]:
            try:
                await db.execute(f"ALTER TABLE sessions ADD COLUMN {col} TEXT DEFAULT {default}")
            except Exception:
                pass  # column already exists
        await db.commit()

    async def create(self, pack_name: str = "default") -> Session:
        session = Session(id=str(uuid.uuid4()), pack_name=pack_name)
        await self.save(session)
        return session

    async def save(self, session: Session) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_schema(db)
            await db.execute(
                """
                INSERT OR REPLACE INTO sessions (
                    id, pack_name, messages, created_at, updated_at,
                    workspace_path, status, title, goal,
                    total_tokens_in, total_tokens_out, total_cost, summary
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.pack_name,
                    json.dumps(session.messages),
                    session.created_at,
                    session.updated_at,
                    session.workspace_path,
                    session.status,
                    session.title,
                    session.goal,
                    session.total_tokens_in,
                    session.total_tokens_out,
                    session.total_cost,
                    session.summary,
                ),
            )
            await db.commit()

    async def load(self, session_id: str) -> Session | None:
        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_schema(db)
            async with db.execute(
                """
                SELECT id, pack_name, messages, created_at, updated_at,
                       workspace_path, status, title, goal,
                       total_tokens_in, total_tokens_out, total_cost, summary
                FROM sessions WHERE id = ?
                """,
                (session_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                return Session.from_dict({
                    "id": row[0],
                    "pack_name": row[1],
                    "messages": json.loads(row[2]),
                    "created_at": row[3],
                    "updated_at": row[4],
                    "workspace_path": row[5],
                    "status": row[6],
                    "title": row[7],
                    "goal": row[8],
                    "total_tokens_in": row[9],
                    "total_tokens_out": row[10],
                    "total_cost": row[11],
                    "summary": row[12],
                })

    async def list_sessions(self, limit: int = 50) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_schema(db)
            async with db.execute(
                """SELECT id, pack_name, created_at, updated_at, title, messages
                   FROM sessions ORDER BY updated_at DESC LIMIT ?""",
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
                results = []
                for r in rows:
                    msg_count = 0
                    try:
                        msgs = json.loads(r[5]) if r[5] else []
                        msg_count = len(msgs)
                    except Exception:
                        pass
                    results.append({
                        "id": r[0],
                        "pack_name": r[1],
                        "created_at": r[2],
                        "updated_at": r[3],
                        "title": r[4],
                        "message_count": msg_count,
                    })
                return results

    async def delete(self, session_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_schema(db)
            cursor = await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await db.commit()
            return cursor.rowcount > 0
