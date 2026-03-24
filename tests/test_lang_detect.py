"""locky_cli/lang_detect.py 단위 테스트."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from locky_cli.lang_detect import detect


# ── detect — git 레포 기반 ────────────────────────────────────────────────────


def test_detect_python_primary(tmp_git_repo: Path):
    (tmp_git_repo / "main.py").write_text("x = 1", encoding="utf-8")
    (tmp_git_repo / "utils.py").write_text("y = 2", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_git_repo, capture_output=True)

    result = detect(tmp_git_repo)
    assert result["primary"] == "python"
    assert "python" in result["all"]


def test_detect_javascript(tmp_git_repo: Path):
    (tmp_git_repo / "app.js").write_text("console.log('hi')", encoding="utf-8")
    (tmp_git_repo / "util.js").write_text("module.exports = {}", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_git_repo, capture_output=True)

    result = detect(tmp_git_repo)
    assert result["primary"] == "javascript"


def test_detect_typescript(tmp_git_repo: Path):
    (tmp_git_repo / "index.ts").write_text("const x: number = 1;", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_git_repo, capture_output=True)

    result = detect(tmp_git_repo)
    assert result["primary"] == "typescript"


def test_detect_mixed_project_most_common_is_primary(tmp_git_repo: Path):
    # Python 2개, JS 1개 → Python이 primary
    (tmp_git_repo / "a.py").write_text("pass", encoding="utf-8")
    (tmp_git_repo / "b.py").write_text("pass", encoding="utf-8")
    (tmp_git_repo / "c.js").write_text("var x = 1;", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_git_repo, capture_output=True)

    result = detect(tmp_git_repo)
    assert result["primary"] == "python"
    assert "javascript" in result["all"]


def test_detect_all_contains_all_languages(tmp_git_repo: Path):
    (tmp_git_repo / "a.py").write_text("pass", encoding="utf-8")
    (tmp_git_repo / "b.go").write_text("package main", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_git_repo, capture_output=True)

    result = detect(tmp_git_repo)
    assert set(result["all"]) == {"python", "go"}


def test_detect_empty_repo_returns_unknown(tmp_git_repo: Path):
    # 소스 파일 없음
    result = detect(tmp_git_repo)
    assert result["primary"] == "unknown"
    assert result["all"] == []


def test_detect_unknown_extensions_ignored(tmp_git_repo: Path):
    (tmp_git_repo / "README.md").write_text("# hi", encoding="utf-8")
    (tmp_git_repo / "data.json").write_text("{}", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_git_repo, capture_output=True)

    result = detect(tmp_git_repo)
    # .md, .json은 매핑 없음 → unknown
    assert result["primary"] == "unknown"


# ── detect — git 없는 폴백 ────────────────────────────────────────────────────


def test_detect_fallback_without_git(tmp_path: Path):
    """git 레포가 아닌 경우 rglob 폴백 사용."""
    (tmp_path / "script.py").write_text("pass", encoding="utf-8")
    (tmp_path / "lib.py").write_text("pass", encoding="utf-8")

    result = detect(tmp_path)
    assert result["primary"] == "python"


def test_detect_fallback_mixed(tmp_path: Path):
    (tmp_path / "a.rs").write_text("fn main() {}", encoding="utf-8")
    (tmp_path / "b.rs").write_text("fn foo() {}", encoding="utf-8")
    (tmp_path / "c.py").write_text("pass", encoding="utf-8")

    result = detect(tmp_path)
    assert result["primary"] == "rust"
    assert "python" in result["all"]
