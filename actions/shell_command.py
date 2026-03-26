"""actions/shell_command.py -- 자연어 요청을 셸 명령으로 변환합니다. (v4.0.0)"""

from __future__ import annotations

import re
from pathlib import Path

# 영어 시스템 프롬프트: Few-shot 예시 포함, 코드 생성 명시 거부
_SYSTEM_PROMPT = """\
You are a shell command generator for macOS/Linux.
Output ONLY a single executable shell command.
No explanations, no markdown, no code blocks. Just the raw command.

RULES:
1. Output must be a valid shell command (bash/zsh/sh).
2. NEVER output programming language code (Python, JavaScript, Go, Rust, etc.).
3. If the user asks to "write code", "implement a program", "create a script", \
or any code-generation task, output exactly: echo 'Use a code editor for programming tasks'
4. If the request is ambiguous, make the most reasonable assumption based on the files listed.
5. If truly impossible, output: echo 'cannot determine command'

EXAMPLES:
User: 현재 디렉토리의 파일 목록을 보여줘
Output: ls -la

User: app.aab를 연결된 기기에 설치해줘
Output: adb install app.aab

User: 파이썬 프로그램을 만들어줘
Output: echo 'Use a code editor for programming tasks'

User: git 로그를 보여줘
Output: git log --oneline -20

User: Docker 컨테이너 목록 보여줘
Output: docker ps -a
"""

# 관련성 높은 확장자 (우선 표시)
_PRIORITY_EXTS = {
    ".aab",
    ".apk",
    ".ipa",
    ".py",
    ".sh",
    ".js",
    ".ts",
    ".zip",
    ".tar",
    ".gz",
    ".jar",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
}

# 프로그래밍 언어 코드 키워드 (startswith 검사)
_CODE_KEYWORDS = frozenset(
    {
        "import ",
        "from ",
        "class ",
        "def ",
        "function ",
        "const ",
        "let ",
        "var ",
        "print(",
        "console.log(",
        "package ",
        "public ",
        "private ",
        "protected ",
        "async ",
        "await ",
        "return ",
        "if __name__",
        "#!/usr/bin/env python",
        "#!/usr/bin/python",
    }
)


def _scan_directory(root: Path) -> str:
    """현재 디렉토리 파일을 요약하여 컨텍스트로 제공합니다."""
    try:
        files = [f.name for f in root.iterdir() if f.is_file()]
        if not files:
            return "(empty)"
        priority = [f for f in files if Path(f).suffix in _PRIORITY_EXTS]
        others = [f for f in files if Path(f).suffix not in _PRIORITY_EXTS]
        shown = (priority + others)[:15]
        result = ", ".join(shown)
        if len(files) > 15:
            result += f" (+{len(files) - 15} more)"
        return result
    except Exception:
        return "(unknown)"


def _extract_command(raw: str) -> str:
    """Ollama 응답에서 실제 셸 명령만 추출합니다."""
    block_match = re.search(r"```(?:\w+)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if block_match:
        raw = block_match.group(1)

    raw = raw.strip("`").strip()

    for line in raw.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line

    return raw.strip()


def _is_valid_command(cmd: str) -> bool:
    """추출된 문자열이 실행 가능한 셸 명령인지 검증합니다."""
    if not cmd:
        return False
    # 한글 포함 = 명령이 아닌 자연어 응답
    if re.search(r"[가-힣ㄱ-ㅎㅏ-ㅣ]", cmd):
        return False
    # 알파벳·경로·변수로 시작해야 함
    if not re.match(r"^[a-zA-Z./~$_(]", cmd):
        return False
    # 프로그래밍 언어 코드 감지
    cmd_lower = cmd.lower()
    for kw in _CODE_KEYWORDS:
        if cmd_lower.startswith(kw):
            return False
    return True


def run(root: Path, request: str = "", auto_confirm: bool = False, **opts) -> dict:
    """자연어 요청을 Ollama를 통해 셸 명령으로 변환합니다.

    Args:
        root: 작업 디렉토리 (컨텍스트 및 cwd로 사용)
        request: 자연어 요청
        auto_confirm: 미사용 (repl.py에서 확인 처리)

    Returns:
        {"status": "ok"|"error", "command": str, "message": str}
    """
    root = Path(root).resolve()

    if not request:
        return {
            "status": "error",
            "command": "",
            "message": "요청 내용이 비어있습니다.",
        }

    # 디렉토리 컨텍스트 포함 -> Ollama가 파일 존재를 인식
    dir_files = _scan_directory(root)
    user_message = (
        f"Working directory: {root}\n"
        f"Files in directory: {dir_files}\n"
        f"Request: {request}"
    )

    try:
        import httpx

        from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT

        try:
            from tools.ollama_guard import ensure_ollama

            ensure_ollama(OLLAMA_BASE_URL, OLLAMA_MODEL)
        except Exception:
            pass

        payload = {
            "model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": user_message}],
            "system": _SYSTEM_PROMPT,
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": 80,
                "top_k": 1,
            },
        }

        with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
            resp = client.post(
                f"{OLLAMA_BASE_URL.rstrip('/')}/api/chat",
                json=payload,
            )
            resp.raise_for_status()
            raw_content = resp.json()["message"]["content"].strip()

        command = _extract_command(raw_content)

        if not _is_valid_command(command):
            return {
                "status": "error",
                "command": "",
                "message": f"유효한 셸 명령을 생성하지 못했습니다.\nLLM 응답: {raw_content[:120]}",
            }

        return {
            "status": "ok",
            "command": command,
            "message": f"생성된 명령: {command}",
        }

    except Exception as exc:
        return {"status": "error", "command": "", "message": f"명령 생성 실패: {exc}"}
