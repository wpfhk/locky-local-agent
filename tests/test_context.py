"""locky_cli/context.py 단위 테스트."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from locky_cli.context import (_profile_path, detect_and_save, load_profile,
                               save_profile, update_last_run)

# ── save_profile / load_profile ───────────────────────────────────────────────


def test_save_and_load_roundtrip(tmp_path: Path):
    data = {"version": "1", "project": {"name": "test"}}
    save_profile(tmp_path, data)
    loaded = load_profile(tmp_path)
    assert loaded == data


def test_load_returns_empty_when_missing(tmp_path: Path):
    assert load_profile(tmp_path) == {}


def test_load_returns_empty_on_invalid_json(tmp_path: Path):
    (tmp_path / ".locky").mkdir()
    (tmp_path / ".locky" / "profile.json").write_text("NOT JSON", encoding="utf-8")
    assert load_profile(tmp_path) == {}


def test_save_creates_locky_dir(tmp_path: Path):
    save_profile(tmp_path, {"key": "value"})
    assert (tmp_path / ".locky" / "profile.json").exists()


def test_save_uses_utf8(tmp_path: Path):
    save_profile(tmp_path, {"msg": "한국어 테스트"})
    raw = (tmp_path / ".locky" / "profile.json").read_text(encoding="utf-8")
    assert "한국어 테스트" in raw


# ── update_last_run ───────────────────────────────────────────────────────────


def test_update_last_run_when_profile_exists(tmp_path: Path):
    save_profile(tmp_path, {"version": "1"})
    update_last_run(tmp_path, "commit", "ok")
    profile = load_profile(tmp_path)
    assert profile["last_run"]["command"] == "commit"
    assert profile["last_run"]["status"] == "ok"
    assert "at" in profile["last_run"]


def test_update_last_run_noop_when_no_profile(tmp_path: Path):
    # 프로파일 없으면 아무것도 생성하지 않음
    update_last_run(tmp_path, "commit", "ok")
    assert not _profile_path(tmp_path).exists()


# ── detect_and_save ───────────────────────────────────────────────────────────


def test_detect_and_save_creates_profile(tmp_git_repo: Path):
    """git 레포에서 detect_and_save가 profile.json을 생성한다."""
    (tmp_git_repo / "main.py").write_text("print('hello')", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_git_repo, capture_output=True)

    profile = detect_and_save(tmp_git_repo)

    assert _profile_path(tmp_git_repo).exists()
    assert profile["version"] == "1"
    assert profile["project"]["name"] == tmp_git_repo.name
    assert "language" in profile


def test_detect_and_save_detects_python(tmp_git_repo: Path):
    (tmp_git_repo / "app.py").write_text("x = 1", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_git_repo, capture_output=True)

    profile = detect_and_save(tmp_git_repo)
    assert profile["language"]["primary"] == "python"


def test_detect_and_save_merges_existing_commit_style(tmp_git_repo: Path):
    """기존 프로파일의 commit_style을 유지한다."""
    existing = {
        "version": "1",
        "commit_style": {"type": "conventional", "lang": "ko", "examples": []},
    }
    save_profile(tmp_git_repo, existing)

    profile = detect_and_save(tmp_git_repo)
    assert profile["commit_style"]["type"] == "conventional"
