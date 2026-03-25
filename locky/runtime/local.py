from __future__ import annotations
import subprocess
from dataclasses import dataclass
from pathlib import Path
import time


@dataclass
class RunResult:
    """subprocess 실행 결과."""
    stdout: str
    stderr: str
    returncode: int
    duration: float

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class LocalRuntime:
    """로컬 subprocess 기반 실행 환경. Docker 없음."""

    def __init__(self, cwd: Path, timeout: int = 60) -> None:
        self.cwd = cwd
        self.timeout = timeout

    def execute(self, cmd: str | list[str]) -> RunResult:
        """명령 실행. 문자열은 shell=True로, 리스트는 shell=False로 실행."""
        start = time.time()

        if isinstance(cmd, str):
            result = subprocess.run(
                cmd, shell=True, cwd=self.cwd,
                capture_output=True, text=True, timeout=self.timeout
            )
        else:
            result = subprocess.run(
                cmd, cwd=self.cwd,
                capture_output=True, text=True, timeout=self.timeout
            )

        return RunResult(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            duration=time.time() - start,
        )
