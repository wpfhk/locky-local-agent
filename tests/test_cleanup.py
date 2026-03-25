"""tests/test_cleanup.py — actions/cleanup.py 테스트 (12개)"""
import pytest
from pathlib import Path
from actions.cleanup import run, _is_excluded, _deduplicate


@pytest.fixture
def root(tmp_path):
    return tmp_path


# --- run() dry_run=True ---

def test_run_dry_run_lists_pycache(root):
    pycache = root / "__pycache__"
    pycache.mkdir()
    (pycache / "mod.cpython-311.pyc").write_bytes(b"")
    result = run(root, dry_run=True)
    assert result["status"] == "ok"
    assert result["dry_run"] is True
    paths = result["removed"]
    assert any("__pycache__" in p for p in paths)


def test_run_dry_run_does_not_delete(root):
    pycache = root / "__pycache__"
    pycache.mkdir()
    run(root, dry_run=True)
    assert pycache.exists()


def test_run_dry_run_lists_pyc(root):
    pyc = root / "module.pyc"
    pyc.write_bytes(b"")
    result = run(root, dry_run=True)
    assert any("module.pyc" in p for p in result["removed"])


def test_run_dry_run_empty_dir(root):
    result = run(root, dry_run=True)
    assert result["status"] == "ok"
    assert result["removed"] == []


def test_run_dry_run_total_size(root):
    pyc = root / "x.pyc"
    pyc.write_bytes(b"hello")
    result = run(root, dry_run=True)
    assert result["total_size_bytes"] >= 5


# --- run() dry_run=False ---

def test_run_force_deletes_pyc(root):
    pyc = root / "old.pyc"
    pyc.write_bytes(b"")
    result = run(root, dry_run=False)
    assert result["dry_run"] is False
    assert not pyc.exists()


def test_run_force_deletes_pycache(root):
    pycache = root / "__pycache__"
    pycache.mkdir()
    (pycache / "x.pyc").write_bytes(b"")
    run(root, dry_run=False)
    assert not pycache.exists()


def test_run_force_removed_list(root):
    (root / "x.pyc").write_bytes(b"")
    result = run(root, dry_run=False)
    assert len(result["removed"]) >= 1


# --- _is_excluded() ---

def test_is_excluded_git(tmp_path):
    git_file = tmp_path / ".git" / "config"
    git_file.parent.mkdir()
    git_file.touch()
    assert _is_excluded(git_file, tmp_path) is True


def test_is_excluded_venv(tmp_path):
    f = tmp_path / ".venv" / "pyvenv.cfg"
    f.parent.mkdir()
    f.touch()
    assert _is_excluded(f, tmp_path) is True


def test_is_excluded_normal(tmp_path):
    f = tmp_path / "src" / "app.py"
    f.parent.mkdir()
    f.touch()
    assert _is_excluded(f, tmp_path) is False


# --- _deduplicate() ---

def test_deduplicate_removes_child_when_parent_included():
    targets = [
        {"path": "a/b", "abs_path": "/a/b", "size_bytes": 10, "is_dir": True},
        {"path": "a/b/c.pyc", "abs_path": "/a/b/c.pyc", "size_bytes": 5, "is_dir": False},
    ]
    result = _deduplicate(targets)
    paths = [t["path"] for t in result]
    assert "a/b" in paths
    assert "a/b/c.pyc" not in paths
