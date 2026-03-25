"""tests/test_tools_file.py — FileTool 테스트 (6개)"""

from pathlib import Path

import pytest

from locky.tools.file import FileTool


def test_file_read_ok(tmp_path):
    (tmp_path / "hello.txt").write_text("world")
    tool = FileTool()
    result = tool.run(tmp_path, action="read", path="hello.txt")
    assert result.ok
    assert "world" in result.message


def test_file_read_not_found(tmp_path):
    tool = FileTool()
    result = tool.run(tmp_path, action="read", path="nope.txt")
    assert result.status == "error"
    assert "파일 없음" in result.message


def test_file_read_path_traversal(tmp_path):
    tool = FileTool()
    result = tool.run(tmp_path, action="read", path="../etc/passwd")
    assert result.status == "error"
    assert "경로 접근 거부" in result.message


def test_file_write_ok(tmp_path):
    tool = FileTool()
    result = tool.run(tmp_path, action="write", path="out.txt", content="hello")
    assert result.ok
    assert (tmp_path / "out.txt").read_text() == "hello"


def test_file_write_creates_dirs(tmp_path):
    tool = FileTool()
    result = tool.run(tmp_path, action="write", path="sub/dir/out.txt", content="data")
    assert result.ok
    assert (tmp_path / "sub" / "dir" / "out.txt").exists()


def test_file_search(tmp_path):
    (tmp_path / "code.py").write_text("def foo():\n    pass\n")
    tool = FileTool()
    result = tool.run(tmp_path, action="search", pattern="def foo", glob="**/*.py")
    assert result.ok
    assert "foo" in result.message


def test_file_unknown_action(tmp_path):
    tool = FileTool()
    result = tool.run(tmp_path, action="unknown")
    assert result.status == "error"
