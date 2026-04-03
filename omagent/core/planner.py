# omagent/core/planner.py
"""Plan tracking — captures agent plans and tracks step completion."""
import json
import re
from datetime import datetime, timezone
from typing import Any
from pathlib import Path
import aiosqlite
from omagent.core.session import get_db_path


class PlanStep:
    def __init__(self, description: str, step_num: int):
        self.step_num = step_num
        self.description = description
        self.status = "pending"  # pending, in_progress, completed, failed
        self.tool_used: str | None = None
        self.result_summary: str | None = None
        self.started_at: str | None = None
        self.completed_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "step_num": self.step_num,
            "description": self.description,
            "status": self.status,
            "tool_used": self.tool_used,
            "result_summary": self.result_summary,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlanStep":
        step = cls(data["description"], data["step_num"])
        step.status = data.get("status", "pending")
        step.tool_used = data.get("tool_used")
        step.result_summary = data.get("result_summary")
        step.started_at = data.get("started_at")
        step.completed_at = data.get("completed_at")
        return step


class AgentPlan:
    def __init__(self, goal: str, steps: list[PlanStep] | None = None):
        self.goal = goal
        self.steps = steps or []
        self.status = "active"  # active, completed, failed
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at

    def add_step(self, description: str) -> PlanStep:
        step = PlanStep(description, len(self.steps) + 1)
        self.steps.append(step)
        self._touch()
        return step

    def start_step(self, step_num: int, tool_name: str | None = None) -> None:
        if 0 < step_num <= len(self.steps):
            step = self.steps[step_num - 1]
            step.status = "in_progress"
            step.started_at = datetime.now(timezone.utc).isoformat()
            if tool_name:
                step.tool_used = tool_name
            self._touch()

    def complete_step(self, step_num: int, result_summary: str | None = None) -> None:
        if 0 < step_num <= len(self.steps):
            step = self.steps[step_num - 1]
            step.status = "completed"
            step.completed_at = datetime.now(timezone.utc).isoformat()
            if result_summary:
                step.result_summary = result_summary
            self._touch()
            # Check if all done
            if all(s.status == "completed" for s in self.steps):
                self.status = "completed"

    def fail_step(self, step_num: int, error: str | None = None) -> None:
        if 0 < step_num <= len(self.steps):
            step = self.steps[step_num - 1]
            step.status = "failed"
            step.completed_at = datetime.now(timezone.utc).isoformat()
            step.result_summary = error
            self._touch()

    @property
    def current_step(self) -> int | None:
        for step in self.steps:
            if step.status in ("pending", "in_progress"):
                return step.step_num
        return None

    @property
    def progress(self) -> str:
        completed = sum(1 for s in self.steps if s.status == "completed")
        return f"{completed}/{len(self.steps)}"

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "status": self.status,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentPlan":
        plan = cls(goal=data["goal"])
        plan.status = data.get("status", "active")
        plan.steps = [PlanStep.from_dict(s) for s in data.get("steps", [])]
        plan.created_at = data.get("created_at", plan.created_at)
        plan.updated_at = data.get("updated_at", plan.updated_at)
        return plan

    @classmethod
    def parse_from_text(cls, text: str) -> "AgentPlan | None":
        """Try to extract an ACTION plan from LLM response text.

        Only matches plans that describe actions to be taken (verbs),
        not summaries, recommendations, or data listings.

        Looks for patterns like:
        1. Load the dataset
        2. Clean missing values
        3. Generate visualizations
        """
        # Must contain plan-like keywords near a numbered list
        plan_indicators = re.search(
            r'(?:plan|approach|steps?|strategy|will|let me|going to|here\'s what|i\'ll|voy a|pasos|plan de)',
            text, re.IGNORECASE
        )
        if not plan_indicators:
            return None

        # Look for numbered lists (at least 3 items for a real plan)
        pattern = r'(?:^|\n)\s*(\d+)[.)]\s+(.+?)(?=\n\s*\d+[.)]|\n\n|\Z)'
        matches = re.findall(pattern, text, re.DOTALL)

        if len(matches) < 3:
            return None

        # Filter: steps must look like actions (start with verb-like words), not data/results
        action_words = re.compile(
            r'^(?:load|read|clean|analyz|creat|generat|build|train|evaluat|check|run|install|'
            r'set|configur|implement|deploy|test|export|import|profil|visualiz|plot|merge|'
            r'cargar|limpiar|analizar|crear|generar|construir|entrenar|evaluar|verificar|'
            r'first|then|next|finally|start|begin|prepare|process|extract|transform|'
            r'identify|compar|calculat|comput|determin|investigat|explor|review)',
            re.IGNORECASE
        )

        action_steps = []
        for num, desc in matches:
            desc_clean = desc.strip()
            # Skip steps that look like data listings (contain currency, bold labels with values)
            if re.search(r'R?\$\s*[\d,]+|^\*\*[^*]+\*\*:\s*[~R$\d]|^`[^`]+`:', desc_clean):
                continue
            # Check if starts with an action word (after removing markdown bold)
            desc_no_bold = re.sub(r'\*\*([^*]+)\*\*', r'\1', desc_clean)
            first_word = desc_no_bold.split()[0] if desc_no_bold.split() else ""
            if action_words.match(first_word) or action_words.match(desc_no_bold):
                action_steps.append(desc_clean)

        if len(action_steps) < 3:
            return None

        # Find goal
        goal_match = re.search(
            r'(?:plan|approach|steps?|strategy)[:\s]*(.+?)(?:\n\s*1[.)])',
            text, re.IGNORECASE
        )
        goal = goal_match.group(1).strip() if goal_match else "Analysis plan"

        plan = cls(goal=goal)
        for desc in action_steps:
            plan.add_step(desc)

        return plan


class PlanStore:
    """SQLite-backed storage for agent plans."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or get_db_path()

    async def _ensure_schema(self, db: aiosqlite.Connection) -> None:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                session_id TEXT NOT NULL,
                plan_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (session_id)
            )
        """)
        await db.commit()

    async def save(self, session_id: str, plan: AgentPlan) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_schema(db)
            await db.execute(
                "INSERT OR REPLACE INTO plans (session_id, plan_json, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, json.dumps(plan.to_dict()), plan.created_at, plan.updated_at),
            )
            await db.commit()

    async def load(self, session_id: str) -> AgentPlan | None:
        async with aiosqlite.connect(self.db_path) as db:
            await self._ensure_schema(db)
            async with db.execute(
                "SELECT plan_json FROM plans WHERE session_id = ?", (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return AgentPlan.from_dict(json.loads(row[0]))
                return None
