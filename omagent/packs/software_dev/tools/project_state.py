# omagent/packs/software_dev/tools/project_state.py
"""Project state management tool for the software_dev pack.

Manages the .planning/ directory with structured state files
for the discuss-plan-execute-verify lifecycle.
"""
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

from omagent.tools.base import Tool

PLANNING_DIR = ".planning"
ALLOWED_FILES = {"STATE.md", "CONTEXT.md", "PLAN.md", "REVIEW.md"}

STATE_TEMPLATE = """# Project State

## Current Phase
{phase}

## Progress
- Started: {started}
- Last Updated: {updated}
- Tasks Completed: 0
- Tasks Total: 0

## Blockers
None
"""

CONTEXT_TEMPLATE = """# Project Context

## Requirements
(To be filled during /discuss phase)

## Decisions
(Captured during discussion)

## Assumptions
(Identified during discussion)

## Constraints
(Technical and business constraints)

## Acceptance Criteria
(Testable criteria for success)
"""

PLAN_TEMPLATE = """# Project Plan

## Goal
(To be filled during /plan phase)

## Tasks
(Numbered task breakdown)

## Dependencies
(Task dependency graph)
"""

REVIEW_TEMPLATE = """# Verification Review

## Date
{date}

## Criteria Results
(To be filled during /verify phase)

## Test Results
(Test execution output)

## Summary
(Overall assessment)
"""


class ProjectStateTool(Tool):
    """Manage project state in the .planning/ directory."""

    @property
    def name(self) -> str:
        return "project_state"

    @property
    def description(self) -> str:
        return (
            "Manage project development state in the .planning/ directory. "
            "Supports operations: init (create structure), read (get a file), "
            "write (update a file), list (show all files), status (current phase)."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["init", "read", "write", "list", "status"],
                    "description": "Operation to perform on project state",
                },
                "file": {
                    "type": "string",
                    "description": "State file name (STATE.md, CONTEXT.md, PLAN.md, REVIEW.md). Required for read/write.",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write. Required for write operation.",
                },
                "phase": {
                    "type": "string",
                    "enum": ["discuss", "plan", "execute", "verify"],
                    "description": "Development phase. Used with init operation.",
                },
            },
            "required": ["operation"],
        }

    def _get_planning_dir(self) -> Path:
        return Path.cwd() / PLANNING_DIR

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        operation = input["operation"]
        planning_dir = self._get_planning_dir()

        if operation == "init":
            return await self._init(planning_dir, input.get("phase", "discuss"))
        elif operation == "read":
            return await self._read(planning_dir, input.get("file", "STATE.md"))
        elif operation == "write":
            return await self._write(
                planning_dir,
                input.get("file", "STATE.md"),
                input.get("content", ""),
            )
        elif operation == "list":
            return await self._list(planning_dir)
        elif operation == "status":
            return await self._status(planning_dir)
        else:
            return {"error": f"Unknown operation: {operation}"}

    async def _init(self, planning_dir: Path, phase: str) -> dict[str, Any]:
        planning_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        files_created = []

        state_file = planning_dir / "STATE.md"
        if not state_file.exists():
            state_file.write_text(
                STATE_TEMPLATE.format(phase=phase, started=now, updated=now)
            )
            files_created.append("STATE.md")

        context_file = planning_dir / "CONTEXT.md"
        if not context_file.exists():
            context_file.write_text(CONTEXT_TEMPLATE)
            files_created.append("CONTEXT.md")

        plan_file = planning_dir / "PLAN.md"
        if not plan_file.exists():
            plan_file.write_text(PLAN_TEMPLATE)
            files_created.append("PLAN.md")

        review_file = planning_dir / "REVIEW.md"
        if not review_file.exists():
            review_file.write_text(REVIEW_TEMPLATE.format(date=now))
            files_created.append("REVIEW.md")

        return {
            "output": f"Initialized .planning/ with {len(files_created)} files",
            "files_created": files_created,
            "planning_dir": str(planning_dir),
        }

    async def _read(self, planning_dir: Path, filename: str) -> dict[str, Any]:
        if filename not in ALLOWED_FILES:
            return {"error": f"File must be one of: {', '.join(sorted(ALLOWED_FILES))}"}
        file_path = (planning_dir / filename).resolve()
        if not file_path.is_relative_to(planning_dir.resolve()):
            return {"error": "Path traversal not allowed"}
        if not file_path.exists():
            return {"error": f"File not found: {filename}. Run init first."}
        content = file_path.read_text(encoding="utf-8")
        return {"output": content, "file": filename}

    async def _write(
        self, planning_dir: Path, filename: str, content: str
    ) -> dict[str, Any]:
        if not content:
            return {"error": "Content is required for write operation"}
        if filename not in ALLOWED_FILES:
            return {"error": f"File must be one of: {', '.join(sorted(ALLOWED_FILES))}"}
        planning_dir.mkdir(parents=True, exist_ok=True)
        file_path = (planning_dir / filename).resolve()
        if not file_path.is_relative_to(planning_dir.resolve()):
            return {"error": "Path traversal not allowed"}
        file_path.write_text(content, encoding="utf-8")
        return {"output": f"Written {len(content)} bytes to {filename}", "file": filename}

    async def _list(self, planning_dir: Path) -> dict[str, Any]:
        if not planning_dir.exists():
            return {"output": "No .planning/ directory. Run init first.", "files": []}
        files = []
        for f in sorted(planning_dir.iterdir()):
            if f.is_file():
                files.append(
                    {"name": f.name, "size": f.stat().st_size}
                )
        return {"output": f"{len(files)} state files", "files": files}

    async def _status(self, planning_dir: Path) -> dict[str, Any]:
        state_file = planning_dir / "STATE.md"
        if not state_file.exists():
            return {
                "output": "No project state. Run init to start.",
                "phase": None,
                "initialized": False,
            }
        import re
        content = state_file.read_text(encoding="utf-8")
        match = re.search(r"## Current Phase\s+(\S+)", content)
        phase = match.group(1) if match else "unknown"

        return {
            "output": content,
            "phase": phase if phase != "extracting" else "unknown",
            "initialized": True,
        }
