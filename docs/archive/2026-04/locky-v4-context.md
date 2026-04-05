# Locky Agent v4.0.0 -- Full Project Context

> 이 문서는 다른 AI에게 프로젝트 컨텍스트를 전달하기 위한 종합 요약본입니다.

---

## 1. 프로젝트 개요

**Locky**는 100% 로컬에서 동작하는 CLI 도구로, 자연어를 셸 명령으로 변환하여 확인 후 실행합니다.

- **핵심 기능**: 사용자가 "현재 디렉토리 파일 목록 보여줘"라고 입력하면 `ls -la`로 변환하고, 사용자 확인(y/N) 후 실행
- **LLM 백엔드**: Ollama (로컬 LLM 서버) -- 클라우드 API 의존성 없음
- **기본 모델**: `qwen2.5-coder:7b`
- **v4 설계 철학**: v3까지 비대해진 기능(멀티 LLM/MCP/session/sandbox/plugins/recipes 등)을 전부 제거하고, "자연어 -> 셸 명령 변환" 단일 기능에만 집중하는 전면 리라이트

---

## 2. 기술 스택

| 항목 | 내용 |
|------|------|
| **언어** | Python 3.10+ |
| **패키지 관리** | setuptools + pyproject.toml |
| **CLI 프레임워크** | Click 8.1+ |
| **HTTP 클라이언트** | httpx 0.27+ (Ollama API 호출) |
| **터미널 UI** | Rich 13.7+ (패널, 테이블, 색상 출력) |
| **입력 처리** | prompt-toolkit 3.0.43+ (REPL, 히스토리) |
| **LLM 서버** | Ollama (로컬, `http://localhost:11434`) |
| **테스트** | pytest 7+ / pytest-cov 4+ |
| **린터** | ruff |

### pyproject.toml (빌드 및 의존성 정의)

```toml
[build-system]
requires = ["setuptools>=61", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "locky-agent"
version = "4.0.0"
description = "Natural Language to Shell Command -- 100% local CLI tool powered by Ollama"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "httpx>=0.27.0",
    "click>=8.1.0",
    "rich>=13.7.0",
    "prompt-toolkit>=3.0.43",
]

[project.scripts]
locky = "locky_cli.main:main"

[project.optional-dependencies]
dev = ["pytest>=7.0.0", "pytest-cov>=4.0.0"]

[tool.setuptools.packages.find]
where = ["."]
include = ["actions*", "tools*", "locky_cli*"]

[tool.setuptools]
py-modules = ["config"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=actions --cov=locky_cli --cov=tools --cov-report=term-missing"
```

---

## 3. 디렉토리 구조

```
locky-agent/
├── locky_cli/                  # CLI 진입점 패키지
│   ├── __init__.py             # 패키지 마커 (한 줄)
│   ├── main.py                 # Click CLI 진입점 -- `locky` 명령 정의
│   └── repl.py                 # REPL 루프 (자연어 -> shell_command -> 확인 -> 실행)
├── actions/                    # 비즈니스 로직 패키지
│   ├── __init__.py             # shell_command만 export
│   └── shell_command.py        # 핵심: 자연어 -> 셸 명령 변환 (Ollama API 호출)
├── tools/                      # 인프라/유틸리티 패키지
│   ├── __init__.py             # OllamaClient만 export
│   ├── ollama_client.py        # Ollama /api/chat 동기/비동기/스트리밍 클라이언트
│   └── ollama_guard.py         # Ollama 헬스체크 + 자동 시작 + 모델 설치 확인
├── config.py                   # 환경변수 기반 설정 (3개 변수)
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # pytest 공통 픽스처 (tmp_git_repo)
│   └── test_shell_command.py   # 핵심 테스트 (30개)
├── pyproject.toml              # 빌드/의존성/테스트 설정
├── requirements.txt            # pip install용 최소 의존성
└── CHANGELOG.md                # v1.0.0 ~ v3.0.0 히스토리
```

---

## 4. 데이터 흐름 / 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        사용자 터미널                              │
│  $ locky [-w /path]                                             │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────┐
│  locky_cli/main.py       │  Click CLI 진입점
│  cli() -> run_interactive │  --workspace 옵션 처리
│  _session()              │
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│  locky_cli/repl.py       │  REPL 루프
│  run_interactive_session()│
│                          │
│  1. 배너 출력            │
│  2. 입력 대기 (prompt)   │
│  3. 슬래시 명령 분기     │  /help, /clear, /exit
│  4. 자연어 입력 처리     │──────────────────┐
└──────────────────────────┘                  │
                                              ▼
                               ┌──────────────────────────┐
                               │  actions/shell_command.py │  핵심 로직
                               │  run(root, request)      │
                               │                          │
                               │  1. _scan_directory()    │  디렉토리 파일 목록 수집
                               │  2. 사용자 메시지 조합   │  (디렉토리 컨텍스트 + 요청)
                               │  3. Ollama API 호출      │──────┐
                               │  4. _extract_command()   │      │
                               │  5. _is_valid_command()  │      │
                               │  6. 결과 dict 반환       │      │
                               └──────────────┬───────────┘      │
                                              │                  │
                                              ▼                  ▼
                               ┌──────────────────┐  ┌───────────────────┐
                               │  repl.py          │  │ tools/             │
                               │  _handle_free_text│  │ ollama_guard.py    │
                               │                   │  │  ensure_ollama()   │
                               │  1. 명령 패널 출력│  │  (헬스체크/자동시작)│
                               │  2. 확인 프롬프트 │  │                   │
                               │     (y/N)         │  │ ollama_client.py   │
                               │  3. subprocess.run│  │  OllamaClient     │
                               │  4. 결과 패널 출력│  │  (chat/stream)     │
                               └──────────────────┘  └───────────────────┘
```

### 핵심 데이터 흐름 요약

1. `locky` 실행 -> `main.py`의 Click CLI가 `repl.py`의 REPL 세션 시작
2. 사용자가 자연어 입력 (예: "현재 디렉토리의 파일 목록을 보여줘")
3. `repl.py`가 `actions/shell_command.run()`을 호출
4. `shell_command.run()`이:
   - 작업 디렉토리의 파일 목록을 스캔하여 컨텍스트 생성
   - Ollama `/api/chat` API에 시스템 프롬프트 + 사용자 메시지 전송
   - 응답에서 셸 명령 추출 (`_extract_command`)
   - 명령 유효성 검증 (`_is_valid_command`) -- 한글, 프로그래밍 코드 키워드 감지
5. 유효한 명령이면 `repl.py`가 사용자에게 확인 프롬프트 표시
6. `y` 입력 시 `subprocess.run()`으로 실행, 결과를 Rich 패널로 출력

---

## 5. 핵심 로직 코드 (전체 소스)

### 5.1 config.py -- 환경변수 설정

```python
"""config.py -- Ollama 설정 (v4.0.0). 환경변수 기반 단순 설정."""

import os

# Ollama 설정
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))
```

### 5.2 actions/shell_command.py -- 핵심 변환 로직

```python
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
    ".aab", ".apk", ".ipa", ".py", ".sh", ".js", ".ts", ".zip",
    ".tar", ".gz", ".jar", ".json", ".yaml", ".yml", ".toml",
}

# 프로그래밍 언어 코드 키워드 (startswith 검사)
_CODE_KEYWORDS = frozenset({
    "import ", "from ", "class ", "def ", "function ",
    "const ", "let ", "var ", "print(", "console.log(",
    "package ", "public ", "private ", "protected ",
    "async ", "await ", "return ", "if __name__",
    "#!/usr/bin/env python", "#!/usr/bin/python",
})


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
```

### 5.3 locky_cli/main.py -- CLI 진입점

```python
"""locky CLI -- Click 진입점 (v4.0.0). REPL만 제공."""

from __future__ import annotations
from pathlib import Path
import click


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version="4.0.0", prog_name="locky")
@click.option(
    "--workspace", "-w", "workspace_dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="Workspace root (default: current directory).",
)
def cli(workspace_dir: Path | None) -> None:
    """Locky -- Natural Language to Shell Command."""
    from locky_cli.repl import run_interactive_session
    run_interactive_session(start_dir=workspace_dir)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
```

### 5.4 locky_cli/repl.py -- REPL 루프

```python
"""인터랙티브 세션 -- Locky REPL (v4.0.0). 자연어 -> 셸 명령 변환 전용."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from prompt_toolkit import PromptSession

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def _get_version() -> str:
    """패키지 버전을 동적으로 읽습니다."""
    try:
        from importlib.metadata import version
        return version("locky-agent")
    except Exception:
        pass
    try:
        import locky_cli
        pyproject = Path(locky_cli.__file__).parent.parent / "pyproject.toml"
        content = pyproject.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("version") and "=" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "unknown"


def _banner(console: Console, workspace: Path) -> None:
    """시작 배너를 출력합니다."""
    from config import OLLAMA_MODEL

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("Version", _get_version())
    table.add_row("Workspace", str(workspace.name))
    table.add_row("Model", OLLAMA_MODEL)
    console.print(
        Panel(
            table,
            title="[bold cyan]Locky[/bold cyan]",
            subtitle="[dim]Natural Language -> Shell Command | /help[/dim]",
            border_style="cyan",
        )
    )


_HELP_TEXT = (
    "[bold]Commands:[/bold]\n"
    "  /help   -- Show this help\n"
    "  /clear  -- Clear screen\n"
    "  /exit   -- Quit (or type exit/quit)\n\n"
    "[bold]Usage:[/bold]\n"
    "  Type any natural language request and Locky will convert it to a shell command.\n"
    "  You will be asked to confirm before execution.\n\n"
    "[bold]Examples:[/bold]\n"
    "  현재 디렉토리의 파일 목록을 보여줘\n"
    "  app.aab를 연결된 기기에 설치해줘\n"
    "  git log를 보여줘"
)


def _handle_free_text(
    console: Console,
    session: "PromptSession",
    workspace: Path,
    text: str,
) -> None:
    """자유 텍스트 입력을 Ollama로 셸 명령으로 변환하고 확인 후 실행합니다."""
    from actions.shell_command import run as shell_command_run

    console.print("[dim]Generating shell command...[/dim]")
    result = shell_command_run(workspace, request=text)

    if result["status"] != "ok":
        console.print(
            Panel(
                f"[red]{result['message']}[/red]",
                title="Command generation failed",
                border_style="red",
                expand=False,
            )
        )
        return

    command = result["command"]
    console.print(
        Panel(
            f"[bold cyan]{command}[/bold cyan]",
            title="Command to execute",
            border_style="cyan",
            expand=False,
        )
    )

    try:
        answer = session.prompt("Execute? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print("[dim]Cancelled.[/dim]")
        return

    if answer not in ("y", "yes"):
        console.print("[dim]Cancelled.[/dim]")
        return

    proc = subprocess.run(
        command,
        shell=True,
        cwd=str(workspace),
        capture_output=True,
        text=True,
    )

    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    returncode = proc.returncode

    output_lines = []
    if stdout:
        output_lines.append(stdout[:2000])
    if stderr:
        output_lines.append(f"[red]{stderr[:1000]}[/red]")

    status_label = "ok" if returncode == 0 else "error"
    color = "green" if returncode == 0 else "red"
    body = "\n".join(output_lines) if output_lines else "(no output)"

    console.print(
        Panel(
            body,
            title=f"Result -- [{color}]{status_label}[/{color}] (exit {returncode})",
            border_style=color,
            expand=False,
        )
    )


def run_interactive_session(start_dir: Optional[Path] = None) -> None:
    """표준 입력 기반 인터랙티브 세션."""
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import InMemoryHistory
    except ImportError:
        print("prompt_toolkit is required: pip install prompt-toolkit", file=sys.stderr)
        sys.exit(1)

    console = Console()
    workspace = (start_dir or Path.cwd()).resolve()

    _banner(console, workspace)

    history = InMemoryHistory()
    session = PromptSession(history=history)

    while True:
        try:
            root_hint = str(workspace)[:48]
            line = session.prompt(f"locky [{root_hint}]> ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Bye.[/dim]")
            break

        line = line.strip()
        if not line:
            continue

        if line.lower() in ("exit", "quit"):
            console.print("[dim]Bye.[/dim]")
            break

        if line.startswith("/"):
            cmd = line.lower().lstrip("/").split()[0] if line.strip() else ""

            if cmd in ("exit", "quit"):
                console.print("[dim]Bye.[/dim]")
                break

            if cmd == "help":
                console.print(Panel(_HELP_TEXT, title="Help", border_style="dim"))
                continue

            if cmd == "clear":
                console.clear()
                _banner(console, workspace)
                continue

            console.print(
                f"[red]Unknown command:[/red] /{cmd}\n"
                "[dim]Available: /help /clear /exit[/dim]"
            )
            continue

        # 일반 텍스트 입력 -- Ollama로 셸 명령 변환 후 사용자 확인
        _handle_free_text(console, session, workspace, line)
```

### 5.5 tools/ollama_client.py -- Ollama API 클라이언트

```python
from typing import AsyncGenerator
import httpx
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT


class OllamaClient:
    """Ollama API 클라이언트"""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
        timeout: int = OLLAMA_TIMEOUT,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(self, messages: list, system: str = "") -> str:
        """동기 채팅 요청. 모델 응답 문자열 반환."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if system:
            payload["system"] = system

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]

    async def stream_chat(
        self, messages: list, system: str = ""
    ) -> AsyncGenerator[str, None]:
        """비동기 스트리밍 채팅 요청. 토큰 문자열을 yield."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST", f"{self.base_url}/api/chat", json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    import json
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if chunk.get("done", False):
                        break

    def stream(self, messages: list, system: str = "", timeout: int | None = None):
        """스트리밍 채팅. 토큰별 동기 제너레이터."""
        import json

        payload = {"model": self.model, "messages": messages, "stream": True}
        if system:
            payload["system"] = system

        effective_timeout = timeout if timeout is not None else self.timeout
        with httpx.Client(timeout=effective_timeout) as client:
            with client.stream(
                "POST", f"{self.base_url}/api/chat", json=payload
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if line:
                        data = json.loads(line)
                        if token := data.get("message", {}).get("content", ""):
                            yield token
                        if data.get("done"):
                            break

    def health_check(self) -> bool:
        """Ollama 서버 상태 확인. 정상이면 True."""
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                return True
        except Exception:
            return False
```

### 5.6 tools/ollama_guard.py -- Ollama 헬스체크 및 자동 시작

```python
"""tools/ollama_guard.py -- Ollama 서버 헬스체크 및 자동 시작. (v1.0.0)"""

from __future__ import annotations
import subprocess
import time


def ensure_ollama(
    base_url: str = "http://localhost:11434",
    model: str = "qwen2.5-coder:7b",
    timeout: int = 10,
) -> dict:
    """Ollama 서버가 준비됐는지 확인하고, 미기동 시 백그라운드 시작을 시도합니다.

    1. GET /api/tags 로 헬스체크
    2. 실패 시: `ollama serve` 백그라운드 시작 (3초 대기 후 재시도)
    3. 모델 미설치 확인 후 설치 안내 제공

    Returns:
        {"status": "ok"|"started"|"error", "message": str, "model_available": bool}
    """
    tags = _fetch_tags(base_url, timeout)
    if tags is None:
        started = _try_start_ollama()
        if not started:
            return {
                "status": "error",
                "message": (
                    f"Ollama 서버에 연결할 수 없습니다 ({base_url}). "
                    "수동으로 `ollama serve`를 실행하세요."
                ),
                "model_available": False,
            }
        time.sleep(3)
        tags = _fetch_tags(base_url, timeout)
        if tags is None:
            return {
                "status": "error",
                "message": "Ollama 시작 후에도 연결에 실패했습니다.",
                "model_available": False,
            }
        server_status = "started"
    else:
        server_status = "ok"

    model_available = _check_model(tags, model)
    if not model_available:
        return {
            "status": server_status,
            "message": f"모델 '{model}'이(가) 설치되지 않았습니다. `ollama pull {model}`을 실행하세요.",
            "model_available": False,
        }

    return {
        "status": server_status,
        "message": f"Ollama 정상 (모델: {model})"
        + (" -- 서버를 새로 시작했습니다." if server_status == "started" else ""),
        "model_available": True,
    }


def _fetch_tags(base_url: str, timeout: int) -> list | None:
    """GET /api/tags 로 설치된 모델 목록을 가져옵니다."""
    try:
        import httpx
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(f"{base_url.rstrip('/')}/api/tags")
            resp.raise_for_status()
            return resp.json().get("models", [])
    except Exception:
        return None


def _check_model(tags: list, model: str) -> bool:
    """tags 리스트에서 모델명 존재 여부를 확인합니다."""
    model_base = model.split(":")[0]
    for tag in tags:
        name = tag.get("name", "")
        if name == model or name.startswith(model_base + ":"):
            return True
    return False


def _try_start_ollama() -> bool:
    """ollama serve를 백그라운드로 시작합니다."""
    try:
        import shutil
        if not shutil.which("ollama"):
            return False
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except Exception:
        return False
```

---

## 6. 테스트 코드

### 6.1 tests/conftest.py -- 공통 픽스처

```python
"""pytest 공통 픽스처 (v4.0.0)."""

from __future__ import annotations
import subprocess
from pathlib import Path
import pytest


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> Path:
    """임시 git 레포지토리를 생성하고 반환합니다."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path, check=True, capture_output=True,
    )
    return tmp_path
```

### 6.2 tests/test_shell_command.py -- 핵심 테스트 (30개)

```python
"""actions/shell_command.py 단위 테스트 (v4.0.0)."""

from __future__ import annotations
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from actions.shell_command import _extract_command, _is_valid_command, _scan_directory

# -- _extract_command --

def test_extract_plain_command():
    assert _extract_command("adb install app.aab") == "adb install app.aab"

def test_extract_strips_backtick_block():
    raw = "```bash\nadb install app.aab\n```"
    assert _extract_command(raw) == "adb install app.aab"

def test_extract_strips_inline_backtick():
    assert _extract_command("`ls -la`") == "ls -la"

def test_extract_skips_comment_lines():
    raw = "# install command\nadb install app.aab"
    assert _extract_command(raw) == "adb install app.aab"

def test_extract_first_non_empty_line():
    raw = "\n\nls -la\npwd"
    assert _extract_command(raw) == "ls -la"

# -- _is_valid_command --

def test_valid_adb_command():
    assert _is_valid_command("adb install app.aab") is True

def test_valid_ls_command():
    assert _is_valid_command("ls -la") is True

def test_valid_path_command():
    assert _is_valid_command("./gradlew build") is True

def test_valid_echo_command():
    assert _is_valid_command("echo 'hello world'") is True

def test_valid_git_command():
    assert _is_valid_command("git log --oneline -20") is True

def test_valid_docker_command():
    assert _is_valid_command("docker ps -a") is True

def test_invalid_korean_response():
    assert _is_valid_command("죄송합니다, 더 자세한 정보가 필요합니다.") is False

def test_invalid_empty_string():
    assert _is_valid_command("") is False

def test_invalid_starts_with_number():
    assert _is_valid_command("1password login") is False

# -- Code keyword rejection (v4 bug fix) --

def test_invalid_import_statement():
    assert _is_valid_command("import os") is False

def test_invalid_from_import():
    assert _is_valid_command("from pathlib import Path") is False

def test_invalid_class_definition():
    assert _is_valid_command("class MyClass:") is False

def test_invalid_def_function():
    assert _is_valid_command("def main():") is False

def test_invalid_javascript_function():
    assert _is_valid_command("function doSomething() {") is False

def test_invalid_const_declaration():
    assert _is_valid_command("const x = 5;") is False

def test_invalid_let_declaration():
    assert _is_valid_command("let y = 10;") is False

def test_invalid_var_declaration():
    assert _is_valid_command("var z = 15;") is False

def test_invalid_print_call():
    assert _is_valid_command("print('hello')") is False

def test_invalid_console_log():
    assert _is_valid_command("console.log('hello')") is False

def test_invalid_if_name_main():
    assert _is_valid_command("if __name__ == '__main__':") is False

# -- _scan_directory --

def test_scan_directory_finds_aab(tmp_path):
    (tmp_path / "app-release.aab").touch()
    (tmp_path / "README.md").touch()
    result = _scan_directory(tmp_path)
    assert "app-release.aab" in result

def test_scan_directory_empty(tmp_path):
    assert _scan_directory(tmp_path) == "(empty)"

def test_scan_directory_priority_ext_first(tmp_path):
    (tmp_path / "main.py").touch()
    (tmp_path / "README.md").touch()
    result = _scan_directory(tmp_path)
    assert result.index("main.py") < result.index("README.md")

def test_scan_directory_limits_to_15(tmp_path):
    for i in range(20):
        (tmp_path / f"file_{i:02d}.py").touch()
    result = _scan_directory(tmp_path)
    assert "+5 more" in result

# -- run() integration (Ollama mock) --

def test_run_empty_request(tmp_path):
    from actions.shell_command import run
    result = run(tmp_path, request="")
    assert result["status"] == "error"
    assert result["command"] == ""

def test_run_returns_ok_with_mock(tmp_path):
    from actions.shell_command import run
    mock_response = MagicMock()
    mock_response.json.return_value = {"message": {"content": "adb install app.aab"}}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client
        result = run(tmp_path, request="aab 파일 설치해줘")

    assert result["status"] == "ok"
    assert result["command"] == "adb install app.aab"

def test_run_rejects_korean_response(tmp_path):
    from actions.shell_command import run
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {"content": "죄송합니다, 어떤 명령인지 모르겠습니다."}
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client
        result = run(tmp_path, request="뭔가 해줘")

    assert result["status"] == "error"
    assert result["command"] == ""

def test_run_rejects_python_code_response(tmp_path):
    """v4 핵심 버그 수정: Ollama가 Python 코드를 반환하면 거부해야 한다."""
    from actions.shell_command import run
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {"content": "import os\nos.makedirs('/temp', exist_ok=True)"}
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client
        result = run(tmp_path, request="파이썬 프로그램 만들어줘")

    assert result["status"] == "error"
    assert result["command"] == ""

def test_run_accepts_echo_refusal(tmp_path):
    """코드 생성 요청에 echo 거부 메시지를 반환하면 유효한 명령으로 인정."""
    from actions.shell_command import run
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "message": {"content": "echo 'Use a code editor for programming tasks'"}
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client
        result = run(tmp_path, request="파이썬 프로그램 만들어줘")

    assert result["status"] == "ok"
    assert "echo" in result["command"]

def test_run_handles_connection_error(tmp_path):
    """Ollama 연결 실패 시 에러를 반환해야 한다."""
    from actions.shell_command import run

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = Exception("Connection refused")
        mock_client_cls.return_value = mock_client
        result = run(tmp_path, request="ls 해줘")

    assert result["status"] == "error"
    assert "명령 생성 실패" in result["message"]
```

---

## 7. 설계 결정 사항 요약

| 결정 | 이유 |
|------|------|
| **v4 전면 리라이트** | v3의 과도한 복잡도(멀티 LLM/MCP/session/sandbox/plugins/recipes)를 제거, shell_command 하나에 집중 |
| **Ollama 직접 호출** | LLM Registry 제거, httpx로 Ollama `/api/chat` 직접 호출 |
| **영어 시스템 프롬프트** | 한국어 입력이어도 LLM이 영어 프롬프트를 더 잘 따름 |
| **Few-shot 예시** | 프롬프트에 5개 예시를 포함하여 응답 형식을 강제 |
| **코드 생성 거부** | `_CODE_KEYWORDS`로 Python/JS 등의 코드 키워드를 감지하여 거부 |
| **한글 감지** | LLM이 설명을 한글로 출력하는 경우를 걸러내는 방어 로직 |
| **디렉토리 스캔** | 작업 디렉토리 파일 목록을 LLM 컨텍스트에 포함하여 파일명 기반 명령 생성 가능 |
| **temperature=0, top_k=1** | 결정론적 출력을 위해 가장 보수적인 샘플링 |
| **num_predict=80** | 셸 명령은 짧으므로 토큰 제한을 낮게 설정 |
| **최소 의존성 4개** | httpx, click, rich, prompt-toolkit만 사용 |

---

## 8. 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | 사용할 Ollama 모델 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 주소 |
| `OLLAMA_TIMEOUT` | `300` | LLM 호출 타임아웃 (초) |

---

## 9. 실행 방법

```bash
# 설치
pip install -e .

# 실행 (REPL 모드)
locky

# 특정 디렉토리에서 시작
locky -w /path/to/project

# 테스트
python -m pytest tests/test_shell_command.py -v
```
