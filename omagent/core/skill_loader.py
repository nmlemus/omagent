# omagent/core/skill_loader.py
"""Skill system — SKILL.md parser, discovery, trigger matching, progressive loading."""
import asyncio
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

MAX_SKILLS_PER_PROMPT = 5


@dataclass
class Skill:
    """A loaded skill from SKILL.md."""
    name: str
    description: str = ""
    triggers: list[str] = field(default_factory=list)
    instructions: str = ""
    allowed_tools: list[str] = field(default_factory=list)
    user_invocable: bool = True
    model_invocable: bool = True
    model: str | None = None
    level: int = 1
    scripts_dir: Path | None = None
    references_dir: Path | None = None
    pack: str | None = None
    path: Path | None = None


def parse_skill_md(skill_md_path: Path) -> Skill | None:
    """Parse a SKILL.md file into a Skill object.

    Format:
    ---
    name: skill-name
    description: what it does
    triggers:
      - keyword1
      - keyword2
    allowed-tools: tool1 tool2
    user-invocable: true
    level: 1
    metadata:
      pack: data_science
    ---

    Markdown instructions...
    """
    try:
        content = skill_md_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to read skill: %s: %s", skill_md_path, e)
        return None

    # Parse YAML frontmatter
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', content, re.DOTALL)
    if not match:
        # No frontmatter — treat entire file as instructions with directory name as skill name
        return Skill(
            name=skill_md_path.parent.name,
            instructions=content,
            path=skill_md_path,
        )

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as e:
        logger.warning("Invalid YAML in skill %s: %s", skill_md_path, e)
        return None

    body = match.group(2).strip()
    skill_dir = skill_md_path.parent

    # Parse allowed-tools (can be string or list)
    allowed_tools_raw = frontmatter.get("allowed-tools", "")
    if isinstance(allowed_tools_raw, str):
        allowed_tools = allowed_tools_raw.split() if allowed_tools_raw else []
    elif isinstance(allowed_tools_raw, list):
        allowed_tools = allowed_tools_raw
    else:
        allowed_tools = []

    # Parse triggers
    triggers = frontmatter.get("triggers", [])
    if isinstance(triggers, str):
        triggers = [triggers]

    metadata = frontmatter.get("metadata", {}) or {}

    scripts_dir = skill_dir / "scripts"
    references_dir = skill_dir / "references"

    return Skill(
        name=frontmatter.get("name", skill_dir.name),
        description=frontmatter.get("description", ""),
        triggers=[t.lower() for t in triggers],
        instructions=body,
        allowed_tools=allowed_tools,
        user_invocable=not frontmatter.get("disable-user-invocation", False),
        model_invocable=not frontmatter.get("disable-model-invocation", False),
        model=frontmatter.get("model"),
        level=frontmatter.get("level", 1),
        scripts_dir=scripts_dir if scripts_dir.is_dir() else None,
        references_dir=references_dir if references_dir.is_dir() else None,
        pack=metadata.get("pack"),
        path=skill_md_path,
    )


def _sanitize_input(text: str) -> str:
    """Sanitize user input for trigger matching.

    Remove code blocks, URLs, file paths to prevent false positives.
    Pattern verified from keyword-detector.mjs.
    """
    text = re.sub(r'```[\s\S]*?```', '', text)           # Code blocks
    text = re.sub(r'`[^`]+`', '', text)                   # Inline code
    text = re.sub(r'https?://[^\s)>\]]+', '', text)       # URLs
    return text.lower()


class SkillRegistry:
    """Discovers, loads, and manages skills with trigger-based matching."""

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def discover(self, search_paths: list[Path]) -> int:
        """Scan directories for SKILL.md files. Returns count of skills found."""
        count = 0
        seen_paths: set[str] = set()

        for base_path in search_paths:
            if not base_path.exists():
                continue
            # Check if base_path itself contains SKILL.md
            skill_md = base_path / "SKILL.md"
            if skill_md.exists():
                real = str(skill_md.resolve())
                if real not in seen_paths:
                    seen_paths.add(real)
                    skill = parse_skill_md(skill_md)
                    if skill:
                        self._skills[skill.name] = skill
                        count += 1

            # Scan subdirectories for SKILL.md
            if base_path.is_dir():
                for child in sorted(base_path.iterdir()):
                    if child.is_dir():
                        skill_md = child / "SKILL.md"
                        if skill_md.exists():
                            real = str(skill_md.resolve())
                            if real not in seen_paths:
                                seen_paths.add(real)
                                skill = parse_skill_md(skill_md)
                                if skill:
                                    self._skills[skill.name] = skill
                                    count += 1
                        # Also check for plain .md files (backward compat)
                        for md_file in sorted(child.glob("*.md")):
                            if md_file.name != "SKILL.md":
                                real = str(md_file.resolve())
                                if real not in seen_paths:
                                    seen_paths.add(real)
                                    skill = parse_skill_md(md_file)
                                    if skill:
                                        self._skills[skill.name] = skill
                                        count += 1

        logger.info("Discovered %d skills from %d paths", count, len(search_paths))
        return count

    def register(self, skill: Skill) -> None:
        """Register a skill directly."""
        self._skills[skill.name] = skill

    def get_by_name(self, name: str) -> Skill | None:
        """Get a skill by name."""
        return self._skills.get(name)

    def names(self) -> list[str]:
        """List all skill names."""
        return list(self._skills.keys())

    def get_metadata_prompt(self) -> str:
        """Level 1: Generate skill names + descriptions for system prompt.

        Lightweight — all skills fit in context as metadata.
        """
        if not self._skills:
            return ""

        lines = ["[Available Skills]"]
        for skill in self._skills.values():
            invocable = " (invoke with /{})".format(skill.name) if skill.user_invocable else ""
            lines.append(f"- {skill.name}: {skill.description}{invocable}")
        return "\n".join(lines)

    def match_triggers(self, user_input: str) -> list[Skill]:
        """Match user input against skill triggers.

        Scoring: +10 per trigger match, sorted descending, capped at MAX_SKILLS_PER_PROMPT.
        Pattern verified from skill-injector.mjs:128-182.
        """
        sanitized = _sanitize_input(user_input)
        scored: list[tuple[int, Skill]] = []

        for skill in self._skills.values():
            if not skill.model_invocable:
                continue
            score = 0
            for trigger in skill.triggers:
                if trigger in sanitized:
                    score += 10
            if score > 0:
                scored.append((score, skill))

        # Sort by score descending, cap at MAX
        scored.sort(key=lambda x: -x[0])
        return [skill for _, skill in scored[:MAX_SKILLS_PER_PROMPT]]

    def load_full(self, skill_name: str) -> str | None:
        """Level 2: Load full instructions for a skill."""
        skill = self._skills.get(skill_name)
        if skill:
            return skill.instructions
        return None

    async def run_script(self, skill_name: str, script_name: str) -> str:
        """Level 3: Execute a script from a skill's scripts/ directory.

        Code never enters context — only stdout is returned.
        """
        skill = self._skills.get(skill_name)
        if not skill or not skill.scripts_dir:
            return f"Skill '{skill_name}' has no scripts directory"

        script_path = skill.scripts_dir / script_name
        if not script_path.exists():
            return f"Script not found: {script_name}"

        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                output += "\n" + stderr.decode("utf-8", errors="replace")
            return output
        except asyncio.TimeoutError:
            return f"Script timed out: {script_name}"
        except Exception as e:
            return f"Script error: {e}"

    def get_user_invocable(self) -> list[Skill]:
        """Get all skills that can be invoked by the user as slash commands."""
        return [s for s in self._skills.values() if s.user_invocable]
