"""tools/editor.py 단위 테스트."""

from __future__ import annotations
from tools.editor import create_backup, diff_markup, read_file_range, replace_in_file


def test_read_file_range_full(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("line1\nline2\nline3\n", encoding="utf-8")
    result = read_file_range(f)
    assert "line1" in result
    assert "line3" in result


def test_read_file_range_partial(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("line1\nline2\nline3\n", encoding="utf-8")
    result = read_file_range(f, start=2, end=2)
    assert "line2" in result
    assert "line1" not in result
    assert "line3" not in result


def test_read_file_range_max_chars(tmp_path):
    f = tmp_path / "big.txt"
    f.write_text("x" * 10000, encoding="utf-8")
    result = read_file_range(f, max_chars=100)
    assert len(result) <= 140  # truncation marker adds ~30 chars
    assert "truncated" in result


def test_read_file_range_missing_file(tmp_path):
    result = read_file_range(tmp_path / "nonexistent.txt")
    assert "read error" in result


def test_create_backup(tmp_path):
    f = tmp_path / "original.py"
    f.write_text("content", encoding="utf-8")
    bak = create_backup(f)
    assert bak.is_file()
    assert bak.suffix == ".bak"
    assert bak.read_text(encoding="utf-8") == "content"


def test_replace_in_file_success(tmp_path):
    f = tmp_path / "ver.py"
    f.write_text('version = "0.5.0"\n', encoding="utf-8")
    ok, diff = replace_in_file(f, '"0.5.0"', '"0.6.0"', backup=False)
    assert ok is True
    assert f.read_text(encoding="utf-8") == 'version = "0.6.0"\n'


def test_replace_in_file_backup_created(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("hello world", encoding="utf-8")
    ok, _ = replace_in_file(f, "hello", "hi", backup=True)
    assert ok is True
    assert (tmp_path / "code.py.bak").is_file()
    assert (tmp_path / "code.py.bak").read_text(encoding="utf-8") == "hello world"


def test_replace_in_file_not_found(tmp_path):
    f = tmp_path / "no.py"
    f.write_text("something", encoding="utf-8")
    ok, diff = replace_in_file(f, "missing", "x", backup=False)
    assert ok is False
    assert diff == ""
    assert f.read_text(encoding="utf-8") == "something"  # unchanged


def test_replace_in_file_diff_shows_changes(tmp_path):
    f = tmp_path / "d.py"
    f.write_text("version = 1\n", encoding="utf-8")
    ok, diff = replace_in_file(f, "version = 1", "version = 2", backup=False)
    assert ok is True
    assert "-version = 1" in diff
    assert "+version = 2" in diff


def test_diff_markup_colors(tmp_path):
    diff = "+new line\n-old line\n@@hunk@@\n---file\n+++file\n context"
    markup = diff_markup(diff)
    assert "[green]+new line[/green]" in markup
    assert "[red]-old line[/red]" in markup
    assert "[cyan]@@hunk@@[/cyan]" in markup
    assert "[dim]---file[/dim]" in markup
