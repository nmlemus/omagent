# omagent/core/workspace.py
"""Workspace manager — per-session directory for artifacts, notebooks, and logs."""
import json
import base64
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_WORKSPACES_DIR = Path.home() / ".omagent" / "workspaces"


def get_workspaces_dir() -> Path:
    env = os.getenv("OMAGENT_WORKSPACES_DIR")
    path = Path(env).expanduser() if env else DEFAULT_WORKSPACES_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


class Workspace:
    """Manages a per-session workspace directory with artifacts, notebooks, logs, and code."""

    def __init__(self, session_id: str, base_dir: Path | None = None):
        self.session_id = session_id
        self.root = (base_dir or get_workspaces_dir()) / session_id
        self.artifacts_dir = self.root / "artifacts"
        self.notebooks_dir = self.root / "notebooks"
        self.logs_dir = self.root / "logs"
        self.code_dir = self.root / "code"
        self._notebook_cells: list[dict] = []
        self._cell_counter = 0
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        for d in [self.artifacts_dir, self.notebooks_dir, self.logs_dir, self.code_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def save_artifact(self, name: str, data: str | bytes, artifact_type: str = "file") -> Path:
        """Save an artifact (chart, CSV, model, etc.) and return its path."""
        path = self.artifacts_dir / name
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_text(data, encoding="utf-8")
        return path

    def save_image_base64(self, name: str, b64_data: str) -> Path:
        """Save a base64-encoded image to artifacts."""
        if not name.lower().endswith(('.png', '.jpg', '.jpeg', '.svg')):
            name += ".png"
        data = base64.b64decode(b64_data)
        return self.save_artifact(name, data, artifact_type="image")

    def save_code(self, filename: str, code: str) -> Path:
        """Save a code file."""
        path = self.code_dir / filename
        path.write_text(code, encoding="utf-8")
        return path

    def append_notebook_cell(
        self,
        code: str,
        outputs: list[dict] | None = None,
        execution_count: int | None = None,
    ) -> None:
        """Append a code cell to the session notebook."""
        self._cell_counter += 1
        cell = {
            "cell_type": "code",
            "execution_count": execution_count or self._cell_counter,
            "metadata": {},
            "source": code.split("\n"),
            "outputs": self._format_notebook_outputs(outputs or []),
        }
        self._notebook_cells.append(cell)
        self._save_notebook()

    def _format_notebook_outputs(self, outputs: list[dict]) -> list[dict]:
        """Convert tool outputs to .ipynb output format."""
        nb_outputs = []
        for out in outputs:
            if isinstance(out, dict):
                if "text" in out:
                    nb_outputs.append({
                        "output_type": "execute_result",
                        "data": {"text/plain": [out["text"]]},
                        "metadata": {},
                        "execution_count": self._cell_counter,
                    })
                if "image_base64" in out:
                    nb_outputs.append({
                        "output_type": "display_data",
                        "data": {"image/png": out["image_base64"]},
                        "metadata": {},
                    })
        return nb_outputs

    def _save_notebook(self) -> None:
        """Write the current notebook state to disk."""
        notebook = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {"name": "python", "version": "3.12"},
                "omagent": {
                    "session_id": self.session_id,
                    "created": datetime.now(timezone.utc).isoformat(),
                },
            },
            "cells": self._notebook_cells,
        }
        path = self.notebooks_dir / "session.ipynb"
        path.write_text(json.dumps(notebook, indent=2), encoding="utf-8")

    def list_artifacts(self) -> list[dict]:
        """List all artifacts in the workspace."""
        artifacts = []
        for path in sorted(self.artifacts_dir.iterdir()):
            stat = path.stat()
            artifacts.append({
                "name": path.name,
                "path": str(path),
                "size": stat.st_size,
                "type": path.suffix.lstrip(".") or "file",
                "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            })
        return artifacts

    def get_artifact_path(self, name: str) -> Path | None:
        """Get the path to an artifact by name."""
        path = self.artifacts_dir / name
        return path if path.exists() else None

    @property
    def notebook_path(self) -> Path:
        return self.notebooks_dir / "session.ipynb"

    @property
    def events_log_path(self) -> Path:
        return self.logs_dir / "events.jsonl"

    @property
    def run_log_path(self) -> Path:
        return self.logs_dir / "run.log"
