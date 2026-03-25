# locky v2 대규모 개편 — Design Document

> **Feature**: locky-v2-overhaul
> **Version**: v2.0.0
> **Author**: youngsang.kwon
> **Date**: 2026-03-25
> **Status**: Draft
> **Plan**: docs/01-plan/features/locky-v2-overhaul.plan.md
> **Architecture**: Option C — Pragmatic (dataclass + 단순 클래스 상속)

---

## Context Anchor

| Key | Value |
|-----|-------|
| **WHY** | OpenHands·Goose 분석 결과, locky의 핵심 기회는 "워크플로 자동화 + AI 에이전트" 결합 — 경쟁사 어느 곳도 가볍게 제공 못함 |
| **WHO** | 터미널 중심 + 100% 로컬 + Ollama 보유 개발자 (한국어 Python/Go 개발자) |
| **RISK** | 대규모 재작성 하위 호환 위험 / 로컬 LLM 품질 한계 |
| **SUCCESS** | Agent loop + locky ask/edit 동작 + 기존 167개 테스트 pass + 신규 커버리지 ≥75% |
| **SCOPE** | Core 에이전트 루프, AI ask/edit, Session 컨텍스트; Docker·GUI·클라우드 제외 |

---

## 1. Overview

### 1.1 Architecture Decision

**선택: Option C — Pragmatic (dataclass + 단순 클래스)**

| 항목 | Option A (Thin) | Option B (ABC) | **Option C (Pragmatic)** |
|------|:--------------:|:--------------:|:------------------------:|
| 추상화 수준 | 없음 | 과도함 | 적절 |
| 코드 양 | 최소 | 최대 | 중간 |
| 테스트 용이성 | 어려움 | 쉬움 | **쉬움** |
| 확장성 | 낮음 | 높음 | **높음** |
| 구현 속도 | 빠름 | 느림 | **빠름** |
| 추천 | - | - | **선택** |

### 1.2 설계 원칙

1. **Delegation First**: `locky/tools/`는 `actions/`를 대체하지 않고 위임
2. **AI Optional**: Ollama 없어도 BaseTool은 모두 동작
3. **Dataclass-driven**: 상태는 dataclass, 비즈니스 로직은 메서드
4. **Fail-safe**: `--dry-run` 기본, `--apply`는 명시적 선택

---

## 2. Package Structure

```
locky-agent/
├── locky/                      # NEW: v2 핵심 패키지
│   ├── __init__.py             # version = "2.0.0"
│   ├── core/
│   │   ├── __init__.py
│   │   ├── agent.py            # BaseAgent, AgentResult
│   │   ├── session.py          # LockySession
│   │   └── context.py          # ContextCollector
│   ├── tools/
│   │   ├── __init__.py         # BaseTool, ToolResult
│   │   ├── format.py           # FormatTool
│   │   ├── test.py             # TestTool
│   │   ├── scan.py             # ScanTool
│   │   ├── commit.py           # CommitTool
│   │   ├── git.py              # GitTool (NEW, 직접 구현)
│   │   └── file.py             # FileTool (NEW, 직접 구현)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── ask_agent.py        # AskAgent
│   │   ├── edit_agent.py       # EditAgent
│   │   └── commit_agent.py     # CommitAgent
│   └── runtime/
│       ├── __init__.py
│       └── local.py            # LocalRuntime
│
├── actions/                    # 유지 (하위 호환, 삭제 없음)
├── tools/                      # 유지 (jira_client.py 등)
├── locky_cli/                  # 유지 + 신규 명령 추가
│   ├── main.py                 # ask/edit/agent 서브커맨드 추가
│   └── repl.py                 # /ask, /edit 슬래시 명령 추가
└── tests/
    ├── test_core_agent.py      # NEW
    ├── test_core_session.py    # NEW
    ├── test_tools_*.py         # NEW (각 Tool별)
    ├── test_agents_*.py        # NEW (각 Agent별)
    └── (기존 테스트 유지)
```

---

## 3. 모듈 상세 설계

### 3.1 `locky/core/agent.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from locky.core.session import LockySession
    from locky.tools import BaseTool

MAX_ITERATIONS = 5
AGENT_TIMEOUT = 60  # seconds


@dataclass
class ActionPlan:
    """Ollama가 생성한 실행 계획."""
    task: str
    steps: list[str]
    tool_calls: list[dict]   # [{"tool": "edit", "file": "...", "instruction": "..."}]
    reasoning: str


@dataclass
class AgentResult:
    """에이전트 실행 결과."""
    status: str              # "ok" | "error" | "partial" | "dry_run"
    output: str
    actions_taken: list[str] = field(default_factory=list)
    iterations: int = 0
    verified: bool = False


class BaseAgent:
    """locky v2 에이전트 기반 클래스.

    plan → execute → verify 루프로 태스크를 수행합니다.
    Ollama 없는 환경에서는 올바른 에러 메시지를 반환합니다.
    """

    def __init__(
        self,
        session: LockySession,
        tools: list[BaseTool],
        max_iterations: int = MAX_ITERATIONS,
    ) -> None:
        self.session = session
        self.tools = {t.name: t for t in tools}
        self.max_iterations = max_iterations

    def run(self, task: str) -> AgentResult:
        """태스크를 실행합니다. 최대 max_iterations 반복."""
        for i in range(1, self.max_iterations + 1):
            plan = self._plan(task)
            if plan is None:
                return AgentResult(status="error", output="계획 생성 실패 (Ollama 연결 확인)", iterations=i)

            result = self._execute(plan)
            verified = self._verify(result, plan)

            result.iterations = i
            result.verified = verified

            self.session.add_history({"type": "agent_run", "task": task,
                                       "result": result.status, "iter": i})
            if verified or result.status in ("ok", "dry_run"):
                return result

        return AgentResult(status="partial", output=f"최대 반복({self.max_iterations}회) 도달",
                           iterations=self.max_iterations)

    def _plan(self, task: str) -> ActionPlan | None:
        """Ollama로 실행 계획 생성. 실패 시 None 반환."""
        from tools.ollama_guard import ensure_ollama
        from config import OLLAMA_BASE_URL, OLLAMA_MODEL

        if not ensure_ollama(OLLAMA_BASE_URL, OLLAMA_MODEL):
            return None

        from tools.ollama_client import OllamaClient
        client = OllamaClient()

        context_summary = self.session.context_summary()
        system = (
            "당신은 개발자 워크플로 자동화 에이전트입니다. "
            "주어진 태스크를 수행하기 위한 구체적인 단계를 JSON으로 반환하세요.\n"
            f"현재 컨텍스트: {context_summary}"
        )
        prompt = (
            f"태스크: {task}\n\n"
            "다음 JSON 형식으로 응답하세요:\n"
            '{"steps": ["step1", ...], "tool_calls": [{"tool": "edit|format|test", '
            '"file": "...", "instruction": "..."}], "reasoning": "..."}'
        )

        try:
            response = client.chat([{"role": "user", "content": prompt}], system=system)
            import json
            data = json.loads(response)
            return ActionPlan(task=task, **data)
        except Exception:
            return ActionPlan(task=task, steps=[task], tool_calls=[], reasoning="fallback")

    def _execute(self, plan: ActionPlan) -> AgentResult:
        """계획된 tool_calls를 순서대로 실행."""
        actions = []
        for call in plan.tool_calls:
            tool_name = call.get("tool", "")
            tool = self.tools.get(tool_name)
            if not tool:
                continue

            result = tool.run(self.session.workspace, **{k: v for k, v in call.items() if k != "tool"})
            actions.append(f"{tool_name}: {result.status}")

            if result.status == "error":
                return AgentResult(status="error", output=result.message, actions_taken=actions)

        return AgentResult(status="ok", output="\n".join(actions), actions_taken=actions)

    def _verify(self, result: AgentResult, plan: ActionPlan) -> bool:
        """결과 검증. 기본 구현은 status 확인."""
        return result.status in ("ok", "dry_run")
```

### 3.2 `locky/core/session.py`

```python
from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class LockySession:
    """locky 세션 상태 — 컨텍스트 누적 및 .locky/session.json 영속화."""

    workspace: Path
    session_id: str = ""
    history: list[dict] = field(default_factory=list)
    profile: str = "default"

    def __post_init__(self):
        if not self.session_id:
            import uuid
            self.session_id = f"{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"

    @classmethod
    def load(cls, workspace: Path) -> LockySession:
        """기존 세션 파일 로드. 없으면 신규 생성."""
        session_file = workspace / ".locky" / "session.json"
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text())
                return cls(
                    workspace=workspace,
                    session_id=data.get("session_id", ""),
                    history=data.get("history", []),
                    profile=data.get("profile", "default"),
                )
            except Exception:
                pass
        return cls(workspace=workspace)

    def save(self) -> None:
        """세션 상태를 .locky/session.json에 저장."""
        session_file = self.workspace / ".locky" / "session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps({
            "session_id": self.session_id,
            "workspace": str(self.workspace),
            "history": self.history[-50:],  # 최근 50개만 보존
            "profile": self.profile,
        }, ensure_ascii=False, indent=2))

    def add_history(self, entry: dict) -> None:
        """히스토리에 항목 추가 (timestamp 자동 포함)."""
        self.history.append({**entry, "timestamp": datetime.now().isoformat()})
        self.save()

    def context_summary(self) -> str:
        """최근 히스토리 요약 (Ollama 프롬프트용)."""
        recent = self.history[-5:]
        return "; ".join(f"{h['type']}: {h.get('result', '')}" for h in recent)

    def clear(self) -> None:
        """세션 초기화."""
        self.history = []
        self.save()
```

### 3.3 `locky/core/context.py`

```python
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
                    ctx.file_contents[f] = path.read_text(encoding="utf-8", errors="replace")
        return ctx

    def collect_test_context(self) -> ProjectContext:
        """테스트 실패 컨텍스트 수집."""
        ctx = self.collect()
        test_out = self._run_tests_dry()
        ctx.test_output = test_out
        ctx.failing_files = self._parse_failing_files(test_out)
        return ctx

    def _git_diff(self) -> str:
        result = subprocess.run(["git", "diff", "--stat"], cwd=self.root,
                                 capture_output=True, text=True, timeout=10)
        return result.stdout if result.returncode == 0 else ""

    def _git_status(self) -> str:
        result = subprocess.run(["git", "status", "--short"], cwd=self.root,
                                 capture_output=True, text=True, timeout=10)
        return result.stdout if result.returncode == 0 else ""

    def _run_tests_dry(self) -> str:
        result = subprocess.run(["python", "-m", "pytest", "--tb=short", "-q"],
                                 cwd=self.root, capture_output=True, text=True, timeout=60)
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
```

### 3.4 `locky/tools/__init__.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ToolResult:
    """Tool 실행 결과 — actions/ dict 결과와 호환."""
    status: str          # "ok" | "error" | "nothing_to_commit" 등
    message: str = ""
    data: dict = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}

    @classmethod
    def from_dict(cls, d: dict) -> ToolResult:
        """actions/ 모듈 반환 dict에서 생성."""
        return cls(
            status=d.get("status", "error"),
            message=d.get("message", str(d)),
            data=d,
        )

    @property
    def ok(self) -> bool:
        return self.status in ("ok", "pass", "clean", "nothing_to_commit")


class BaseTool:
    """Tool 기반 클래스. 모든 Tool은 이를 상속."""
    name: str = ""
    description: str = ""

    def run(self, root: Path, **opts) -> ToolResult:
        raise NotImplementedError(f"{self.__class__.__name__}.run() 미구현")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
```

### 3.5 `locky/tools/format.py` — Delegation 패턴 예시

```python
from pathlib import Path
from locky.tools import BaseTool, ToolResult


class FormatTool(BaseTool):
    name = "format"
    description = "다언어 코드 포매터 (black, prettier, gofmt 등)"

    def run(self, root: Path, **opts) -> ToolResult:
        from actions.format_code import run  # delegation
        return ToolResult.from_dict(run(root, **opts))
```

### 3.6 `locky/tools/git.py` — 신규 GitTool

```python
from __future__ import annotations
import subprocess
from dataclasses import dataclass
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
        r = subprocess.run(["git", "status", "--short"], cwd=root,
                            capture_output=True, text=True, timeout=10)
        return ToolResult(status="ok" if r.returncode == 0 else "error",
                          message=r.stdout or r.stderr,
                          data={"output": r.stdout})

    def _diff(self, root: Path, ref: str) -> ToolResult:
        r = subprocess.run(["git", "diff", ref], cwd=root,
                            capture_output=True, text=True, timeout=10)
        return ToolResult(status="ok" if r.returncode == 0 else "error",
                          message=r.stdout[:4000], data={"diff": r.stdout})

    def _log(self, root: Path, n: int) -> ToolResult:
        r = subprocess.run(["git", "log", f"-{n}", "--oneline"], cwd=root,
                            capture_output=True, text=True, timeout=10)
        return ToolResult(status="ok" if r.returncode == 0 else "error",
                          message=r.stdout, data={"log": r.stdout})
```

### 3.7 `locky/tools/file.py` — 신규 FileTool

```python
from __future__ import annotations
from pathlib import Path
from locky.tools import BaseTool, ToolResult


class FileTool(BaseTool):
    name = "file"
    description = "파일 읽기, 쓰기, 검색"

    def run(self, root: Path, action: str = "read", **opts) -> ToolResult:
        if action == "read":
            return self._read(root, opts.get("path", ""))
        elif action == "write":
            return self._write(root, opts.get("path", ""), opts.get("content", ""))
        elif action == "search":
            return self._search(root, opts.get("pattern", ""), opts.get("glob", "**/*.py"))
        return ToolResult(status="error", message=f"알 수 없는 action: {action}")

    def _read(self, root: Path, rel_path: str) -> ToolResult:
        path = (root / rel_path).resolve()
        # 경로 순회 방지
        if not str(path).startswith(str(root.resolve())):
            return ToolResult(status="error", message="경로 접근 거부 (루트 벗어남)")
        if not path.exists():
            return ToolResult(status="error", message=f"파일 없음: {rel_path}")
        content = path.read_text(encoding="utf-8", errors="replace")
        return ToolResult(status="ok", message=content[:5000], data={"content": content, "path": str(path)})

    def _write(self, root: Path, rel_path: str, content: str) -> ToolResult:
        path = (root / rel_path).resolve()
        if not str(path).startswith(str(root.resolve())):
            return ToolResult(status="error", message="경로 접근 거부")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ToolResult(status="ok", message=f"저장: {rel_path}", data={"path": str(path)})

    def _search(self, root: Path, pattern: str, glob: str) -> ToolResult:
        import re
        matches = []
        for f in root.rglob(glob):
            if not f.is_file():
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(text.splitlines(), 1):
                    if re.search(pattern, line):
                        matches.append(f"{f.relative_to(root)}:{i}: {line.strip()}")
                        if len(matches) >= 50:
                            break
            except Exception:
                continue
        return ToolResult(status="ok", message="\n".join(matches), data={"matches": matches})
```

### 3.8 `locky/agents/ask_agent.py`

```python
from __future__ import annotations
from pathlib import Path
from locky.core.context import ContextCollector
from locky.core.session import LockySession


class AskAgent:
    """코드 Q&A 에이전트 — 파일 컨텍스트 기반 질의응답."""

    def __init__(self, session: LockySession) -> None:
        self.session = session

    def run(self, question: str, files: list[str] | None = None) -> str:
        """질문에 답변. 파일 지정 시 해당 파일 컨텍스트 포함."""
        root = self.session.workspace
        collector = ContextCollector(root)
        ctx = collector.collect(files=files or [])

        from tools.ollama_guard import ensure_ollama
        from config import OLLAMA_BASE_URL, OLLAMA_MODEL
        if not ensure_ollama(OLLAMA_BASE_URL, OLLAMA_MODEL):
            return "Ollama 서버를 시작할 수 없습니다. `ollama serve` 실행 후 재시도하세요."

        from tools.ollama_client import OllamaClient
        client = OllamaClient()

        system = (
            "당신은 친절한 코드 어시스턴트입니다. "
            "주어진 코드 컨텍스트를 바탕으로 질문에 답변하세요. "
            "코드 변경이나 편집은 하지 않습니다."
        )
        prompt = f"{ctx.to_prompt_context()}\n\n질문: {question}"

        answer = client.chat([{"role": "user", "content": prompt}], system=system)

        self.session.add_history({"type": "ask", "question": question[:100],
                                   "files": files or []})
        return answer

    def stream(self, question: str, files: list[str] | None = None):
        """스트리밍 답변 제너레이터."""
        root = self.session.workspace
        collector = ContextCollector(root)
        ctx = collector.collect(files=files or [])

        from tools.ollama_guard import ensure_ollama
        from config import OLLAMA_BASE_URL, OLLAMA_MODEL
        if not ensure_ollama(OLLAMA_BASE_URL, OLLAMA_MODEL):
            yield "Ollama 서버를 시작할 수 없습니다."
            return

        from tools.ollama_client import OllamaClient
        client = OllamaClient()
        system = "당신은 친절한 코드 어시스턴트입니다. 코드 변경 없이 질문에 답변하세요."
        prompt = f"{ctx.to_prompt_context()}\n\n질문: {question}"

        yield from client.stream([{"role": "user", "content": prompt}], system=system)
```

### 3.9 `locky/agents/edit_agent.py`

```python
from __future__ import annotations
import re
from pathlib import Path
from locky.core.context import ContextCollector
from locky.core.session import LockySession


DIFF_SYSTEM = """당신은 코드 편집 전문 에이전트입니다.
주어진 파일 내용과 지시사항을 바탕으로 unified diff 형식으로 변경 사항을 반환하세요.

응답 형식:
```diff
--- a/파일경로
+++ b/파일경로
@@ -N,M +N,M @@
 변경 전 줄
-삭제할 줄
+추가할 줄
```

주의: diff 블록 외 설명은 최소화하세요."""


class EditAgent:
    """코드 편집 에이전트 — unified diff 생성 및 적용."""

    def __init__(self, session: LockySession) -> None:
        self.session = session

    def run(self, instruction: str, file_path: str,
            dry_run: bool = True) -> dict:
        """
        Returns:
            {"status": "dry_run"|"ok"|"error", "diff": str, "message": str, "applied": bool}
        """
        root = self.session.workspace

        # 파일 읽기
        path = (root / file_path).resolve()
        if not str(path).startswith(str(root.resolve())):
            return {"status": "error", "diff": "", "message": "경로 접근 거부", "applied": False}
        if not path.exists():
            return {"status": "error", "diff": "", "message": f"파일 없음: {file_path}", "applied": False}

        original = path.read_text(encoding="utf-8")

        # Ollama로 diff 생성
        from tools.ollama_guard import ensure_ollama
        from config import OLLAMA_BASE_URL, OLLAMA_MODEL
        if not ensure_ollama(OLLAMA_BASE_URL, OLLAMA_MODEL):
            return {"status": "error", "diff": "", "message": "Ollama 서버 없음", "applied": False}

        from tools.ollama_client import OllamaClient
        client = OllamaClient()

        prompt = (
            f"파일: {file_path}\n\n"
            f"```python\n{original[:3000]}\n```\n\n"
            f"지시사항: {instruction}"
        )

        response = client.chat([{"role": "user", "content": prompt}], system=DIFF_SYSTEM)
        diff = self._extract_diff(response)

        if not diff:
            # diff 파싱 실패 시 전체 응답 표시
            return {"status": "dry_run", "diff": response[:2000],
                    "message": "diff 파싱 실패. 응답을 수동 확인 필요.", "applied": False}

        if dry_run:
            return {"status": "dry_run", "diff": diff, "message": "미리보기 (--apply로 적용)", "applied": False}

        # diff 적용
        applied = self._apply_diff(path, original, diff)
        if applied:
            self.session.add_history({"type": "edit", "file": file_path,
                                       "instruction": instruction[:100]})
            return {"status": "ok", "diff": diff, "message": f"적용 완료: {file_path}", "applied": True}

        return {"status": "error", "diff": diff, "message": "diff 적용 실패. 수동 적용 필요.", "applied": False}

    def _extract_diff(self, response: str) -> str:
        """응답에서 diff 블록 추출."""
        # ```diff ... ``` 블록 추출
        match = re.search(r"```diff\n(.*?)```", response, re.DOTALL)
        if match:
            return match.group(1)
        # --- a/ 로 시작하는 패턴 직접 추출
        match = re.search(r"(--- a/.*?\+\+\+ b/.*?(?=\n\n|\Z))", response, re.DOTALL)
        return match.group(1) if match else ""

    def _apply_diff(self, path: Path, original: str, diff: str) -> bool:
        """patch 명령으로 diff 적용. 실패 시 False."""
        import subprocess, tempfile, os

        with tempfile.NamedTemporaryFile(mode="w", suffix=".patch",
                                          delete=False, encoding="utf-8") as f:
            f.write(diff)
            patch_file = f.name

        try:
            result = subprocess.run(
                ["patch", "-p1", str(path)],
                input=diff, capture_output=True, text=True,
                cwd=path.parent, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
        finally:
            os.unlink(patch_file)
```

### 3.10 `locky/runtime/local.py`

```python
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
```

---

## 4. CLI 통합 설계

### 4.1 신규 CLI 명령 (`locky_cli/main.py`)

```python
# --- 추가될 명령들 ---

@cli.command("ask")
@click.argument("question")
@click.argument("files", nargs=-1)
@click.option("--workspace", "-w", default=None)
def ask_cmd(question: str, files: tuple, workspace: str | None):
    """AI에게 코드에 대해 질문합니다."""
    from locky.core.session import LockySession
    from locky.agents.ask_agent import AskAgent

    root = resolve_workspace_root(workspace)
    session = LockySession.load(root)
    agent = AskAgent(session)

    console = Console()
    with console.status("생각 중..."):
        answer = agent.run(question, files=list(files))

    console.print(Panel(answer, title="AI 답변", border_style="blue"))


@cli.command("edit")
@click.argument("instruction")
@click.argument("file")
@click.option("--dry-run/--apply", default=True, help="미리보기(기본) 또는 실제 적용")
@click.option("--workspace", "-w", default=None)
def edit_cmd(instruction: str, file: str, dry_run: bool, workspace: str | None):
    """AI를 사용해 코드를 편집합니다."""
    from locky.core.session import LockySession
    from locky.agents.edit_agent import EditAgent

    root = resolve_workspace_root(workspace)
    session = LockySession.load(root)
    agent = EditAgent(session)

    result = agent.run(instruction, file_path=file, dry_run=dry_run)
    _print_result(console, result)


@cli.command("agent")
@click.argument("task")
@click.option("--workspace", "-w", default=None)
@click.option("--max-iter", default=5, help="최대 반복 횟수")
def agent_cmd(task: str, workspace: str | None, max_iter: int):
    """Agent Loop로 복합 태스크를 실행합니다."""
    from locky.core.session import LockySession
    from locky.core.agent import BaseAgent
    from locky.tools.format import FormatTool
    from locky.tools.test import TestTool
    from locky.tools.git import GitTool
    from locky.tools.file import FileTool

    root = resolve_workspace_root(workspace)
    session = LockySession.load(root)

    tools = [FormatTool(), TestTool(), GitTool(), FileTool()]
    agent = BaseAgent(session, tools, max_iterations=max_iter)

    result = agent.run(task)
    _print_result(console, {"status": result.status, "message": result.output,
                             "iterations": result.iterations})
```

### 4.2 REPL 통합 (`locky_cli/repl.py`)

```python
# 기존 _SLASH_COMMANDS dict에 추가:
_SLASH_COMMANDS = {
    # ... 기존 명령들 ...
    "/ask": _cmd_ask,     # NEW
    "/edit": _cmd_edit,   # NEW
}

def _cmd_ask(args: str, state: SessionState, console: Console) -> None:
    """/ask [파일...] 질문"""
    parts = args.strip().split()
    # 마지막 연속 공백 이전은 파일, 따옴표 포함 부분은 질문
    from locky.core.session import LockySession
    from locky.agents.ask_agent import AskAgent

    session = LockySession.load(state.workspace_root)
    agent = AskAgent(session)
    answer = agent.run(args)
    console.print(Panel(answer, title="AI", border_style="cyan"))

def _cmd_edit(args: str, state: SessionState, console: Console) -> None:
    """/edit 파일경로 지시사항"""
    from locky.core.session import LockySession
    from locky.agents.edit_agent import EditAgent

    session = LockySession.load(state.workspace_root)
    agent = EditAgent(session)

    parts = args.strip().split(" ", 1)
    if len(parts) < 2:
        console.print("[red]사용법: /edit 파일경로 지시사항[/red]")
        return

    result = agent.run(parts[1], file_path=parts[0], dry_run=True)
    console.print(Panel(result.get("diff", result.get("message", "")),
                        title="diff 미리보기 (적용하려면 /edit-apply 사용)",
                        border_style="yellow"))
```

---

## 5. 테스트 설계

### 5.1 테스트 파일 목록 (신규 ≥ 40개)

| 파일 | 테스트 수 | 주요 케이스 |
|------|----------|------------|
| `tests/test_core_agent.py` | 8 | BaseAgent.run 정상/실패/최대반복, plan/execute/verify |
| `tests/test_core_session.py` | 6 | load, save, add_history, context_summary, clear |
| `tests/test_core_context.py` | 5 | collect, collect_test_context, parse_failing_files |
| `tests/test_tools_base.py` | 4 | ToolResult.from_dict, BaseTool.run NotImplemented |
| `tests/test_tools_format.py` | 3 | FormatTool delegation, ToolResult.ok |
| `tests/test_tools_git.py` | 6 | status, diff, log, 에러 케이스 |
| `tests/test_tools_file.py` | 6 | read, write, search, 경로순회방지 |
| `tests/test_agents_ask.py` | 4 | run 정상, Ollama 없음, 파일 컨텍스트 |
| `tests/test_agents_edit.py` | 6 | dry_run, apply, diff 추출 실패 fallback |
| `tests/test_runtime_local.py` | 4 | execute str, execute list, timeout, 에러 |
| **합계** | **52개** | |

### 5.2 테스트 패턴

```python
# tests/test_core_session.py 예시
import pytest
from pathlib import Path
from locky.core.session import LockySession


def test_session_new(tmp_path):
    session = LockySession(workspace=tmp_path)
    assert session.session_id != ""
    assert session.history == []

def test_session_save_load(tmp_path):
    session = LockySession(workspace=tmp_path)
    session.add_history({"type": "test", "result": "ok"})

    loaded = LockySession.load(tmp_path)
    assert len(loaded.history) == 1
    assert loaded.history[0]["type"] == "test"

def test_session_history_limit(tmp_path):
    session = LockySession(workspace=tmp_path)
    for i in range(60):
        session.add_history({"type": "test", "i": i})

    loaded = LockySession.load(tmp_path)
    assert len(loaded.history) <= 50  # 최근 50개만 보존
```

---

## 6. OllamaClient 스트리밍 확장

기존 `tools/ollama_client.py`에 `stream()` 메서드 추가 필요:

```python
# tools/ollama_client.py에 추가
def stream(self, messages: list, system: str = ""):
    """스트리밍 채팅. 토큰별 제너레이터."""
    payload = {"model": self.model, "messages": messages, "stream": True}
    if system:
        payload["system"] = system

    with httpx.Client(timeout=self.timeout) as client:
        with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
            for line in resp.iter_lines():
                if line:
                    import json
                    data = json.loads(line)
                    if token := data.get("message", {}).get("content", ""):
                        yield token
                    if data.get("done"):
                        break
```

---

## 7. Migration Guide (v1 → v2)

### 7.1 기존 코드 영향 없음

```python
# v1 코드 — 변경 없이 동작
from actions.format_code import run
result = run(Path("/my/project"))

# v2 신규 방식 — 선택적
from locky.tools.format import FormatTool
tool = FormatTool()
result = tool.run(Path("/my/project"))
```

### 7.2 import shim (`locky/__init__.py`)

```python
# locky/__init__.py
"""locky v2 — 하위 호환 shim."""
__version__ = "2.0.0"

# v1 actions/ 경로 유지를 위한 re-export (선택적)
# from actions import *  # 필요시 주석 해제
```

---

## 8. pyproject.toml 변경 사항

```toml
# 추가될 패키지 경로
[tool.setuptools.packages.find]
where = ["."]
include = ["locky*", "locky_cli*", "actions*", "tools*", "agents*"]

# 버전 업데이트
[project]
version = "2.0.0"
```

---

## 9. 리스크 완화 상세

| 리스크 | 완화 구현 |
|--------|---------|
| LLM diff 파싱 실패 | `_extract_diff()` 2단계 fallback + 전체 응답 표시 |
| actions/ 하위 호환 | Tool은 delegation만, 원본 actions/ 코드 수정 없음 |
| Agent Loop 무한 반복 | `max_iterations=5` 하드코딩 + 60초 타임아웃 |
| FileTool 경로 순회 | `str(path).startswith(str(root.resolve()))` 체크 |
| Ollama 없는 환경 | 모든 AI 기능 진입점에서 `ensure_ollama()` 체크 |

---

## 10. 의존성 변경

| 패키지 | 변경 | 이유 |
|--------|------|------|
| `httpx` | 유지 | OllamaClient 스트리밍 확장 |
| `rich` | 유지 | CLI 출력 |
| `click` | 유지 | CLI |
| `patch` (시스템) | 런타임 의존 | EditAgent diff 적용 (`subprocess patch`) |
| 신규 pip 패키지 | **0개** | 기존 패키지만 사용 |

---

## 11. Implementation Guide

### 11.1 구현 순서

1. `locky/` 패키지 뼈대 생성 (`__init__.py` 파일들)
2. `locky/runtime/local.py` — LocalRuntime (가장 단순)
3. `locky/tools/__init__.py` — BaseTool, ToolResult
4. `locky/tools/git.py`, `file.py` — 신규 Tool
5. `locky/tools/format.py`, `test.py`, `scan.py`, `commit.py` — Delegation Tool
6. `locky/core/context.py` — ContextCollector
7. `locky/core/session.py` — LockySession
8. `locky/core/agent.py` — BaseAgent
9. `locky/agents/ask_agent.py` — AskAgent
10. `locky/agents/edit_agent.py` — EditAgent
11. `tools/ollama_client.py` — stream() 추가 (기존 파일 수정)
12. `locky_cli/main.py` — ask/edit/agent 명령 추가
13. `locky_cli/repl.py` — /ask, /edit 슬래시 명령 추가
14. `tests/` — 52개 신규 테스트

### 11.2 파일 변경 요약

| 구분 | 파일 수 | 비고 |
|------|---------|------|
| 신규 생성 | 19개 | locky/ 패키지 전체 |
| 기존 수정 | 3개 | ollama_client.py, main.py, repl.py |
| 기존 유지 | 전체 | actions/, tools/jira_client.py 등 |
| 신규 테스트 | 10개 | 52개 테스트 케이스 |

### 11.3 Session Guide

#### Module Map

| Module | 파일 | 의존성 |
|--------|------|--------|
| M1-runtime | `locky/runtime/local.py` | 없음 |
| M2-tools-base | `locky/tools/__init__.py` | 없음 |
| M3-tools-impl | `locky/tools/{git,file,format,test,scan,commit}.py` | M2 |
| M4-context | `locky/core/context.py` | 없음 |
| M5-session | `locky/core/session.py` | 없음 |
| M6-agent | `locky/core/agent.py` | M2,M5 |
| M7-ask-agent | `locky/agents/ask_agent.py` | M4,M5,ollama |
| M8-edit-agent | `locky/agents/edit_agent.py` | M4,M5,ollama |
| M9-ollama-stream | `tools/ollama_client.py` (수정) | 없음 |
| M10-cli | `locky_cli/main.py`, `repl.py` (수정) | M6,M7,M8 |

#### Recommended Session Plan

| 세션 | 모듈 | 예상 테스트 |
|------|------|-----------|
| Session 1 | M1 + M2 + M3 | 23개 (runtime + tools 전체) |
| Session 2 | M4 + M5 + M6 | 19개 (core 전체) |
| Session 3 | M7 + M8 + M9 | 10개 (agents + stream) |
| Session 4 | M10 + 회귀 테스트 | 기존 167개 회귀 + 통합 |

```
/pdca do locky-v2-overhaul --scope M1,M2,M3   # Session 1
/pdca do locky-v2-overhaul --scope M4,M5,M6   # Session 2
/pdca do locky-v2-overhaul --scope M7,M8,M9   # Session 3
/pdca do locky-v2-overhaul --scope M10        # Session 4
```

---

> **다음 단계**: `/pdca do locky-v2-overhaul --scope M1,M2,M3`
