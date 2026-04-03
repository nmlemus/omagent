import pytest
from pathlib import Path
from omagent.core.skill_loader import Skill, SkillRegistry, parse_skill_md


@pytest.fixture
def skill_dir(tmp_path):
    """Create a test skill directory."""
    eda_dir = tmp_path / "eda"
    eda_dir.mkdir()
    (eda_dir / "SKILL.md").write_text("""---
name: eda
description: Exploratory data analysis
triggers:
  - eda
  - explore the data
  - profile
allowed-tools: jupyter_execute dataset_profile
user-invocable: true
level: 1
metadata:
  pack: data_science
---

## EDA Workflow

1. Profile the dataset
2. Check distributions
3. Find correlations
""")
    scripts_dir = eda_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "quick_check.py").write_text('print("hello from script")')

    modeling_dir = tmp_path / "modeling"
    modeling_dir.mkdir()
    (modeling_dir / "SKILL.md").write_text("""---
name: modeling
description: ML model training workflow
triggers:
  - model
  - train
  - predict
user-invocable: true
level: 2
---

## Modeling Workflow
1. Prepare features
2. Train model
""")
    return tmp_path


def test_parse_skill_md(skill_dir):
    skill = parse_skill_md(skill_dir / "eda" / "SKILL.md")
    assert skill is not None
    assert skill.name == "eda"
    assert skill.description == "Exploratory data analysis"
    assert "eda" in skill.triggers
    assert "explore the data" in skill.triggers
    assert skill.user_invocable is True
    assert skill.scripts_dir is not None


def test_discover(skill_dir):
    registry = SkillRegistry()
    count = registry.discover([skill_dir])
    assert count == 2
    assert "eda" in registry.names()
    assert "modeling" in registry.names()


def test_metadata_prompt(skill_dir):
    registry = SkillRegistry()
    registry.discover([skill_dir])
    prompt = registry.get_metadata_prompt()
    assert "[Available Skills]" in prompt
    assert "eda" in prompt
    assert "modeling" in prompt


def test_match_triggers(skill_dir):
    registry = SkillRegistry()
    registry.discover([skill_dir])

    matches = registry.match_triggers("can you explore the data please")
    assert len(matches) >= 1
    assert matches[0].name == "eda"


def test_match_triggers_no_match(skill_dir):
    registry = SkillRegistry()
    registry.discover([skill_dir])

    matches = registry.match_triggers("hello world")
    assert len(matches) == 0


def test_load_full(skill_dir):
    registry = SkillRegistry()
    registry.discover([skill_dir])

    instructions = registry.load_full("eda")
    assert instructions is not None
    assert "Profile the dataset" in instructions


def test_user_invocable(skill_dir):
    registry = SkillRegistry()
    registry.discover([skill_dir])

    invocable = registry.get_user_invocable()
    assert len(invocable) == 2


@pytest.mark.asyncio
async def test_run_script(skill_dir):
    registry = SkillRegistry()
    registry.discover([skill_dir])

    output = await registry.run_script("eda", "quick_check.py")
    assert "hello from script" in output
