# omagent/packs/loader.py
import importlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from omagent.tools.base import Tool

logger = logging.getLogger(__name__)

# Default search paths for packs
PACK_SEARCH_PATHS = [
    Path(__file__).parent,                    # omagent/packs/ (built-in packs)
    Path.cwd() / "packs",                     # ./packs/ (user packs in cwd)
    Path.home() / ".omagent" / "packs",       # ~/.omagent/packs/ (user global)
]


@dataclass
class DomainPack:
    """A loaded domain pack with resolved tools and config."""
    name: str
    version: str = "0.1.0"
    description: str = ""
    system_prompt: str = "You are a helpful AI assistant."
    tools: list[Tool] = field(default_factory=list)
    permissions: dict[str, str] = field(default_factory=dict)
    skills: list[Path] = field(default_factory=list)
    pack_dir: Path | None = None


def _import_tool_class(dotted_path: str) -> type[Tool]:
    """
    Import a tool class from a dotted path like 'omagent.tools.builtin.read_file:ReadFileTool'.
    Format: 'module.path:ClassName'
    """
    if ":" not in dotted_path:
        raise ValueError(
            f"Tool path must be 'module:ClassName', got: {dotted_path!r}"
        )
    module_path, class_name = dotted_path.rsplit(":", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    if not (isinstance(cls, type) and issubclass(cls, Tool)):
        raise TypeError(f"{dotted_path} is not a Tool subclass")
    return cls


def _find_pack_dir(pack_name: str) -> Path | None:
    """Search for a pack directory by name across search paths."""
    for search_path in PACK_SEARCH_PATHS:
        candidate = search_path / pack_name
        if candidate.is_dir() and (candidate / "pack.yaml").exists():
            return candidate
    return None


class DomainPackLoader:
    """Loads domain packs from YAML config files."""

    def __init__(self, extra_search_paths: list[Path] | None = None):
        self.search_paths = list(PACK_SEARCH_PATHS)
        if extra_search_paths:
            self.search_paths = extra_search_paths + self.search_paths

    def load(self, pack_name: str) -> DomainPack:
        """Load a domain pack by name. Searches known paths for pack.yaml."""
        pack_dir: Path | None = None
        for search_path in self.search_paths:
            candidate = search_path / pack_name
            if candidate.is_dir() and (candidate / "pack.yaml").exists():
                pack_dir = candidate
                break
        if pack_dir is None:
            raise FileNotFoundError(
                f"Domain pack '{pack_name}' not found. "
                f"Searched: {[str(p) for p in self.search_paths]}"
            )
        return self.load_from_dir(pack_dir)

    def load_from_dir(self, pack_dir: Path) -> DomainPack:
        """Load a domain pack from an explicit directory."""
        yaml_path = pack_dir / "pack.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"No pack.yaml in {pack_dir}")

        with open(yaml_path) as f:
            config = yaml.safe_load(f) or {}

        # Resolve tools
        tools: list[Tool] = []
        for tool_path in config.get("tools", []):
            try:
                tool_cls = _import_tool_class(tool_path)
                tools.append(tool_cls())
                logger.debug("Loaded tool: %s from %s", tool_cls.__name__, tool_path)
            except Exception as e:
                logger.warning("Failed to load tool %s: %s", tool_path, e)

        # Resolve skill file paths
        skills: list[Path] = []
        for skill_rel in config.get("skills", []):
            skill_path = pack_dir / skill_rel
            if skill_path.exists():
                skills.append(skill_path)
            else:
                logger.warning("Skill file not found: %s", skill_path)

        return DomainPack(
            name=config.get("name", pack_dir.name),
            version=config.get("version", "0.1.0"),
            description=config.get("description", ""),
            system_prompt=config.get("system_prompt", "You are a helpful AI assistant."),
            tools=tools,
            permissions=config.get("permissions", {}),
            skills=skills,
            pack_dir=pack_dir,
        )

    def list_packs(self) -> list[str]:
        """List all available pack names."""
        packs = set()
        for search_path in self.search_paths:
            if search_path.is_dir():
                for child in search_path.iterdir():
                    if child.is_dir() and (child / "pack.yaml").exists():
                        packs.add(child.name)
        return sorted(packs)
