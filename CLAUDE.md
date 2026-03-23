# Locky Agent — CLAUDE.md

100% 로컬 AI 개발 에이전트. Ollama + LangGraph 기반의 Planner → Coder → Tester 3단계 파이프라인.

---

## 프로젝트 구조

```
locky-agent/
├── config.py                  # Ollama URL/모델/타임아웃, 파이프라인 설정
├── graph.py                   # LangGraph StateGraph 빌드 + run() / run_with_root()
├── cli.py                     # 호환 진입점 (locky run 으로 위임)
│
├── locky_cli/                 # Click CLI 패키지
│   ├── main.py                # locky run / develop / dashboard / web 커맨드
│   ├── fs_context.py          # ContextVar 기반 MCP_FILESYSTEM_ROOT 관리
│   ├── repl.py                # 대화형 REPL 모드
│   └── permissions.py        # 파일 접근 권한 헬퍼
│
├── agents/
│   ├── planner/
│   │   ├── lead.py            # Planner LangGraph 노드 (타이밍 포함)
│   │   ├── context_analyzer.py # 코드베이스 분석 서브에이전트
│   │   └── task_breaker.py    # 원자 단위 태스크 분할 서브에이전트
│   ├── coder/
│   │   ├── lead.py            # Coder LangGraph 노드 (타이밍 포함)
│   │   ├── core_developer.py  # 코드 구현 서브에이전트 (파일 저장)
│   │   └── refactor_formatter.py # PEP8/Conventional Commits 정리
│   ├── tester/
│   │   ├── lead.py            # Tester LangGraph 노드 (타이밍 포함)
│   │   ├── qa_validator.py    # pytest 테스트 생성·실행 서브에이전트
│   │   └── security_auditor.py # 정적 보안 분석 서브에이전트
│   └── prompts/               # 각 에이전트 역할 정의 마크다운 (*.md)
│
├── states/
│   └── state.py               # LockyGlobalState TypedDict (파이프라인 전역 상태)
│
├── tools/
│   ├── ollama_client.py       # Ollama /api/chat 동기·스트리밍 클라이언트
│   ├── mcp_filesystem.py      # read_file / write_file / search_in_files (경로 순회 방지)
│   └── mcp_git.py             # GitPython 래퍼 (status / diff / commit)
│
├── pipeline/                  # Claude Code /develop 스킬용 JSON 상태 관리
│   ├── state.py               # init_run / advance_stage / mark_complete 등
│   ├── runner.py              # CLI: python pipeline/runner.py <verb> <run_id>
│   └── orchestrator.py        # claude_agent_sdk 기반 오케스트레이터 (선택 사용)
│
├── ui/
│   └── app.py                 # Chainlit 웹 UI (/develop 접두사 → 파이프라인)
│
├── docs/                      # 설계 문서 + 패치노트
│   └── patch-notes/           # 날짜별 패치노트 (YYYY-MM-DD.md)
│
├── requirements.txt           # pip 의존성
└── pyproject.toml             # 패키지 설정 (진입점: locky = locky_cli.main:main)
```

---

## 파이프라인 아키텍처

```
사용자 요구사항 (cmd)
        │
        ▼
┌─────────────────────────────────────────────┐
│ Stage 1: Planner Team                       │
│  context_analyzer → (단순 요청: Ollama 스킵)  │
│  task_breaker     → 원자 단위 태스크 JSON     │
└───────────────────┬─────────────────────────┘
                    │ planner_output.task_list
                    ▼
┌─────────────────────────────────────────────┐
│ Stage 2: Coder Team                         │
│  core_developer   → Ollama 코드 생성 + 저장  │
│  refactor_formatter → PEP8 정리             │
└───────────────────┬─────────────────────────┘
                    │ coder_output.modified_files
                    ▼
┌─────────────────────────────────────────────┐
│ Stage 3: Tester Team                        │
│  qa_validator     → pytest 생성·실행        │
│  security_auditor → 정적 패턴 스캔          │
└───────────────────┬─────────────────────────┘
                    │ verdict: pass | fail
          ┌─────────┴──────────┐
        pass               fail (retry_count < 3)
          │                    │
          ▼                    ▼
        END            Coder (피드백 루프)
```

**LangGraph 노드:** `planner_lead → coder_lead → tester_lead`
**조건부 엣지:** `should_continue()` — `verdict == "pass"` 또는 재시도 한도 초과 → END, 그 외 → coder_lead 재실행
**최대 재시도:** `MAX_RETRY_ITERATIONS=3` (env 오버라이드 가능)

---

## 전역 상태 (LockyGlobalState)

| 필드 | 타입 | 설명 |
|------|------|------|
| `cmd` | `str` | 사용자 요구사항 원문 |
| `messages` | `List[str]` (append-only) | 파이프라인 로그 |
| `planner_output` | `PlannerState` | 태스크 목록, 파일 트리, 의존성 요약 |
| `coder_output` | `CoderState` | 수정된 파일 목록, 커밋 메시지 초안 |
| `tester_output` | `TesterState` | 테스트 결과, 보안 이슈, verdict, 피드백 |
| `current_stage` | `str` | `planning/coding/testing/complete/failed` |
| `retry_count` | `int` | 피드백 루프 반복 횟수 |
| `final_report` | `str` | 최종 요약 문자열 |

---

## 서브에이전트 구성

> 모델 티어 원칙
> - **Sonnet**: 코드 생성·추론·테스트 로직 등 품질이 성능에 직결되는 작업
> - **Haiku**: 구조화 출력, 패턴 매칭, 포맷 정리 등 속도·컨텍스트 절약이 우선인 작업
> - 응답은 항상 필요한 최소 형식으로 제한 (JSON only, 설명 금지 등)

### Planner Team

| 에이전트 | 모델 | 이유 |
|---------|------|------|
| **ContextAnalyzer** | `haiku` | 파일 트리 읽기 + 구조 요약. 추론 불필요, 빠른 분석이 우선 |
| **TaskBreaker** | `haiku` | JSON 구조화 출력만 필요. 3회 폴백 로직이 이미 안전망 역할 |

### Coder Team

| 에이전트 | 모델 | 이유 |
|---------|------|------|
| **CoreDeveloper** | `sonnet` | 실제 코드 생성. 품질 저하는 Tester retry 증가로 이어져 오히려 컨텍스트 낭비 |
| **RefactorFormatter** | `haiku` | PEP8 + Conventional Commits 패턴 정리. 규칙 기반 작업 |

### Tester Team

| 에이전트 | 모델 | 이유 |
|---------|------|------|
| **QAValidator** | `sonnet` | pytest 코드 생성 + 실패 원인 분석 포함. 품질이 피드백 루프 횟수에 직결 |
| **SecurityAuditor** | `haiku` | OWASP 패턴 매칭 + 정적 스캔. Critical/High 판정은 규칙 기반이므로 Haiku 충분 |

---

## 컨텍스트 절약 지침

### 1. 응답 형식 강제
각 에이전트 프롬프트(`agents/prompts/*.md`) 말미에 아래 규칙 추가:

- **Haiku 에이전트**: `Output: JSON only. No explanation. No markdown.`
- **Sonnet 에이전트**: `Output: 결과물만 반환. 불필요한 서문·후기 금지.`

### 2. 부모로 돌아오는 응답 크기 제한
CoreDeveloper, QAValidator는 응답이 길어지기 쉬운 에이전트.
프롬프트에 명시:
```
수정된 파일 경로 목록과 결과 요약만 반환.
전체 코드 본문을 응답에 포함하지 말 것 (파일은 write_file()로만 저장).
```

### 3. 단순 요청 패스스루 유지
기존 `len(cmd) < 150` 단순 요청 감지 로직은 유지.
Haiku 에이전트도 단순 요청 시 Ollama 호출 스킵 조건 동일하게 적용.

### 4. SecurityAuditor 스캔 범위 고정
`modified_files`가 비어 있으면 즉시 `skipped` 반환 (기존 로직 유지).
Haiku로 교체 시 전체 프로젝트 스캔 실수 방지를 위해
`_safe_path()` 검사 전 `modified_files` 빈값 체크를 에이전트 진입부에서 명시적으로 수행.

---

## 패치노트 작성 지침

### 규칙
모든 작업이 완료된 후, 반드시 `docs/patch-notes/` 경로에 패치노트 파일을 생성한다.

- **파일명**: `YYYY-MM-DD.md` (예: `2026-03-23.md`)
- **같은 날 여러 작업**: 기존 파일에 섹션을 추가 (덮어쓰기 금지)
- **생성 타이밍**: 파이프라인 `verdict == "pass"` 직후, 최종 리포트 출력 전

### 파일 형식

```markdown
# Patch Notes — YYYY-MM-DD

## [HH:MM] 작업 제목 (cmd 요약)

### Added
- 새로 추가된 기능·파일 목록

### Changed
- 수정된 기능·파일 목록

### Fixed
- 버그 수정 내용

### Files
- `추가/수정된 파일 경로` — 변경 내용 한 줄 요약
```

### 작성 규칙
- `Added / Changed / Fixed` 중 해당 항목만 포함 (빈 섹션 생략)
- 같은 날 두 번째 작업부터는 기존 파일 하단에 새 `## [HH:MM]` 섹션 추가
- `Files` 섹션에는 `coder_output.modified_files` 기준으로 실제 변경된 파일만 기록
- 테스트 실패 후 retry된 경우: `Fixed`에 수정 내용 기재, retry 횟수는 생략

### 예시

```markdown
# Patch Notes — 2026-03-23

## [14:32] 덧셈 프로그램 추가

### Added
- 두 정수를 입력받아 합계를 출력하는 CLI 프로그램

### Files
- `addition.py` — 덧셈 함수 및 CLI 진입점 추가
- `tests/test_addition.py` — pytest 테스트 3종 추가

## [15:10] REST API 서버 기본 구조 추가

### Added
- FastAPI 기반 REST API 서버 뼈대

### Files
- `api/main.py` — FastAPI 앱 초기화 및 라우터 등록
- `api/routes/health.py` — /health 엔드포인트 추가
```

---

## 핵심 설계 패턴

### MCP 파일시스템 루트
- 파이프라인은 작업 대상 프로젝트의 루트를 `MCP_FILESYSTEM_ROOT`로 고정
- `locky_cli/fs_context.py` — `ContextVar` 기반으로 스레드 안전하게 루트 관리
- 모든 파일 I/O는 `tools/mcp_filesystem.py`의 `_safe_path()`를 통해 루트 밖 접근 차단
- 실행: `locky run "요구사항"` → 현재 디렉터리를 루트로 사용

### Ollama 클라이언트
- `tools/ollama_client.py` — httpx 동기(`chat()`) + 비동기 스트리밍(`stream_chat()`)
- 기본 타임아웃: `OLLAMA_TIMEOUT=300s`
- 태스크 분할 전용 짧은 타임아웃: `OLLAMA_TASK_TIMEOUT=60s`
- 단순 요청 감지: `len(cmd) < 150` + 복잡 키워드 없음 → Ollama 호출 최소화

### 파일 블록 파싱 (CoreDeveloper)
LLM 응답에서 파일을 추출하는 3단계 폴백:
1. `[파일경로]\n코드` 형식
2. `=== 파일경로 ===\n코드` 형식
3. `` ```lang\n코드\n``` `` 형식
4. 최종 폴백: `files_to_create[0]` 또는 cmd에서 파일명 추론

### 피드백 루프
- Tester fail → `tester_output.feedback`에 파일/라인/수정방향 포함
- `retry_count`가 `MAX_RETRY_ITERATIONS` 미만이면 Coder 재실행
- CoreDeveloper는 `retry_count > 0`일 때 feedback을 프롬프트에 주입

---

## 진입점 및 실행

```bash
# CLI
locky run "파이썬으로 덧셈 프로그램 만들어줘"
locky run "요구사항" --workspace /path/to/project

# 직접 실행
python cli.py "요구사항"

# 웹 UI
locky dashboard   # Chainlit (localhost:8000)

# Python API
from graph import run_with_root
result = run_with_root("요구사항", root=Path("/path/to/project"))
```

---

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 서버 주소 |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | 사용 모델 |
| `OLLAMA_TIMEOUT` | `300` | 일반 Ollama 호출 타임아웃 (초) |
| `OLLAMA_TASK_TIMEOUT` | `60` | 태스크 분할 전용 타임아웃 (초) |
| `MCP_FILESYSTEM_ROOT` | `cwd` | 파이프라인이 읽기·쓰기 가능한 루트 경로 |
| `MAX_RETRY_ITERATIONS` | `3` | Coder-Tester 피드백 최대 반복 횟수 |

---

## Claude Code /develop 스킬

`~/.claude/commands/develop.md` — 글로벌 스킬로 등록되어 있음.
Claude Code가 직접 Planner→Coder→Tester를 Agent 도구로 오케스트레이션.
파이프라인 상태는 `.pipeline/runs/{run_id}/` JSON 파일로 관리.

스킬 사용:
```
/develop 파이썬으로 REST API 서버 만들어줘
```

---

## 주요 의존성

| 패키지 | 용도 |
|--------|------|
| `langgraph` | 파이프라인 StateGraph |
| `langchain-core` | 메시지 타입 |
| `httpx` | Ollama HTTP 클라이언트 |
| `gitpython` | Git 래퍼 |
| `click` + `rich` | CLI |
| `chainlit` | 웹 UI |
| `pydantic` | 데이터 검증 |

---

## 알려진 설계 결정

- **Ollama 단순 요청 최적화**: `context_analyzer`와 `task_breaker` 모두 `len(cmd) < 150` + 비복잡 키워드 체크로 Ollama 호출을 건너뜀. 단순 "만들어줘" 요청은 1-2분 내 완료 가능.
- **보안 스캔 범위**: `modified_files`가 비어 있으면 전체 프로젝트 스캔을 하지 않음. 이전에 `.venv` 포함 20,000개 오탐 버그가 있었으며 수정 완료.
- **파일명 추론**: TaskBreaker JSON 파싱 실패 시 한글 명사 맵 + 영어 단어 추출로 `addition.py` 같은 의미 있는 파일명 자동 생성.
- **진행 상황 출력**: 각 lead 노드가 `time.time()` 기반 경과 시간을 출력. CLI는 스피너 없이 에이전트 `print()`가 그대로 터미널에 출력됨.