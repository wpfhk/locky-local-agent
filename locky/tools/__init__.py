from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ToolResult:
    """Tool 실행 결과 — actions/ dict 결과와 호환."""
    status: str          # "ok" | "error" | "nothing_to_commit" 등
    message: str = ""
    data: dict = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}

    @classmethod
    def from_dict(cls, d: dict) -> ToolResult:
        """actions/ 모듈 반환 dict에서 생성."""
        return cls(
            status=d.get("status", "error"),
            message=d.get("message", str(d)),
            data=d,
        )

    @property
    def ok(self) -> bool:
        return self.status in ("ok", "pass", "clean", "nothing_to_commit")


class BaseTool:
    """Tool 기반 클래스. 모든 Tool은 이를 상속."""
    name: str = ""
    description: str = ""

    def run(self, root: Path, **opts) -> ToolResult:
        raise NotImplementedError(f"{self.__class__.__name__}.run() 미구현")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
