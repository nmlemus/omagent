import pytest
from pathlib import Path
from omagent.packs.loader import DomainPackLoader, DomainPack


@pytest.fixture
def sample_pack(tmp_path):
    pack_dir = tmp_path / "test_pack"
    pack_dir.mkdir()
    (pack_dir / "pack.yaml").write_text("""
name: test_pack
version: 1.0.0
description: Test domain pack
system_prompt: You are a test assistant.
tools:
  - omagent.tools.builtin.read_file:ReadFileTool
  - omagent.tools.builtin.list_dir:ListDirTool
permissions:
  ReadFileTool: auto
  ListDirTool: auto
""")
    return tmp_path


def test_load_from_dir(sample_pack):
    loader = DomainPackLoader()
    pack = loader.load_from_dir(sample_pack / "test_pack")
    assert pack.name == "test_pack"
    assert pack.version == "1.0.0"
    assert len(pack.tools) == 2
    assert pack.tools[0].name == "read_file"


def test_load_by_name(sample_pack):
    loader = DomainPackLoader(extra_search_paths=[sample_pack])
    pack = loader.load("test_pack")
    assert pack.name == "test_pack"


def test_list_packs(sample_pack):
    loader = DomainPackLoader(extra_search_paths=[sample_pack])
    names = loader.list_packs()
    assert "test_pack" in names


def test_missing_pack():
    loader = DomainPackLoader()
    with pytest.raises(FileNotFoundError):
        loader.load("nonexistent_pack_xyz")
