"""tools/planner.py -- 자연어 요청을 다단계 셸 명령 계획으로 변환합니다."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


_PLANNER_SYSTEM_PROMPT = """\
You are a shell command planner. Given a complex task, decompose it into sequential steps.
Output ONLY a JSON array (no markdown, no explanation):
[
  {"step": 1, "description": "...", "command": "..."},
  ...
]

RULES:
1. Each "command" must be a valid executable shell command OR a special tool.
2. Maximum 7 steps. Use the minimum needed.
3. No programming language code (Python/JS/etc), only shell commands.
4. Output ONLY the JSON array, nothing else.

SPECIAL TOOLS (use when file editing or reading is needed):
- Read a file:  {"step": N, "description": "...", "command": "read_file", "path": "relative/path.py"}
- Edit a file:  {"step": N, "description": "...", "command": "edit_file", "path": "relative/path.py", "old": "exact text to replace", "new": "replacement text"}

EXAMPLES:
Task: Update version in main.py from 0.5.0 to 0.6.0
[
  {"step": 1, "description": "Update version string in main.py", "command": "edit_file", "path": "locky_cli/main.py", "old": "version=\\"0.5.0\\"", "new": "version=\\"0.6.0\\""},
  {"step": 2, "description": "Verify the change", "command": "grep -n version locky_cli/main.py"}
]
"""

_DANGEROUS_PATTERNS = [
    r"rm\s+-[rRfF]{1,2}\s+/",  # rm -rf / (root)
    r"rm\s+-[rRfF]{1,2}\s+\*",  # rm -rf *
    r"rm\s+-[rRfF]{1,2}\s+\.\s*$",  # rm -rf . (current dir only, not ./path)
    r"dd\s+.*of=/dev/[sh]d",  # dd to disk
    r"mkfs\.",  # format filesystem
    r":\(\)\s*\{.*\}",  # fork bomb
    r"chmod\s+-R\s+777\s+/",  # chmod 777 /
    r"DROP\s+TABLE",  # SQL drop
    r"DROP\s+DATABASE",
    r"format\s+c:",  # Windows format
    r"del\s+/[sq]\s+[a-zA-Z]:[/\\]",  # Windows del /s C:\
    r"curl\s+.*\|\s*(?:ba)?sh",  # curl | bash (remote code exec)
    r"wget\s+.*\|\s*(?:ba)?sh",  # wget | bash
    r"curl\s+.*-[dX].*@",  # curl data exfiltration (POST file contents)
    r"powershell\s+.*-enc",  # powershell encoded command
    r"net\s+user\s+\w+\s+.*/add",  # Windows user creation
]

_DANGEROUS_RE = [re.compile(p, re.IGNORECASE) for p in _DANGEROUS_PATTERNS]


def is_dangerous(command: str) -> bool:
    """위험한 명령인지 검사합니다."""
    return any(rx.search(command) for rx in _DANGEROUS_RE)


def parse_plan(raw: str) -> list[dict]:
    """LLM 응답에서 JSON 계획을 파싱합니다."""
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
        if not isinstance(data, list):
            return []
        steps = []
        for i, item in enumerate(data[:7]):
            if not isinstance(item, dict):
                continue
            cmd = str(item.get("command", "")).strip()
            desc = str(item.get("description", "")).strip()
            if not cmd:
                continue
            step: dict = {
                "step": int(item.get("step", i + 1)),
                "description": desc,
                "command": cmd,
            }
            # Preserve extra fields for special tools
            for field in ("path", "old", "new"):
                if field in item:
                    step[field] = str(item[field])
            steps.append(step)
        return steps
    except (json.JSONDecodeError, ValueError, TypeError):
        return []


def save_plan(workspace: Path, request: str, steps: list[dict]) -> Path:
    """계획을 .omc/plan.md에 저장합니다."""
    omc_dir = Path(workspace) / ".omc"
    omc_dir.mkdir(exist_ok=True)
    plan_path = omc_dir / "plan.md"

    lines = [
        "# Autopilot Plan",
        "",
        f"**Request:** {request}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Steps:** {len(steps)}",
        "",
        "| Step | Description | Command |",
        "|------|-------------|---------|",
    ]
    for s in steps:
        lines.append(f"| {s['step']} | {s['description']} | `{s['command']}` |")

    plan_path.write_text("\n".join(lines), encoding="utf-8")
    return plan_path


def generate_plan(workspace: Path, request: str, on_token=None) -> list[dict]:
    """자연어 요청을 다단계 계획으로 변환합니다."""
    from tools.ollama_client import OllamaClient

    workspace = Path(workspace).resolve()
    try:
        files = [f.name for f in workspace.iterdir() if f.is_file()]
        dir_listing = ", ".join(files[:15]) + (
            f" (+{len(files) - 15} more)" if len(files) > 15 else ""
        )
    except Exception:
        dir_listing = "(unknown)"

    user_message = (
        f"Working directory: {workspace}\nFiles: {dir_listing}\n\nTask: {request}"
    )

    client = OllamaClient()
    options_dict = {"temperature": 0.1, "num_predict": 600, "top_k": 5}

    if on_token is not None:
        raw_parts: list[str] = []
        for token in client.stream(
            messages=[{"role": "user", "content": user_message}],
            system=_PLANNER_SYSTEM_PROMPT,
            options=options_dict,
            think=False,
        ):
            raw_parts.append(token)
            on_token(token)
        raw = "".join(raw_parts).strip()
    else:
        raw = client.chat(
            messages=[{"role": "user", "content": user_message}],
            system=_PLANNER_SYSTEM_PROMPT,
            options=options_dict,
            think=False,
        ).strip()

    return parse_plan(raw)


_EVAL_SYSTEM_PROMPT = """\
You are evaluating whether a task has been completed based on execution results.
Output ONLY a JSON object:
{"goal_achieved": true or false, "thought": "brief reason"}
"""


def evaluate_progress(
    workspace: Path, request: str, completed_steps: list[dict]
) -> dict:
    """계획 실행 후 목표 달성 여부를 LLM으로 평가합니다.

    Returns:
        {"goal_achieved": bool, "thought": str}
    """
    from tools.ollama_client import OllamaClient

    steps_summary = "\n".join(
        f"- Step {s['step']}: {s['description']} -> command: {s['command']}, "
        f"exit_code: {s.get('exit_code', '?')}, output: {s.get('output', '')[:100]}"
        for s in completed_steps
    )

    user_message = (
        f"Original task: {request}\n\n"
        f"Completed steps:\n{steps_summary}\n\n"
        "Was the task fully completed?"
    )

    try:
        client = OllamaClient()
        raw = client.chat(
            messages=[{"role": "user", "content": user_message}],
            system=_EVAL_SYSTEM_PROMPT,
            options={"temperature": 0, "num_predict": 100, "top_k": 1},
            think=False,
        ).strip()

        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            result = json.loads(match.group(0))
            return {
                "goal_achieved": bool(result.get("goal_achieved", False)),
                "thought": str(result.get("thought", "")),
            }
    except Exception:
        pass

    return {"goal_achieved": True, "thought": "evaluation unavailable"}
