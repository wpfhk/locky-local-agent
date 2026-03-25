"""tests/test_runtime_local.py — LocalRuntime 테스트 (4개)"""

import sys
from pathlib import Path

import pytest

from locky.runtime.local import LocalRuntime, RunResult


def test_execute_str_command(tmp_path):
    rt = LocalRuntime(cwd=tmp_path)
    result = rt.execute("echo hello")
    assert result.ok
    assert "hello" in result.stdout


def test_execute_list_command(tmp_path):
    rt = LocalRuntime(cwd=tmp_path)
    result = rt.execute([sys.executable, "-c", "print('world')"])
    assert result.ok
    assert "world" in result.stdout


def test_execute_timeout(tmp_path):
    rt = LocalRuntime(cwd=tmp_path, timeout=1)
    with pytest.raises(Exception):
        rt.execute("sleep 5")


def test_execute_error_command(tmp_path):
    rt = LocalRuntime(cwd=tmp_path)
    result = rt.execute([sys.executable, "-c", "import sys; sys.exit(1)"])
    assert not result.ok
    assert result.returncode == 1


def test_run_result_duration(tmp_path):
    rt = LocalRuntime(cwd=tmp_path)
    result = rt.execute([sys.executable, "-c", "pass"])
    assert result.duration >= 0
