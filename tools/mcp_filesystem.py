import re
from pathlib import Path
from typing import List

from locky_cli.fs_context import get_filesystem_root


def _safe_path(path: str) -> Path:
    """
    경로 순회 공격을 방지하여 MCP 파일시스템 루트 내의 안전한 절대 경로를 반환합니다.

    Args:
        path: 상대 또는 절대 경로 문자열

    Returns:
        검증된 절대 Path 객체

    Raises:
        ValueError: 경로가 루트 밖을 벗어날 경우
    """
    root = get_filesystem_root()
    target = (root / path).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError(
            f"경로 순회 감지: '{path}'는 MCP_FILESYSTEM_ROOT('{root}') 밖을 벗어납니다."
        )
    return target


def read_file(path: str) -> str:
    """
    파일 내용을 읽어 문자열로 반환합니다.

    Args:
        path: MCP_FILESYSTEM_ROOT 기준 상대 경로

    Returns:
        파일 내용 문자열
    """
    target = _safe_path(path)
    return target.read_text(encoding="utf-8")


def write_file(path: str, content: str) -> bool:
    """
    파일에 내용을 씁니다. 필요한 상위 디렉토리를 자동 생성합니다.

    Args:
        path: MCP_FILESYSTEM_ROOT 기준 상대 경로
        content: 기록할 문자열 내용

    Returns:
        성공 시 True
    """
    target = _safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return True


def list_directory(path: str) -> List[str]:
    """
    디렉토리 내 항목 목록을 반환합니다.

    Args:
        path: MCP_FILESYSTEM_ROOT 기준 상대 경로

    Returns:
        항목 이름 문자열 목록 (디렉토리는 '/' 접미사 포함)
    """
    target = _safe_path(path)
    entries: List[str] = []
    for entry in sorted(target.iterdir()):
        name = entry.name + ("/" if entry.is_dir() else "")
        entries.append(name)
    return entries


def get_file_tree(root: str = ".", max_depth: int = 4) -> str:
    """
    지정한 루트 경로부터 파일 트리를 문자열로 반환합니다.

    Args:
        root: MCP_FILESYSTEM_ROOT 기준 시작 상대 경로
        max_depth: 탐색 최대 깊이

    Returns:
        tree 형식의 문자열
    """
    target = _safe_path(root)
    lines: List[str] = [target.name + "/"]

    def _walk(directory: Path, prefix: str, depth: int) -> None:
        if depth > max_depth:
            return
        entries = sorted(directory.iterdir(), key=lambda e: (e.is_file(), e.name))
        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            lines.append(
                prefix + connector + entry.name + ("/" if entry.is_dir() else "")
            )
            if entry.is_dir():
                extension = "    " if is_last else "│   "
                _walk(entry, prefix + extension, depth + 1)

    _walk(target, "", 1)
    return "\n".join(lines)


def search_in_files(pattern: str, root: str = ".") -> List[dict]:
    """
    지정한 루트 경로 내에서 정규식 패턴으로 파일 내용을 검색합니다.

    Args:
        pattern: 검색할 정규식 패턴
        root: MCP_FILESYSTEM_ROOT 기준 시작 상대 경로

    Returns:
        매칭 결과 딕셔너리 목록.
        각 항목: {"file": str, "line": int, "content": str}
    """
    target = _safe_path(root)
    regex = re.compile(pattern)
    results: List[dict] = []

    for filepath in sorted(target.rglob("*")):
        if not filepath.is_file():
            continue
        # 바이너리 파일 건너뜀
        try:
            text = filepath.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                rel_path = str(filepath.relative_to(get_filesystem_root()))
                results.append(
                    {
                        "file": rel_path,
                        "line": line_number,
                        "content": line,
                    }
                )
    return results
