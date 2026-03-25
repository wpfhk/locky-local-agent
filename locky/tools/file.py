from __future__ import annotations

import re
from pathlib import Path

from locky.tools import BaseTool, ToolResult


class FileTool(BaseTool):
    name = "file"
    description = "파일 읽기, 쓰기, 검색"

    def run(self, root: Path, action: str = "read", **opts) -> ToolResult:
        if action == "read":
            return self._read(root, opts.get("path", ""))
        elif action == "write":
            return self._write(root, opts.get("path", ""), opts.get("content", ""))
        elif action == "search":
            return self._search(
                root, opts.get("pattern", ""), opts.get("glob", "**/*.py")
            )
        return ToolResult(status="error", message=f"알 수 없는 action: {action}")

    def _read(self, root: Path, rel_path: str) -> ToolResult:
        path = (root / rel_path).resolve()
        if not str(path).startswith(str(root.resolve())):
            return ToolResult(status="error", message="경로 접근 거부 (루트 벗어남)")
        if not path.exists():
            return ToolResult(status="error", message=f"파일 없음: {rel_path}")
        content = path.read_text(encoding="utf-8", errors="replace")
        return ToolResult(
            status="ok",
            message=content[:5000],
            data={"content": content, "path": str(path)},
        )

    def _write(self, root: Path, rel_path: str, content: str) -> ToolResult:
        path = (root / rel_path).resolve()
        if not str(path).startswith(str(root.resolve())):
            return ToolResult(status="error", message="경로 접근 거부")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ToolResult(
            status="ok", message=f"저장: {rel_path}", data={"path": str(path)}
        )

    def _search(self, root: Path, pattern: str, glob: str) -> ToolResult:
        matches = []
        for f in root.rglob(glob):
            if not f.is_file():
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(text.splitlines(), 1):
                    if re.search(pattern, line):
                        matches.append(f"{f.relative_to(root)}:{i}: {line.strip()}")
                        if len(matches) >= 50:
                            break
            except Exception:
                continue
        return ToolResult(
            status="ok", message="\n".join(matches), data={"matches": matches}
        )
