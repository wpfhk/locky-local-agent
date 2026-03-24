"""actions/shell_command.py — 자연어 요청을 셸 명령으로 변환합니다."""

from __future__ import annotations

import re
from pathlib import Path


_SYSTEM_PROMPT = (
    "당신은 셸 명령 생성기입니다. "
    "사용자 요청을 처리하는 셸 명령 한 줄만 출력하세요. "
    "주석, 설명, 마크다운 코드블록 없이 명령어만 출력하세요. "
    "명령어는 bash 호환 셸에서 실행 가능해야 합니다."
)


def _extract_command(raw: str) -> str:
    """Ollama 응답에서 실제 셸 명령만 추출합니다.

    마크다운 코드블록(```...```) 및 인라인 코드(` `)를 제거하고
    첫 번째 비어있지 않은 줄을 반환합니다.
    """
    # ```bash ... ``` 또는 ``` ... ``` 블록 추출
    block_match = re.search(r"```(?:\w+)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if block_match:
        raw = block_match.group(1)

    # 인라인 백틱 제거
    raw = raw.strip("`").strip()

    # 첫 번째 비어있지 않은 줄 반환
    for line in raw.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line

    return raw.strip()


def run(root: Path, request: str = "", auto_confirm: bool = False, **opts) -> dict:
    """자연어 요청을 Ollama를 통해 셸 명령으로 변환합니다.

    Args:
        root: 프로젝트 루트 Path (실행 시 cwd로 사용)
        request: 자연어로 작성된 사용자 요청
        auto_confirm: True면 사용자 확인 없이 즉시 실행 (기본값: False)

    Returns:
        {
            "status": "ok" | "error",
            "command": str,       # 생성된 셸 명령 (오류 시 빈 문자열)
            "message": str,       # 사용자 안내 메시지
        }
    """
    root = Path(root).resolve()

    if not request:
        return {
            "status": "error",
            "command": "",
            "message": "요청 내용이 비어있습니다.",
        }

    try:
        from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT
        import httpx

        payload = {
            "model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": request}],
            "system": _SYSTEM_PROMPT,
            "stream": False,
        }

        with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
            response = client.post(
                f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            raw_content = data["message"]["content"].strip()

        command = _extract_command(raw_content)

        if not command:
            return {
                "status": "error",
                "command": "",
                "message": "Ollama가 유효한 명령을 생성하지 못했습니다.",
            }

        return {
            "status": "ok",
            "command": command,
            "message": f"생성된 명령: {command}",
        }

    except Exception as exc:
        return {
            "status": "error",
            "command": "",
            "message": f"명령 생성 실패: {exc}",
        }
