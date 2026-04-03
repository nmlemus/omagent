import pytest
from pathlib import Path
from omagent.core.skill_loader import Skill, SkillRegistry


@pytest.fixture
def skill_dir(tmp_path):
    """Create valid SKILL.md files."""
    eda_dir = tmp_path / "eda"
    eda_dir.mkdir()
    (eda_dir / "SKILL.md").write_text("""---
name: eda
description: Exploratory data analysis workflow
allowed-tools: jupyter_execute dataset_profile
metadata:
  pack: data_science
  user-invocable: "true"
---

## EDA Workflow
1. Profile the dataset
2. Check distributions
""")

    modeling_dir = tmp_path / "modeling"
    modeling_dir.mkdir()
    (modeling_dir / "SKILL.md").write_text("""---
name: modeling
description: ML model training workflow
metadata:
  pack: data_science
---

## Modeling
1. Prepare features
2. Train model
""")
    return tmp_path


def test_discover(skill_dir):
    reg = SkillRegistry()
    count = reg.discover([skill_dir])
    assert count == 2
    assert "eda" in reg.names()
    assert "modeling" in reg.names()


def test_get_by_name(skill_dir):
    reg = SkillRegistry()
    reg.discover([skill_dir])
    skill = reg.get_by_name("eda")
    assert skill is not None
    assert skill.name == "eda"
    assert skill.description == "Exploratory data analysis workflow"


def test_case_insensitive(skill_dir):
    reg = SkillRegistry()
    reg.discover([skill_dir])
    assert reg.get_by_name("EDA") is not None


def test_get_full_content(skill_dir):
    reg = SkillRegistry()
    reg.discover([skill_dir])
    content = reg.get_full_content("eda")
    assert content is not None
    assert "EDA Workflow" in content


def test_prompt_xml(skill_dir):
    reg = SkillRegistry()
    reg.discover([skill_dir])
    xml = reg.get_prompt_xml()
    assert "<available_skills>" in xml
    assert "<name>" in xml
    assert "eda" in xml


def test_list_all(skill_dir):
    reg = SkillRegistry()
    reg.discover([skill_dir])
    all_skills = reg.list_all()
    assert len(all_skills) == 2
    assert all_skills[0]["name"] in ("eda", "modeling")


def test_invalid_skill_rejected(tmp_path):
    bad_dir = tmp_path / "bad-skill"
    bad_dir.mkdir()
    (bad_dir / "SKILL.md").write_text("no frontmatter here")

    reg = SkillRegistry()
    count = reg.discover([tmp_path])
    assert count == 0


def test_user_invocable(skill_dir):
    reg = SkillRegistry()
    reg.discover([skill_dir])
    invocable = reg.get_user_invocable()
    assert len(invocable) >= 1


def test_skill_tool():
    from omagent.tools.builtin.skill_tool import SkillTool
    reg = SkillRegistry()
    tool = SkillTool(skill_registry=reg)
    assert tool.name == "Skill"
    schema = tool.to_schema()
    assert "skill" in schema["input_schema"]["properties"]


@pytest.mark.asyncio
async def test_skill_tool_execute(skill_dir):
    from omagent.tools.builtin.skill_tool import SkillTool
    reg = SkillRegistry()
    reg.discover([skill_dir])
    tool = SkillTool(skill_registry=reg)

    result = await tool.execute({"skill": "eda"})
    assert result["skill"] == "eda"
    assert "EDA Workflow" in result["prompt"]
    assert result["description"] == "Exploratory data analysis workflow"


@pytest.mark.asyncio
async def test_skill_tool_unknown(skill_dir):
    from omagent.tools.builtin.skill_tool import SkillTool
    reg = SkillRegistry()
    reg.discover([skill_dir])
    tool = SkillTool(skill_registry=reg)

    result = await tool.execute({"skill": "nonexistent"})
    assert "error" in result
