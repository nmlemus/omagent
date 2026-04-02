import pytest
from omagent.core.registry import ToolRegistry, ToolNotFoundError
from omagent.tools.builtin import ReadFileTool, ListDirTool


def test_register_and_get():
    reg = ToolRegistry()
    reg.register(ReadFileTool())
    assert reg.has("read_file")
    assert reg.get("read_file").name == "read_file"


def test_get_schemas():
    reg = ToolRegistry()
    reg.register_many([ReadFileTool(), ListDirTool()])
    schemas = reg.get_schemas()
    assert len(schemas) == 2
    assert all("name" in s and "input_schema" in s for s in schemas)


def test_not_found():
    reg = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        reg.get("nonexistent")


async def test_execute_builtin(tmp_path):
    reg = ToolRegistry()
    reg.register(ListDirTool())
    result = await reg.execute("list_dir", {"path": str(tmp_path)})
    assert "output" in result
    assert isinstance(result["output"], list)
