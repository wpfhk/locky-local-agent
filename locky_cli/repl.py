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
        print(
            "prompt_toolkit is required: pip install prompt-toolkit", file=sys.stderr
        )
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
