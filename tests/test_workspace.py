import pytest
from pathlib import Path
from omagent.core.workspace import Workspace


@pytest.fixture
def workspace(tmp_path):
    return Workspace(session_id="test-ws", base_dir=tmp_path)


def test_workspace_creates_dirs(workspace):
    assert workspace.artifacts_dir.exists()
    assert workspace.notebooks_dir.exists()
    assert workspace.logs_dir.exists()
    assert workspace.code_dir.exists()


def test_save_artifact(workspace):
    path = workspace.save_artifact("test.csv", "a,b,c\n1,2,3")
    assert path.exists()
    assert path.read_text() == "a,b,c\n1,2,3"


def test_save_image_base64(workspace):
    # Minimal PNG (1x1 pixel)
    import base64
    b64 = base64.b64encode(b'\x89PNG\r\n\x1a\n' + b'\x00' * 50).decode()
    path = workspace.save_image_base64("chart", b64)
    assert path.name == "chart.png"
    assert path.exists()


def test_append_notebook_cell(workspace):
    workspace.append_notebook_cell("print('hello')", [{"text": "hello"}])
    workspace.append_notebook_cell("x = 1 + 1")

    nb_path = workspace.notebook_path
    assert nb_path.exists()
    import json
    nb = json.loads(nb_path.read_text())
    assert len(nb["cells"]) == 2


def test_list_artifacts(workspace):
    workspace.save_artifact("a.csv", "data")
    workspace.save_artifact("b.png", b"\x89PNG")
    arts = workspace.list_artifacts()
    assert len(arts) == 2
    assert arts[0]["name"] == "a.csv"
