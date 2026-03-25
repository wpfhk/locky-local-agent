"""tests/test_cli_commands.py — locky_cli/main.py 주요 명령 커버리지 (20개)"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from locky_cli.main import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def workspace(tmp_path):
    return tmp_path


# --- commit ---


def test_commit_dry_run(runner, workspace):
    with patch(
        "actions.commit.run", return_value={"status": "ok", "message": "feat: x"}
    ):
        result = runner.invoke(
            cli, ["commit", "--dry-run", "--workspace", str(workspace)]
        )
    assert result.exit_code == 0


def test_commit_default(runner, workspace):
    with patch(
        "actions.commit.run", return_value={"status": "ok", "message": "fix: y"}
    ):
        result = runner.invoke(cli, ["commit", "--workspace", str(workspace)])
    assert result.exit_code == 0


def test_commit_nothing_to_commit(runner, workspace):
    with patch("actions.commit.run", return_value={"status": "nothing_to_commit"}):
        result = runner.invoke(cli, ["commit", "--workspace", str(workspace)])
    assert result.exit_code == 0
    assert "nothing_to_commit" in result.output


# --- format ---


def test_format_cmd(runner, workspace):
    with patch(
        "actions.format_code.run",
        return_value={
            "status": "ok",
            "language": "python",
            "black": {"status": "ok", "output": ""},
            "isort": {"status": "ok", "output": ""},
        },
    ):
        result = runner.invoke(cli, ["format", "--workspace", str(workspace)])
    assert result.exit_code == 0


def test_format_check_only(runner, workspace):
    with patch(
        "actions.format_code.run",
        return_value={
            "status": "ok",
            "language": "python",
        },
    ) as mock:
        runner.invoke(cli, ["format", "--check", "--workspace", str(workspace)])
    _, kwargs = mock.call_args
    assert kwargs.get("check_only") is True


# --- test ---


def test_test_cmd_pass(runner, workspace):
    with patch(
        "actions.test_runner.run",
        return_value={
            "status": "pass",
            "passed": 5,
            "failed": 0,
            "errors": 0,
            "duration": 1.0,
            "output": "5 passed",
        },
    ):
        result = runner.invoke(cli, ["test", "--workspace", str(workspace)])
    assert result.exit_code == 0


def test_test_cmd_fail(runner, workspace):
    with patch(
        "actions.test_runner.run",
        return_value={
            "status": "fail",
            "passed": 1,
            "failed": 2,
            "errors": 0,
            "duration": 0.5,
            "output": "1 passed, 2 failed",
        },
    ):
        result = runner.invoke(cli, ["test", "--workspace", str(workspace)])
    assert result.exit_code == 0  # CLI 자체는 0 반환


def test_test_cmd_verbose(runner, workspace):
    with patch(
        "actions.test_runner.run",
        return_value={
            "status": "pass",
            "passed": 1,
            "failed": 0,
            "errors": 0,
            "duration": 0.1,
            "output": "",
        },
    ) as mock:
        runner.invoke(cli, ["test", "-v", "--workspace", str(workspace)])
    _, kwargs = mock.call_args
    assert kwargs.get("verbose") is True


# --- todo ---


def test_todo_cmd(runner, workspace):
    with patch(
        "actions.todo_collector.run",
        return_value={
            "status": "ok",
            "total": 2,
            "items": [
                {"tag": "TODO", "file": "app.py", "line": 1, "text": "fix"},
                {"tag": "FIXME", "file": "app.py", "line": 2, "text": "broken"},
            ],
        },
    ):
        result = runner.invoke(cli, ["todo", "--workspace", str(workspace)])
    assert result.exit_code == 0


def test_todo_cmd_no_items(runner, workspace):
    with patch(
        "actions.todo_collector.run",
        return_value={"status": "ok", "total": 0, "items": []},
    ):
        result = runner.invoke(cli, ["todo", "--workspace", str(workspace)])
    assert result.exit_code == 0


# --- scan ---


def test_scan_cmd_clean(runner, workspace):
    with patch(
        "actions.security_scan.run",
        return_value={
            "status": "clean",
            "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "issues": [],
        },
    ):
        result = runner.invoke(cli, ["scan", "--workspace", str(workspace)])
    assert result.exit_code == 0


def test_scan_cmd_issues(runner, workspace):
    with patch(
        "actions.security_scan.run",
        return_value={
            "status": "issues_found",
            "summary": {"critical": 1, "high": 0, "medium": 0, "low": 0},
            "issues": [
                {
                    "severity": "critical",
                    "file": "app.py",
                    "line": 1,
                    "description": "hardcoded secret",
                    "category": "hardcoded_secret",
                }
            ],
        },
    ):
        result = runner.invoke(cli, ["scan", "--workspace", str(workspace)])
    assert result.exit_code == 0


def test_scan_cmd_severity_filter(runner, workspace):
    with patch(
        "actions.security_scan.run",
        return_value={
            "status": "clean",
            "summary": {},
            "issues": [],
        },
    ) as mock:
        runner.invoke(
            cli, ["scan", "--severity", "high", "--workspace", str(workspace)]
        )
    _, kwargs = mock.call_args
    assert kwargs.get("severity_filter") == "high"


# --- clean ---


def test_clean_dry_run(runner, workspace):
    with patch(
        "actions.cleanup.run",
        return_value={
            "status": "ok",
            "removed": ["__pycache__"],
            "total_size_bytes": 100,
            "dry_run": True,
        },
    ):
        result = runner.invoke(cli, ["clean", "--workspace", str(workspace)])
    assert result.exit_code == 0
    assert "dry-run" in result.output


def test_clean_force(runner, workspace):
    with patch(
        "actions.cleanup.run",
        return_value={
            "status": "ok",
            "removed": ["__pycache__"],
            "total_size_bytes": 100,
            "dry_run": False,
        },
    ) as mock:
        runner.invoke(cli, ["clean", "--force", "--workspace", str(workspace)])
    _, kwargs = mock.call_args
    assert kwargs.get("dry_run") is False


# --- deps ---


def test_deps_cmd(runner, workspace):
    with patch(
        "actions.deps_check.run",
        return_value={
            "status": "ok",
            "dependencies": [],
            "outdated": [],
        },
    ):
        result = runner.invoke(cli, ["deps", "--workspace", str(workspace)])
    assert result.exit_code == 0


# --- env ---


def test_env_cmd(runner, workspace):
    with patch(
        "actions.env_template.run",
        return_value={
            "status": "ok",
            "output_file": ".env.example",
            "keys": ["DB_URL"],
        },
    ):
        result = runner.invoke(cli, ["env", "--workspace", str(workspace)])
    assert result.exit_code == 0


# --- help / version ---


def test_help_flag(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "locky" in result.output.lower()


def test_commands_registered():
    expected = {
        "commit",
        "format",
        "test",
        "todo",
        "scan",
        "clean",
        "deps",
        "env",
        "ask",
        "edit",
        "agent",
    }
    assert expected.issubset(set(cli.commands.keys()))
