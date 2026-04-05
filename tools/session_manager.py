"""tools/session_manager.py -- JSON 기반 세션 메모리 관리."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

_MAX_ENTRIES = 20
_PROMPT_ENTRIES = 5
_OUTPUT_LIMIT = 200


class SessionManager:
    """작업 이력을 .omc/session.json에 관리합니다."""

    def __init__(self, root: Path, max_entries: int = _MAX_ENTRIES):
        self.path = Path(root).resolve() / ".omc" / "session.json"
        self.max_entries = max_entries
        self.entries: list[dict] = []
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.entries = data.get("entries", [])
        except Exception:
            self.entries = []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"entries": self.entries}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def record(
        self,
        request: str,
        command: str,
        exit_code: int,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        """실행 결과를 기록합니다."""
        output = (stdout or stderr)[:_OUTPUT_LIMIT]
        entry = {
            "request": request,
            "command": command,
            "exit_code": exit_code,
            "output": output,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        self.entries.append(entry)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries :]
        self._save()

    def get_recent(self, n: int = _PROMPT_ENTRIES) -> list[dict]:
        """최근 n개 이력을 반환합니다."""
        return self.entries[-n:]

    def format_context(self, n: int = _PROMPT_ENTRIES) -> str:
        """최근 이력을 프롬프트 컨텍스트 문자열로 포맷합니다."""
        recent = self.get_recent(n)
        if not recent:
            return ""
        lines = ["Previous actions:"]
        for e in recent:
            status = "ok" if e["exit_code"] == 0 else "error"
            lines.append(f'- [{status}] "{e["request"]}" -> {e["command"]}')
            if e.get("output"):
                lines.append(f"  output: {e['output'][:100]}")
        return "\n".join(lines)

    def clear(self) -> None:
        """세션 이력을 초기화합니다."""
        self.entries = []
        self._save()
