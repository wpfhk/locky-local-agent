"""locky_cli/autopilot.py -- Autopilot 실행 엔진 (v0.6.0: 파일 편집 + 상태 추적)."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prompt_toolkit import PromptSession
    from rich.console import Console

from rich.panel import Panel
from rich.table import Table


# ---------------------------------------------------------------------------
# State tracking
# ---------------------------------------------------------------------------


def _write_state(workspace: Path, request: str, step: dict, thought: str = "") -> None:
    """현재 에이전트 상태를 .omc/state/agent_state.json에 기록합니다."""
    state_dir = workspace / ".omc" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "request": request,
        "current_step": step,
        "thought": thought,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    (state_dir / "agent_state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Command execution helpers
# ---------------------------------------------------------------------------


def _execute_command(command: str, workspace: Path) -> tuple[int, str, str]:
    """셸 명령을 실행하고 (returncode, stdout, stderr)을 반환합니다."""
    proc = subprocess.run(
        command,
        shell=True,
        cwd=str(workspace),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _show_result(
    console: "Console",
    returncode: int,
    stdout: str,
    stderr: str,
    title_prefix: str = "Result",
) -> None:
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
            title=f"{title_prefix} -- [{color}]{status_label}[/{color}] (exit {returncode})",
            border_style=color,
            expand=False,
        )
    )


# ---------------------------------------------------------------------------
# Special tool handlers
# ---------------------------------------------------------------------------


def _handle_read_file(
    console: "Console",
    workspace: Path,
    step: dict,
) -> tuple[bool, str, str]:
    """read_file 도구를 처리합니다. (success, stdout, stderr)"""
    from tools.editor import read_file_range

    rel_path = step.get("path", "")
    if not rel_path:
        return False, "", "read_file: 'path' field missing"

    target = (workspace / rel_path).resolve()
    if not target.is_relative_to(workspace):
        return False, "", f"read_file: path escapes workspace: {rel_path}"
    content = read_file_range(target)
    console.print(
        Panel(
            content[:3000],
            title=f"[cyan]{rel_path}[/cyan]",
            border_style="cyan",
            expand=False,
        )
    )
    return True, content, ""


def _handle_edit_file(
    console: "Console",
    session: "PromptSession",
    workspace: Path,
    step: dict,
) -> tuple[bool, str, str]:
    """edit_file 도구를 처리합니다. diff 미리보기 후 사용자 승인. (success, stdout, stderr)"""
    from tools.editor import diff_markup, replace_in_file

    rel_path = step.get("path", "")
    old_text = step.get("old", "")
    new_text = step.get("new", "")

    if not rel_path:
        return False, "", "edit_file: 'path' field missing"
    if old_text == "":
        return False, "", "edit_file: 'old' field missing"

    target = (workspace / rel_path).resolve()
    if not target.is_relative_to(workspace):
        return False, "", f"edit_file: path escapes workspace: {rel_path}"
    if not target.is_file():
        return False, "", f"edit_file: file not found: {rel_path}"

    # Dry run: compute diff without writing
    import shutil as _shutil
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as f:
        tmp = Path(f.name)
    try:
        _shutil.copy2(target, tmp)
        ok_dry, diff = replace_in_file(tmp, old_text, new_text, backup=False)
    finally:
        tmp.unlink(missing_ok=True)

    if not ok_dry:
        return False, "", f"edit_file: pattern not found in {rel_path}"

    if diff:
        console.print(
            Panel(
                diff_markup(diff),
                title=f"Diff preview -- [cyan]{rel_path}[/cyan]",
                border_style="yellow",
                expand=False,
            )
        )
    else:
        console.print(f"[dim]No changes in {rel_path}[/dim]")
        return True, "(no changes)", ""

    try:
        ans = session.prompt("Apply this edit? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False, "", "Cancelled"

    if ans not in ("y", "yes"):
        console.print("[dim]Edit skipped.[/dim]")
        return True, "(skipped)", ""

    ok, _ = replace_in_file(target, old_text, new_text, backup=True)
    if ok:
        console.print(
            f"[green]Saved {rel_path}[/green] ([dim]backup: {rel_path}.bak[/dim])"
        )
        return True, f"Edited {rel_path}", ""
    else:
        return False, "", f"edit_file: write failed for {rel_path}"


# ---------------------------------------------------------------------------
# Main autopilot engine
# ---------------------------------------------------------------------------


def run_autopilot(
    console: "Console",
    session: "PromptSession",
    workspace: Path,
    request: str,
    session_mgr=None,
) -> None:
    """Autopilot: 복잡한 요청을 다단계로 계획하고 순차 실행합니다."""
    from actions.shell_command import run_fix
    from tools.planner import evaluate_progress, generate_plan, is_dangerous, save_plan

    try:
        with console.status("[dim]Planning steps...[/dim]", spinner="dots"):
            steps = generate_plan(workspace, request)
    except Exception as exc:
        console.print(
            Panel(
                f"[red]Plan generation failed: {exc}[/red]",
                border_style="red",
                expand=False,
            )
        )
        return

    if not steps:
        console.print(
            Panel(
                "[red]Could not generate a valid plan.[/red]",
                border_style="red",
                expand=False,
            )
        )
        return

    # Display plan table
    plan_path = save_plan(workspace, request, steps)

    table = Table(title="Autopilot Plan", show_header=True, header_style="bold cyan")
    table.add_column("Step", width=5, justify="center")
    table.add_column("Description", min_width=28)
    table.add_column("Command", min_width=28)
    for s in steps:
        cmd_display = s["command"]
        if s["command"] in ("edit_file", "read_file"):
            path_display = s.get("path", "")
            cmd_display = f"[tool]{s['command']}({path_display})[/tool]"
        table.add_row(str(s["step"]), s["description"], f"[cyan]{cmd_display}[/cyan]")
    console.print(table)
    console.print(f"[dim]Plan saved → {plan_path.relative_to(workspace)}[/dim]")

    try:
        confirm = (
            session.prompt(f"\nExecute this {len(steps)}-step plan? [y/N] ")
            .strip()
            .lower()
        )
    except (EOFError, KeyboardInterrupt):
        console.print("[dim]Cancelled.[/dim]")
        return
    if confirm not in ("y", "yes"):
        console.print("[dim]Cancelled.[/dim]")
        return

    completed = 0
    failed_at = None
    completed_steps: list[dict] = []

    for i, step in enumerate(steps, 1):
        command = step["command"]
        description = step["description"]

        console.print(f"\n[bold cyan]Step {i}/{len(steps)}:[/bold cyan] {description}")
        _write_state(
            workspace, request, step, thought=f"Executing step {i}/{len(steps)}"
        )

        # --- Special tools ---
        if command == "read_file":
            success, stdout, stderr = _handle_read_file(console, workspace, step)
        elif command == "edit_file":
            console.print(
                Panel(
                    f"[bold cyan]edit_file:[/bold cyan] {step.get('path', '')}",
                    border_style="cyan",
                    expand=False,
                )
            )
            success, stdout, stderr = _handle_edit_file(
                console, session, workspace, step
            )
        else:
            # Regular shell command
            console.print(
                Panel(
                    f"[bold cyan]{command}[/bold cyan]",
                    border_style="cyan",
                    expand=False,
                )
            )

            # Dangerous command check
            if is_dangerous(command):
                console.print(
                    Panel(
                        f"[bold red]WARNING: Destructive command![/bold red]\n[red]{command}[/red]",
                        title="Dangerous Command",
                        border_style="red",
                        expand=False,
                    )
                )
                try:
                    danger_ans = session.prompt(
                        "Type 'yes' to confirm, or Enter to skip: "
                    ).strip()
                except (EOFError, KeyboardInterrupt):
                    console.print("[dim]Plan aborted.[/dim]")
                    break
                if danger_ans != "yes":
                    console.print("[dim]Skipped (dangerous).[/dim]")
                    completed += 1
                    continue
            else:
                try:
                    ans = (
                        session.prompt("[y] Execute / [s] Skip / [q] Quit: ")
                        .strip()
                        .lower()
                    )
                except (EOFError, KeyboardInterrupt):
                    console.print("\n[dim]Plan aborted.[/dim]")
                    break
                if ans == "q":
                    console.print("[dim]Plan aborted.[/dim]")
                    break
                elif ans in ("s", "") or ans not in ("y", "yes"):
                    console.print("[dim]Skipped.[/dim]")
                    completed += 1
                    continue

            returncode, stdout, stderr = _execute_command(command, workspace)
            _show_result(console, returncode, stdout, stderr, f"Step {i}/{len(steps)}")
            success = returncode == 0

            if not success:
                failed_at = i
                try:
                    with console.status(
                        f"[dim]Step {i} failed. Analyzing error...[/dim]",
                        spinner="dots",
                    ):
                        fix_result = run_fix(workspace, description, command, stderr)
                except KeyboardInterrupt:
                    console.print("[dim]Plan aborted.[/dim]")
                    break

                if fix_result["status"] == "ok":
                    fixed_cmd = fix_result["command"]
                    console.print(
                        Panel(
                            f"[bold yellow]{fixed_cmd}[/bold yellow]",
                            title="Suggested fix",
                            border_style="yellow",
                            expand=False,
                        )
                    )
                    try:
                        fix_ans = session.prompt("Execute fix? [y/N] ").strip().lower()
                    except (EOFError, KeyboardInterrupt):
                        console.print("[dim]Plan aborted.[/dim]")
                        break

                    if fix_ans in ("y", "yes"):
                        rc2, out2, err2 = _execute_command(fixed_cmd, workspace)
                        _show_result(console, rc2, out2, err2, "Fix result")
                        if rc2 == 0:
                            stdout, stderr = out2, err2
                            success = True
                            failed_at = None
                            if session_mgr:
                                session_mgr.record(
                                    f"(autopilot fix step {i}) {description}",
                                    fixed_cmd,
                                    0,
                                    out2,
                                )

                if not success:
                    console.print(
                        f"\n[red]Plan stopped at step {i}/{len(steps)}.[/red]"
                    )
                    break

        if success:
            step_record = {**step, "exit_code": 0, "output": stdout[:200]}
            completed_steps.append(step_record)
            if session_mgr:
                session_mgr.record(
                    f"(autopilot step {i}) {description}", command, 0, stdout
                )
            completed += 1

    # Post-execution evaluation
    if completed == len(steps) and not failed_at:
        _write_state(workspace, request, {}, thought="Evaluating goal completion")
        try:
            with console.status(
                "[dim]Evaluating goal completion...[/dim]", spinner="dots"
            ):
                eval_result = evaluate_progress(workspace, request, completed_steps)
            thought = eval_result.get("thought", "")
            achieved = eval_result.get("goal_achieved", True)
            if thought:
                console.print(f"[dim]Assessment: {thought}[/dim]")
        except Exception:
            achieved = True

        color = "green" if achieved else "yellow"
        label = "Goal achieved" if achieved else "Partially achieved"
        console.print(
            Panel(
                f"[{color}]All {len(steps)} steps completed. {label}.[/{color}]",
                title="Autopilot Complete",
                border_style=color,
                expand=False,
            )
        )
    else:
        status = f"[yellow]{completed}/{len(steps)} steps completed.[/yellow]"
        if failed_at:
            status += f"\n[red]Stopped at step {failed_at}.[/red]"
        console.print(
            Panel(
                status, title="Autopilot Summary", border_style="yellow", expand=False
            )
        )

    _write_state(workspace, request, {}, thought="Plan finished")
