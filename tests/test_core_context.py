"""tests/test_core_context.py — ContextCollector 테스트 (5개)"""
import subprocess
import pytest
from pathlib import Path
from locky.core.context import ProjectContext, ContextCollector


@pytest.fixture
def git_repo(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "hello.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


def test_collect_basic(git_repo):
    collector = ContextCollector(git_repo)
    ctx = collector.collect()
    assert isinstance(ctx.git_status, str)
    assert isinstance(ctx.git_diff, str)
    assert ctx.failing_files == []
    assert ctx.file_contents == {}


def test_collect_with_files(git_repo):
    (git_repo / "code.py").write_text("def foo(): pass\n")
    collector = ContextCollector(git_repo)
    ctx = collector.collect(files=["code.py"])
    assert "code.py" in ctx.file_contents
    assert "foo" in ctx.file_contents["code.py"]


def test_collect_missing_file_skipped(git_repo):
    collector = ContextCollector(git_repo)
    ctx = collector.collect(files=["nonexistent.py"])
    assert "nonexistent.py" not in ctx.file_contents


def test_to_prompt_context(tmp_path):
    ctx = ProjectContext(
        git_diff="diff output",
        test_output="FAILED test_foo",
        failing_files=["tests/test_foo.py"],
        file_contents={"foo.py": "def foo(): pass"},
    )
    prompt = ctx.to_prompt_context()
    assert "Git Diff" in prompt
    assert "Test Output" in prompt
    assert "Failing Files" in prompt
    assert "foo.py" in prompt


def test_parse_failing_files(tmp_path):
    collector = ContextCollector(tmp_path)
    output = "FAILED tests/test_foo.py::test_bar - AssertionError"
    files = collector._parse_failing_files(output)
    assert files == ["tests/test_foo.py"]
