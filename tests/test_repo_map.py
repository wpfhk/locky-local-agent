"""tests/test_repo_map.py -- RepoMap 테스트."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.repo_map import RepoMap


@pytest.fixture
def repo_dir(tmp_path):
    """가상 git repo 디렉토리."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".locky").mkdir()
    return tmp_path


@pytest.fixture
def repo_map(repo_dir):
    return RepoMap(repo_dir)


# ---------------------------------------------------------------------------
# Python parsing
# ---------------------------------------------------------------------------


class TestParsePython:
    def test_functions_and_classes(self, repo_map, repo_dir):
        py_file = repo_dir / "example.py"
        py_file.write_text(
            '''
import os
from pathlib import Path

class MyClass:
    def method(self):
        pass

def top_level_func():
    pass

async def async_func():
    pass
'''
        )
        result = repo_map._parse_python(py_file)
        assert "MyClass" in result["classes"]
        assert "method" in result["functions"]
        assert "top_level_func" in result["functions"]
        assert "async_func" in result["functions"]
        assert "os" in result["imports"]
        assert "pathlib" in result["imports"]

    def test_empty_file(self, repo_map, repo_dir):
        py_file = repo_dir / "empty.py"
        py_file.write_text("")
        result = repo_map._parse_python(py_file)
        assert result == {"functions": [], "classes": [], "imports": []}

    def test_syntax_error_handled(self, repo_map, repo_dir):
        py_file = repo_dir / "bad.py"
        py_file.write_text("def broken(:\n  pass")
        with pytest.raises(SyntaxError):
            repo_map._parse_python(py_file)


# ---------------------------------------------------------------------------
# Generic (JS/TS) parsing
# ---------------------------------------------------------------------------


class TestParseGeneric:
    def test_js_functions(self, repo_map, repo_dir):
        js_file = repo_dir / "example.js"
        js_file.write_text(
            '''
import React from 'react';
import { useState } from 'react';

function greet() {}
export function hello() {}
const add = (a, b) => a + b;
export class MyComponent {}
async function fetchData() {}
'''
        )
        result = repo_map._parse_generic(js_file)
        assert "greet" in result["functions"]
        assert "hello" in result["functions"]
        assert "fetchData" in result["functions"]
        assert "MyComponent" in result["classes"]
        assert "react" in result["imports"]

    def test_empty_js(self, repo_map, repo_dir):
        js_file = repo_dir / "empty.js"
        js_file.write_text("")
        result = repo_map._parse_generic(js_file)
        assert result["functions"] == []
        assert result["classes"] == []


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


class TestBuild:
    def test_build_creates_map(self, repo_map, repo_dir):
        (repo_dir / "main.py").write_text("def main(): pass")
        (repo_dir / "util.py").write_text("class Helper: pass")

        with patch.object(repo_map, "_get_tracked_files", return_value=["main.py", "util.py"]):
            with patch.object(repo_map, "_get_git_hash", return_value="abc123"):
                data = repo_map.build()

        assert data["version"] == 1
        assert data["git_hash"] == "abc123"
        assert "main.py" in data["files"]
        assert "main" in data["files"]["main.py"]["functions"]
        assert "Helper" in data["files"]["util.py"]["classes"]

    def test_build_skips_unsupported_ext(self, repo_map, repo_dir):
        (repo_dir / "readme.md").write_text("# Hello")

        with patch.object(repo_map, "_get_tracked_files", return_value=["readme.md"]):
            with patch.object(repo_map, "_get_git_hash", return_value="abc"):
                data = repo_map.build()

        assert "readme.md" not in data["files"]

    def test_build_handles_parse_error(self, repo_map, repo_dir):
        (repo_dir / "bad.py").write_text("def broken(:\n  pass")

        with patch.object(repo_map, "_get_tracked_files", return_value=["bad.py"]):
            with patch.object(repo_map, "_get_git_hash", return_value="abc"):
                data = repo_map.build()

        # 파싱 실패해도 빈 항목으로 포함
        assert "bad.py" in data["files"]
        assert data["files"]["bad.py"]["functions"] == []

    def test_build_saves_cache(self, repo_map, repo_dir):
        (repo_dir / "main.py").write_text("def main(): pass")

        with patch.object(repo_map, "_get_tracked_files", return_value=["main.py"]):
            with patch.object(repo_map, "_get_git_hash", return_value="abc123"):
                repo_map.build()

        assert repo_map.cache_path.exists()
        cached = json.loads(repo_map.cache_path.read_text())
        assert cached["git_hash"] == "abc123"


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


class TestCache:
    def test_cache_hit(self, repo_map, repo_dir):
        cache_data = {
            "version": 1,
            "git_hash": "abc123",
            "generated_at": "2026-01-01",
            "files": {"cached.py": {"functions": ["cached_fn"], "classes": [], "imports": []}},
        }
        repo_map.cache_path.write_text(json.dumps(cache_data))

        with patch.object(repo_map, "_get_git_hash", return_value="abc123"):
            loaded = repo_map._load_cache()

        assert loaded is not None
        assert "cached.py" in loaded["files"]

    def test_cache_miss_different_hash(self, repo_map, repo_dir):
        cache_data = {
            "version": 1,
            "git_hash": "old_hash",
            "generated_at": "2026-01-01",
            "files": {},
        }
        repo_map.cache_path.write_text(json.dumps(cache_data))

        with patch.object(repo_map, "_get_git_hash", return_value="new_hash"):
            loaded = repo_map._load_cache()

        assert loaded is None

    def test_cache_miss_no_file(self, repo_map):
        loaded = repo_map._load_cache()
        assert loaded is None

    def test_cache_miss_wrong_version(self, repo_map, repo_dir):
        cache_data = {"version": 999, "git_hash": "abc", "files": {}}
        repo_map.cache_path.write_text(json.dumps(cache_data))

        with patch.object(repo_map, "_get_git_hash", return_value="abc"):
            loaded = repo_map._load_cache()

        assert loaded is None


# ---------------------------------------------------------------------------
# Get context
# ---------------------------------------------------------------------------


class TestGetContext:
    def test_get_context_matching(self, repo_map, repo_dir):
        (repo_dir / "commit.py").write_text("def generate_commit(): pass")

        with patch.object(repo_map, "_get_tracked_files", return_value=["commit.py"]):
            with patch.object(repo_map, "_get_git_hash", return_value="abc"):
                repo_map.build()
                ctx = repo_map.get_context("commit")

        assert "commit.py" in ctx
        assert "generate_commit" in ctx

    def test_get_context_no_match(self, repo_map, repo_dir):
        (repo_dir / "main.py").write_text("def main(): pass")

        with patch.object(repo_map, "_get_tracked_files", return_value=["main.py"]):
            with patch.object(repo_map, "_get_git_hash", return_value="abc"):
                repo_map.build()
                ctx = repo_map.get_context("nonexistent_query_xyz")

        assert "해당하는 항목이 없습니다" in ctx

    def test_get_context_token_limit(self, repo_map, repo_dir):
        # Create many files
        for i in range(50):
            (repo_dir / f"module_{i}.py").write_text(f"def func_{i}(): pass")

        files = [f"module_{i}.py" for i in range(50)]
        with patch.object(repo_map, "_get_tracked_files", return_value=files):
            with patch.object(repo_map, "_get_git_hash", return_value="abc"):
                repo_map.build()
                ctx = repo_map.get_context("module", max_tokens=100)

        # Should be limited by token budget
        assert len(ctx) < 1000  # 100 tokens * 4 chars + header


# ---------------------------------------------------------------------------
# Incremental update
# ---------------------------------------------------------------------------


class TestUpdateIncremental:
    def test_incremental_update_modifies_changed(self, repo_map, repo_dir):
        # Initial build
        (repo_dir / "main.py").write_text("def original(): pass")

        with patch.object(repo_map, "_get_tracked_files", return_value=["main.py"]):
            with patch.object(repo_map, "_get_git_hash", return_value="hash1"):
                repo_map.build()

        # Modify file
        (repo_dir / "main.py").write_text("def updated(): pass")

        with patch.object(repo_map, "_get_git_hash", return_value="hash1"):
            data = repo_map.update_incremental(changed_files=["main.py"])

        assert "updated" in data["files"]["main.py"]["functions"]
        assert "original" not in data["files"]["main.py"]["functions"]

    def test_incremental_removes_deleted_file(self, repo_map, repo_dir):
        (repo_dir / "main.py").write_text("def main(): pass")

        with patch.object(repo_map, "_get_tracked_files", return_value=["main.py"]):
            with patch.object(repo_map, "_get_git_hash", return_value="hash1"):
                repo_map.build()

        # Delete file
        (repo_dir / "main.py").unlink()

        with patch.object(repo_map, "_get_git_hash", return_value="hash1"):
            data = repo_map.update_incremental(changed_files=["main.py"])

        assert "main.py" not in data["files"]

    def test_incremental_no_cache_does_full_build(self, repo_map, repo_dir):
        (repo_dir / "main.py").write_text("def main(): pass")

        with patch.object(repo_map, "_get_tracked_files", return_value=["main.py"]):
            with patch.object(repo_map, "_get_git_hash", return_value="abc"):
                data = repo_map.update_incremental(changed_files=["main.py"])

        assert "main.py" in data["files"]
