"""tests/test_todo_collector.py — actions/todo_collector.py 테스트 (12개)"""

from pathlib import Path

import pytest

from actions.todo_collector import run


@pytest.fixture
def root(tmp_path):
    return tmp_path


def _write(root, name, content):
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


# --- run() ---


def test_run_finds_todo(root):
    _write(root, "app.py", "# TODO: fix this\nx = 1\n")
    result = run(root)
    assert result["status"] == "ok"
    assert result["total"] == 1
    assert result["items"][0]["tag"] == "TODO"
    assert result["items"][0]["text"] == "fix this"


def test_run_finds_fixme(root):
    _write(root, "app.py", "# FIXME: broken logic\n")
    result = run(root)
    assert result["total"] == 1
    assert result["items"][0]["tag"] == "FIXME"


def test_run_finds_multiple_tags(root):
    _write(root, "app.py", "# TODO: a\n# FIXME: b\n# HACK: c\n# XXX: d\n")
    result = run(root)
    assert result["total"] == 4
    tags = {item["tag"] for item in result["items"]}
    assert tags == {"TODO", "FIXME", "HACK", "XXX"}


def test_run_no_todos(root):
    _write(root, "app.py", "x = 1\ny = 2\n")
    result = run(root)
    assert result["total"] == 0
    assert result["items"] == []


def test_run_item_has_required_fields(root):
    _write(root, "app.py", "# TODO: check this\n")
    result = run(root)
    item = result["items"][0]
    assert "file" in item
    assert "line" in item
    assert "tag" in item
    assert "text" in item


def test_run_case_insensitive(root):
    _write(root, "app.py", "# todo: lowercase\n")
    result = run(root)
    assert result["total"] == 1
    assert result["items"][0]["tag"] == "TODO"


def test_run_excludes_venv(root):
    _write(root, ".venv/lib/x.py", "# TODO: ignore me\n")
    _write(root, "app.py", "x = 1\n")
    result = run(root)
    assert result["total"] == 0


def test_run_md_files(root):
    _write(root, "README.md", "<!-- # TODO: document -->\n# TODO: add docs\n")
    result = run(root)
    assert result["total"] >= 1


def test_run_output_file(root):
    _write(root, "app.py", "# TODO: write output\n")
    out = str(root / "todos.md")
    result = run(root, output_file=out)
    assert Path(out).exists()
    content = Path(out).read_text()
    assert "TODO" in content


def test_run_output_file_markdown_format(root):
    _write(root, "app.py", "# TODO: check format\n")
    out = str(root / "out.md")
    run(root, output_file=out)
    content = Path(out).read_text()
    assert "# TODO / FIXME 목록" in content
    assert "|" in content  # 표 형식


def test_run_line_number_correct(root):
    _write(root, "app.py", "x = 1\n# TODO: on line 2\n")
    result = run(root)
    assert result["items"][0]["line"] == 2


def test_run_multiple_files(root):
    _write(root, "a.py", "# TODO: a\n")
    _write(root, "b.py", "# FIXME: b\n")
    result = run(root)
    assert result["total"] == 2
    files = {item["file"] for item in result["items"]}
    assert len(files) == 2
