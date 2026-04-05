"""tools/planner.py 단위 테스트."""

from __future__ import annotations
from pathlib import Path
from tools.planner import is_dangerous, parse_plan, save_plan


def test_parse_plan_valid_json():
    raw = '[{"step": 1, "description": "List files", "command": "ls -la"}]'
    result = parse_plan(raw)
    assert len(result) == 1
    assert result[0]["command"] == "ls -la"
    assert result[0]["description"] == "List files"
    assert result[0]["step"] == 1


def test_parse_plan_extracts_json_from_surrounding_text():
    raw = 'Here is the plan:\n[{"step": 1, "description": "Check", "command": "echo hi"}]\nDone.'
    result = parse_plan(raw)
    assert len(result) == 1
    assert result[0]["command"] == "echo hi"


def test_parse_plan_max_7_steps():
    items = [
        {"step": i, "description": f"step {i}", "command": f"cmd{i}"}
        for i in range(1, 12)
    ]
    import json

    result = parse_plan(json.dumps(items))
    assert len(result) == 7


def test_parse_plan_invalid_json_returns_empty():
    assert parse_plan("not json at all") == []


def test_parse_plan_empty_returns_empty():
    assert parse_plan("") == []


def test_parse_plan_skips_steps_without_command():
    raw = '[{"step": 1, "description": "ok", "command": "ls"}, {"step": 2, "description": "bad", "command": ""}]'
    result = parse_plan(raw)
    assert len(result) == 1
    assert result[0]["command"] == "ls"


def test_is_dangerous_rm_rf_root():
    assert is_dangerous("rm -rf /") is True
    assert is_dangerous("rm -rf /home") is True


def test_is_dangerous_rm_rf_asterisk():
    assert is_dangerous("rm -rf *") is True


def test_is_dangerous_safe_commands():
    assert is_dangerous("ls -la") is False
    assert is_dangerous("git status") is False
    assert is_dangerous("ruff check .") is False
    assert is_dangerous("rm -rf ./build") is False  # relative path is ok


def test_save_plan_creates_file(tmp_path: Path):
    steps = [
        {"step": 1, "description": "Find files", "command": "find . -name '*.py'"},
        {"step": 2, "description": "Run lint", "command": "ruff check ."},
    ]
    path = save_plan(tmp_path, "lint all python files", steps)
    assert path.is_file()
    content = path.read_text(encoding="utf-8")
    assert "lint all python files" in content
    assert "find . -name '*.py'" in content
    assert "ruff check ." in content
