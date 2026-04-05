"""locky CLI -- Click 진입점. REPL + 원샷 모드."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version="1.0.0", prog_name="locky")
@click.option(
    "--workspace",
    "-w",
    "workspace_dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
    default=None,
    help="Workspace root (default: current directory).",
)
@click.option(
    "--command",
    "-c",
    "command_text",
    type=str,
    default=None,
    help="One-shot mode: convert natural language and exit.",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    default=False,
    help="Output raw JSON (for programmatic use).",
)
@click.option(
    "--autopilot",
    "-a",
    "autopilot_text",
    type=str,
    default=None,
    help="Autopilot mode: plan and execute multi-step task.",
)
def cli(
    workspace_dir: Path | None,
    command_text: str | None,
    json_output: bool,
    autopilot_text: str | None,
) -> None:
    """Locky -- Natural Language to Shell Command."""
    if command_text is not None:
        _run_oneshot(workspace_dir, command_text, json_output)
    elif autopilot_text is not None:
        _run_autopilot_session(workspace_dir, autopilot_text)
    else:
        from locky_cli.repl import run_interactive_session

        run_interactive_session(start_dir=workspace_dir)


def _run_oneshot(workspace_dir: Path | None, text: str, json_output: bool) -> None:
    """원샷 모드: 변환 결과 출력 후 종료."""
    from actions.shell_command import run as shell_command_run

    workspace = (workspace_dir or Path.cwd()).resolve()
    result = shell_command_run(workspace, request=text)

    if json_output:
        print(json.dumps(result, ensure_ascii=False))
    else:
        if result["status"] == "ok":
            print(result["command"])
        else:
            print(f"Error: {result['message']}", file=sys.stderr)

    sys.exit(0 if result["status"] == "ok" else 1)


def _run_autopilot_session(workspace_dir: Path | None, text: str) -> None:
    """Autopilot 모드: 계획 생성 후 순차 실행."""
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import InMemoryHistory
    except ImportError:
        print("prompt_toolkit is required: pip install prompt-toolkit", file=sys.stderr)
        sys.exit(1)

    from rich.console import Console

    from locky_cli.autopilot import run_autopilot
    from tools.session_manager import SessionManager

    workspace = (workspace_dir or Path.cwd()).resolve()
    console = Console()
    session = PromptSession(history=InMemoryHistory())
    session_mgr = SessionManager(workspace)

    run_autopilot(console, session, workspace, text, session_mgr)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
