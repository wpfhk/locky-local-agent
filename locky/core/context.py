from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProjectContext:
    """수집된 프로젝트 컨텍스트."""

    git_diff: str = ""
    git_status: str = ""
    test_output: str = ""
    failing_files: list[str] = None
    file_contents: dict[str, str] = None  # {path: content}

    def __post_init__(self):
        if self.failing_files is None:
            self.failing_files = []
        if self.file_contents is None:
            self.file_contents = {}

    def to_prompt_context(self) -> str:
        """Ollama 프롬프트용 컨텍스트 문자열."""
        parts = []
        if self.git_diff:
            parts.append(f"## Git Diff\n```\n{self.git_diff[:2000]}\n```")
        if self.test_output:
            parts.append(f"## Test Output\n```\n{self.test_output[:1000]}\n```")
        if self.failing_files:
            parts.append(f"## Failing Files\n{', '.join(self.failing_files)}")
        for path, content in list(self.file_contents.items())[:3]:  # 최대 3파일
            parts.append(f"## {path}\n```\n{content[:1000]}\n```")
        return "\n\n".join(parts)


class ContextCollector:
    """프로젝트 컨텍스트 수집기."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def collect(self, files: list[str] | None = None) -> ProjectContext:
        """컨텍스트 수집. files 지정 시 해당 파일 내용도 포함."""
        ctx = ProjectContext(
            git_diff=self._git_diff(),
            git_status=self._git_status(),
        )
        if files:
            for f in files:
                path = self.root / f
                if path.exists():
                    ctx.file_contents[f] = path.read_text(
                        encoding="utf-8", errors="replace"
                    )
        return ctx

    def collect_test_context(self) -> ProjectContext:
        """테스트 실패 컨텍스트 수집."""
        ctx = self.collect()
        test_out = self._run_tests_dry()
        ctx.test_output = test_out
        ctx.failing_files = self._parse_failing_files(test_out)
        return ctx

    def _git_diff(self) -> str:
        result = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout if result.returncode == 0 else ""

    def _git_status(self) -> str:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout if result.returncode == 0 else ""

    def _run_tests_dry(self) -> str:
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--tb=short", "-q"],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.stdout + result.stderr

    def _parse_failing_files(self, test_output: str) -> list[str]:
        """테스트 출력에서 실패한 파일 경로 추출."""
        files = []
        for line in test_output.splitlines():
            if "FAILED" in line and "::" in line:
                file_part = line.split("::")[0].strip().replace("FAILED ", "")
                if file_part and file_part not in files:
                    files.append(file_part)
        return files
