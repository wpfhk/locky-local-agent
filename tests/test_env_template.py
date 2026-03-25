"""tests/test_env_template.py — actions/env_template.py 테스트 (12개)"""
import pytest
from pathlib import Path
from actions.env_template import run


@pytest.fixture
def root(tmp_path):
    return tmp_path


# --- .env 파일 있을 때 ---

def test_run_with_env_file(root):
    (root / ".env").write_text("DB_URL=postgres://localhost/db\nSECRET_KEY=abc123\n")
    result = run(root)
    assert result["status"] == "ok"
    assert "DB_URL" in result["keys"]
    assert "SECRET_KEY" in result["keys"]


def test_run_env_file_creates_example(root):
    (root / ".env").write_text("API_KEY=secret\n")
    run(root)
    example = root / ".env.example"
    assert example.exists()
    content = example.read_text()
    assert "API_KEY=" in content
    assert "secret" not in content


def test_run_env_file_strips_values(root):
    (root / ".env").write_text("TOKEN=my_token_value\n")
    run(root)
    content = (root / ".env.example").read_text()
    assert "TOKEN=" in content
    assert "my_token_value" not in content


def test_run_env_file_preserves_comments(root):
    (root / ".env").write_text("# DB 설정\nDB_HOST=localhost\n")
    run(root)
    content = (root / ".env.example").read_text()
    assert "# DB 설정" in content


def test_run_custom_output_filename(root):
    (root / ".env").write_text("X=1\n")
    result = run(root, output="custom.env.example")
    assert (root / "custom.env.example").exists()


# --- .env 파일 없을 때 ---

def test_run_no_env_no_source_keys(root):
    (root / "app.py").write_text("x = 1\n")
    result = run(root)
    assert result["status"] == "no_env_file"
    assert result["keys"] == []


def test_run_no_env_collects_from_source(root):
    (root / "app.py").write_text(
        'import os\nos.environ.get("DATABASE_URL")\nos.getenv("SECRET_KEY")\n'
    )
    result = run(root)
    assert result["status"] == "ok"
    assert "DATABASE_URL" in result["keys"]
    assert "SECRET_KEY" in result["keys"]


def test_run_no_env_creates_example_from_source(root):
    (root / "app.py").write_text('os.environ.get("MY_VAR")\n')
    run(root)
    example = root / ".env.example"
    assert example.exists()
    content = example.read_text()
    assert "MY_VAR=" in content


def test_run_deduplicates_keys(root):
    (root / "a.py").write_text('os.environ.get("KEY")\n')
    (root / "b.py").write_text('os.getenv("KEY")\n')
    result = run(root)
    assert result["keys"].count("KEY") == 1


def test_run_includes_header_comment(root):
    (root / ".env").write_text("X=1\n")
    run(root)
    content = (root / ".env.example").read_text()
    assert ".env.example" in content


def test_run_output_file_path_returned(root):
    (root / ".env").write_text("X=1\n")
    result = run(root)
    assert ".env.example" in result["output_file"]


def test_run_env_file_empty_lines_preserved(root):
    (root / ".env").write_text("A=1\n\nB=2\n")
    result = run(root)
    assert "A" in result["keys"]
    assert "B" in result["keys"]
