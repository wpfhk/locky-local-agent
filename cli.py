"""Locky CLI 진입점 — Click + Rich."""

from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from tools.ollama_client import OllamaClient

console = Console()


def _print_banner() -> None:
    """시작 배너를 Rich Panel로 출력합니다."""
    console.print(
        Panel(
            "[bold cyan]🔒 Locky — Local AI Agent[/bold cyan]\n"
            "[dim]Planner → Coder → Tester[/dim]",
            expand=False,
            border_style="cyan",
        )
    )


@click.command()
@click.argument("cmd")
def develop(cmd: str) -> None:
    """/develop {CMD} — Locky AI 개발 에이전트 실행."""
    _print_banner()

    # Ollama 상태 확인
    ollama = OllamaClient()
    console.print("[dim]Ollama 서버 상태 확인 중...[/dim]")
    if not ollama.health_check():
        console.print(
            Panel(
                "[bold red]오류:[/bold red] Ollama 서버에 연결할 수 없습니다.\n"
                "Ollama가 실행 중인지 확인하세요: [cyan]ollama serve[/cyan]",
                title="[red]연결 실패[/red]",
                border_style="red",
            )
        )
        sys.exit(1)

    console.print(f"\n[bold green]요구사항:[/bold green] {cmd}\n")

    # 각 단계별 스피너 표시하며 그래프 실행
    from graph import run  # 지연 임포트 (그래프 로딩 비용 최소화)

    result: dict = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=False,
    ) as progress:
        planning_task = progress.add_task("[cyan]Planning...[/cyan]", total=None)

        # 그래프를 직접 단계별로 실행하는 대신 run()을 호출하고
        # 단계 완료 시 스피너를 업데이트합니다.
        # LangGraph는 동기 invoke를 지원하므로 순차 실행됩니다.

        try:
            # Planning 단계 시뮬레이션 (그래프 내부에서 실제 실행)
            progress.update(planning_task, description="[cyan]Planning...[/cyan]")

            coding_task = progress.add_task("[yellow]Coding...[/yellow]", total=None, visible=False)
            testing_task = progress.add_task("[magenta]Testing...[/magenta]", total=None, visible=False)

            result = run(cmd)

            # 완료 표시
            progress.update(planning_task, description="[green]Planning  [/green]")
            progress.update(coding_task, visible=True, description="[green]Coding    [/green]")
            progress.update(testing_task, visible=True, description="[green]Testing   [/green]")

        except Exception as exc:
            progress.stop()
            console.print(
                Panel(
                    f"[bold red]파이프라인 실행 중 오류 발생:[/bold red]\n{exc}",
                    title="[red]오류[/red]",
                    border_style="red",
                )
            )
            sys.exit(1)

    # 최종 결과 출력
    tester_output = result.get("tester_output") or {}
    verdict = tester_output.get("verdict", "unknown")
    final_report = result.get("final_report", "")
    retry_count = result.get("retry_count", 0)
    messages = result.get("messages", [])

    verdict_color = "green" if verdict == "pass" else "red"
    verdict_icon = "✅" if verdict == "pass" else "❌"

    summary_lines = [
        f"[bold]판정:[/bold] [{verdict_color}]{verdict_icon} {verdict.upper()}[/{verdict_color}]",
        f"[bold]반복 횟수:[/bold] {retry_count}",
        f"[bold]최종 보고:[/bold] {final_report}",
    ]

    if messages:
        summary_lines.append("\n[bold]실행 로그:[/bold]")
        for msg in messages:
            summary_lines.append(f"  • {msg}")

    if tester_output.get("feedback"):
        summary_lines.append(f"\n[bold]피드백:[/bold]\n{tester_output['feedback']}")

    console.print(
        Panel(
            "\n".join(summary_lines),
            title=f"[bold]Locky 실행 완료 — {cmd[:50]}[/bold]",
            border_style=verdict_color,
            expand=False,
        )
    )


if __name__ == "__main__":
    develop()
