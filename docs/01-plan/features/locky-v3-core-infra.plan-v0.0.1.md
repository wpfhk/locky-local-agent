# locky-v3-core-infra Planning Document

> **Summary**: Locky v3 Phase 1 -- Multi-provider LLM, MCP stdio client, Repo Map 핵심 인프라 업그레이드
>
> **Project**: locky-agent
> **Version**: 2.0.0 -> 3.0.0
> **Author**: CTO Lead (PDCA)
> **Date**: 2026-03-26
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | Locky는 Ollama-only 단일 LLM, MCP 미지원, 코드베이스 인식 부재로 Goose/Aider 대비 확장성과 경쟁력이 부족하다 |
| **Solution** | Multi-provider LLM 추상 계층(Ollama/OpenAI/Anthropic + optional litellm), MCP stdio 클라이언트, AST 기반 Repo Map 도입 |
| **Function/UX Effect** | 사용자가 `config.yaml`에서 프로바이더를 선택하면 기존 CLI 명령이 동일하게 동작하며, MCP 서버 도구를 등록하여 확장 가능 |
| **Core Value** | 100% 로컬 우선 철학 유지 + 모델 독립성 확보 + MCP 생태계 접근 = 개방형 개발자 자동화 플랫폼 |

---

## Context Anchor

> Auto-generated from Executive Summary. Propagated to Design/Do documents for context continuity.

| Key | Value |
|-----|-------|
| **WHY** | Ollama-only, MCP 미지원, repo-map 부재로 확장성 한계 |
| **WHO** | Locky CLI 사용자 (개발자), 다양한 LLM 프로바이더 사용자 |
| **RISK** | 기존 351개 테스트 회귀, config.yaml 하위 호환성 깨짐, 외부 의존성 증가 |
| **SUCCESS** | 3+ LLM 프로바이더 동작, MCP stdio 서버 연결 성공, repo-map 생성/쿼리 동작, 기존 테스트 100% 통과 |
| **SCOPE** | Phase 1만: LLM 추상화 + MCP stdio client + Repo Map. 세션/스트리밍/UI/샌드박스 제외 |

---

## 1. Overview

### 1.1 Purpose

Locky v3 Phase 1은 세 가지 핵심 인프라를 추가하여 Locky를 모델 독립적이고 확장 가능한 CLI 에이전트로 업그레이드한다:

1. **Multi-Provider LLM**: Ollama 외에 OpenAI, Anthropic을 직접 지원하고, litellm 어댑터로 75+ 프로바이더 확장
2. **MCP stdio Client**: 표준 MCP 서버를 외부 도구로 등록하여 Locky의 기능을 무한 확장
3. **Repo Map**: 코드베이스 구조를 AST 기반으로 인덱싱하여 컨텍스트 품질 향상

### 1.2 Background

- Goose는 25+ 프로바이더 + MCP-First 아키텍처로 빠르게 성장 중 (18K+ Stars)
- Aider는 litellm 기반 75+ 프로바이더 + repo-map으로 코드 생성 품질 우위
- Locky v2.0.1은 자동화 명령(format/scan/hook/deps)에서 차별화되지만, LLM/확장성에서 뒤처짐
- PRD 분석 결과 Phase 1 (Multi-Provider + MCP + Repo Map)이 가장 높은 영향도와 우선순위

### 1.3 Related Documents

- PRD: `docs/00-pm/locky-v3-upgrade.prd.md`
- 현재 아키텍처: `CLAUDE.md` 프로젝트 구조 섹션

---

## 2. Scope

### 2.1 In Scope

- [x] Multi-Provider LLM 추상 계층 (`tools/llm/`)
  - [x] `base.py` -- `BaseLLMClient` ABC (chat, stream, health_check)
  - [x] `ollama.py` -- 기존 `OllamaClient` 리팩토링
  - [x] `openai.py` -- OpenAI/OpenRouter 클라이언트
  - [x] `anthropic.py` -- Anthropic Claude 클라이언트
  - [x] `registry.py` -- 프로바이더 레지스트리 + 팩토리
  - [x] `litellm_adapter.py` -- optional litellm 통합
- [x] MCP stdio Client (`tools/mcp/`)
  - [x] `client.py` -- stdio 프로토콜 MCP 클라이언트
  - [x] `registry.py` -- 등록된 MCP 서버 관리
  - [x] `config.py` -- MCP 서버 설정 로더
- [x] Repo Map (`tools/repo_map.py`)
  - [x] Python AST 파싱으로 함수/클래스/import 추출
  - [x] git ls-files 기반 파일 목록
  - [x] 증분 업데이트 (변경 파일만 재인덱싱)
  - [x] `.locky/repo-map.json` 캐시 (git hash 기반 무효화)
- [x] `config.yaml` 확장 (llm, mcp_servers 섹션 추가, 하위 호환)
- [x] 기존 `commit.py`, `shell_command.py`에서 새 LLM 추상 계층 사용
- [x] 모든 신규 모듈에 대한 단위 테스트

### 2.2 Out of Scope

- 세션 관리 고도화 (Phase 2)
- 스트리밍 출력 개선 (Phase 2)
- `locky init` 마법사 개선 (Phase 2)
- 재시도/fallback 고급 로직 (Phase 2, 최소한의 에러 처리만 포함)
- Lead/Worker 멀티모델 전략 (Phase 2)
- 토큰/비용 추적 (Phase 2)
- 플러그인 v2 (Phase 3)
- Recipes 워크플로 템플릿 (Phase 3)
- MCP 서버 내보내기 (Phase 3)
- 샌드박싱 (Phase 3)
- Web/Desktop/TUI UI (Phase 3)
- SSE/Streamable HTTP MCP 전송 (Phase 2)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | `BaseLLMClient` ABC 정의: `chat()`, `stream()`, `health_check()` 메서드 | High | Pending |
| FR-02 | `OllamaLLMClient` -- 기존 OllamaClient 기능을 BaseLLMClient 인터페이스로 래핑 | High | Pending |
| FR-03 | `OpenAILLMClient` -- OpenAI Chat Completions API 지원 (httpx 기반) | High | Pending |
| FR-04 | `AnthropicLLMClient` -- Anthropic Messages API 지원 (httpx 기반) | High | Pending |
| FR-05 | `LLMRegistry` -- config.yaml 기반 프로바이더 자동 선택 + 팩토리 | High | Pending |
| FR-06 | `LiteLLMAdapter` -- litellm optional import, 없으면 ImportError 안내 | Medium | Pending |
| FR-07 | MCP stdio Client -- subprocess로 MCP 서버 프로세스 관리, JSON-RPC over stdio | High | Pending |
| FR-08 | MCP Registry -- config.yaml의 `mcp_servers` 섹션에서 서버 목록 로드 | High | Pending |
| FR-09 | MCP Tool Discovery -- `tools/list` 호출로 MCP 서버 도구 목록 조회 | High | Pending |
| FR-10 | MCP Tool Call -- `tools/call` 로 MCP 서버 도구 실행 | High | Pending |
| FR-11 | `RepoMap.build()` -- git ls-files + Python AST 파싱으로 구조 맵 생성 | High | Pending |
| FR-12 | `RepoMap.get_context()` -- 쿼리 관련 파일/함수 선택하여 컨텍스트 문자열 반환 | High | Pending |
| FR-13 | `RepoMap.update_incremental()` -- 변경 파일만 재파싱 | Medium | Pending |
| FR-14 | `.locky/repo-map.json` 캐시 -- git commit hash 기반 무효화 | Medium | Pending |
| FR-15 | `config.yaml` 하위 호환 -- 기존 ollama 섹션 그대로 동작 | High | Pending |
| FR-16 | `commit.py`에서 LLM Registry를 통해 커밋 메시지 생성 (기존 동작 유지) | High | Pending |
| FR-17 | `shell_command.py`에서 LLM Registry를 통해 명령 생성 (기존 동작 유지) | High | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Performance | LLM 클라이언트 초기화 < 100ms | 단위 테스트 타이밍 |
| Performance | Repo Map build (1000 파일) < 5초 | 벤치마크 테스트 |
| Compatibility | Python 3.10+ 지원 | CI 매트릭스 |
| Compatibility | 기존 351개 테스트 100% 통과 | pytest 실행 |
| Security | API 키를 config.yaml에 직접 저장하지 않음 (env var 참조만 허용) | 코드 리뷰 |
| Reliability | Ollama 미실행 시 기존과 동일한 fallback 동작 | 통합 테스트 |
| Extensibility | 새 LLM 프로바이더 추가 시 1개 파일만 작성 | 아키텍처 리뷰 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] 모든 FR (FR-01 ~ FR-17) 구현 완료
- [ ] `tools/llm/` 패키지: 4개 프로바이더 클라이언트 + 레지스트리 + litellm 어댑터
- [ ] `tools/mcp/` 패키지: stdio client + registry + config
- [ ] `tools/repo_map.py`: build + get_context + update_incremental + 캐시
- [ ] `config.yaml` 확장: llm, mcp_servers 섹션 추가
- [ ] `commit.py`, `shell_command.py` LLM 추상 계층 사용으로 전환
- [ ] 단위 테스트: 신규 모듈별 최소 10개 이상
- [ ] 기존 351개 테스트 100% 통과 (회귀 없음)
- [ ] 코드 리뷰 완료

### 4.2 Quality Criteria

- [ ] 신규 코드 테스트 커버리지 80% 이상
- [ ] 기존 커버리지(67%) 감소 없음 (증가 목표)
- [ ] 설계-구현 Match Rate >= 90%
- [ ] Critical 이슈 0개

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| 기존 commit.py/shell_command.py 리팩토링 시 회귀 | High | Medium | LLM Registry에 Ollama 기본값 유지, 기존 테스트 먼저 확인 후 점진적 전환 |
| litellm 의존성이 무거움 (200MB+) | Medium | High | optional extras로 분리: `pip install locky-agent[litellm]` |
| MCP stdio 프로세스 관리 복잡도 | Medium | Medium | 단순한 subprocess.Popen + JSON-RPC 파서, 타임아웃 처리 |
| config.yaml 스키마 변경으로 기존 설정 깨짐 | High | Low | 기존 `ollama` 섹션 그대로 유지, `llm` 섹션은 추가(additive) |
| OpenAI/Anthropic API 키 노출 위험 | High | Low | config.yaml에는 env var 이름만 저장, `api_key_env: OPENAI_API_KEY` 패턴 |
| Python AST 파싱이 JS/TS 미지원 | Medium | High | Phase 1은 Python만, JS/TS는 정규식 fallback 또는 Phase 2 |
| MCP 서버 프로세스 좀비/누수 | Medium | Medium | atexit 핸들러 + context manager 패턴으로 정리 보장 |

---

## 6. Impact Analysis

### 6.1 Changed Resources

| Resource | Type | Change Description |
|----------|------|--------------------|
| `tools/ollama_client.py` | Module | 기존 사용 유지하되, `tools/llm/ollama.py`가 이를 래핑. 직접 사용하는 곳은 LLM Registry로 전환 |
| `tools/ollama_guard.py` | Module | 변경 없음. Ollama 전용 guard로 그대로 유지 |
| `config.py` | Config | `llm` 섹션 추가를 위해 `_cfg()` 확장. 기존 `OLLAMA_*` 상수 유지 |
| `locky_cli/config_loader.py` | Config | `llm`, `mcp_servers` 섹션 파싱 추가 |
| `actions/commit.py` | Module | `_generate_commit_message()` 내부를 LLM Registry 호출로 전환 |
| `actions/shell_command.py` | Module | Ollama 직접 호출을 LLM Registry 호출로 전환 |
| `.locky/config.yaml` | Config File | `llm`, `mcp_servers` 섹션 추가 (기존 `ollama` 섹션 유지) |
| `pyproject.toml` | Build Config | optional deps에 `litellm`, `openai`, `anthropic` 추가 |
| `requirements.txt` | Dependencies | 핵심 의존성은 변경 없음 (httpx 이미 존재) |

### 6.2 Current Consumers

| Resource | Operation | Code Path | Impact |
|----------|-----------|-----------|--------|
| `OllamaClient` | CREATE | `actions/commit.py:_generate_commit_message()` | LLM Registry로 전환 |
| `OllamaClient` | CREATE | `actions/shell_command.py` (Ollama 직접 호출) | LLM Registry로 전환 |
| `OllamaClient` | CREATE | `tools/ollama_client.py` (직접 import) | 래핑 유지 |
| `config.OLLAMA_*` | READ | `config.py`, `actions/commit.py`, `locky_cli/` | 하위 호환 유지 |
| `config_loader.load_config()` | READ | `config.py:_cfg()`, `locky_cli/main.py` | 확장 (기존 동작 유지) |
| `ollama_guard.ensure_ollama()` | CALL | `actions/commit.py` | 변경 없음 |

### 6.3 Verification

- [ ] `actions/commit.py` -- LLM Registry 전환 후 기존 테스트 통과
- [ ] `actions/shell_command.py` -- LLM Registry 전환 후 기존 테스트 통과
- [ ] `config.yaml` 없는 환경에서 기존 OLLAMA_* 환경변수로 동작 확인
- [ ] `config.yaml`에 `llm` 섹션 없이 `ollama` 섹션만 있는 경우 기존 동작 유지
- [ ] 모든 기존 테스트 (351개) 통과

---

## 7. Architecture Considerations

### 7.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| **Starter** | Simple structure | Static sites, portfolios | |
| **Dynamic** | Feature-based modules, BaaS | Web apps with backend | **X** |
| **Enterprise** | Strict layer separation, DI, microservices | High-traffic systems | |

Locky는 Dynamic 레벨 프로젝트. CLI 도구이며 actions/ 패키지 기반 모듈러 구조.

### 7.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| LLM 추상화 | A: litellm only / B: 직접 3개 / C: 하이브리드 | **C: 하이브리드** | 내장 3개(Ollama/OpenAI/Anthropic) + optional litellm. 경량 유지 + 확장성 |
| MCP 프로토콜 | A: stdio only / B: stdio + SSE | **A: stdio only** | Phase 1 범위. 대부분 MCP 서버가 stdio 지원 |
| Repo Map 파싱 | A: Python ast only / B: tree-sitter | **A: Python ast** | 외부 의존성 없음, Python 프로젝트 우선. JS/TS는 정규식 fallback |
| HTTP 클라이언트 | httpx (기존) / requests / aiohttp | **httpx** | 기존 사용 중, sync+async 모두 지원 |
| Config 스키마 | A: 기존 ollama 확장 / B: llm 섹션 신규 추가 | **B: llm 섹션 추가** | 하위 호환 유지 (ollama 섹션 그대로) + 새 프로바이더용 llm 섹션 |
| API 키 관리 | A: config.yaml 직접 저장 / B: env var 참조 | **B: env var 참조** | 보안. `api_key_env: OPENAI_API_KEY` 패턴 |
| 언어 | Python 유지 | **Python** | PRD 하드 제약. Rust 전환 금지 |

### 7.3 Clean Architecture Approach

```
Selected Level: Dynamic

Folder Structure (Phase 1 additions):
tools/
├── llm/                    # NEW: Multi-Provider LLM
│   ├── __init__.py         # Public exports
│   ├── base.py             # BaseLLMClient ABC
│   ├── ollama.py           # OllamaLLMClient
│   ├── openai.py           # OpenAILLMClient
│   ├── anthropic.py        # AnthropicLLMClient
│   ├── litellm_adapter.py  # LiteLLMClient (optional)
│   └── registry.py         # LLMRegistry (factory + config binding)
├── mcp/                    # NEW: MCP stdio Client
│   ├── __init__.py
│   ├── client.py           # MCPClient (stdio JSON-RPC)
│   ├── registry.py         # MCPRegistry (server management)
│   └── config.py           # MCP config loader
├── repo_map.py             # NEW: Repo Map builder
├── ollama_client.py        # EXISTING: kept for backward compat
├── ollama_guard.py         # EXISTING: unchanged
├── mcp_filesystem.py       # EXISTING: unchanged
├── mcp_git.py              # EXISTING: unchanged
└── jira_client.py          # EXISTING: unchanged
```

---

## 8. Convention Prerequisites

### 8.1 Existing Project Conventions

- [x] `CLAUDE.md` has coding conventions section
- [ ] `docs/01-plan/conventions.md` exists -- N/A
- [ ] `CONVENTIONS.md` exists at project root -- N/A
- [ ] ESLint configuration -- N/A (Python project)
- [ ] Prettier configuration -- N/A
- [x] `pyproject.toml` exists with pytest config

### 8.2 Conventions to Define/Verify

| Category | Current State | To Define | Priority |
|----------|---------------|-----------|:--------:|
| **Naming** | `snake_case` for Python | 유지 | High |
| **Folder structure** | `actions/`, `tools/`, `locky_cli/` | `tools/llm/`, `tools/mcp/` 추가 | High |
| **Import order** | stdlib > third-party > local | 유지 | Medium |
| **Environment variables** | `OLLAMA_*` 패턴 | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` 추가 | Medium |
| **Error handling** | Exception catch + fallback | LLM 통합 에러 타입 정의 (`LLMError`) | Medium |

### 8.3 Environment Variables Needed

| Variable | Purpose | Scope | To Be Created |
|----------|---------|-------|:-------------:|
| `OLLAMA_BASE_URL` | Ollama 서버 주소 | Server | Existing |
| `OLLAMA_MODEL` | Ollama 모델명 | Server | Existing |
| `OLLAMA_TIMEOUT` | Ollama 타임아웃 | Server | Existing |
| `OPENAI_API_KEY` | OpenAI API 키 | Server | New |
| `ANTHROPIC_API_KEY` | Anthropic API 키 | Server | New |
| `LITELLM_API_KEY` | litellm 프로바이더 API 키 | Server | New (optional) |

---

## 9. Next Steps

1. [x] Write design document (`locky-v3-core-infra.design-v0.0.1.md`)
2. [ ] Implement Phase 1 modules
3. [ ] Run gap analysis
4. [ ] Generate completion report

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.0.1 | 2026-03-26 | Initial draft -- Phase 1 scope (LLM + MCP + Repo Map) | CTO Lead |
