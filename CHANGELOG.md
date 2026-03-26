# Changelog

All notable changes to Locky are documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
Versioning: [Semantic Versioning](https://semver.org/)

---

## [3.0.0] - 2026-03-26

> Ollama-only CLI에서 75+ 프로바이더, MCP 네이티브 확장 플랫폼으로 도약

### Added

**Phase 1 — Core Infra**
- `tools/llm/` 멀티 프로바이더 LLM 추상 계층 (base, ollama, openai, anthropic, registry)
- `tools/llm/litellm_adapter.py` optional 어댑터로 75+ 프로바이더 지원
- `tools/mcp/client.py` MCP stdio 클라이언트 (JSON-RPC)
- `tools/mcp/registry.py` MCP 서버 레지스트리 및 라이프사이클 관리
- `tools/mcp/config.py` `.locky/config.yaml` 기반 MCP 서버 설정 로더
- `tools/repo_map.py` AST 기반 코드베이스 인덱싱 + 증분 업데이트
- `actions/commit.py`, `actions/shell_command.py` LLM Registry 통합 리팩토링

**Phase 2 — UX + Reliability**
- `tools/session/store.py` SQLite 기반 세션 저장소 (WAL 모드)
- `tools/session/manager.py` 세션 라이프사이클 (create/resume/export/delete)
- `tools/llm/streaming.py` 프로바이더 무관 통합 스트리밍 (StreamEvent + UnifiedStreamer)
- `tools/llm/retry.py` Exponential backoff (3회 기본) + fallback chain
- `tools/llm/tracker.py` 호출별 토큰 수 및 비용 추정 (주요 프로바이더 가격표 내장)
- `locky session list` / `resume <id>` / `export <id>` CLI 명령
- `locky init` 프로바이더 자동 감지 (Ollama/OpenAI/Anthropic) + config 검증
- Lead/Worker 멀티모델 전략 (`llm.lead` / `llm.worker` config 섹션)

**Phase 3 — Extensibility**
- `tools/plugins/manifest.py` 선언적 `plugin.yaml` 매니페스트 파서
- `tools/plugins/loader.py` 플러그인 디스커버리 및 로딩
- `tools/plugins/registry.py` 플러그인 라이프사이클 관리
- `tools/recipes/parser.py` YAML 워크플로 템플릿 파서
- `tools/recipes/runner.py` 레시피 실행 엔진
- `tools/mcp/server.py` Locky 기능을 MCP stdio 서버로 노출 (format/scan/test/deps)
- `tools/sandbox/base.py` OS 추상 샌드박스 인터페이스
- `tools/sandbox/macos.py` macOS seatbelt (`sandbox-exec`) 구현
- `tools/sandbox/linux.py` Linux seccomp + 네임스페이스 구현
- `ui/tui.py` Rich/Textual 기반 터미널 대시보드
- `locky recipe run <name>` / `list` CLI 명령
- `locky serve-mcp` CLI 명령
- `locky tui` CLI 명령

### Changed
- `locky_cli/config_loader.py` — LLM/MCP/Session/Lead-Worker config 헬퍼 추가
- `locky_cli/main.py` — 20+ 서브커맨드로 확장
- `tools/llm/registry.py` — `get_lead_client()`, `get_worker_client()`, `get_fallback_client()` 추가
- `pyproject.toml` — litellm/textual optional extras 추가

### Fixed
- `actions/update.py` `_git_pull` 에러 메시지에 `git pull 실패:` 접두사 누락 수정

### Metrics
- Tests: 351 → **721** (+370)
- Coverage: 67% → **72%** (+5%)
- CLI commands: 15 → **20+**
- LLM providers: 1 → **75+**
- New source files: **~36**
- New test files: **~24**

---

## [2.0.1] - 2026-03-25

> CPU 추론 안정화 및 버그 픽스

### Fixed
- `actions/commit.py` per-file `git add` → `git add -u` / `git add .`로 교체 (pathspec 오류 해결)
- `locky/agents/edit_agent.py` `chat()` → `stream()` 전환 (CPU-only Ollama ReadTimeout 해결)
- `locky/agents/edit_agent.py` `timeout=None` 옵션 추가 (CPU 추론 무제한 대기)
- `tests/test_agents_edit.py` mock을 `stream()` 기반으로 업데이트

### Metrics
- Tests: 351/351 (100%)
- Coverage: 67%
- Design match rate: 98%

---

## [2.0.0] - 2026-03-24

> 자동화 도구에서 AI 에이전트로 진화

### Added
- `locky/core/` 패키지 — Session, Context, Agent 3계층 아키텍처
- `locky/agents/` 패키지 — ask_agent, edit_agent, commit_agent
- `locky/runtime/local.py` 로컬 런타임 (Ollama 기반)
- `locky ask "질문"` 코드베이스 자연어 질의응답 명령
- `locky edit FILE "지시" [--apply]` AI 코드 편집 명령 (unified diff + streaming)
- `locky agent "태스크"` 멀티스텝 자율 에이전트 명령
- REPL `/ask`, `/edit` 슬래시 명령 추가
- 67개 신규 테스트 (v2 패키지)

### Changed
- CLI 명령어: 11 → **15개**
- 테스트: 263 → **351개** (+88)
- 커버리지: 53% → **67%** (+14%)

### Metrics
- Design match rate: 97%
- Tests: 351 passed
- Coverage: 67%

---

## [1.1.0] - 2026-03-23

> 설정 시스템 + REPL 고도화 + Jira 통합

### Added
- `.locky/config.yaml` 프로젝트 설정 시스템 도입
- `locky init` 대화형 초기화 마법사
- `locky update` 셀프 업데이트 명령 (git pull + pip reinstall)
- `locky jira list` / `create` / `status` Jira 통합 명령
- `tools/jira_client.py` Jira REST API 클라이언트
- `locky_cli/context.py` 세션 프로파일 (`.locky/profile.json`) 관리
- REPL `/update` 슬래시 명령

### Changed
- 환경변수 기반 설정 → config.yaml + 환경변수 하이브리드
- REPL 세션 컨텍스트 자동 업데이트 (프로파일 기반)

---

## [1.0.0] - 2026-03-22

> 100% 로컬 개발자 자동화 도구 — 첫 릴리스

### Added
- `locky commit [--dry-run] [--push]` Ollama 기반 AI 커밋 메시지 생성
- `locky format [--check] [--lang LANG]` 7개 언어 자동 감지 포맷터
- `locky test [PATH] [-v]` pytest 실행 및 결과 파싱
- `locky todo [--output FILE]` TODO/FIXME/HACK/XXX 수집
- `locky scan [--severity LEVEL]` OWASP 패턴 기반 보안 스캔
- `locky clean [--force]` 캐시/임시 파일 정리
- `locky deps` 의존성 버전 비교 (requirements.txt/pyproject.toml/package.json/go.mod)
- `locky env [--output FILE]` .env → .env.example 자동 생성
- `locky hook install/uninstall/status` pre-commit 훅 (format→test→scan)
- `locky run STEP [STEP...]` 멀티스텝 파이프라인
- `locky plugin list` 플러그인 목록
- 인터랙티브 REPL (`locky` 인수 없이 실행)
- `tools/ollama_client.py` httpx 기반 Ollama /api/chat 클라이언트
- `tools/ollama_guard.py` Ollama 헬스체크 + 자동 시작 + 모델 확인
- `tools/mcp_filesystem.py` 경로 순회 방지 파일 접근
- `tools/mcp_git.py` GitPython 래퍼
- `locky_cli/lang_detect.py` git ls-files 기반 언어 자동 감지
- `~/.locky/plugins/` 디렉터리 기반 플러그인 로더

### Architecture
- `actions/` 독립 모듈 패턴 — 각 명령이 `run(root, **opts) -> dict` 시그니처
- `_STEP_RUNNERS` 딕셔너리 기반 파이프라인
- `MCP_FILESYSTEM_ROOT` ContextVar 기반 파일 접근 격리

### Metrics
- CLI commands: 11
- Formatter languages: 7 (Python/JS/TS/Go/Rust/Kotlin/Swift)
- Tests: ~100
- 100% local, zero cloud dependency
