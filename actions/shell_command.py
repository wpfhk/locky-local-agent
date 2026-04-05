"""actions/shell_command.py -- 자연어 요청을 셸 명령으로 변환합니다."""

from __future__ import annotations

import platform
import re
import time
from pathlib import Path

_IS_WINDOWS = platform.system() == "Windows"
_SHELL_NAME = "Windows PowerShell" if _IS_WINDOWS else "macOS/Linux"

# OS별 시스템 프롬프트: Few-shot 예시 포함, 코드 생성 명시 거부
_SYSTEM_PROMPT = f"""\
You are a shell command generator for {"Windows PowerShell" if _IS_WINDOWS else "macOS/Linux"}.
Output ONLY a single executable shell command.
No explanations, no markdown, no code blocks. Just the raw command.

RULES:
1. Output must be a valid {"PowerShell command" if _IS_WINDOWS else "shell command (bash/zsh/sh)"}.
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


_CODE_MAP_TTL = 300  # 5분


def _get_code_map(root: Path) -> str:
    """코드 맵을 로드합니다. 없거나 오래되면 자동 생성."""
    map_path = root / ".omc" / "repo_map.md"

    try:
        needs_update = not map_path.is_file() or (
            time.time() - map_path.stat().st_mtime > _CODE_MAP_TTL
        )
        if needs_update:
            from tools.indexer import save_repo_map

            save_repo_map(root)
    except Exception:
        pass

    if not map_path.is_file():
        return ""

    try:
        content = map_path.read_text(encoding="utf-8")
        return content[:4000] if len(content) > 4000 else content
    except Exception:
        return ""


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
    # 알파벳·숫자·경로·변수로 시작해야 함
    if not re.match(r"^[a-zA-Z0-9./~$_(]", cmd):
        return False
    # 프로그래밍 언어 코드 감지
    cmd_lower = cmd.lower()
    for kw in _CODE_KEYWORDS:
        if cmd_lower.startswith(kw):
            return False
    return True


def run(
    root: Path, request: str = "", history: str = "", on_token=None, **opts
) -> dict:
    """자연어 요청을 Ollama를 통해 셸 명령으로 변환합니다.

    Args:
        root: 작업 디렉토리 (컨텍스트 및 cwd로 사용)
        request: 자연어 요청
        history: 세션 이력 컨텍스트 (format_context() 결과)

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

    # 디렉토리 + 코드 맵 + 세션 이력 컨텍스트 포함
    dir_files = _scan_directory(root)
    code_map = _get_code_map(root)

    parts = [
        f"Working directory: {root}",
        f"Files in directory: {dir_files}",
    ]
    if code_map:
        parts.append(f"\nProject code map:\n{code_map}")
    if history:
        parts.append(f"\n{history}")
    parts.append(f"\nRequest: {request}")
    user_message = "\n".join(parts)

    try:
        from tools.ollama_client import OllamaClient

        try:
            from config import OLLAMA_BASE_URL, OLLAMA_MODEL

            from tools.ollama_guard import ensure_ollama

            ensure_ollama(OLLAMA_BASE_URL, OLLAMA_MODEL)
        except Exception:
            pass

        client = OllamaClient()
        options_dict = {"temperature": 0, "num_predict": 150, "top_k": 1}

        if on_token is not None:
            # Streaming mode
            raw_parts: list[str] = []
            for token in client.stream(
                messages=[{"role": "user", "content": user_message}],
                system=_SYSTEM_PROMPT,
                options=options_dict,
            ):
                raw_parts.append(token)
                on_token(token)
            raw_content = "".join(raw_parts).strip()
        else:
            raw_content = client.chat(
                messages=[{"role": "user", "content": user_message}],
                system=_SYSTEM_PROMPT,
                options=options_dict,
            ).strip()

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


# -- 자가 수정 프롬프트 ---------------------------------------------------------

_FIX_SYSTEM_PROMPT = f"""\
You are a shell command debugger for {_SHELL_NAME}.
A command failed. Analyze the error and output ONLY a single corrected shell command.
No explanations, no markdown, no code blocks. Just the fixed raw command.

FAILURE PATTERNS:
- Typo in command name (e.g. "gitt") -> correct the spelling (e.g. "git")
- Permission denied -> prepend sudo (Linux/macOS) or suggest Run as Admin
- No such file or directory -> fix the path using the file listing provided
- Command not installed -> output the install command (e.g. apt install, brew install)
- Wrong flags or syntax -> fix the flags based on the tool's usage

If truly unrecoverable, output: echo 'Cannot fix: <brief reason>'
"""


def run_fix(
    root: Path,
    request: str,
    failed_command: str,
    error_msg: str,
    on_token=None,
) -> dict:
    """실패한 명령을 분석하고 교정된 명령을 제안합니다.

    Args:
        root: 작업 디렉토리
        request: 원래 자연어 요청
        failed_command: 실패한 셸 명령
        error_msg: stderr 출력

    Returns:
        {"status": "ok"|"error", "command": str, "message": str}
    """
    root = Path(root).resolve()

    dir_files = _scan_directory(root)
    code_map = _get_code_map(root)

    parts = [
        f"Working directory: {root}",
        f"Files: {dir_files}",
    ]
    if code_map:
        parts.append(f"\nProject code map:\n{code_map}")
    parts.append(f"\nOriginal request: {request}")
    parts.append(f"Failed command: {failed_command}")
    parts.append(f"Error output:\n{error_msg[:500]}")
    parts.append("\nProvide the corrected command:")
    user_message = "\n".join(parts)

    try:
        from tools.ollama_client import OllamaClient

        client = OllamaClient()
        options_dict = {"temperature": 0, "num_predict": 150, "top_k": 1}

        if on_token is not None:
            raw_parts: list[str] = []
            for token in client.stream(
                messages=[{"role": "user", "content": user_message}],
                system=_FIX_SYSTEM_PROMPT,
                options=options_dict,
            ):
                raw_parts.append(token)
                on_token(token)
            raw_content = "".join(raw_parts).strip()
        else:
            raw_content = client.chat(
                messages=[{"role": "user", "content": user_message}],
                system=_FIX_SYSTEM_PROMPT,
                options=options_dict,
            ).strip()

        command = _extract_command(raw_content)

        if not _is_valid_command(command):
            return {
                "status": "error",
                "command": "",
                "message": f"교정 실패.\nLLM 응답: {raw_content[:120]}",
            }

        return {
            "status": "ok",
            "command": command,
            "message": f"교정된 명령: {command}",
        }

    except Exception as exc:
        return {"status": "error", "command": "", "message": f"교정 실패: {exc}"}
