# locky-agent v0.4.0~v1.0.0 Design Document

> **Summary**: 기존 actions/+locky_cli/ 패턴을 유지하며 컨텍스트 캐시·hook·다언어·파이프라인·플러그인을 점진 추가
>
> **Project**: locky-agent
> **Version**: 0.3.0 → 1.0.0
> **Author**: youngsang.kwon
> **Date**: 2026-03-24
> **Status**: Draft
> **Planning Doc**: [locky-agent.plan.md](../01-plan/features/locky-agent.plan.md)

---

## Context Anchor

> Plan 문서에서 복사. Design→Do 핸드오프 시 전략 컨텍스트 유지.

| Key | Value |
|-----|-------|
| **WHY** | 세션 간 기억 없음·멀티스텝 불가·Python 전용으로 "매일 쓰는 도구"가 되지 못하고 있다. |
| **WHO** | 로컬 LLM(Ollama) 사용 개발자, 프라이버시 중시, 한국어 사용자 |
| **RISK** | Ollama 서버 미기동 시 AI 기능 전체 무력화 / 다언어 감지 오탐 |
| **SUCCESS** | pre-commit hook 2주 유지율 70%↑ / 커밋 메시지 수정 없이 수용률 80%↑ |
| **SCOPE** | v0.4.0(컨텍스트+hook) → v0.5.0(다언어+파이프라인) → v1.0.0(플러그인+Ollama자동관리) |

---

## 1. Overview

### 1.1 Design Goals

- `run(root: Path, **opts) -> dict` 인터페이스를 모든 신규 actions/ 모듈에 일관 적용
- `.locky/profile.json` 한 파일로 프로젝트 메타를 유지 (의존성 추가 없음)
- pre-commit hook은 기존 hook을 백업·복원하는 안전한 설치/제거
- 다언어 포맷터는 해당 툴이 설치된 경우에만 실행 (미설치 시 skip + 안내)
- 플러그인 아키텍처는 `importlib` 표준 라이브러리만 사용

### 1.2 Design Principles

- **최소 의존성**: 표준 라이브러리 + 기존 deps 우선, 신규 pip 패키지 최소화
- **인터페이스 일관성**: 모든 actions 모듈은 `run(root, **opts) -> dict` 유지
- **점진적 확장**: v0.4.0 → v0.5.0 → v1.0.0 순서로 각 버전이 독립적으로 동작
- **안전한 변경**: hook 설치 시 기존 hook 백업, 레거시 제거 전 import 검증

---

## 2. Architecture

### 2.0 선택된 아키텍처: Option C — Pragmatic Balance

| 기준 | 값 |
|------|-----|
| **접근법** | 기존 actions/ + locky_cli/ 패턴 유지, 신규 파일 추가 |
| **신규 파일** | 5개 (hook.py, pipeline.py, context.py, lang_detect.py, ollama_guard.py) |
| **수정 파일** | 4개 (main.py, format_code.py, __init__.py, deps_check.py) |
| **복잡도** | 중간 |
| **유지보수성** | 높음 |
| **선택 이유** | 기존 `run(root,**opts)->dict` 인터페이스를 그대로 유지하여 코드 일관성 확보. 과도한 레이어 분리 없이 v0.4.0을 빠르게 릴리스 가능. |

### 2.1 컴포넌트 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI Layer (locky_cli/)                   │
│  main.py ──► commit / format / test / scan / hook / run ...  │
│  repl.py ──► REPL + free-text (shell_command)                │
│  context.py ──► .locky/profile.json 읽기/쓰기               │
│  lang_detect.py ──► git ls-files → 언어 감지                │
└────────────────────┬────────────────────────────────────────┘
                     │ calls run(root, **opts)
┌────────────────────▼────────────────────────────────────────┐
│                  Actions Layer (actions/)                     │
│  commit.py       format_code.py   test_runner.py             │
│  security_scan.py  todo_collector.py  cleanup.py             │
│  deps_check.py   env_template.py  shell_command.py           │
│  hook.py  (NEW)  pipeline.py (NEW)                           │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                   Tools Layer (tools/)                        │
│  ollama_client.py    mcp_filesystem.py    mcp_git.py         │
│  ollama_guard.py (NEW) ──► 헬스체크 + 자동 시작             │
└─────────────────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│              Local State (.locky/)                            │
│  profile.json ──► 언어, 커밋 패턴, 마지막 실행              │
│  config.yaml  ──► 사용자 오버라이드 (선택)                   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 데이터 흐름

```
[사용자 입력]
  │
  ├── locky hook install
  │     └── actions/hook.py → .git/hooks/pre-commit 생성
  │
  ├── locky format (또는 hook 트리거)
  │     └── locky_cli/lang_detect.py → 언어 감지
  │         └── actions/format_code.py → 언어별 포맷터 실행
  │
  ├── locky run "format test commit"
  │     └── actions/pipeline.py → 순서대로 actions 실행
  │
  └── REPL 자유 텍스트
        └── locky_cli/context.py → .locky/profile.json 로드
            └── actions/shell_command.py → 컨텍스트 포함 Ollama 요청
```

### 2.3 의존성

| 컴포넌트 | 의존 대상 | 목적 |
|---------|---------|------|
| `locky_cli/context.py` | `pathlib`, `json` | .locky/ 캐시 관리 |
| `locky_cli/lang_detect.py` | `subprocess` (git ls-files) | 언어 감지 |
| `actions/hook.py` | `pathlib`, `shutil` | hook 설치/제거 |
| `actions/pipeline.py` | `actions/__init__` | 멀티스텝 실행 |
| `tools/ollama_guard.py` | `subprocess`, `tools/ollama_client` | Ollama 헬스체크+시작 |
| `actions/format_code.py` | `subprocess`, `lang_detect` | 다언어 포맷터 |

---

## 3. 데이터 모델

### 3.1 `.locky/profile.json` 스키마

```json
{
  "version": "1",
  "project": {
    "name": "my-project",
    "root": "/path/to/project"
  },
  "language": {
    "primary": "python",
    "all": ["python", "javascript"],
    "detected_at": "2026-03-24T13:00:00Z"
  },
  "commit_style": {
    "type": "conventional",
    "lang": "ko",
    "examples": ["feat(auth): 로그인 기능 추가"]
  },
  "last_run": {
    "command": "commit",
    "at": "2026-03-24T13:05:00Z",
    "status": "ok"
  }
}
```

### 3.2 `.locky/config.yaml` 스키마 (사용자 오버라이드, 선택)

```yaml
# .locky/config.yaml — 자동 감지 결과를 오버라이드
language:
  primary: javascript   # 강제 지정

formatters:
  javascript: "prettier --write"  # 커스텀 포맷터
  python: "ruff format"

hook:
  steps: [format, test, scan]   # 기본값: [format, test, scan]
  fail_fast: true
```

---

## 4. 모듈별 상세 설계

### 4.1 `locky_cli/context.py` (NEW — v0.4.0)

```python
# 공개 인터페이스
def load_profile(root: Path) -> dict:
    """`.locky/profile.json` 읽기. 없으면 {} 반환."""

def save_profile(root: Path, data: dict) -> None:
    """`profile.json` 저장. `.locky/` 디렉토리 자동 생성."""

def update_last_run(root: Path, command: str, status: str) -> None:
    """last_run 필드만 갱신."""

def detect_and_save(root: Path) -> dict:
    """최초 실행 또는 갱신: lang_detect + git log 분석 → profile 저장."""
```

**저장 위치**: `{root}/.locky/profile.json`
**호출 시점**: `locky_cli/main.py` 각 서브커맨드 시작 시 `detect_and_save(root)` 1회

---

### 4.2 `locky_cli/lang_detect.py` (NEW — v0.5.0)

```python
# 공개 인터페이스
def detect(root: Path) -> dict:
    """
    git ls-files 결과의 확장자를 집계하여 언어를 반환.
    Returns: {"primary": "python", "all": ["python", "javascript"]}
    """

# 내부 매핑
_EXT_TO_LANG = {
    ".py": "python",
    ".js": "javascript", ".ts": "typescript", ".jsx": "javascript", ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".java": "java",
    ".kt": "kotlin",
}
```

**감지 로직**: `git ls-files` → 확장자 집계 → 상위 1개 `primary`, 전체 `all`
**fallback**: git 미사용 디렉토리 → `glob("**/*")` 사용

---

### 4.3 `actions/hook.py` (NEW — v0.4.0)

```python
# 공개 인터페이스
def run(root: Path, action: str = "install", steps: list = None, **opts) -> dict:
    """
    action: "install" | "uninstall" | "status"
    steps: hook 실행 순서 (기본: ["format", "test", "scan"])
    Returns: {"status": "ok"|"error", "message": str, "hook_path": str}
    """
```

**hook 설치 내용** (`.git/hooks/pre-commit`):
```bash
#!/bin/sh
# locky pre-commit hook (v0.4.0)
# backup: .git/hooks/pre-commit.locky-backup
set -e
locky format --check || exit 1
locky test || exit 1
locky scan --severity high || exit 1
```

**기존 hook 처리**:
- 존재 시: `.git/hooks/pre-commit.locky-backup`으로 복사 후 설치
- `uninstall` 시: backup 복원, 없으면 단순 삭제

---

### 4.4 `actions/pipeline.py` (NEW — v0.5.0)

```python
# 공개 인터페이스
def run(root: Path, steps: str = "", **opts) -> dict:
    """
    steps: 공백 구분 명령어 문자열 ("format test commit")
    Returns: {"status": "ok"|"partial"|"error", "results": [...], "failed_at": str|None}
    """
```

**실행 로직**:
1. `steps.split()` → 명령 리스트
2. 각 명령을 `actions.__init__`의 함수 매핑으로 실행
3. `fail_fast=True` (기본): 하나라도 실패 시 중단
4. 각 단계 결과를 `results` 리스트에 누적

---

### 4.5 `actions/format_code.py` 확장 (수정 — v0.5.0)

**현재**: `black + isort + flake8` (Python 전용)

**변경 후**:
```python
# 언어별 포맷터 매핑
_FORMATTERS: dict[str, list[list[str]]] = {
    "python": [["black", "{files}"], ["isort", "{files}"], ["ruff", "check", "--fix", "{files}"]],
    "javascript": [["prettier", "--write", "{files}"]],
    "typescript": [["prettier", "--write", "{files}"], ["eslint", "--fix", "{files}"]],
    "go": [["gofmt", "-w", "{files}"]],
    "rust": [["rustfmt", "{files}"]],
}

def run(root: Path, lang: str = "auto", **opts) -> dict:
    """
    lang: "auto" → lang_detect.detect(root) 사용
    포맷터 미설치 시: skip + "not found" 경고 포함 결과 반환
    """
```

---

### 4.6 `tools/ollama_guard.py` (NEW — v1.0.0)

```python
# 공개 인터페이스
def ensure_ollama(base_url: str, model: str, timeout: int = 10) -> dict:
    """
    1. GET /api/tags 로 헬스체크
    2. 실패 시: `ollama serve` 백그라운드 시작 (3초 대기 후 재시도)
    3. 모델 미설치 시: "ollama pull {model}" 안내
    Returns: {"status": "ok"|"started"|"error", "message": str}
    """
```

**호출 위치**: `actions/commit.py`, `actions/shell_command.py` 상단에서 `ensure_ollama()` 호출

---

### 4.7 플러그인 아키텍처 (v1.0.0)

**로드 경로**: `~/.locky/plugins/{name}/action.py`

**플러그인 인터페이스** (필수):
```python
# ~/.locky/plugins/my-plugin/action.py
PLUGIN_NAME = "my-plugin"
PLUGIN_VERSION = "1.0.0"

def run(root: Path, **opts) -> dict:
    """actions/ 모듈과 동일한 인터페이스."""
    ...
```

**로드 코드** (`locky_cli/main.py`):
```python
def _load_plugins() -> dict:
    plugins_dir = Path.home() / ".locky" / "plugins"
    loaded = {}
    for plugin_dir in plugins_dir.glob("*/"):
        action_file = plugin_dir / "action.py"
        if action_file.exists():
            spec = importlib.util.spec_from_file_location(plugin_dir.name, action_file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            loaded[mod.PLUGIN_NAME] = mod.run
    return loaded
```

---

## 5. CLI 인터페이스 설계

### 5.1 신규 서브커맨드 (main.py 추가)

```bash
# v0.4.0
locky hook install              # pre-commit hook 설치
locky hook install --steps "format scan commit"  # 커스텀 순서
locky hook uninstall            # hook 제거
locky hook status               # 설치 여부 확인

# v0.5.0
locky run "format test commit"  # 멀티스텝 파이프라인
locky run "scan commit --push"  # 옵션 포함

# v1.0.0
locky init                      # 대화형 초기 설정
locky plugin list               # 설치된 플러그인 목록
```

### 5.2 기존 명령 변경 없음

- `locky commit`, `locky format`, `locky test` 등 기존 8개 명령 인터페이스 유지
- `format`에 `--lang` 옵션 추가 (기본: auto)

---

## 6. 에러 처리

| 상황 | 처리 방식 | 출력 |
|------|---------|------|
| `.locky/` 쓰기 권한 없음 | 경고 후 캐시 없이 계속 실행 | `[warn] .locky/ 쓰기 실패, 캐시 비활성화` |
| git 미사용 디렉토리에서 hook install | 에러 반환 | `[error] .git/ 디렉토리를 찾을 수 없습니다` |
| 포맷터 미설치 | skip + 경고 | `[skip] prettier not found. npm install -g prettier` |
| Ollama 미기동 | 자동 시작 시도 → 실패 시 에러 | `[error] Ollama 연결 실패. ollama serve 실행 필요` |
| pipeline 중간 단계 실패 | fail_fast=True → 중단 | `[stop] test 실패로 pipeline 중단. 이후 단계 실행 안 함` |

---

## 7. 보안 고려사항

- [ ] `actions/hook.py`: hook 파일 쓰기 시 경로 검증 (`.git/hooks/` 외부 쓰기 방지)
- [ ] `actions/pipeline.py`: steps 파싱 시 셸 인젝션 방지 (허용 명령어 화이트리스트)
- [ ] `tools/ollama_guard.py`: `ollama serve` 실행 시 경로 검증
- [ ] `.locky/profile.json`: 민감 정보 (API 키 등) 저장 금지

---

## 8. 테스트 계획

### 8.1 테스트 범위

| 타입 | 대상 | 도구 |
|------|------|------|
| 단위 테스트 | 각 actions/ 모듈 | pytest |
| 통합 테스트 | hook install → pre-commit 실행 | pytest + tmp_path |
| 언어 감지 테스트 | 다양한 확장자 조합 | pytest |
| 커버리지 | actions/ 전체 | pytest-cov (≥ 70%) |

### 8.2 핵심 테스트 케이스

```
tests/
├── test_hook.py
│   ├── test_install_creates_hook_file
│   ├── test_install_backs_up_existing_hook
│   ├── test_uninstall_restores_backup
│   └── test_install_fails_without_git_dir
│
├── test_lang_detect.py
│   ├── test_detects_python_project
│   ├── test_detects_mixed_project
│   └── test_fallback_without_git
│
├── test_pipeline.py
│   ├── test_runs_steps_in_order
│   ├── test_stops_on_failure
│   └── test_empty_steps_returns_error
│
├── test_shell_command.py (기존)
│   ├── test_valid_command_extracted
│   └── test_korean_response_rejected
│
└── test_context.py
    ├── test_save_and_load_profile
    └── test_detect_and_save_creates_file
```

---

## 9. 레거시 제거 계획 (v0.4.0)

### 9.1 제거 대상

| 경로 | 현황 | 검증 방법 |
|------|------|---------|
| `agents/` (전체) | LangGraph 파이프라인 잔재 | `grep -r "from agents"` |
| `states/state.py` | LockyGlobalState (미사용) | `grep -r "from states"` |
| `graph.py` | 미사용 shim | `grep -r "import graph"` |
| `pipeline/` (전체) | /develop 스킬용 (외부 도구가 사용) | `grep -r "from pipeline"` |

### 9.2 제거 순서

1. `grep` 검증으로 의존성 확인
2. `pyproject.toml`의 `langgraph`, `langchain-*` 의존성 제거
3. 파일/디렉토리 삭제
4. `pip install -e .` 후 `locky --help` 정상 동작 확인

---

## 10. 코딩 컨벤션

### 10.1 기존 패턴 유지

| 항목 | 컨벤션 |
|------|--------|
| 모듈 인터페이스 | `run(root: Path, **opts) -> dict` |
| 상태 코드 | `"ok"`, `"pass"`, `"clean"`, `"nothing_to_commit"`, `"error"` |
| 출력 색상 | `"ok"/"pass"/"clean"` → green, `"nothing_to_commit"` → yellow, else → red |
| import 순서 | `from __future__ import annotations` → stdlib → third-party → local |
| docstring | 필요한 경우만, 짧게 |

### 10.2 신규 파일 컨벤션

```python
# 모든 신규 actions/ 모듈 헤더
"""actions/{module}.py — {한 줄 설명}."""
from __future__ import annotations
from pathlib import Path
```

---

## 11. 구현 가이드

### 11.1 파일 구조 (최종 v1.0.0)

```
locky-agent/
├── actions/
│   ├── __init__.py           수정: hook, pipeline export 추가
│   ├── commit.py
│   ├── cleanup.py
│   ├── deps_check.py         수정: pyproject.toml/package.json/go.mod 파서
│   ├── env_template.py
│   ├── format_code.py        수정: 다언어 포맷터 확장
│   ├── hook.py               NEW (v0.4.0)
│   ├── pipeline.py           NEW (v0.5.0)
│   ├── security_scan.py
│   ├── shell_command.py
│   ├── test_runner.py
│   └── todo_collector.py
│
├── locky_cli/
│   ├── context.py            NEW (v0.4.0)
│   ├── fs_context.py
│   ├── lang_detect.py        NEW (v0.5.0)
│   ├── main.py               수정: hook·run·init 서브커맨드
│   ├── permissions.py
│   └── repl.py               수정: context.py 통합
│
├── tools/
│   ├── mcp_filesystem.py
│   ├── mcp_git.py
│   ├── ollama_client.py
│   └── ollama_guard.py       NEW (v1.0.0)
│
├── tests/                    NEW (v0.4.0)
│   ├── conftest.py
│   ├── test_commit.py
│   ├── test_context.py
│   ├── test_hook.py
│   ├── test_lang_detect.py
│   ├── test_pipeline.py
│   └── test_shell_command.py
│
├── .locky/                   프로젝트별 상태 (gitignore)
│   ├── profile.json
│   └── config.yaml
│
└── [삭제 v0.4.0]
    ├── agents/
    ├── states/
    ├── graph.py
    └── pipeline/
```

### 11.2 구현 순서

**v0.4.0 (우선순위 High)**

1. [ ] `grep` 검증 후 레거시 제거 (agents/, states/, graph.py, pipeline/)
2. [ ] `locky_cli/context.py` 구현 + `tests/test_context.py`
3. [ ] `actions/hook.py` 구현 + `tests/test_hook.py`
4. [ ] `locky_cli/main.py` — `hook` 서브커맨드 추가
5. [ ] `tests/` 디렉토리 셋업 (conftest.py, pytest.ini)
6. [ ] coverage 70%↑ 달성
7. [ ] `pyproject.toml` — langgraph/langchain 의존성 제거

**v0.5.0**

8. [ ] `locky_cli/lang_detect.py` + `tests/test_lang_detect.py`
9. [ ] `actions/format_code.py` — 다언어 포맷터 확장
10. [ ] `actions/pipeline.py` + `tests/test_pipeline.py`
11. [ ] `locky_cli/main.py` — `run` 서브커맨드 추가
12. [ ] `actions/deps_check.py` — pyproject.toml/package.json/go.mod 파서

**v1.0.0**

13. [ ] `tools/ollama_guard.py` 구현
14. [ ] `actions/commit.py`, `actions/shell_command.py` — ollama_guard 통합
15. [ ] 플러그인 로더 (`locky_cli/main.py` — `_load_plugins()`)
16. [ ] `locky init` 서브커맨드
17. [ ] README + CLAUDE.md 업데이트

### 11.3 Session Guide

> `/pdca do locky-agent --scope <module>` 으로 세션별 구현 가능

#### Module Map

| 모듈 | Scope Key | 설명 | 예상 턴 |
|------|-----------|------|:------:|
| 레거시 제거 + 테스트 기반 | `module-1` | grep 검증, 삭제, conftest/pytest.ini, test_shell_command.py | 15-20 |
| 컨텍스트 캐시 | `module-2` | context.py + test_context.py | 15-20 |
| pre-commit hook | `module-3` | hook.py + test_hook.py + main.py hook 서브커맨드 | 20-25 |
| 언어 감지 + 다언어 포맷터 | `module-4` | lang_detect.py + format_code.py 확장 + tests | 20-25 |
| 파이프라인 체이닝 | `module-5` | pipeline.py + main.py run 서브커맨드 + tests | 15-20 |
| Ollama 가드 + 플러그인 | `module-6` | ollama_guard.py + plugin loader + locky init | 20-25 |

#### Recommended Session Plan

| 세션 | 단계 | Scope | 예상 턴 |
|------|------|-------|:------:|
| Session 1 | Plan + Design | 전체 | 이미 완료 |
| Session 2 | Do | `--scope module-1,module-2` | 30-40 |
| Session 3 | Do | `--scope module-3` | 25-30 |
| Session 4 | Do | `--scope module-4,module-5` | 35-45 |
| Session 5 | Do | `--scope module-6` | 25-30 |
| Session 6 | Check + Report | 전체 | 30-40 |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-24 | Initial draft (Option C Pragmatic 선택) | youngsang.kwon |
