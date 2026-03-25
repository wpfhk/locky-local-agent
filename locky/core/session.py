from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class LockySession:
    """locky 세션 상태 — 컨텍스트 누적 및 .locky/session.json 영속화."""

    workspace: Path
    session_id: str = ""
    history: list[dict] = field(default_factory=list)
    profile: str = "default"

    def __post_init__(self):
        if not self.session_id:
            import uuid
            self.session_id = f"{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

    @classmethod
    def load(cls, workspace: Path) -> LockySession:
        """기존 세션 파일 로드. 없으면 신규 생성."""
        session_file = workspace / ".locky" / "session.json"
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text())
                return cls(
                    workspace=workspace,
                    session_id=data.get("session_id", ""),
                    history=data.get("history", []),
                    profile=data.get("profile", "default"),
                )
            except Exception:
                pass
        return cls(workspace=workspace)

    def save(self) -> None:
        """세션 상태를 .locky/session.json에 저장."""
        session_file = self.workspace / ".locky" / "session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps({
            "session_id": self.session_id,
            "workspace": str(self.workspace),
            "history": self.history[-50:],  # 최근 50개만 보존
            "profile": self.profile,
        }, ensure_ascii=False, indent=2))

    def add_history(self, entry: dict) -> None:
        """히스토리에 항목 추가 (timestamp 자동 포함)."""
        self.history.append({**entry, "timestamp": datetime.now().isoformat()})
        self.save()

    def context_summary(self) -> str:
        """최근 히스토리 요약 (Ollama 프롬프트용)."""
        recent = self.history[-5:]
        return "; ".join(f"{h['type']}: {h.get('result', '')}" for h in recent)

    def clear(self) -> None:
        """세션 초기화."""
        self.history = []
        self.save()
