from __future__ import annotations
import re
from locky.core.context import ContextCollector
from locky.core.session import LockySession


DIFF_SYSTEM = """당신은 코드 편집 전문 에이전트입니다.
주어진 파일 내용과 지시사항을 바탕으로 unified diff 형식으로 변경 사항을 반환하세요.

응답 형식:
```diff
--- a/파일경로
+++ b/파일경로
@@ -N,M +N,M @@
 변경 전 줄
-삭제할 줄
+추가할 줄
```

주의: diff 블록 외 설명은 최소화하세요."""


class EditAgent:
    """코드 편집 에이전트 — unified diff 생성 및 적용."""

    def __init__(self, session: LockySession) -> None:
        self.session = session

    def run(self, instruction: str, file_path: str,
            dry_run: bool = True) -> dict:
        """
        Returns:
            {"status": "dry_run"|"ok"|"error", "diff": str, "message": str, "applied": bool}
        """
        root = self.session.workspace

        path = (root / file_path).resolve()
        if not str(path).startswith(str(root.resolve())):
            return {"status": "error", "diff": "", "message": "경로 접근 거부", "applied": False}
        if not path.exists():
            return {"status": "error", "diff": "", "message": f"파일 없음: {file_path}", "applied": False}

        original = path.read_text(encoding="utf-8")

        from tools.ollama_guard import ensure_ollama
        from config import OLLAMA_BASE_URL, OLLAMA_MODEL
        if not ensure_ollama(OLLAMA_BASE_URL, OLLAMA_MODEL):
            return {"status": "error", "diff": "", "message": "Ollama 서버 없음", "applied": False}

        from tools.ollama_client import OllamaClient
        client = OllamaClient()

        prompt = (
            f"파일: {file_path}\n\n"
            f"```python\n{original[:3000]}\n```\n\n"
            f"지시사항: {instruction}"
        )

        response = client.chat([{"role": "user", "content": prompt}], system=DIFF_SYSTEM)
        diff = self._extract_diff(response)

        if not diff:
            return {"status": "dry_run", "diff": response[:2000],
                    "message": "diff 파싱 실패. 응답을 수동 확인 필요.", "applied": False}

        if dry_run:
            return {"status": "dry_run", "diff": diff, "message": "미리보기 (--apply로 적용)", "applied": False}

        applied = self._apply_diff(path, original, diff)
        if applied:
            self.session.add_history({"type": "edit", "file": file_path,
                                      "instruction": instruction[:100]})
            return {"status": "ok", "diff": diff, "message": f"적용 완료: {file_path}", "applied": True}

        return {"status": "error", "diff": diff, "message": "diff 적용 실패. 수동 적용 필요.", "applied": False}

    def _extract_diff(self, response: str) -> str:
        """응답에서 diff 블록 추출."""
        match = re.search(r"```diff\n(.*?)```", response, re.DOTALL)
        if match:
            return match.group(1)
        match = re.search(r"(--- a/.*?\+\+\+ b/.*?(?=\n\n|\Z))", response, re.DOTALL)
        return match.group(1) if match else ""

    def _apply_diff(self, path, original: str, diff: str) -> bool:
        """patch 명령으로 diff 적용. 실패 시 False."""
        import subprocess
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode="w", suffix=".patch",
                                         delete=False, encoding="utf-8") as f:
            f.write(diff)
            patch_file = f.name

        try:
            result = subprocess.run(
                ["patch", "-p1", str(path)],
                input=diff, capture_output=True, text=True,
                cwd=path.parent, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
        finally:
            os.unlink(patch_file)
