"""tests/test_test_runner.py — actions/test_runner.py 테스트 (10개)"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from actions.test_runner import _parse_pytest_output, run


@pytest.fixture
def root(tmp_path):
    return tmp_path


# --- _parse_pytest_output() ---


def test_parse_passed_only():
    out = "5 passed in 1.23s"
    p, f, e = _parse_pytest_output(out)
    assert p == 5
    assert f == 0
    assert e == 0


def test_parse_passed_and_failed():
    out = "3 passed, 2 failed in 0.5s"
    p, f, e = _parse_pytest_output(out)
    assert p == 3
    assert f == 2


def test_parse_errors():
    out = "1 passed, 1 error in 0.1s"
    p, f, e = _parse_pytest_output(out)
    assert e == 1


def test_parse_empty_output():
    p, f, e = _parse_pytest_output("")
    assert p == 0 and f == 0 and e == 0


# --- run() ---


def test_run_pytest_not_installed(root):
    with patch("shutil.which", return_value=None):
        result = run(root)
    assert result["status"] == "error"
    assert "pytest" in result["output"]


def test_run_pass(root):
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = "3 passed in 0.5s"
    mock.stderr = ""
    with (
        patch("subprocess.run", return_value=mock),
        patch("shutil.which", return_value="/usr/bin/pytest"),
    ):
        result = run(root)
    assert result["status"] == "pass"
    assert result["passed"] == 3


def test_run_fail(root):
    mock = MagicMock()
    mock.returncode = 1
    mock.stdout = "1 passed, 2 failed in 1s"
    mock.stderr = ""
    with (
        patch("subprocess.run", return_value=mock),
        patch("shutil.which", return_value="/usr/bin/pytest"),
    ):
        result = run(root)
    assert result["status"] == "fail"
    assert result["failed"] == 2


def test_run_verbose_flag(root):
    mock = MagicMock(returncode=0, stdout="1 passed in 0.1s", stderr="")
    with (
        patch("subprocess.run", return_value=mock) as mock_run,
        patch("shutil.which", return_value="/usr/bin/pytest"),
    ):
        run(root, verbose=True)
    cmd = mock_run.call_args[0][0]
    assert "-v" in cmd


def test_run_specific_path(root):
    mock = MagicMock(returncode=0, stdout="1 passed in 0.1s", stderr="")
    with (
        patch("subprocess.run", return_value=mock) as mock_run,
        patch("shutil.which", return_value="/usr/bin/pytest"),
    ):
        run(root, path="tests/test_foo.py")
    cmd = mock_run.call_args[0][0]
    assert "tests/test_foo.py" in cmd


def test_run_timeout(root):
    import subprocess

    with (
        patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pytest", 120)),
        patch("shutil.which", return_value="/usr/bin/pytest"),
    ):
        result = run(root)
    assert result["status"] == "error"
    assert "타임아웃" in result["output"]
