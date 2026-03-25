"""tests/test_security_scan.py — actions/security_scan.py 테스트 (15개)"""
import pytest
from pathlib import Path
from actions.security_scan import run, _is_excluded, _scan_patterns, _get_recommendation


@pytest.fixture
def scan_root(tmp_path):
    return tmp_path


def _write(root, filename, content):
    p = root / filename
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


# --- run() ---

def test_run_clean_directory(scan_root):
    _write(scan_root, "safe.py", "x = 1\nprint(x)\n")
    result = run(scan_root)
    assert result["status"] == "clean"
    assert result["issues"] == []
    assert result["summary"]["critical"] == 0


def test_run_detects_hardcoded_password(scan_root):
    _write(scan_root, "config.py", 'password = "secret123"\n')
    result = run(scan_root)
    assert result["status"] == "issues_found"
    assert any(i["category"] == "hardcoded_secret" for i in result["issues"])


def test_run_detects_eval(scan_root):
    _write(scan_root, "risky.py", "eval(user_input)\n")
    result = run(scan_root)
    assert any(i["category"] == "code_injection" for i in result["issues"])


def test_run_detects_shell_true(scan_root):
    _write(scan_root, "cmd.py", "subprocess.run(cmd, shell=True)\n")
    result = run(scan_root)
    assert any(i["category"] == "command_injection" for i in result["issues"])


def test_run_severity_filter_critical_only(scan_root):
    _write(scan_root, "mixed.py",
           'password = "abc"\nhttp://external.com/api\n')
    result = run(scan_root, severity_filter="critical")
    severities = {i["severity"] for i in result["issues"]}
    assert severities <= {"critical"}


def test_run_severity_filter_high_includes_critical(scan_root):
    _write(scan_root, "mixed.py",
           'password = "abc"\neval(x)\n')
    result = run(scan_root, severity_filter="high")
    severities = {i["severity"] for i in result["issues"]}
    assert severities <= {"critical", "high", "medium"}  # test file downgrade 포함


def test_run_summary_counts(scan_root):
    _write(scan_root, "a.py", 'password = "abc"\neval(x)\n')
    result = run(scan_root)
    assert sum(result["summary"].values()) == len(result["issues"])


def test_run_test_file_downgrade(scan_root):
    """테스트 파일의 critical/high 이슈는 medium으로 다운그레이드."""
    _write(scan_root, "tests/test_foo.py", 'password = "secret"\n')
    result = run(scan_root)
    for issue in result["issues"]:
        if "test_foo" in issue["file"]:
            assert issue["severity"] == "medium"


def test_run_excludes_venv(scan_root):
    _write(scan_root, ".venv/lib/bad.py", 'password = "oops"\n')
    _write(scan_root, "src.py", "x = 1\n")
    result = run(scan_root)
    for issue in result["issues"]:
        assert ".venv" not in issue["file"]


def test_run_returns_issue_fields(scan_root):
    _write(scan_root, "x.py", 'api_key = "abc123"\n')
    result = run(scan_root)
    assert result["issues"]
    issue = result["issues"][0]
    for key in ("severity", "category", "file", "line", "code_snippet", "description", "recommendation"):
        assert key in issue


# --- _is_excluded() ---

def test_is_excluded_venv(tmp_path):
    venv_file = tmp_path / ".venv" / "lib" / "foo.py"
    venv_file.parent.mkdir(parents=True)
    venv_file.touch()
    assert _is_excluded(venv_file, tmp_path) is True


def test_is_excluded_normal_file(tmp_path):
    f = tmp_path / "src" / "app.py"
    f.parent.mkdir()
    f.touch()
    assert _is_excluded(f, tmp_path) is False


# --- _get_recommendation() ---

def test_get_recommendation_known_category():
    rec = _get_recommendation("hardcoded_secret")
    assert "환경변수" in rec


def test_get_recommendation_unknown_category():
    rec = _get_recommendation("unknown_category")
    assert rec  # 기본 메시지 반환


def test_scan_patterns_empty_list():
    assert _scan_patterns([]) == []
