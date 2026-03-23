# Locky Agent — CLAUDE.md

100% 로컬 개발자 자동화 도구. Ollama 기반 AI 커밋 메시지 생성 + 8개 자동화 명령(포매팅, 테스트, 보안 스캔 등).

---

## 프로젝트 구조

```
locky-agent/
├── config.py                  # Ollama URL/모델/타임아웃, 파이프라인 설정
├── cli.py                     # 호환 진입점 (locky_cli.main으로 위임)
│
├── locky_cli/                 # Click CLI 패키지
│   ├── main.py                # 8개 서브커맨드 + REPL 진입점 (v0.3.0)
│   ├── fs_context.py          # ContextVar 기반 MCP_FILESYSTEM_ROOT 관리
│   ├── repl.py                # 대화형 REPL (/commit, /format 등 슬래시 명령)
│   └── permissions.py        # 파일 접근 권한 헬퍼
│
├── actions/                   # 자동화 명령 모듈 (각각 run(root, **opts) -> dict)
│   ├── __init__.py            # 모든 runner export
│   ├── commit.py              # git diff → Ollama → Conventional Commits → commit
│   ├── format_code.py         # black + isort + flake8 실행
│   ├── test_runner.py         # pytest 실행 및 결과 파싱
│   ├── todo_collector.py      # TODO/FIXME/HACK/XXX 수집 및 마크다운 저장
│   ├── security_scan.py       # OWASP 패턴 기반 정적 보안 스캔
│   ├── cleanup.py             # __pycache__, .pyc, .pytest_cache 등 정리
│   ├── deps_check.py          # requirements.txt vs 설치 버전 비교
│   └── env_template.py        # .env → .env.example 자동 생성
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
├── tools/
│   ├── ollama_client.py       # Ollama /api/chat 동기·스트리밍 클라이언트
│   ├── mcp_filesystem.py      # read_file / write_file / search_in_files (경로 순회 방지)
│   └── mcp_git.py             # GitPython 래퍼 (status / diff / commit)
│
├── pipeline/                  # Claude Code /develop 스킬용 JSON 상태 관리
│   ├── state.py               # init_run / advance_stage / mark_complete 등
│   ├── runner.py              # CLI: python pipeline/runner.py <verb> <run_id>
│   └── orchestrator.py        # claude_agent_sdk 기반 오케스트레이터
│
├── ui/
│   └── app.py                 # Chainlit 웹 UI
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
locky format [--check] [PATH...]
locky test   [PATH] [-v]
locky todo   [--output FILE]
locky scan   [--severity LEVEL]
locky clean  [--force]
locky deps
locky env    [--output FILE]
```

### REPL 슬래시 명령

`locky` (인수 없이) → REPL 진입. `/commit`, `/format` 등 슬래시 명령으로 동일한 actions/ 모듈 호출.
`exit` / `quit` (슬래시 없이도) → 종료.

---

## 주요 설계 패턴

| 패턴 | 내용 |
|---|---|
| `_is_simple_request(cmd)` | `len(cmd) <= 150` and 복잡 키워드 없음 → Ollama 스킵 |
| `MCP_FILESYSTEM_ROOT` | ContextVar로 파일 접근 루트 격리, 경로 순회(`../`) 방지 |
| `OllamaClient` | httpx 동기 클라이언트, `timeout` 파라미터 지원 |
| `_print_result(console, dict)` | `status` 기반 색상, Panel + 목록 출력 |

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
- **actions/ 독립 모듈 구조**: 각 명령이 서로 의존하지 않아 단위 테스트 및 독립 사용 용이.
- **보안 스캔 패턴 기반**: LLM 보안 리뷰 제거, regex 패턴으로만 스캔 (속도 우선).
