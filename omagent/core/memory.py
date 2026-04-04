# omagent/core/memory.py
"""Memory system — conversation summarizer + persistent key-value store."""
import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from omagent.core.session import get_db_path, _connect_wal

logger = logging.getLogger(__name__)

# Summarizer defaults
DEFAULT_MAX_MESSAGES = 50
DEFAULT_KEEP_RECENT = 10
DEFAULT_SUMMARY_MODEL = "anthropic/claude-haiku-4-5-20251001"


class ConversationSummarizer:
    """LLM-based conversation summarization for context window management."""

    def __init__(
        self,
        max_messages: int = DEFAULT_MAX_MESSAGES,
        keep_recent: int = DEFAULT_KEEP_RECENT,
        summary_model: str | None = None,
    ):
        self.max_messages = max_messages
        self.keep_recent = keep_recent
        self.summary_model = summary_model or os.getenv(
            "OMAGENT_SUMMARY_MODEL", DEFAULT_SUMMARY_MODEL
        )

    def needs_summarization(self, messages: list[dict]) -> bool:
        """Check if the conversation exceeds the threshold."""
        return len(messages) > self.max_messages

    async def summarize(self, messages: list[dict]) -> dict:
        """
        Summarize older messages and return compacted message list.

        Returns:
            {
                "messages": list[dict],  # Compacted messages (summary + recent)
                "summary": str,           # The generated summary text
                "messages_summarized": int, # How many messages were summarized
                "messages_kept": int,       # How many recent messages kept
            }
        """
        if not self.needs_summarization(messages):
            return {
                "messages": messages,
                "summary": None,
                "messages_summarized": 0,
                "messages_kept": len(messages),
            }

        # Split: old messages to summarize, recent to keep
        cutoff = len(messages) - self.keep_recent
        old_messages = messages[:cutoff]
        recent_messages = messages[cutoff:]

        # Generate summary via LLM
        summary_text = await self._generate_summary(old_messages)

        # Build compacted message list
        summary_message = {
            "role": "system",
            "content": f"[Context Summary — {len(old_messages)} previous messages]\n\n{summary_text}",
        }
        compacted = [summary_message] + recent_messages

        return {
            "messages": compacted,
            "summary": summary_text,
            "messages_summarized": len(old_messages),
            "messages_kept": len(recent_messages),
        }

    async def _generate_summary(self, messages: list[dict]) -> str:
        """Use LLM to generate a structured summary of messages."""
        try:
            from litellm import acompletion

            # Build a transcript for the LLM to summarize
            transcript = self._messages_to_transcript(messages)

            response = await acompletion(
                model=self.summary_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Summarize this conversation between a user and an AI agent. "
                            "Include:\n"
                            "1. What data/files were loaded\n"
                            "2. What analysis/operations were performed\n"
                            "3. Key findings and results\n"
                            "4. Current state and any pending work\n"
                            "5. Important decisions made\n\n"
                            "Be concise but thorough. This summary will replace the original "
                            "messages in the conversation context."
                        ),
                    },
                    {"role": "user", "content": f"Summarize this conversation:\n\n{transcript}"},
                ],
                max_tokens=1000,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.warning("LLM summarization failed, using fallback: %s", e)
            return self._fallback_summary(messages)

    def _messages_to_transcript(self, messages: list[dict]) -> str:
        """Convert messages to a readable transcript for summarization."""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            if isinstance(content, list):
                # Handle tool call arrays
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        if "text" in block:
                            parts.append(block["text"])
                        elif "name" in block:
                            parts.append(f"[Tool: {block['name']}]")
                content = " ".join(parts)
            elif content is None:
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    names = [tc.get("function", {}).get("name", "?") for tc in tool_calls]
                    content = f"[Tool calls: {', '.join(names)}]"
                else:
                    content = ""

            # Truncate very long messages
            if len(str(content)) > 500:
                content = str(content)[:500] + "..."

            lines.append(f"{role}: {content}")

        return "\n".join(lines)

    def _fallback_summary(self, messages: list[dict]) -> str:
        """Simple text-based summary when LLM is unavailable."""
        user_msgs = [m for m in messages if m.get("role") == "user"]
        tool_msgs = [m for m in messages if m.get("role") == "tool"]
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]

        parts = [
            f"Conversation with {len(messages)} messages:",
            f"- {len(user_msgs)} user messages",
            f"- {len(assistant_msgs)} assistant responses",
            f"- {len(tool_msgs)} tool results",
        ]

        # Extract user intents
        if user_msgs:
            parts.append("\nUser requests:")
            for m in user_msgs[:5]:
                content = str(m.get("content", ""))[:100]
                parts.append(f"  - {content}")

        return "\n".join(parts)


class MemoryStore:
    """Persistent key-value memory per session, stored in SQLite."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or get_db_path()
        self._schema_initialized = False

    async def _ensure_schema(self, db: aiosqlite.Connection) -> None:
        if self._schema_initialized:
            return
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                session_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (session_id, key)
            )
        """)
        await db.commit()
        self._schema_initialized = True

    async def set(self, session_id: str, key: str, value: str) -> None:
        """Store or update a memory."""
        now = datetime.now(timezone.utc).isoformat()
        async with _connect_wal(self.db_path) as db:
            await self._ensure_schema(db)
            await db.execute(
                """
                INSERT OR REPLACE INTO memories (session_id, key, value, created_at, updated_at)
                VALUES (?, ?, ?, COALESCE(
                    (SELECT created_at FROM memories WHERE session_id = ? AND key = ?), ?
                ), ?)
                """,
                (session_id, key, value, session_id, key, now, now),
            )
            await db.commit()

    async def get(self, session_id: str, key: str) -> str | None:
        """Retrieve a memory value."""
        async with _connect_wal(self.db_path) as db:
            await self._ensure_schema(db)
            async with db.execute(
                "SELECT value FROM memories WHERE session_id = ? AND key = ?",
                (session_id, key),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def get_all(self, session_id: str) -> dict[str, str]:
        """Get all memories for a session."""
        async with _connect_wal(self.db_path) as db:
            await self._ensure_schema(db)
            async with db.execute(
                "SELECT key, value FROM memories WHERE session_id = ? ORDER BY updated_at",
                (session_id,),
            ) as cursor:
                return {row[0]: row[1] async for row in cursor}

    async def delete(self, session_id: str, key: str) -> bool:
        """Delete a memory."""
        async with _connect_wal(self.db_path) as db:
            await self._ensure_schema(db)
            cursor = await db.execute(
                "DELETE FROM memories WHERE session_id = ? AND key = ?",
                (session_id, key),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_context_injection(self, session_id: str) -> str | None:
        """Generate a context string for system prompt injection."""
        memories = await self.get_all(session_id)
        if not memories:
            return None
        lines = ["[Agent Memory]"]
        for key, value in memories.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)
