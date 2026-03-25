"""인터랙티브 세션 — Locky 자동화 REPL."""

from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from prompt_toolkit import PromptSession

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from locky_cli.permissions import PermissionMode, resolve_workspace_root


@dataclass
class SessionState:
    """REPL 세션 상태."""

    workspace_root: Path
    mode: PermissionMode = PermissionMode.WORKSPACE


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


def _banner(console: Console, state: SessionState) -> None:
    from locky_cli.config_loader import get_hook_steps, get_ollama_model

    root = state.workspace_root
    model = get_ollama_model(root)
    hook_steps = get_hook_steps(root)

    # profile.json에서 언어 감지 결과 로드
    lang = "unknown"
    try:
        from locky_cli.context import load_profile

        profile = load_profile(root)
        if profile:
            lang = profile.get("language", {}).get("primary", "unknown")
    except Exception:
        pass

    # config.yaml 사용 여부 표시
    config_path = root / ".locky" / "config.yaml"
    model_source = " [dim](config.yaml)[/dim]" if config_path.exists() else ""

    hook_display = " → ".join(hook_steps) if hook_steps else "미설치"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_row("버전", _get_version())
    table.add_row("프로젝트", str(root.name))
    table.add_row("언어", lang)
    table.add_row("모델", f"{model}{model_source}")
    table.add_row("훅", hook_display)
    console.print(
        Panel(
            table,
            title="[bold cyan]Locky[/bold cyan]",
            subtitle="[dim]개발자 귀찮은 작업 자동화 · /help 로 명령 안내[/dim]",
            border_style="cyan",
        )
    )


def _parse_slash(line: str) -> tuple[str, List[str]]:
    try:
        parts = shlex.split(line)
    except ValueError:
        parts = line.split()
    if not parts:
        return "", []
    cmd = parts[0].lower().lstrip("/")
    return cmd, parts[1:]


def _get_root(state: SessionState) -> Path:
    return state.workspace_root


def _print_result(console: Console, result: dict, title: str = "결과") -> None:
    """결과 dict를 Rich Panel로 출력합니다."""
    status = result.get("status", "unknown")
    color = "green" if status in ("ok", "pass", "clean") else "red"
    if status == "nothing_to_commit":
        color = "yellow"

    lines = []
    for key, value in result.items():
        if key == "status":
            continue
        if isinstance(value, list):
            if value:
                lines.append(f"[bold]{key}[/bold] ({len(value)}개):")
                for item in value[:10]:
                    if isinstance(item, dict):
                        # 이슈/항목 요약
                        sev = item.get("severity", "")
                        file_ = item.get("file", item.get("path", ""))
                        line_ = item.get("line", "")
                        desc = item.get("text", item.get("description", str(item)))
                        if sev:
                            lines.append(f"  [{sev}] {file_}:{line_} — {desc}"[:120])
                        else:
                            lines.append(f"  {file_}:{line_} {desc}"[:120])
                    else:
                        lines.append(f"  • {str(item)[:100]}")
                if len(value) > 10:
                    lines.append(f"  ... 외 {len(value) - 10}개")
            else:
                lines.append(f"[bold]{key}[/bold]: (없음)")
        elif isinstance(value, dict):
            sub = ", ".join(f"{k}={v}" for k, v in value.items())
            lines.append(f"[bold]{key}[/bold]: {sub}")
        else:
            val_str = str(value)
            if len(val_str) > 300:
                val_str = val_str[:300] + "..."
            lines.append(f"[bold]{key}[/bold]: {val_str}")

    body = "\n".join(lines) if lines else "(결과 없음)"
    console.print(
        Panel(
            body,
            title=f"{title} — [{color}]{status}[/{color}]",
            border_style=color,
            expand=False,
        )
    )


help_text = (
    "/commit [--dry-run] [--push]  — 커밋 메시지 자동 생성 후 커밋\n"
    "/format [--check] [PATH...]   — black/isort/flake8 실행\n"
    "/test [PATH] [-v]             — pytest 실행\n"
    "/todo [--output FILE]         — TODO/FIXME 수집\n"
    "/scan [--severity LEVEL]      — 보안 패턴 스캔\n"
    "/clean [--force]              — 캐시/임시파일 정리\n"
    "/deps                         — 의존성 버전 확인\n"
    "/env [--output FILE]          — .env.example 생성\n"
    "/update [--check]             — locky 최신 버전으로 업데이트\n"
    "/ask 질문 [파일...]           — AI에게 코드 질문\n"
    "/edit 파일경로 지시사항       — AI 코드 편집 (미리보기)\n"
    "/clear                        — 화면 초기화\n"
    "/help                         — 도움말\n"
    "/exit 또는 /quit              — 종료\n\n"
    "[bold]자연어 명령[/bold] — 슬래시 없이 입력하면 Ollama가 셸 명령으로 변환하여 확인 후 실행\n"
    "  예) 현재 디렉토리에 존재하는 aab를 연결된 단말에 설치해줘"
)


def _handle_free_text(
    console: Console,
    session: "PromptSession",
    state: SessionState,
    text: str,
) -> None:
    """자유 텍스트 입력을 Ollama로 셸 명령으로 변환하고 확인 후 실행합니다."""
    from actions.shell_command import run as shell_command_run

    console.print("[dim]Ollama에 셸 명령 생성 요청 중...[/dim]")
    result = shell_command_run(_get_root(state), request=text)

    if result["status"] != "ok":
        console.print(
            Panel(
                f"[red]{result['message']}[/red]\n\n"
                "[dim]슬래시 명령을 사용하세요: /commit /format /test /help[/dim]",
                title="명령 생성 실패",
                border_style="red",
                expand=False,
            )
        )
        return

    command = result["command"]
    console.print(
        Panel(
            f"[bold cyan]{command}[/bold cyan]",
            title="실행할 명령",
            border_style="cyan",
            expand=False,
        )
    )

    try:
        answer = session.prompt("실행하시겠습니까? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print("[dim]취소되었습니다.[/dim]")
        return

    if answer not in ("y", "yes"):
        console.print("[dim]취소되었습니다.[/dim]")
        return

    workspace_root = str(_get_root(state))
    proc = subprocess.run(
        command,
        shell=True,
        cwd=workspace_root,
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
    body = "\n".join(output_lines) if output_lines else "(출력 없음)"

    console.print(
        Panel(
            body,
            title=f"실행 결과 — [{color}]{status_label}[/{color}] (exit {returncode})",
            border_style=color,
            expand=False,
        )
    )


def run_interactive_session(
    initial_mode: Optional[PermissionMode] = None,
    start_dir: Optional[Path] = None,
) -> None:
    """표준 입력 기반 인터랙티브 세션."""
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import InMemoryHistory
    except ImportError:
        print(
            "prompt_toolkit이 필요합니다: pip install prompt-toolkit", file=sys.stderr
        )
        sys.exit(1)

    console = Console()
    ws = resolve_workspace_root(start_dir)
    mode = initial_mode or PermissionMode.WORKSPACE

    state = SessionState(workspace_root=ws, mode=mode)
    _banner(console, state)

    history = InMemoryHistory()
    session = PromptSession(history=history)

    while True:
        try:
            root_hint = str(_get_root(state))[:48]
            line = session.prompt(f"locky [{root_hint}]> ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]종료합니다.[/dim]")
            break

        line = line.strip()
        if not line:
            continue

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

            if cmd == "commit":
                dry_run = "--dry-run" in args
                push = "--push" in args
                from actions.commit import run

                result = run(_get_root(state), dry_run=dry_run, push=push)
                _print_result(console, result, "commit")
                continue

            if cmd == "format":
                check_only = "--check" in args
                path_args = [a for a in args if not a.startswith("--")]
                from actions.format_code import run

                result = run(
                    _get_root(state), check_only=check_only, paths=path_args or None
                )
                _print_result(console, result, "format")
                # 도구별 상세 출력
                for tool in ["black", "isort", "flake8"]:
                    t = result.get(tool, {})
                    if t.get("output"):
                        console.print(f"[dim]{tool}:[/dim] {t['output'][:200]}")
                continue

            if cmd == "test":
                verbose = "-v" in args or "--verbose" in args
                path_args = [a for a in args if not a.startswith("-")]
                test_path = path_args[0] if path_args else None
                from actions.test_runner import run

                result = run(_get_root(state), path=test_path, verbose=verbose)
                _print_result(console, result, "test")
                continue

            if cmd == "todo":
                output_file = None
                if "--output" in args:
                    idx = args.index("--output")
                    if idx + 1 < len(args):
                        output_file = args[idx + 1]
                from actions.todo_collector import run

                result = run(_get_root(state), output_file=output_file)
                _print_result(console, result, "todo")
                continue

            if cmd == "scan":
                severity = None
                if "--severity" in args:
                    idx = args.index("--severity")
                    if idx + 1 < len(args):
                        severity = args[idx + 1]
                from actions.security_scan import run

                result = run(_get_root(state), severity_filter=severity)
                _print_result(console, result, "scan")
                continue

            if cmd == "clean":
                force = "--force" in args
                from actions.cleanup import run

                result = run(_get_root(state), dry_run=not force)
                _print_result(console, result, "clean")
                if not force:
                    console.print(
                        "[dim]실제 삭제하려면 /clean --force 를 사용하세요.[/dim]"
                    )
                continue

            if cmd == "deps":
                from actions.deps_check import run

                result = run(_get_root(state))
                _print_result(console, result, "deps")
                continue

            if cmd == "env":
                output_file = ".env.example"
                if "--output" in args:
                    idx = args.index("--output")
                    if idx + 1 < len(args):
                        output_file = args[idx + 1]
                from actions.env_template import run

                result = run(_get_root(state), output=output_file)
                _print_result(console, result, "env")
                continue

            if cmd == "update":
                check_only = "--check" in args
                from actions.update import run

                result = run(_get_root(state), check_only=check_only)
                _print_result(console, result, "update")
                continue

            if cmd == "ask":
                from locky.agents.ask_agent import AskAgent
                from locky.core.session import LockySession

                # args 파싱: 파일(.py/.ts 등)과 질문 분리
                files = [a for a in args if "." in a and not a.startswith("-")]
                question_parts = [a for a in args if a not in files]
                question = " ".join(question_parts).strip()

                if not question:
                    console.print("[red]사용법: /ask 질문 [파일...][/red]")
                    continue

                locky_session = LockySession.load(_get_root(state))
                agent = AskAgent(locky_session)
                console.print("[dim]AI가 답변 중...[/dim]")
                answer = agent.run(question, files=files or None)
                console.print(Panel(answer, title="AI 답변", border_style="cyan"))
                continue

            if cmd == "edit":
                from locky.agents.edit_agent import EditAgent
                from locky.core.session import LockySession

                if len(args) < 2:
                    console.print("[red]사용법: /edit 파일경로 지시사항[/red]")
                    continue

                file_path = args[0]
                instruction = " ".join(args[1:])
                locky_session = LockySession.load(_get_root(state))
                agent = EditAgent(locky_session)
                result = agent.run(instruction, file_path=file_path, dry_run=True)
                diff_text = result.get("diff") or result.get("message", "")
                console.print(
                    Panel(
                        diff_text,
                        title=f"diff 미리보기 — {result['status']} (적용: locky edit --apply)",
                        border_style="yellow",
                    )
                )
                continue

            console.print(
                f"[red]알 수 없는 명령:[/red] /{cmd}\n"
                "[dim]지원하는 명령: /commit /format /test /todo /scan /clean /deps /env /ask /edit /help[/dim]"
            )
            continue

        # 일반 텍스트 입력 — Ollama로 셸 명령 변환 후 사용자 확인
        _handle_free_text(console, session, state, line)
