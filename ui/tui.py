"""ui/tui.py — Rich-based TUI dashboard (Phase 3).

Provides a terminal UI for running locky actions interactively.
Falls back to simple Rich console output if textual is not installed.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

import actions


# Available actions for TUI menu
_ACTIONS = {
    "1": ("format", "코드 포맷팅"),
    "2": ("test", "테스트 실행"),
    "3": ("scan", "보안 스캔"),
    "4": ("deps", "의존성 확인"),
    "5": ("clean", "캐시 정리"),
    "6": ("todo", "TODO 수집"),
    "7": ("commit", "AI 커밋"),
    "8": ("env", ".env.example 생성"),
}


def _run_action(action: str, root: Path, console: Console) -> None:
    """Execute a locky action and display results."""
    runner_map = {
        "format": "format_code",
        "test": "test_runner",
        "scan": "security_scan",
        "deps": "deps_check",
        "clean": "cleanup",
        "todo": "todo_collector",
        "commit": "commit",
        "env": "env_template",
    }

    runner_name = runner_map.get(action)
    if not runner_name:
        console.print(f"[red]Unknown action: {action}[/red]")
        return

    try:
        runner = getattr(actions, runner_name)
        result = runner(root)
    except Exception as exc:
        result = {"status": "error", "message": str(exc)}

    status = result.get("status", "unknown")
    color = "green" if status in ("ok", "pass", "clean") else "red"
    if status == "nothing_to_commit":
        color = "yellow"

    # Build result display
    lines = []
    for key, value in result.items():
        if key == "status":
            continue
        if isinstance(value, list):
            lines.append(f"[bold]{key}[/bold]: {len(value)}개")
        elif isinstance(value, dict):
            lines.append(f"[bold]{key}[/bold]: {value}")
        else:
            text = str(value)[:200]
            lines.append(f"[bold]{key}[/bold]: {text}")

    body = "\n".join(lines) if lines else "(결과 없음)"
    console.print(
        Panel(
            body,
            title=f"[bold]{action}[/bold] — [{color}]{status}[/{color}]",
            border_style=color,
            expand=False,
        )
    )


def _show_menu(console: Console) -> None:
    """Display the TUI action menu."""
    table = Table(title="Locky TUI — 작업 선택", show_header=True)
    table.add_column("번호", style="cyan", width=4)
    table.add_column("명령", style="bold")
    table.add_column("설명")

    for key, (action, desc) in _ACTIONS.items():
        table.add_row(key, action, desc)

    table.add_row("q", "quit", "종료")
    console.print(table)


def _show_status(console: Console, root: Path) -> None:
    """Display project status panel."""
    import subprocess

    # Git status
    try:
        git_result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=5,
        )
        git_status = git_result.stdout.strip() or "(clean)"
    except Exception:
        git_status = "(git not available)"

    # Last commit
    try:
        log_result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=5,
        )
        last_commit = log_result.stdout.strip() or "(no commits)"
    except Exception:
        last_commit = "(unknown)"

    console.print(
        Panel(
            f"[bold]Root:[/bold] {root}\n"
            f"[bold]Git:[/bold] {git_status[:200]}\n"
            f"[bold]Last Commit:[/bold] {last_commit}",
            title="[bold cyan]Project Status[/bold cyan]",
            border_style="cyan",
            expand=False,
        )
    )


def run_tui(root: Path | None = None) -> None:
    """Run the Rich-based TUI dashboard.

    Args:
        root: Project root path (defaults to cwd)
    """
    console = Console()
    root = (root or Path.cwd()).resolve()

    console.print("\n[bold cyan]Locky TUI Dashboard[/bold cyan]")
    console.print("[dim]종료: q 또는 Ctrl+C[/dim]\n")

    _show_status(console, root)

    while True:
        try:
            console.print()
            _show_menu(console)
            choice = Prompt.ask(
                "\n[cyan]실행할 작업 번호[/cyan]",
                choices=list(_ACTIONS.keys()) + ["q"],
                default="q",
            )

            if choice == "q":
                console.print("[dim]종료합니다.[/dim]")
                break

            action, desc = _ACTIONS[choice]
            console.print(f"\n[cyan]{desc} 실행 중...[/cyan]")
            _run_action(action, root, console)

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]종료합니다.[/dim]")
            break
