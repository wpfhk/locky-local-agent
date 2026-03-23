"""인터랙티브 세션 — Claude Code 스타일 REPL."""

from __future__ import annotations

import os
import shlex
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.rule import Rule
from rich.table import Table

from locky_cli.fs_context import default_full_access_root
from locky_cli.permissions import PermissionMode, resolve_workspace_root
from tools.ollama_client import OllamaClient


@dataclass
class SessionState:
    """REPL 세션 상태."""

    workspace_root: Path
    mode: PermissionMode = PermissionMode.WORKSPACE
    run_count: int = 0
    last_cmd: str = ""


def _banner(console: Console, state: SessionState) -> None:
    from config import OLLAMA_MODEL

    mode_label = "workspace (이 디렉터리 이하)" if state.mode == PermissionMode.WORKSPACE else "full (로컬 전체)"
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("모델", OLLAMA_MODEL)
    table.add_row("워크스페이스", str(state.workspace_root))
    table.add_row("권한", mode_label)
    console.print(
        Panel(
            table,
            title="[bold cyan]Locky[/bold cyan]",
            subtitle="[dim]Planner → Coder → Tester · /help 로 명령 안내[/dim]",
            border_style="cyan",
        )
    )


def _effective_root(state: SessionState) -> Path:
    if state.mode == PermissionMode.FULL:
        return default_full_access_root()
    return state.workspace_root


def _run_develop(cmd: str, state: SessionState, console: Console) -> None:
    from graph import run_with_root

    ollama = OllamaClient()
    if not ollama.health_check():
        console.print(
            "[bold red]Ollama에 연결할 수 없습니다.[/bold red] [dim]ollama serve[/dim] 후 다시 시도하세요."
        )
        return

    root = _effective_root(state)
    state.run_count += 1
    state.last_cmd = cmd

    console.print(Rule("[dim]파이프라인 시작[/dim]"))
    t0 = time.time()
    try:
        result = run_with_root(cmd, root)
    except Exception as exc:
        console.print(Panel(str(exc), title="오류", border_style="red"))
        return
    elapsed = time.time() - t0
    console.print(Rule(f"[dim]완료 — {elapsed:.1f}s[/dim]"))

    tester_output = result.get("tester_output") or {}
    verdict = tester_output.get("verdict", "unknown")
    final_report = result.get("final_report", "")
    retry_count = result.get("retry_count", 0)
    vc = "green" if verdict == "pass" else "red"
    console.print(
        Panel(
            f"[bold]판정:[/bold] [{vc}]{verdict.upper()}[/{vc}]\n"
            f"[bold]소요:[/bold] {elapsed:.1f}s\n"
            f"[bold]반복:[/bold] {retry_count}\n"
            f"[bold]보고:[/bold] {final_report}",
            title="실행 결과",
            border_style=vc,
        )
    )


def _confirm_full(console: Console) -> bool:
    return Confirm.ask(
        "[bold red]full 모드는 이 머신의 파일 대부분에 접근할 수 있습니다. "
        "정말 전환할까요?[/bold red]",
        default=False,
    )


def _parse_slash(line: str) -> tuple[str, List[str]]:
    parts = shlex.split(line)
    if not parts:
        return "", []
    cmd = parts[0].lower().lstrip("/")
    return cmd, parts[1:]


def run_interactive_session(
    initial_mode: Optional[PermissionMode] = None,
    start_dir: Optional[Path] = None,
) -> None:
    """표준 입력 기반 인터랙티브 세션."""
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import InMemoryHistory
    except ImportError:
        print("prompt_toolkit이 필요합니다: pip install prompt-toolkit", file=sys.stderr)
        sys.exit(1)

    console = Console()
    ws = resolve_workspace_root(start_dir)

    mode = initial_mode or PermissionMode.WORKSPACE
    env_mode = os.environ.get("LOCKY_PERMISSION_MODE", "").lower().strip()
    if env_mode == "full":
        console.print(
            "[yellow]LOCKY_PERMISSION_MODE=full 이 설정되어 있습니다.[/yellow]"
        )
        if not _confirm_full(console):
            mode = PermissionMode.WORKSPACE
        else:
            mode = PermissionMode.FULL

    state = SessionState(workspace_root=ws, mode=mode)
    _banner(console, state)

    history = InMemoryHistory()
    session = PromptSession(history=history)

    help_text = (
        "[dim]일반 텍스트[/dim] — 개발 파이프라인 실행 (/develop 과 동일)\n"
        "/develop [요구사항] — Planner→Coder→Tester 실행\n"
        "/mode workspace|full — 권한 모드 (full 은 확인)\n"
        "/permissions — 현재 모드·루트 표시\n"
        "/clear — 화면 안내 재출력\n"
        "/help — 도움말\n"
        "/exit 또는 /quit — 종료"
    )

    while True:
        try:
            root_hint = str(_effective_root(state))[:48]
            line = session.prompt(f"locky [{root_hint}]> ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]종료합니다.[/dim]")
            break

        line = line.strip()
        if not line:
            continue

        # exit / quit 슬래시 없이도 종료
        if line.lower() in ("exit", "quit"):
            console.print("[dim]종료합니다.[/dim]")
            break

        if line.startswith("/"):
            cmd, args = _parse_slash(line)
            if cmd in ("exit", "quit"):
                console.print("[dim]종료합니다.[/dim]")
                break
            if cmd == "help":
                console.print(Panel(help_text, title="도움말", border_style="dim"))
                continue
            if cmd == "clear":
                console.clear()
                _banner(console, state)
                continue
            if cmd == "permissions":
                console.print(
                    f"모드: [bold]{state.mode.value}[/bold]\n"
                    f"워크스페이스 앵커: {state.workspace_root}\n"
                    f"실제 MCP 루트: {_effective_root(state)}"
                )
                continue
            if cmd == "mode":
                if not args:
                    console.print("[red]사용법:[/red] /mode workspace | /mode full")
                    continue
                m = args[0].lower()
                if m == "workspace":
                    state.mode = PermissionMode.WORKSPACE
                    state.workspace_root = resolve_workspace_root(None)
                    console.print("[green]workspace 모드:[/green] 현재 디렉터리 이하만 허용합니다.")
                    continue
                if m == "full":
                    if not _confirm_full(console):
                        continue
                    state.mode = PermissionMode.FULL
                    console.print("[red]full 모드[/red]: 로컬 전역 접근이 활성화되었습니다.")
                    continue
                console.print("[red]workspace 또는 full 만 지원합니다.[/red]")
                continue
            if cmd == "develop":
                req = " ".join(args).strip()
                if not req:
                    console.print("[red]요구사항을 입력하세요.[/red] 예: /develop JWT 추가")
                    continue
                _run_develop(req, state, console)
                continue
            console.print(f"[red]알 수 없는 명령:[/red] /{cmd} — /help 참고")
            continue

        # 일반 입력 = develop
        _run_develop(line, state, console)
