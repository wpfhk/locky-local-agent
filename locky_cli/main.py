"""전역 `locky` CLI — Click 그룹."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _get_root(workspace_dir: Path | None) -> Path:
    return (workspace_dir or Path.cwd()).resolve()


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
                lines.append(f"[bold]{key}[/bold]:")
                for item in value[:20]:
                    if isinstance(item, dict):
                        lines.append(f"  • {item}")
                    else:
                        lines.append(f"  • {item}")
                if len(value) > 20:
                    lines.append(f"  ... 외 {len(value) - 20}개")
            else:
                lines.append(f"[bold]{key}[/bold]: (없음)")
        elif isinstance(value, dict):
            lines.append(f"[bold]{key}[/bold]: {value}")
        else:
            lines.append(f"[bold]{key}[/bold]: {value}")

    body = "\n".join(lines) if lines else "(결과 없음)"
    console.print(
        Panel(
            body,
            title=f"[bold]{title}[/bold] — [{color}]{status}[/{color}]",
            border_style=color,
            expand=False,
        )
    )


@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(version="1.1.0", prog_name="locky")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Locky — 개발자 귀찮은 작업 자동화 도구."""
    if ctx.invoked_subcommand is None:
        from locky_cli.repl import run_interactive_session

        run_interactive_session()


@cli.command("commit")
@click.option("--dry-run", is_flag=True, help="메시지만 생성하고 커밋하지 않음.")
@click.option("--push", is_flag=True, help="커밋 후 push까지 수행.")
@click.option(
    "--workspace", "-w",
    "workspace_dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="워크스페이스 루트(기본: 현재 디렉터리).",
)
def commit_cmd(dry_run: bool, push: bool, workspace_dir: Path | None) -> None:
    """커밋 메시지를 자동 생성하고 커밋합니다."""
    from actions.commit import run

    console = Console()
    root = _get_root(workspace_dir)
    console.print(f"[dim]루트:[/dim] {root}")

    result = run(root, dry_run=dry_run, push=push)
    _print_result(console, result, "locky commit")


@cli.command("format")
@click.option("--check", is_flag=True, help="수정하지 않고 검사만 수행.")
@click.option(
    "--lang", "-l",
    default="auto",
    show_default=True,
    help="사용할 언어 (auto/python/javascript/typescript/go/rust 등).",
)
@click.argument("paths", nargs=-1)
@click.option(
    "--workspace", "-w",
    "workspace_dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="워크스페이스 루트(기본: 현재 디렉터리).",
)
def format_cmd(check: bool, lang: str, paths: tuple, workspace_dir: Path | None) -> None:
    """black/isort/flake8 또는 언어별 포맷터를 실행합니다."""
    from actions.format_code import run

    console = Console()
    root = _get_root(workspace_dir)
    path_list = list(paths) if paths else None

    console.print(f"[dim]루트:[/dim] {root}")
    result = run(root, check_only=check, paths=path_list, lang=lang)

    status = result.get("status", "ok")
    lang = result.get("language", "python")
    color = "green" if status == "ok" else "red"

    # 결과에서 도구 항목만 추출 (status, language 키 제외)
    _skip = {"status", "language"}
    tool_names = [k for k, v in result.items() if k not in _skip and isinstance(v, dict)]

    table = Table(title=f"포맷 결과 [{lang}]", show_header=True)
    table.add_column("도구", style="cyan")
    table.add_column("상태")
    table.add_column("출력")

    for tool in tool_names:
        tool_result = result.get(tool, {})
        tool_status = tool_result.get("status", "unknown")
        tool_output = (tool_result.get("output", "") or "")[:120]
        t_color = "green" if tool_status == "ok" else ("dim" if tool_status == "not_installed" else "red")
        table.add_row(tool, f"[{t_color}]{tool_status}[/{t_color}]", tool_output)

    console.print(table)


@cli.command("test")
@click.argument("path", required=False, default=None)
@click.option("-v", "--verbose", is_flag=True, help="상세 출력.")
@click.option(
    "--workspace", "-w",
    "workspace_dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="워크스페이스 루트(기본: 현재 디렉터리).",
)
def test_cmd(path: str | None, verbose: bool, workspace_dir: Path | None) -> None:
    """pytest를 실행합니다."""
    from actions.test_runner import run

    console = Console()
    root = _get_root(workspace_dir)
    console.print(f"[dim]루트:[/dim] {root}")

    result = run(root, path=path, verbose=verbose)
    status = result.get("status", "error")
    color = "green" if status == "pass" else "red"

    table = Table(title=f"테스트 결과 — [{color}]{status.upper()}[/{color}]", show_header=True)
    table.add_column("항목", style="cyan")
    table.add_column("값")

    table.add_row("통과", str(result.get("passed", 0)))
    table.add_row("실패", str(result.get("failed", 0)))
    table.add_row("오류", str(result.get("errors", 0)))
    table.add_row("소요 시간", f"{result.get('duration', 0):.2f}s")

    console.print(table)

    output = result.get("output", "")
    if output:
        console.print(Panel(output[-2000:], title="pytest 출력", border_style="dim"))


@cli.command("todo")
@click.option("--output", "-o", default=None, help="결과를 저장할 마크다운 파일.")
@click.option(
    "--workspace", "-w",
    "workspace_dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="워크스페이스 루트(기본: 현재 디렉터리).",
)
def todo_cmd(output: str | None, workspace_dir: Path | None) -> None:
    """TODO/FIXME/HACK/XXX를 수집합니다."""
    from actions.todo_collector import run

    console = Console()
    root = _get_root(workspace_dir)
    console.print(f"[dim]루트:[/dim] {root}")

    result = run(root, output_file=output)
    items = result.get("items", [])

    table = Table(title=f"TODO 목록 — 총 {result.get('total', 0)}개", show_header=True)
    table.add_column("태그", style="yellow", width=8)
    table.add_column("파일:줄", style="cyan")
    table.add_column("내용")

    for item in items[:50]:
        table.add_row(
            item.get("tag", ""),
            f"{item.get('file', '')}:{item.get('line', '')}",
            item.get("text", "")[:80],
        )
    if len(items) > 50:
        console.print(f"[dim]... 외 {len(items) - 50}개[/dim]")

    console.print(table)
    if output:
        console.print(f"[green]결과 저장:[/green] {output}")


@cli.command("scan")
@click.option(
    "--severity", "-s",
    default=None,
    type=click.Choice(["critical", "high", "medium", "low"], case_sensitive=False),
    help="심각도 필터.",
)
@click.option(
    "--workspace", "-w",
    "workspace_dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="워크스페이스 루트(기본: 현재 디렉터리).",
)
def scan_cmd(severity: str | None, workspace_dir: Path | None) -> None:
    """보안 패턴을 스캔합니다."""
    from actions.security_scan import run

    console = Console()
    root = _get_root(workspace_dir)
    console.print(f"[dim]루트:[/dim] {root}")

    result = run(root, severity_filter=severity)
    status = result.get("status", "unknown")
    color = "green" if status == "clean" else "red"
    summary = result.get("summary", {})
    issues = result.get("issues", [])

    # 요약 테이블
    sum_table = Table(title=f"보안 스캔 — [{color}]{status}[/{color}]", show_header=True)
    sum_table.add_column("심각도", style="cyan")
    sum_table.add_column("건수")
    for sev in ["critical", "high", "medium", "low"]:
        cnt = summary.get(sev, 0)
        sev_color = {"critical": "red", "high": "orange3", "medium": "yellow", "low": "dim"}.get(sev, "white")
        sum_table.add_row(f"[{sev_color}]{sev}[/{sev_color}]", str(cnt))
    console.print(sum_table)

    if issues:
        issue_table = Table(title="이슈 목록", show_header=True)
        issue_table.add_column("심각도", width=10)
        issue_table.add_column("파일:줄", style="cyan")
        issue_table.add_column("설명")
        for issue in issues[:30]:
            sev = issue.get("severity", "low")
            sev_color = {"critical": "red", "high": "orange3", "medium": "yellow", "low": "dim"}.get(sev, "white")
            issue_table.add_row(
                f"[{sev_color}]{sev}[/{sev_color}]",
                f"{issue.get('file', '')}:{issue.get('line', '')}",
                issue.get("description", ""),
            )
        if len(issues) > 30:
            console.print(f"[dim]... 외 {len(issues) - 30}개[/dim]")
        console.print(issue_table)


@cli.command("clean")
@click.option("--force", is_flag=True, help="실제 삭제 수행 (기본은 dry-run).")
@click.option(
    "--workspace", "-w",
    "workspace_dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="워크스페이스 루트(기본: 현재 디렉터리).",
)
def clean_cmd(force: bool, workspace_dir: Path | None) -> None:
    """캐시/임시 파일을 정리합니다."""
    from actions.cleanup import run

    console = Console()
    root = _get_root(workspace_dir)
    dry_run = not force
    console.print(f"[dim]루트:[/dim] {root}")
    if dry_run:
        console.print("[yellow]dry-run 모드:[/yellow] 실제 삭제하려면 --force를 사용하세요.")

    result = run(root, dry_run=dry_run)
    removed = result.get("removed", [])
    total_size = result.get("total_size_bytes", 0)
    action = "삭제 예정" if dry_run else "삭제됨"

    table = Table(title=f"정리 대상 — {len(removed)}개 ({_human_size(total_size)})", show_header=True)
    table.add_column(action, style="cyan")
    for path in removed[:40]:
        table.add_row(path)
    if len(removed) > 40:
        console.print(f"[dim]... 외 {len(removed) - 40}개[/dim]")
    console.print(table)


@cli.command("deps")
@click.option(
    "--workspace", "-w",
    "workspace_dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="워크스페이스 루트(기본: 현재 디렉터리).",
)
def deps_cmd(workspace_dir: Path | None) -> None:
    """의존성 버전을 확인합니다."""
    from actions.deps_check import run

    console = Console()
    root = _get_root(workspace_dir)
    console.print(f"[dim]루트:[/dim] {root}")

    result = run(root)
    if result.get("status") == "error":
        console.print(Panel(result.get("message", "오류"), title="오류", border_style="red"))
        return

    packages = result.get("packages", [])
    table = Table(title=f"의존성 확인 — {len(packages)}개", show_header=True)
    table.add_column("패키지", style="cyan")
    table.add_column("required")
    table.add_column("installed")
    table.add_column("상태")

    for pkg in packages:
        outdated = pkg.get("outdated", False)
        installed = pkg.get("installed", "")
        status_str = "[red]미설치/불일치[/red]" if outdated else "[green]OK[/green]"
        if installed == "not_installed":
            status_str = "[red]미설치[/red]"
        table.add_row(
            pkg.get("name", ""),
            pkg.get("required", ""),
            installed,
            status_str,
        )
    console.print(table)


@cli.command("env")
@click.option("--output", "-o", default=".env.example", help="출력 파일명 (기본: .env.example).")
@click.option(
    "--workspace", "-w",
    "workspace_dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="워크스페이스 루트(기본: 현재 디렉터리).",
)
def env_cmd(output: str, workspace_dir: Path | None) -> None:
    """.env.example을 생성합니다."""
    from actions.env_template import run

    console = Console()
    root = _get_root(workspace_dir)
    console.print(f"[dim]루트:[/dim] {root}")

    result = run(root, output=output)
    status = result.get("status", "unknown")
    keys = result.get("keys", [])

    color = "green" if status == "ok" else "yellow"
    console.print(
        Panel(
            f"[bold]출력 파일:[/bold] {result.get('output_file', '')}\n"
            f"[bold]수집된 키:[/bold] {len(keys)}개\n"
            + "\n".join(f"  • {k}" for k in keys[:20])
            + (f"\n  ... 외 {len(keys) - 20}개" if len(keys) > 20 else ""),
            title=f"[bold]locky env[/bold] — [{color}]{status}[/{color}]",
            border_style=color,
            expand=False,
        )
    )


@cli.command("run")
@click.argument("steps", nargs=-1, required=True)
@click.option("--no-fail-fast", "fail_fast", is_flag=True, default=True, flag_value=False,
              help="실패해도 나머지 단계를 계속 실행합니다.")
@click.option(
    "--workspace", "-w",
    "workspace_dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="워크스페이스 루트(기본: 현재 디렉터리).",
)
def run_cmd(steps: tuple, fail_fast: bool, workspace_dir: Path | None) -> None:
    """여러 명령을 순서대로 실행합니다. 예: locky run format test commit"""
    from actions.pipeline import run

    console = Console()
    root = _get_root(workspace_dir)
    steps_str = " ".join(steps)
    console.print(f"[dim]루트:[/dim] {root}")
    console.print(f"[dim]단계:[/dim] {steps_str}")

    result = run(root, steps=steps_str, fail_fast=fail_fast)

    if result.get("status") == "error" and not result.get("results"):
        console.print(Panel(result.get("message", "오류"), title="오류", border_style="red"))
        return

    table = Table(title=f"파이프라인 결과 — {result['executed']}/{result['total']} 단계", show_header=True)
    table.add_column("단계", style="cyan", width=12)
    table.add_column("상태")
    table.add_column("메시지")

    for step_result in result.get("results", []):
        step = step_result.get("step", "")
        s = step_result.get("status", "unknown")
        msg = step_result.get("message", step_result.get("output", ""))
        if isinstance(msg, str):
            msg = msg[:80]
        else:
            msg = ""
        s_color = "green" if s in ("ok", "pass", "clean", "nothing_to_commit") else "red"
        table.add_row(step, f"[{s_color}]{s}[/{s_color}]", msg)

    console.print(table)

    failed_at = result.get("failed_at")
    if failed_at:
        console.print(f"[red]'{failed_at}' 단계에서 중단되었습니다.[/red]")


@cli.command("hook")
@click.argument("action", type=click.Choice(["install", "uninstall", "status"]), default="install")
@click.option(
    "--steps", "-s",
    default="format,test,scan",
    show_default=True,
    help="실행할 단계(쉼표 구분): format, test, scan",
)
@click.option(
    "--workspace", "-w",
    "workspace_dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="워크스페이스 루트(기본: 현재 디렉터리).",
)
def hook_cmd(action: str, steps: str, workspace_dir: Path | None) -> None:
    """pre-commit hook을 설치·제거·상태 확인합니다."""
    from actions.hook import run

    console = Console()
    root = _get_root(workspace_dir)
    console.print(f"[dim]루트:[/dim] {root}")

    step_list = [s.strip() for s in steps.split(",") if s.strip()]
    result = run(root, action=action, steps=step_list)
    _print_result(console, result, f"locky hook {action}")


@cli.command("init")
@click.option(
    "--workspace", "-w",
    "workspace_dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="워크스페이스 루트(기본: 현재 디렉터리).",
)
def init_cmd(workspace_dir: Path | None) -> None:
    """프로젝트를 초기화합니다 (.locky/config.yaml 생성, hook 설치)."""
    import yaml  # type: ignore
    from locky_cli.context import detect_and_save
    from actions.hook import run as hook_run

    console = Console()
    root = _get_root(workspace_dir)
    console.print(f"\n[bold cyan]Locky 프로젝트 설정을 시작합니다.[/bold cyan]")
    console.print(f"[dim]루트:[/dim] {root}\n")

    # 1. Ollama 모델 선택
    model = click.prompt(
        "Ollama 모델을 선택하세요",
        default="qwen2.5-coder:7b",
        show_default=True,
    )

    # 2. hook 설치 여부
    install_hook = click.confirm("pre-commit 훅을 설치할까요?", default=True)

    # 3. hook 스텝 선택
    hook_steps_str = "format,test,scan"
    if install_hook:
        hook_steps_str = click.prompt(
            "훅 실행 스텝 (쉼표 구분)",
            default="format,test,scan",
            show_default=True,
        )

    # 4. config.yaml 생성
    locky_dir = root / ".locky"
    locky_dir.mkdir(exist_ok=True)
    config_path = locky_dir / "config.yaml"

    hook_steps = [s.strip() for s in hook_steps_str.split(",") if s.strip()]
    config_data = {
        "ollama": {"model": model},
        "hook": {"steps": hook_steps},
        "init": {"auto_profile": True},
    }
    config_path.write_text(yaml.dump(config_data, allow_unicode=True, default_flow_style=False))
    console.print(f"\n[green]✓[/green] .locky/config.yaml 생성 완료")

    # 5. 프로젝트 컨텍스트 감지 및 저장
    console.print("[cyan]프로젝트 컨텍스트 감지 중...[/cyan]")
    try:
        profile = detect_and_save(root)
        lang = profile.get("language", {}).get("primary", "unknown")
        console.print(f"[green]✓[/green] 언어 감지: [bold]{lang}[/bold]  (.locky/profile.json 저장)")
    except Exception:
        console.print("[dim]프로파일 감지 생략[/dim]")

    # 6. hook 설치
    if install_hook:
        hook_result = hook_run(root, action="install", steps=hook_steps)
        hook_status = hook_result.get("status", "error")
        if hook_status == "ok":
            console.print(f"[green]✓[/green] pre-commit 훅 설치 완료 ({' → '.join(hook_steps)})")
        else:
            console.print(f"[yellow]![/yellow] 훅 설치: {hook_result.get('message', hook_status)}")

    console.print("\n[bold green]초기화 완료![/bold green] `locky --help`로 사용법을 확인하세요.")


@cli.command("update")
@click.option("--check", is_flag=True, help="버전 확인만 (업데이트하지 않음).")
def update_cmd(check: bool) -> None:
    """locky를 최신 버전으로 업데이트합니다."""
    from actions.update import run

    console = Console()
    if not check:
        console.print("[cyan]업데이트를 확인하는 중...[/cyan]")
    result = run(Path.cwd(), check_only=check)
    _print_result(console, result, "locky update")


@cli.group("plugin")
def plugin_group() -> None:
    """플러그인을 관리합니다."""


@plugin_group.command("list")
def plugin_list_cmd() -> None:
    """설치된 플러그인 목록을 표시합니다."""
    console = Console()
    plugins = _load_plugins()

    if not plugins:
        console.print("[dim]설치된 플러그인이 없습니다.[/dim]")
        console.print(f"[dim]플러그인 경로: {Path.home() / '.locky' / 'plugins'}[/dim]")
        return

    table = Table(title=f"플러그인 목록 — {len(plugins)}개", show_header=True)
    table.add_column("이름", style="cyan")
    table.add_column("버전")
    table.add_column("설명")

    for name, mod in plugins.items():
        version = getattr(mod, "PLUGIN_VERSION", "?")
        desc = getattr(mod, "PLUGIN_DESCRIPTION", "")
        table.add_row(name, version, desc)

    console.print(table)


def _load_plugins() -> dict:
    """~/.locky/plugins/{name}/action.py 플러그인을 로드합니다."""
    plugins_dir = Path.home() / ".locky" / "plugins"
    if not plugins_dir.is_dir():
        return {}

    loaded = {}
    for plugin_dir in sorted(plugins_dir.iterdir()):
        if not plugin_dir.is_dir():
            continue
        action_file = plugin_dir / "action.py"
        if not action_file.exists():
            continue
        try:
            spec = importlib.util.spec_from_file_location(plugin_dir.name, action_file)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            plugin_name = getattr(mod, "PLUGIN_NAME", plugin_dir.name)
            loaded[plugin_name] = mod
        except Exception:
            pass  # 플러그인 로드 실패 시 무시
    return loaded


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


def _human_size(size_bytes: int) -> str:
    """바이트를 사람이 읽기 좋은 형태로 변환합니다."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
