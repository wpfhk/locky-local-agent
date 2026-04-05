"""tools/indexer.py -- 프로젝트 코드 맵 생성기. AST 기반 시그니처 추출."""

from __future__ import annotations

import ast
from pathlib import Path

_IGNORE_DIRS = frozenset(
    {
        ".git",
        "__pycache__",
        ".omc",
        ".afd",
        ".claude",
        ".cursor",
        "node_modules",
        ".venv",
        "venv",
        ".pytest_cache",
        "dist",
        "build",
        ".tox",
        "tests",
        "archive",
    }
)

_IGNORE_FILES = frozenset(
    {
        ".env",
        ".env.local",
        ".env.production",
        "secrets.json",
        "credentials.json",
    }
)

_INDEX_EXTS = frozenset({".py", ".md", ".toml", ".yaml", ".yml", ".json", ".sh"})


def build_code_map(root: Path) -> str:
    """프로젝트의 코드 맵을 마크다운으로 생성합니다."""
    root = Path(root).resolve()
    all_files = sorted(_walk_files(root))

    if not all_files:
        return ""

    parts = [f"# Code Map: {root.name}", ""]

    # File tree
    parts.append("## Files")
    for f in all_files:
        parts.append(f"- {f.relative_to(root).as_posix()}")
    parts.append("")

    # Python signatures
    py_files = [f for f in all_files if f.suffix == ".py"]
    for path in py_files:
        sigs = _extract_python_signatures(path)
        if sigs:
            rel = path.relative_to(root).as_posix()
            parts.append(f"## {rel}")
            parts.extend(f"- {s}" for s in sigs)
            parts.append("")

    return "\n".join(parts)


def save_repo_map(root: Path) -> Path:
    """코드 맵을 .omc/repo_map.md에 저장합니다."""
    root = Path(root).resolve()
    omc_dir = root / ".omc"
    omc_dir.mkdir(exist_ok=True)

    output = omc_dir / "repo_map.md"
    content = build_code_map(root)
    output.write_text(content, encoding="utf-8")
    return output


def _walk_files(root: Path):
    """인덱싱 대상 파일을 순회합니다."""
    try:
        entries = sorted(root.iterdir())
    except PermissionError:
        return

    for item in entries:
        if item.is_dir():
            if item.name in _IGNORE_DIRS or item.name.startswith("."):
                continue
            yield from _walk_files(item)
        elif item.is_file():
            if item.name in _IGNORE_FILES or item.name.startswith("."):
                continue
            if item.suffix in _INDEX_EXTS:
                yield item


def _extract_python_signatures(path: Path) -> list[str]:
    """파이썬 파일에서 클래스/함수 시그니처를 추출합니다."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception:
        return []

    sigs: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sigs.append(_format_function(node))
        elif isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node)
            line = f"class {node.name}"
            if doc:
                line += f" -- {doc.split(chr(10))[0].strip()}"
            sigs.append(line)
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not item.name.startswith("_") or item.name == "__init__":
                        sigs.append(_format_function(item, indent=True))

    return sigs


def _format_function(node: ast.FunctionDef, indent: bool = False) -> str:
    """함수 노드를 시그니처 문자열로 포맷합니다."""
    args = []
    for arg in node.args.args:
        if arg.arg == "self":
            continue
        name = arg.arg
        if arg.annotation:
            name += f": {ast.unparse(arg.annotation)}"
        args.append(name)

    prefix = "  " if indent else ""
    sig = f"{prefix}def {node.name}({', '.join(args)})"

    if node.returns:
        sig += f" -> {ast.unparse(node.returns)}"

    doc = ast.get_docstring(node)
    if doc:
        first_line = doc.split("\n")[0].strip()
        if first_line:
            sig += f" -- {first_line}"

    return sig


if __name__ == "__main__":
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    out = save_repo_map(target)
    content = out.read_text(encoding="utf-8")
    print(content)
    print(f"\nSaved to: {out}")
