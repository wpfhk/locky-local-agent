"""tests/test_tools_git.py — GitTool 테스트 (6개)"""

import subprocess
from pathlib import Path

import pytest

from locky.tools.git import GitTool


@pytest.fixture
def git_repo(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / "hello.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True
    )
    return tmp_path


def test_git_status_ok(git_repo):
    tool = GitTool()
    result = tool.run(git_repo, action="status")
    assert result.ok


def test_git_status_shows_changes(git_repo):
    (git_repo / "new_file.py").write_text("y = 2\n")
    tool = GitTool()
    result = tool.run(git_repo, action="status")
    assert result.ok
    assert "new_file.py" in result.message


def test_git_log_ok(git_repo):
    tool = GitTool()
    result = tool.run(git_repo, action="log", n=1)
    assert result.ok
    assert "init" in result.message


def test_git_diff_ok(git_repo):
    (git_repo / "hello.py").write_text("x = 2\n")
    tool = GitTool()
    result = tool.run(git_repo, action="diff")
    assert result.ok


def test_git_unknown_action(git_repo):
    tool = GitTool()
    result = tool.run(git_repo, action="unknown")
    assert result.status == "error"
    assert "알 수 없는" in result.message


def test_git_tool_repr():
    tool = GitTool()
    assert "GitTool" in repr(tool)
    assert tool.name == "git"
