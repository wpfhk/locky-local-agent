"""tools/indexer.py 단위 테스트."""

from __future__ import annotations

from pathlib import Path

from tools.indexer import build_code_map, save_repo_map


def test_build_code_map_empty(tmp_path: Path):
    result = build_code_map(tmp_path)
    assert result == ""


def test_build_code_map_extracts_functions(tmp_path: Path):
    (tmp_path / "example.py").write_text(
        'def hello(name: str) -> str:\n    """Say hello."""\n    return f"hi {name}"\n',
        encoding="utf-8",
    )
    result = build_code_map(tmp_path)
    assert "def hello(name: str) -> str" in result
    assert "Say hello." in result


def test_build_code_map_extracts_classes(tmp_path: Path):
    (tmp_path / "models.py").write_text(
        'class Dog:\n    """A good dog."""\n    def bark(self) -> str:\n        return "woof"\n',
        encoding="utf-8",
    )
    result = build_code_map(tmp_path)
    assert "class Dog" in result
    assert "def bark()" in result


def test_build_code_map_skips_private_methods(tmp_path: Path):
    (tmp_path / "secret.py").write_text(
        "class Foo:\n    def _private(self): pass\n    def public(self): pass\n",
        encoding="utf-8",
    )
    result = build_code_map(tmp_path)
    assert "_private" not in result
    assert "public" in result


def test_build_code_map_includes_init(tmp_path: Path):
    (tmp_path / "client.py").write_text(
        "class Client:\n    def __init__(self, url: str): pass\n",
        encoding="utf-8",
    )
    result = build_code_map(tmp_path)
    assert "__init__(url: str)" in result


def test_build_code_map_ignores_pycache(tmp_path: Path):
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "cached.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "real.py").write_text("def real(): pass\n", encoding="utf-8")
    result = build_code_map(tmp_path)
    assert "cached" not in result
    assert "real" in result


def test_build_code_map_ignores_env(tmp_path: Path):
    (tmp_path / ".env").write_text("SECRET=abc\n")
    result = build_code_map(tmp_path)
    assert ".env" not in result


def test_build_code_map_ignores_tests(tmp_path: Path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_foo.py").write_text("def test_foo(): pass\n", encoding="utf-8")
    result = build_code_map(tmp_path)
    assert "test_foo" not in result


def test_build_code_map_file_tree(tmp_path: Path):
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Hi\n", encoding="utf-8")
    result = build_code_map(tmp_path)
    assert "app.py" in result
    assert "README.md" in result


def test_save_repo_map_creates_file(tmp_path: Path):
    (tmp_path / "main.py").write_text("def main(): pass\n", encoding="utf-8")
    output = save_repo_map(tmp_path)
    assert output.exists()
    assert output.name == "repo_map.md"
    assert "main" in output.read_text(encoding="utf-8")
