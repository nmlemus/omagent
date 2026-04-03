"""Tests for the software_dev domain pack."""
import pytest
from pathlib import Path


def test_pack_loads():
    """Verify the software_dev pack loads from pack.yaml."""
    from omagent.packs.loader import DomainPackLoader

    loader = DomainPackLoader()
    pack = loader.load("software_dev")
    assert pack.name == "software_dev"
    assert "Forge" in pack.system_prompt
    assert len(pack.tools) >= 1  # at least project_state


def test_pack_has_project_state_tool():
    """Verify project_state tool is loaded."""
    from omagent.packs.loader import DomainPackLoader

    loader = DomainPackLoader()
    pack = loader.load("software_dev")
    tool_names = [t.name for t in pack.tools]
    assert "project_state" in tool_names


def test_pack_permissions():
    """Verify permissions are set correctly."""
    from omagent.packs.loader import DomainPackLoader

    loader = DomainPackLoader()
    pack = loader.load("software_dev")
    assert pack.permissions.get("project_state") == "auto"
    assert pack.permissions.get("write_file") == "prompt"
    assert pack.permissions.get("bash") == "prompt"


def test_project_state_tool_schema():
    """Verify project_state tool has correct schema."""
    from omagent.packs.software_dev.tools.project_state import ProjectStateTool

    tool = ProjectStateTool()
    assert tool.name == "project_state"
    schema = tool.to_schema()
    props = schema["input_schema"]["properties"]
    assert "operation" in props
    assert set(props["operation"]["enum"]) == {"init", "read", "write", "list", "status"}


@pytest.mark.asyncio
async def test_project_state_init(tmp_path, monkeypatch):
    """Test init creates .planning/ structure."""
    from omagent.packs.software_dev.tools.project_state import ProjectStateTool

    monkeypatch.chdir(tmp_path)
    tool = ProjectStateTool()
    result = await tool.execute({"operation": "init", "phase": "discuss"})

    assert "output" in result
    assert (tmp_path / ".planning" / "STATE.md").exists()
    assert (tmp_path / ".planning" / "CONTEXT.md").exists()
    assert (tmp_path / ".planning" / "PLAN.md").exists()
    assert (tmp_path / ".planning" / "REVIEW.md").exists()


@pytest.mark.asyncio
async def test_project_state_read_write(tmp_path, monkeypatch):
    """Test read and write operations."""
    from omagent.packs.software_dev.tools.project_state import ProjectStateTool

    monkeypatch.chdir(tmp_path)
    tool = ProjectStateTool()

    # Init first
    await tool.execute({"operation": "init"})

    # Write
    result = await tool.execute({
        "operation": "write",
        "file": "CONTEXT.md",
        "content": "# Test Context\n\n## Requirements\n- Build a REST API",
    })
    assert "output" in result

    # Read back
    result = await tool.execute({"operation": "read", "file": "CONTEXT.md"})
    assert "Build a REST API" in result["output"]


@pytest.mark.asyncio
async def test_project_state_list(tmp_path, monkeypatch):
    """Test list shows all state files."""
    from omagent.packs.software_dev.tools.project_state import ProjectStateTool

    monkeypatch.chdir(tmp_path)
    tool = ProjectStateTool()
    await tool.execute({"operation": "init"})

    result = await tool.execute({"operation": "list"})
    file_names = [f["name"] for f in result["files"]]
    assert "STATE.md" in file_names
    assert "CONTEXT.md" in file_names
    assert "PLAN.md" in file_names
    assert "REVIEW.md" in file_names


@pytest.mark.asyncio
async def test_project_state_status(tmp_path, monkeypatch):
    """Test status returns current phase."""
    from omagent.packs.software_dev.tools.project_state import ProjectStateTool

    monkeypatch.chdir(tmp_path)
    tool = ProjectStateTool()
    await tool.execute({"operation": "init", "phase": "discuss"})

    result = await tool.execute({"operation": "status"})
    assert result["initialized"] is True
    assert result["phase"] == "discuss"


@pytest.mark.asyncio
async def test_project_state_read_nonexistent(tmp_path, monkeypatch):
    """Test reading a file that doesn't exist returns error."""
    from omagent.packs.software_dev.tools.project_state import ProjectStateTool

    monkeypatch.chdir(tmp_path)
    tool = ProjectStateTool()
    result = await tool.execute({"operation": "read", "file": "STATE.md"})
    assert "error" in result


@pytest.mark.asyncio
async def test_project_state_path_traversal_write(tmp_path, monkeypatch):
    """Test path traversal is blocked on write."""
    from omagent.packs.software_dev.tools.project_state import ProjectStateTool

    monkeypatch.chdir(tmp_path)
    tool = ProjectStateTool()
    await tool.execute({"operation": "init"})

    result = await tool.execute({
        "operation": "write",
        "file": "../../etc/passwd",
        "content": "malicious",
    })
    assert "error" in result


@pytest.mark.asyncio
async def test_project_state_path_traversal_read(tmp_path, monkeypatch):
    """Test path traversal is blocked on read."""
    from omagent.packs.software_dev.tools.project_state import ProjectStateTool

    monkeypatch.chdir(tmp_path)
    tool = ProjectStateTool()
    await tool.execute({"operation": "init"})

    result = await tool.execute({
        "operation": "read",
        "file": "../../etc/passwd",
    })
    assert "error" in result


@pytest.mark.asyncio
async def test_project_state_disallowed_filename(tmp_path, monkeypatch):
    """Test that only allowed filenames are accepted."""
    from omagent.packs.software_dev.tools.project_state import ProjectStateTool

    monkeypatch.chdir(tmp_path)
    tool = ProjectStateTool()
    await tool.execute({"operation": "init"})

    result = await tool.execute({
        "operation": "write",
        "file": "exploit.py",
        "content": "import os; os.system('rm -rf /')",
    })
    assert "error" in result


def test_skills_discovered():
    """Verify all 5 skills are discovered from the pack."""
    from omagent.core.skill_loader import SkillRegistry

    pack_skills_dir = Path(__file__).parent.parent / "omagent" / "packs" / "software_dev" / "skills"
    if not pack_skills_dir.exists():
        pytest.skip("Pack skills directory not found")

    registry = SkillRegistry()
    count = registry.discover([pack_skills_dir])
    assert count == 5

    names = registry.names()
    assert "discuss" in names
    assert "plan" in names
    assert "execute" in names
    assert "verify" in names
    assert "architecture" in names


def test_skills_user_invocable():
    """Verify all skills are user-invocable."""
    from omagent.core.skill_loader import SkillRegistry

    pack_skills_dir = Path(__file__).parent.parent / "omagent" / "packs" / "software_dev" / "skills"
    if not pack_skills_dir.exists():
        pytest.skip("Pack skills directory not found")

    registry = SkillRegistry()
    registry.discover([pack_skills_dir])
    invocable = registry.get_user_invocable()
    assert len(invocable) == 5


def test_skills_have_content():
    """Verify each skill has readable content."""
    from omagent.core.skill_loader import SkillRegistry

    pack_skills_dir = Path(__file__).parent.parent / "omagent" / "packs" / "software_dev" / "skills"
    if not pack_skills_dir.exists():
        pytest.skip("Pack skills directory not found")

    registry = SkillRegistry()
    registry.discover([pack_skills_dir])

    for name in ["discuss", "plan", "execute", "verify", "architecture"]:
        content = registry.get_full_content(name)
        assert content is not None
        assert len(content) > 100
