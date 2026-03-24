"""tests/test_deps_check.py — deps_check.py 단위 테스트 (v1.1.0)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from actions.deps_check import (
    _find_dep_file,
    _is_outdated,
    _parse_go_mod,
    _parse_package_json,
    _parse_pyproject,
    _parse_requirements,
    run,
)


# ── _find_dep_file ─────────────────────────────────────────────────────────────


def test_find_requirements_txt(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    path, fmt = _find_dep_file(tmp_path)
    assert path == tmp_path / "requirements.txt"
    assert fmt == "requirements.txt"


def test_find_pyproject_toml(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
    path, fmt = _find_dep_file(tmp_path)
    assert path == tmp_path / "pyproject.toml"
    assert fmt == "pyproject.toml"


def test_find_package_json(tmp_path):
    (tmp_path / "package.json").write_text('{"dependencies": {}}')
    path, fmt = _find_dep_file(tmp_path)
    assert path == tmp_path / "package.json"
    assert fmt == "package.json"


def test_find_go_mod(tmp_path):
    (tmp_path / "go.mod").write_text("module example.com/app\ngo 1.21\n")
    path, fmt = _find_dep_file(tmp_path)
    assert path == tmp_path / "go.mod"
    assert fmt == "go.mod"


def test_find_priority_requirements_over_pyproject(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    (tmp_path / "pyproject.toml").write_text("[project]\n")
    path, fmt = _find_dep_file(tmp_path)
    assert fmt == "requirements.txt"


def test_find_no_dep_file(tmp_path):
    path, fmt = _find_dep_file(tmp_path)
    assert path is None
    assert fmt == ""


# ── _parse_requirements ────────────────────────────────────────────────────────


def test_parse_requirements_basic(tmp_path):
    f = tmp_path / "requirements.txt"
    f.write_text("requests==2.28.0\nflask>=2.0\nclick\n")
    result = _parse_requirements(f)
    assert ("requests", "==2.28.0") in result
    assert ("flask", ">=2.0") in result
    assert ("click", "") in result


def test_parse_requirements_ignores_comments(tmp_path):
    f = tmp_path / "requirements.txt"
    f.write_text("# comment\nrequests==2.28.0\n")
    result = _parse_requirements(f)
    assert len(result) == 1
    assert result[0][0] == "requests"


def test_parse_requirements_ignores_flags(tmp_path):
    f = tmp_path / "requirements.txt"
    f.write_text("-r other.txt\nrequests==2.28.0\n")
    result = _parse_requirements(f)
    assert len(result) == 1


def test_parse_requirements_empty(tmp_path):
    f = tmp_path / "requirements.txt"
    f.write_text("")
    assert _parse_requirements(f) == []


# ── _parse_pyproject ───────────────────────────────────────────────────────────


def test_parse_pyproject_pep621(tmp_path):
    f = tmp_path / "pyproject.toml"
    f.write_text(
        '[project]\ndependencies = [\n  "requests>=2.28",\n  "click>=8.0",\n]\n'
    )
    result = _parse_pyproject(f)
    names = [r[0] for r in result]
    assert "requests" in names
    assert "click" in names


def test_parse_pyproject_poetry(tmp_path):
    f = tmp_path / "pyproject.toml"
    f.write_text(
        "[tool.poetry.dependencies]\npython = \"^3.11\"\nrequests = \"^2.28\"\n"
    )
    result = _parse_pyproject(f)
    names = [r[0] for r in result]
    assert "requests" in names
    assert "python" not in names


def test_parse_pyproject_empty(tmp_path):
    f = tmp_path / "pyproject.toml"
    f.write_text("[project]\nname = 'foo'\n")
    result = _parse_pyproject(f)
    assert result == []


# ── _parse_package_json ────────────────────────────────────────────────────────


def test_parse_package_json_dependencies(tmp_path):
    f = tmp_path / "package.json"
    f.write_text(json.dumps({"dependencies": {"react": "^18.0.0", "axios": "^1.0.0"}}))
    result = _parse_package_json(f)
    assert ("react", "^18.0.0") in result
    assert ("axios", "^1.0.0") in result


def test_parse_package_json_dev_dependencies(tmp_path):
    f = tmp_path / "package.json"
    f.write_text(json.dumps({"devDependencies": {"eslint": "^8.0.0"}}))
    result = _parse_package_json(f)
    assert ("eslint", "^8.0.0") in result


def test_parse_package_json_both_sections(tmp_path):
    f = tmp_path / "package.json"
    f.write_text(
        json.dumps({
            "dependencies": {"react": "^18.0.0"},
            "devDependencies": {"jest": "^29.0.0"},
        })
    )
    result = _parse_package_json(f)
    names = [r[0] for r in result]
    assert "react" in names
    assert "jest" in names


def test_parse_package_json_empty(tmp_path):
    f = tmp_path / "package.json"
    f.write_text(json.dumps({}))
    assert _parse_package_json(f) == []


# ── _parse_go_mod ──────────────────────────────────────────────────────────────


def test_parse_go_mod_block(tmp_path):
    f = tmp_path / "go.mod"
    f.write_text(
        "module example.com/app\n\nrequire (\n"
        "\tgithub.com/gin-gonic/gin v1.9.0\n"
        "\tgithub.com/stretchr/testify v1.8.0\n"
        ")\n"
    )
    result = _parse_go_mod(f)
    assert ("github.com/gin-gonic/gin", "v1.9.0") in result
    assert ("github.com/stretchr/testify", "v1.8.0") in result


def test_parse_go_mod_single_line(tmp_path):
    f = tmp_path / "go.mod"
    f.write_text("module example.com/app\n\nrequire github.com/foo/bar v1.2.3\n")
    result = _parse_go_mod(f)
    assert ("github.com/foo/bar", "v1.2.3") in result


def test_parse_go_mod_ignores_comments(tmp_path):
    f = tmp_path / "go.mod"
    f.write_text(
        "module example.com/app\n\nrequire (\n"
        "\t// indirect\n"
        "\tgithub.com/foo/bar v1.0.0\n"
        ")\n"
    )
    result = _parse_go_mod(f)
    assert ("github.com/foo/bar", "v1.0.0") in result


def test_parse_go_mod_empty(tmp_path):
    f = tmp_path / "go.mod"
    f.write_text("module example.com/app\ngo 1.21\n")
    assert _parse_go_mod(f) == []


# ── _is_outdated ───────────────────────────────────────────────────────────────


def test_is_outdated_not_installed():
    assert _is_outdated("==2.0.0", None) is True


def test_is_outdated_exact_match_ok():
    assert _is_outdated("==2.0.0", "2.0.0") is False


def test_is_outdated_exact_match_fail():
    assert _is_outdated("==2.0.0", "1.9.0") is True


def test_is_outdated_no_spec():
    assert _is_outdated("", "1.0.0") is False
    assert _is_outdated(None, "1.0.0") is False


def test_is_outdated_non_exact_spec():
    # >=, <=, ~= 등은 단순 비교 불가 → False 반환
    assert _is_outdated(">=2.0.0", "1.0.0") is False


# ── run() ──────────────────────────────────────────────────────────────────────


def test_run_no_dep_file(tmp_path):
    result = run(tmp_path)
    assert result["status"] == "error"
    assert "dep_file" in result
    assert result["packages"] == []


def test_run_requirements_txt(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    with patch("actions.deps_check._pip_version", return_value="2.28.0"):
        result = run(tmp_path)
    assert result["status"] == "ok"
    assert result["dep_file"] == "requirements.txt"
    pkgs = {p["name"]: p for p in result["packages"]}
    assert pkgs["requests"]["installed"] == "2.28.0"
    assert pkgs["requests"]["outdated"] is False


def test_run_package_json(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"react": "^18.0.0"}})
    )
    with patch("actions.deps_check._npm_version", return_value=None):
        result = run(tmp_path)
    assert result["status"] == "ok"
    pkgs = {p["name"]: p for p in result["packages"]}
    assert pkgs["react"]["installed"] == "not_installed"
    assert pkgs["react"]["outdated"] is True


def test_run_outdated_package(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests==2.28.0\n")
    with patch("actions.deps_check._pip_version", return_value="2.27.0"):
        result = run(tmp_path)
    pkgs = {p["name"]: p for p in result["packages"]}
    assert pkgs["requests"]["outdated"] is True


def test_run_dep_file_relative_path(tmp_path):
    (tmp_path / "requirements.txt").write_text("click\n")
    with patch("actions.deps_check._pip_version", return_value="8.0.0"):
        result = run(tmp_path)
    assert result["dep_file"] == "requirements.txt"
