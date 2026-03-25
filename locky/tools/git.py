from __future__ import annotations

import subprocess
from pathlib import Path

from locky.tools import BaseTool, ToolResult


class GitTool(BaseTool):
    name = "git"
    description = "git 상태, diff, 로그 조회"

    def run(self, root: Path, action: str = "status", **opts) -> ToolResult:
        if action == "status":
            return self._status(root)
        elif action == "diff":
            return self._diff(root, opts.get("ref", "HEAD"))
        elif action == "log":
            return self._log(root, opts.get("n", 5))
        return ToolResult(status="error", message=f"알 수 없는 action: {action}")

    def _status(self, root: Path) -> ToolResult:
        r = subprocess.run(
            ["git", "status", "--short"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return ToolResult(
            status="ok" if r.returncode == 0 else "error",
            message=r.stdout or r.stderr,
            data={"output": r.stdout},
        )

    def _diff(self, root: Path, ref: str) -> ToolResult:
        r = subprocess.run(
            ["git", "diff", ref], cwd=root, capture_output=True, text=True, timeout=10
        )
        return ToolResult(
            status="ok" if r.returncode == 0 else "error",
            message=r.stdout[:4000],
            data={"diff": r.stdout},
        )

    def _log(self, root: Path, n: int) -> ToolResult:
        r = subprocess.run(
            ["git", "log", f"-{n}", "--oneline"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return ToolResult(
            status="ok" if r.returncode == 0 else "error",
            message=r.stdout,
            data={"log": r.stdout},
        )
