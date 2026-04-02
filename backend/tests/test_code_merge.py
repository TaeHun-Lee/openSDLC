import pytest
import re
from pathlib import Path
from app.core.artifacts.code_extractor import apply_search_replace, normalize_code_path, write_code_blocks

def test_apply_search_replace_basic():
    original = "line1\nline2\nline3\n"
    patch = "<<<< SEARCH\nline2\n====\nline2_new\n>>>> REPLACE"
    expected = "line1\nline2_new\nline3\n"
    assert apply_search_replace(original, patch) == expected

def test_apply_search_replace_multiple():
    original = "a\nb\nc\nd\n"
    patch = (
        "<<<< SEARCH\nb\n====\nB\n>>>> REPLACE\n"
        "<<<< SEARCH\nd\n====\nD\n>>>> REPLACE"
    )
    expected = "a\nB\nc\nD\n"
    assert apply_search_replace(original, patch) == expected

def test_apply_search_replace_mismatch():
    original = "line1\nline2\n"
    patch = "<<<< SEARCH\nline3\n====\nline3_new\n>>>> REPLACE"
    with pytest.raises(ValueError, match="SEARCH block not found"):
        apply_search_replace(original, patch)

def test_apply_search_replace_ambiguous():
    original = "line1\nline2\nline2\nline3\n"
    patch = "<<<< SEARCH\nline2\n====\nline2_new\n>>>> REPLACE"
    with pytest.raises(ValueError, match="SEARCH block is ambiguous"):
        apply_search_replace(original, patch)

def test_write_code_blocks_with_merge(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    file_path = workspace / "test.py"
    file_path.write_text("def hello():\n    print('hi')\n", encoding="utf-8")
    
    code_blocks = [{
        "path": "test.py",
        "content": "<<<< SEARCH\n    print('hi')\n====\n    print('hello world')\n>>>> REPLACE"
    }]
    
    write_code_blocks(code_blocks, workspace)
    
    assert file_path.read_text(encoding="utf-8") == "def hello():\n    print('hello world')\n"

def test_merge_code_blocks_basic():
    from app.core.artifacts.code_extractor import merge_code_blocks
    
    prev_context = "<!-- FILE: app.py -->\n```python\nline1\nline2\n```"
    new_blocks = [{"path": "app.py", "content": "<<<< SEARCH\nline2\n====\nline2_new\n>>>> REPLACE"}]
    
    merged = merge_code_blocks(prev_context, new_blocks)
    assert "line2_new" in merged
    assert "line1" in merged
    assert "SEARCH" not in merged

def test_merge_code_blocks_new_file():
    from app.core.artifacts.code_extractor import merge_code_blocks
    
    prev_context = "<!-- FILE: app.py -->\n```python\nline1\n```"
    new_blocks = [{"path": "new.py", "content": "print('new')"}]
    
    merged = merge_code_blocks(prev_context, new_blocks)
    assert "app.py" in merged
    assert "new.py" in merged
    assert "print('new')" in merged


def test_normalize_code_path_strips_external_workspace_slug():
    assert normalize_code_path(
        "test-server/server.js",
        workspace_root_name="test-server",
        workspace_mode="external_project_root",
    ) == "server.js"
    assert normalize_code_path(
        "workspace/test-server/server.js",
        workspace_root_name="test-server",
        workspace_mode="external_project_root",
    ) == "server.js"


def test_normalize_code_path_rejects_absolute_and_traversal():
    with pytest.raises(ValueError, match="Absolute paths"):
        normalize_code_path("/tmp/server.js")
    with pytest.raises(ValueError, match="Path traversal"):
        normalize_code_path("../server.js")


def test_write_code_blocks_normalizes_external_workspace_paths(tmp_path):
    workspace = tmp_path / "test-server"
    workspace.mkdir()
    code_blocks = [{
        "path": "test-server/server.js",
        "content": "console.log('ok')\n",
    }]

    write_code_blocks(
        code_blocks,
        workspace,
        workspace_root_name="test-server",
        workspace_mode="external_project_root",
    )

    assert (workspace / "server.js").read_text(encoding="utf-8") == "console.log('ok')\n"
    assert not (workspace / "test-server" / "server.js").exists()
