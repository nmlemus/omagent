# omagent/core/skill_loader.py
"""Skill system — uses skills-ref library for Agent Skills spec compliance."""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skills_ref import read_properties, validate, to_prompt, find_skill_md, SkillProperties

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """A discovered skill with its properties and location."""
    name: str
    description: str = ""
    allowed_tools: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    path: Path | None = None  # Path to SKILL.md
    skill_dir: Path | None = None  # Parent directory
    source: str = "unknown"  # "project", "pack", "user"
    full_content: str | None = None  # Cached full SKILL.md content

    @classmethod
    def from_properties(cls, props: SkillProperties, skill_dir: Path, source: str = "unknown") -> "Skill":
        skill_md = find_skill_md(skill_dir)
        content = skill_md.read_text(encoding="utf-8") if skill_md else None
        return cls(
            name=props.name,
            description=props.description,
            allowed_tools=props.allowed_tools,
            metadata=props.metadata or {},
            path=skill_md,
            skill_dir=skill_dir,
            source=source,
            full_content=content,
        )


class SkillRegistry:
    """Discovers and manages skills using the skills-ref library."""

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._skill_dirs: list[Path] = []

    def discover(self, search_paths: list[Path], source: str = "unknown") -> int:
        """Scan directories for SKILL.md files using skills-ref."""
        count = 0
        seen: set[str] = set()

        for base_path in search_paths:
            if not base_path.exists() or not base_path.is_dir():
                continue

            # Check if base_path itself is a skill directory
            if find_skill_md(base_path):
                real = str(base_path.resolve())
                if real not in seen:
                    seen.add(real)
                    skill = self._load_skill(base_path, source)
                    if skill:
                        count += 1

            # Check subdirectories
            for child in sorted(base_path.iterdir()):
                if child.is_dir() and find_skill_md(child):
                    real = str(child.resolve())
                    if real not in seen:
                        seen.add(real)
                        skill = self._load_skill(child, source)
                        if skill:
                            count += 1

        logger.info("Discovered %d skills from %d paths (source: %s)", count, len(search_paths), source)
        return count

    def discover_walk_up(self, cwd: Path | None = None) -> int:
        """Walk up from cwd ancestors checking for skills directories.

        Pattern from claw-code-parity discover_skill_roots().
        Checks .omagent/skills/ and .claude/skills/ at each ancestor.
        """
        cwd = cwd or Path.cwd()
        count = 0
        import itertools
        for ancestor in itertools.chain([cwd], cwd.parents):
            for leaf in (".omagent/skills", ".claude/skills"):
                skills_dir = ancestor / leaf
                if skills_dir.is_dir():
                    count += self.discover([skills_dir], source="project")
            # Stop at filesystem root
            if ancestor == ancestor.parent:
                break
        return count

    # Trust tiers: builtin > user > project
    # Project-local skills (from cloned repos) may contain untrusted content
    TRUSTED_SOURCES = {"builtin", "pack"}

    def _load_skill(self, skill_dir: Path, source: str) -> Skill | None:
        """Load and validate a single skill directory."""
        # Validate first
        errors = validate(skill_dir)
        if errors:
            logger.warning("Skill validation errors in %s: %s", skill_dir, errors)
            return None

        try:
            props = read_properties(skill_dir)
        except Exception as e:
            logger.warning("Failed to read skill %s: %s", skill_dir, e)
            return None

        skill = Skill.from_properties(props, skill_dir, source)

        # Warn on project-local skills (potential prompt injection from cloned repos)
        if source == "project" and source not in self.TRUSTED_SOURCES:
            logger.warning(
                "Loading project-local skill '%s' from %s — "
                "project skills may contain untrusted instructions",
                skill.name, skill_dir,
            )

        # Don't overwrite existing (first found wins — higher priority)
        if skill.name not in self._skills:
            self._skills[skill.name] = skill
            self._skill_dirs.append(skill_dir)
            return skill
        return None

    def register(self, skill: Skill) -> None:
        """Register a skill directly."""
        self._skills[skill.name] = skill
        if skill.skill_dir and skill.skill_dir not in self._skill_dirs:
            self._skill_dirs.append(skill.skill_dir)

    def get_by_name(self, name: str) -> Skill | None:
        """Get skill by name (case-insensitive like claw-code)."""
        # Exact match first
        if name in self._skills:
            return self._skills[name]
        # Case-insensitive fallback
        name_lower = name.lower()
        for skill_name, skill in self._skills.items():
            if skill_name.lower() == name_lower:
                return skill
        return None

    def get_full_content(self, name: str) -> str | None:
        """Get the full SKILL.md content for a skill (for the Skill tool)."""
        skill = self.get_by_name(name)
        if skill and skill.full_content:
            return skill.full_content
        if skill and skill.path and skill.path.exists():
            return skill.path.read_text(encoding="utf-8")
        return None

    def get_prompt_xml(self) -> str:
        """Generate <available_skills> XML using skills-ref to_prompt()."""
        if not self._skill_dirs:
            return ""
        try:
            return to_prompt(self._skill_dirs)
        except Exception as e:
            logger.warning("Failed to generate skills prompt: %s", e)
            return ""

    def names(self) -> list[str]:
        return list(self._skills.keys())

    def list_all(self) -> list[dict]:
        """List all skills with metadata for /skills list command."""
        return [
            {
                "name": s.name,
                "description": s.description,
                "source": s.source,
                "path": str(s.skill_dir) if s.skill_dir else None,
                "allowed_tools": s.allowed_tools,
            }
            for s in self._skills.values()
        ]

    def get_user_invocable(self) -> list[Skill]:
        """Get skills that can be invoked as slash commands."""
        # All skills are user-invocable unless metadata says otherwise
        return [
            s for s in self._skills.values()
            if s.metadata.get("user-invocable", "true").lower() != "false"
        ]
