"""전역 `locky` CLI — Click 그룹."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import time

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.rule import Rule

from locky_cli.fs_context import default_full_access_root
from tools.ollama_client import OllamaClient


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _run_pipeline_once(cmd: str, root: Path, console: Console) -> None:
    from graph import run_with_root

    ollama = OllamaClient()
    if not ollama.health_check():
        console.print(
            Panel(
                "Ollama 서버에 연결할 수 없습니다.\n[cyan]ollama serve[/cyan] 후 다시 시도하세요.",
                title="연결 실패",
                border_style="red",
            )
        )
        raise SystemExit(1)

    console.print(f"\n[bold green]요구사항:[/bold green] {cmd}")
    console.print(f"[dim]MCP 루트:[/dim] {root}\n")
    console.print(Rule("[dim]파이프라인 시작[/dim]"))

    pipeline_start = time.time()
    try:
        result = run_with_root(cmd, root)
    except Exception as exc:
        console.print(Panel(str(exc), title="오류", border_style="red"))
        raise SystemExit(1) from exc

    pipeline_elapsed = time.time() - pipeline_start
    console.print(Rule(f"[dim]파이프라인 완료 — 총 {pipeline_elapsed:.1f}s[/dim]"))

    tester_output = result.get("tester_output") or {}
    verdict = tester_output.get("verdict", "unknown")
    final_report = result.get("final_report", "")
    retry_count = result.get("retry_count", 0)
    messages = result.get("messages", [])
    vc = "green" if verdict == "pass" else "red"

    summary_lines = [
        f"[bold]판정:[/bold] [{vc}]{verdict.upper()}[/{vc}]",
        f"[bold]소요 시간:[/bold] {pipeline_elapsed:.1f}s",
        f"[bold]반복 횟수:[/bold] {retry_count}",
        f"[bold]최종 보고:[/bold] {final_report}",
    ]
    if messages:
        summary_lines.append("\n[bold]로그:[/bold]")
        for msg in messages:
            summary_lines.append(f"  • {msg}")
    if tester_output.get("feedback"):
        summary_lines.append(f"\n[bold]피드백:[/bold]\n{tester_output['feedback']}")

    console.print(
        Panel(
            "\n".join(summary_lines),
            title="Locky 완료",
            border_style=vc,
            expand=False,
        )
    )


@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(version="0.2.0", prog_name="locky")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Locky — 로컬 AI 개발 에이전트."""
    if ctx.invoked_subcommand is None:
        from locky_cli.repl import run_interactive_session

        run_interactive_session()


def _cli_run_pipeline(
    requirement: tuple[str, ...], full: bool, workspace_dir: Path | None
) -> None:
    """run / develop 공통 구현."""
    console = Console()
    cmd = " ".join(requirement).strip()
    if not cmd:
        raise click.UsageError("요구사항 문자열이 필요합니다.")

    root: Path
    if full:
        if not Confirm.ask(
            "[bold red]전체 로컬 디스크에 대한 접근이 허용됩니다. 계속할까요?[/bold red]",
            default=False,
        ):
            raise SystemExit(1)
        root = default_full_access_root()
    else:
        root = (workspace_dir or Path.cwd()).resolve()

    _run_pipeline_once(cmd, root, console)


@cli.command("run", help="요구사항 한 줄로 파이프라인을 한 번 실행합니다.")
@click.argument("requirement", nargs=-1, required=True)
@click.option(
    "--full",
    is_flag=True,
    help="로컬 전체 디스크 권한(확인 프롬프트 표시).",
)
@click.option(
    "--workspace",
    "-w",
    "workspace_dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="워크스페이스 루트(기본: 현재 디렉터리).",
)
def run_cmd(requirement: tuple[str, ...], full: bool, workspace_dir: Path | None) -> None:
    _cli_run_pipeline(requirement, full, workspace_dir)


@cli.command("develop", help="run 과 동일합니다.")
@click.argument("requirement", nargs=-1, required=True)
@click.option(
    "--full",
    is_flag=True,
    help="로컬 전체 디스크 권한(확인 프롬프트 표시).",
)
@click.option(
    "--workspace",
    "-w",
    "workspace_dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="워크스페이스 루트(기본: 현재 디렉터리).",
)
def develop_cmd(requirement: tuple[str, ...], full: bool, workspace_dir: Path | None) -> None:
    _cli_run_pipeline(requirement, full, workspace_dir)


def _launch_chainlit_dashboard() -> None:
    root = _project_root()
    app_py = root / "ui" / "app.py"
    if not app_py.is_file():
        click.echo(f"ui/app.py 을 찾을 수 없습니다: {app_py}", err=True)
        raise SystemExit(1)
    env = os.environ.copy()
    if "MCP_FILESYSTEM_ROOT" not in env:
        env["MCP_FILESYSTEM_ROOT"] = str(Path.cwd().resolve())
    cmd = [
        sys.executable,
        "-m",
        "chainlit",
        "run",
        str(app_py),
        "-w",
        str(root),
    ]
    click.echo(f"Chainlit 시작: {' '.join(cmd)}")
    raise SystemExit(subprocess.call(cmd, cwd=str(root), env=env))


@cli.command("dashboard")
def dashboard_cmd() -> None:
    """Chainlit 웹 대시보드를 실행합니다."""
    _launch_chainlit_dashboard()


@cli.command("web")
def web_cmd() -> None:
    """dashboard 와 동일합니다."""
    _launch_chainlit_dashboard()


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
