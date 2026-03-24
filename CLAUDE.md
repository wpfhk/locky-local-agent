# Locky Agent — CLAUDE.md

100% 로컬 개발자 자동화 도구 (v1.0.0). Ollama 기반 AI 커밋 메시지 생성 + 11개 자동화 명령 (포매팅·테스트·보안 스캔·훅·파이프라인 등).

---

## 프로젝트 구조

```
locky-agent/
├── config.py                  # Ollama URL/모델/타임아웃, 파이프라인 설정
├── cli.py                     # 호환 진입점 (locky_cli.main으로 위임)
│
├── locky_cli/                 # Click CLI 패키지
│   ├── main.py                # 11개 서브커맨드 + REPL 진입점 (v1.0.0)
│   ├── context.py             # 세션 프로파일 (.locky/profile.json) 관리
│   ├── lang_detect.py         # git ls-files + rglob fallback 언어 감지
│   ├── fs_context.py          # ContextVar 기반 MCP_FILESYSTEM_ROOT 관리
│   ├── repl.py                # 대화형 REPL (/commit, /format 등 슬래시 명령)
│   └── permissions.py        # 파일 접근 권한 헬퍼
│
├── actions/                   # 자동화 명령 모듈 (각각 run(root, **opts) -> dict)
│   ├── __init__.py            # 모든 runner export
│   ├── commit.py              # git diff → Ollama → Conventional Commits → commit
│   ├── format_code.py         # 다언어 포매터 (Python/JS/TS/Go/Rust/Kotlin/Swift)
│   ├── hook.py                # pre-commit 훅 install/uninstall/status
│   ├── pipeline.py            # 멀티스텝 파이프라인 (format→test→scan 등)
│   ├── test_runner.py         # pytest 실행 및 결과 파싱
│   ├── todo_collector.py      # TODO/FIXME/HACK/XXX 수집 및 마크다운 저장
│   ├── security_scan.py       # OWASP 패턴 기반 정적 보안 스캔
│   ├── cleanup.py             # __pycache__, .pyc, .pytest_cache 등 정리
│   ├── deps_check.py          # requirements.txt/pyproject.toml/package.json/go.mod 버전 비교
│   └── env_template.py        # .env → .env.example 자동 생성
│
├── tools/
│   ├── ollama_client.py       # Ollama /api/chat 동기·스트리밍 클라이언트
│   ├── ollama_guard.py        # Ollama 헬스체크 + 자동 시작 + 모델 확인
│   ├── mcp_filesystem.py      # read_file / write_file / search_in_files (경로 순회 방지)
│   └── mcp_git.py             # GitPython 래퍼 (status / diff / commit)
│
├── agents/                    # (레거시) 내부 파이프라인 에이전트 — 직접 사용 안 함
│   ├── planner/               # 컨텍스트 분석, 태스크 분할
│   ├── coder/                 # 코어 개발자, 리팩터 포매터
│   ├── tester/                # QA 검증기, 보안 감사
│   └── prompts/               # 에이전트 역할 정의 마크다운
│
├── states/
│   └── state.py               # LockyGlobalState TypedDict (레거시)
│
├── pipeline/                  # Claude Code /develop 스킬용 JSON 상태 관리
│   ├── state.py               # init_run / advance_stage / mark_complete 등
│   ├── runner.py              # CLI: python pipeline/runner.py <verb> <run_id>
│   └── orchestrator.py        # claude_agent_sdk 기반 오케스트레이터
│
├── ui/
│   └── app.py                 # Chainlit 웹 UI
│
├── tests/                     # 단위 테스트 (pytest, 132개 테스트)
│   ├── conftest.py            # tmp_git_repo 픽스처
│   ├── test_hook.py           # hook.py — 21 tests
│   ├── test_context.py        # context.py — 8 tests
│   ├── test_lang_detect.py    # lang_detect.py — 9 tests
│   ├── test_format_code.py    # format_code.py — 16 tests
│   ├── test_pipeline.py       # pipeline.py — 14 tests
│   ├── test_ollama_guard.py   # ollama_guard.py — 14 tests
│   ├── test_shell_command.py  # shell_command.py — 17 tests
│   └── test_deps_check.py     # deps_check.py — 31 tests
│
├── graph.py                   # 미사용 shim (actions/ 패키지로 대체됨)
├── requirements.txt           # pip 의존성
└── pyproject.toml             # 패키지 설정 (진입점: locky = locky_cli.main:main)
```

---

## 핵심 아키텍처

### actions/ 패키지 — 메인 자동화 엔진

각 모듈은 `run(root: Path, **opts) -> dict` 시그니처를 따릅니다.

```python
from actions.commit import run
result = run(Path("/my/project"), dry_run=True)
# result = {"status": "ok", "message": "feat: ...", "committed": False, ...}
```

`status` 값:
- `"ok"` / `"pass"` / `"clean"` → 초록
- `"nothing_to_commit"` → 노랑
- 그 외 → 빨강

### CLI 서브커맨드

```
locky commit [--dry-run] [--push]
locky format [--check] [--lang LANG] [PATH...]
locky test   [PATH] [-v]
locky todo   [--output FILE]
locky scan   [--severity LEVEL]
locky clean  [--force]
locky deps
locky env    [--output FILE]
locky hook   install|uninstall|status [--steps STEPS]
locky run    STEP [STEP...] [--no-fail-fast]
locky init   [--hook/--no-hook]
locky plugin list
```

### 다언어 포맷터 (`format_code.py`)

`lang="auto"` (기본): `lang_detect.py`로 언어 자동 감지 후 해당 포매터 실행.

| 언어 | 포매터 |
|---|---|
| python | black + isort + flake8 |
| javascript | prettier |
| typescript | prettier + eslint |
| go | gofmt |
| rust | rustfmt |
| kotlin | ktlint |
| swift | swiftformat |

### pre-commit 훅 (`hook.py`)

- `install`: `.git/hooks/pre-commit` 생성, 기존 훅은 `.pre-commit.locky-backup`으로 백업
- `uninstall`: locky 훅 제거, 백업 파일 자동 복원
- `status`: 훅 설치 여부 + 스텝 목록 확인

### 파이프라인 (`pipeline.py`)

`_STEP_RUNNERS` 딕셔너리로 스텝 이름 → actions 모듈 매핑. `fail_fast=True` (기본)이면 첫 실패 시 중단.

```python
result = {"status": "ok"|"partial"|"error", "results": [...], "failed_at": str|None, "executed": int, "total": int}
```

### Ollama 가드 (`tools/ollama_guard.py`)

`ensure_ollama(base_url, model)`:
1. GET `/api/tags` 헬스체크
2. 실패 시 `ollama serve` 백그라운드 시작, 3초 대기, 재시도
3. 모델 목록에서 지정 모델 확인

`commit.py`와 `shell_command.py`의 Ollama 호출 전에 자동 실행됨.

### 플러그인 로더

`locky_cli/main.py`의 `_load_plugins()`:
- `~/.locky/plugins/*.py` 파일을 `importlib.util`로 동적 로드
- 각 플러그인은 `register(main_cli)` 함수로 Click 커맨드를 등록

### 의존성 확인 (`deps_check.py`)

우선순위 순으로 파일 자동 감지: `requirements.txt` → `pyproject.toml` → `package.json` → `go.mod`.

- `pyproject.toml`: `tomllib` (3.11+) 또는 `tomli` 사용, 없으면 정규식 fallback
- `package.json`: `dependencies` + `devDependencies` 모두 파싱
- `go.mod`: `require (...)` 블록 및 단일 행 `require` 파싱

### REPL 슬래시 명령

`locky` (인수 없이) → REPL 진입. `/commit`, `/format` 등 슬래시 명령으로 동일한 actions/ 모듈 호출.
`exit` / `quit` (슬래시 없이도) → 종료.

---

## 주요 설계 패턴

| 패턴 | 내용 |
|---|---|
| `actions/` 독립 모듈 | 각 명령이 서로 의존하지 않아 단위 테스트 및 독립 사용 용이 |
| `_is_simple_request(cmd)` | `len(cmd) <= 150` and 복잡 키워드 없음 → Ollama 스킵 |
| `MCP_FILESYSTEM_ROOT` | ContextVar로 파일 접근 루트 격리, 경로 순회(`../`) 방지 |
| `OllamaClient` | httpx 동기 클라이언트, `timeout` 파라미터 지원 |
| `_print_result(console, dict)` | `status` 기반 색상, Panel + 목록 출력 |
| `lang_detect.py` | git ls-files 우선, 비git 디렉터리는 rglob fallback |

---

## 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | 사용할 Ollama 모델 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 주소 |
| `OLLAMA_TIMEOUT` | `300` | LLM 호출 타임아웃 (초) |
| `MCP_FILESYSTEM_ROOT` | 현재 디렉터리 | 파일 접근 루트 |

---

## 설계 결정 사항

- **LangGraph 파이프라인 제거**: v0.3.0에서 Planner→Coder→Tester 파이프라인을 제거하고 독립적인 자동화 명령 모음으로 전환. 코드 생성 대신 개발자 워크플로 자동화에 집중.
- **Ollama는 commit만 사용**: 포매팅, 스캔, 정리 등 나머지 명령은 Ollama 없이 즉시 실행됨.
- **보안 스캔 패턴 기반**: LLM 보안 리뷰 제거, regex 패턴으로만 스캔 (속도 우선).
- **언어 자동 감지**: `git ls-files` 기반으로 실제 추적 파일만 검사, git 외부에서는 rglob fallback.
- **훅 안전 설계**: 기존 pre-commit 훅 자동 백업, uninstall 시 원본 복원 보장.
