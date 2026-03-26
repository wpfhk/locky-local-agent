"""tools/repo_map.py -- Code repository structure map builder (v3.0.0).

git ls-files + AST parsing으로 코드베이스 구조를 인덱싱합니다.
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


class RepoMap:
    """코드베이스 구조 맵 생성기.

    Python 파일은 ``ast`` 모듈로 정밀 파싱하고,
    JS/TS 등은 정규식 기반으로 함수/클래스/import를 추출합니다.
    """

    CACHE_VERSION = 1

    # 파싱 지원 확장자
    _PYTHON_EXTS = {".py"}
    _JS_TS_EXTS = {".js", ".ts", ".jsx", ".tsx"}
    _SUPPORTED_EXTS = _PYTHON_EXTS | _JS_TS_EXTS

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.cache_path = self.root / ".locky" / "repo-map.json"

    def build(self) -> dict:
        """전체 코드베이스 스캔 -> 구조 맵 생성.

        Returns:
            {"version": 1, "git_hash": "...", "generated_at": "...", "files": {...}}
        """
        git_hash = self._get_git_hash()
        files = self._get_tracked_files()

        file_map: dict[str, dict] = {}
        for filepath in files:
            ext = Path(filepath).suffix
            if ext not in self._SUPPORTED_EXTS:
                continue
            full_path = self.root / filepath
            if not full_path.exists():
                continue
            try:
                if ext in self._PYTHON_EXTS:
                    file_map[filepath] = self._parse_python(full_path)
                elif ext in self._JS_TS_EXTS:
                    file_map[filepath] = self._parse_generic(full_path)
            except Exception:
                # 파싱 실패 시 해당 파일 건너뜀
                file_map[filepath] = {"functions": [], "classes": [], "imports": []}

        data = {
            "version": self.CACHE_VERSION,
            "git_hash": git_hash,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "files": file_map,
        }
        self._save_cache(data)
        return data

    def get_context(self, query: str, max_tokens: int = 4000) -> str:
        """쿼리 관련 파일/함수만 선택하여 컨텍스트 문자열 반환.

        간단한 문자열 매칭으로 관련 항목을 점수화합니다.
        """
        data = self._load_cache()
        if data is None:
            data = self.build()

        query_lower = query.lower()
        query_terms = set(query_lower.split())
        scored: list[tuple[float, str, dict]] = []

        for filepath, info in data.get("files", {}).items():
            score = 0.0
            filepath_lower = filepath.lower()

            # 파일 경로 매칭
            for term in query_terms:
                if term in filepath_lower:
                    score += 2.0

            # 함수명 매칭
            for func in info.get("functions", []):
                for term in query_terms:
                    if term in func.lower():
                        score += 3.0

            # 클래스명 매칭
            for cls in info.get("classes", []):
                for term in query_terms:
                    if term in cls.lower():
                        score += 3.0

            if score > 0:
                scored.append((score, filepath, info))

        # 점수 내림차순 정렬
        scored.sort(key=lambda x: x[0], reverse=True)

        # 토큰 제한 내에서 컨텍스트 생성 (대략 4자 = 1토큰)
        lines: list[str] = []
        char_budget = max_tokens * 4
        used = 0

        for _score, filepath, info in scored:
            entry = f"## {filepath}\n"
            if info.get("classes"):
                entry += f"  classes: {', '.join(info['classes'])}\n"
            if info.get("functions"):
                entry += f"  functions: {', '.join(info['functions'])}\n"
            if info.get("imports"):
                entry += f"  imports: {', '.join(info['imports'][:10])}\n"
            entry += "\n"

            if used + len(entry) > char_budget:
                break
            lines.append(entry)
            used += len(entry)

        if not lines:
            return f"(쿼리 '{query}'에 해당하는 항목이 없습니다)"

        return "# Repo Map Context\n\n" + "".join(lines)

    def update_incremental(self, changed_files: list[str] | None = None) -> dict:
        """변경된 파일만 재파싱.

        Args:
            changed_files: 변경 파일 목록. None이면 git diff로 감지.

        Returns:
            업데이트된 전체 맵.
        """
        data = self._load_cache()
        if data is None:
            return self.build()

        if changed_files is None:
            changed_files = self._get_changed_files()

        file_map = data.get("files", {})

        for filepath in changed_files:
            ext = Path(filepath).suffix
            if ext not in self._SUPPORTED_EXTS:
                continue
            full_path = self.root / filepath
            if not full_path.exists():
                # 파일 삭제됨
                file_map.pop(filepath, None)
                continue
            try:
                if ext in self._PYTHON_EXTS:
                    file_map[filepath] = self._parse_python(full_path)
                elif ext in self._JS_TS_EXTS:
                    file_map[filepath] = self._parse_generic(full_path)
            except Exception:
                file_map[filepath] = {"functions": [], "classes": [], "imports": []}

        data["git_hash"] = self._get_git_hash()
        data["generated_at"] = datetime.now(timezone.utc).isoformat()
        data["files"] = file_map
        self._save_cache(data)
        return data

    # -- Cache management --------------------------------------------------

    def _load_cache(self) -> dict | None:
        """캐시 로드. git hash 불일치 시 None."""
        if not self.cache_path.exists():
            return None
        try:
            raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if raw.get("version") != self.CACHE_VERSION:
                return None
            if raw.get("git_hash") != self._get_git_hash():
                return None
            return raw
        except Exception:
            return None

    def _save_cache(self, data: dict) -> None:
        """캐시 저장."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # -- Git helpers -------------------------------------------------------

    def _get_git_hash(self) -> str:
        """현재 HEAD commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return ""

    def _get_tracked_files(self) -> list[str]:
        """git ls-files로 추적 파일 목록."""
        try:
            result = subprocess.run(
                ["git", "ls-files"],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return []
            return [f for f in result.stdout.strip().splitlines() if f]
        except Exception:
            return []

    def _get_changed_files(self) -> list[str]:
        """git diff로 변경 파일 감지 (staged + unstaged)."""
        files: set[str] = set()
        for cmd in (
            ["git", "diff", "--name-only"],
            ["git", "diff", "--cached", "--name-only"],
        ):
            try:
                result = subprocess.run(
                    cmd,
                    cwd=str(self.root),
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    files.update(f for f in result.stdout.strip().splitlines() if f)
            except Exception:
                pass
        return list(files)

    # -- Parsers -----------------------------------------------------------

    def _parse_python(self, filepath: Path) -> dict:
        """Python AST로 함수/클래스/import 추출."""
        source = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(filepath))

        functions: list[str] = []
        classes: list[str] = []
        imports: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return {
            "functions": functions,
            "classes": classes,
            "imports": sorted(set(imports)),
        }

    def _parse_generic(self, filepath: Path) -> dict:
        """정규식 기반 일반 파싱 (JS/TS)."""
        source = filepath.read_text(encoding="utf-8", errors="replace")

        # Functions: function name(...), const name = (...) =>, async function name
        func_patterns = [
            r"(?:export\s+)?(?:async\s+)?function\s+(\w+)",
            r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(",
        ]
        functions: list[str] = []
        for pattern in func_patterns:
            functions.extend(re.findall(pattern, source))

        # Classes: class Name
        classes = re.findall(r"(?:export\s+)?class\s+(\w+)", source)

        # Imports: import ... from '...'
        imports = re.findall(r"(?:import|from)\s+['\"]([^'\"]+)['\"]", source)
        imports += re.findall(r"from\s+['\"]([^'\"]+)['\"]", source)

        return {
            "functions": list(dict.fromkeys(functions)),  # dedupe preserving order
            "classes": list(dict.fromkeys(classes)),
            "imports": sorted(set(imports)),
        }
