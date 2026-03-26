# Locky v3 Upgrade PRD — Goose 수준 CLI Agent로 도약

> PM Analysis Date: 2026-03-26
> Feature: locky-v3-upgrade
> Status: PM Complete

---

## Executive Summary

| 관점 | 내용 |
|------|------|
| **Problem** | Locky는 현재 Ollama-only 단일 모델, 확장성 없는 플러그인, MCP 미지원으로 Goose/Aider 대비 경쟁력 부족 |
| **Solution** | Multi-provider LLM 지원, MCP 네이티브 확장 시스템, 세션 관리, 샌드박싱 등 핵심 인프라 업그레이드 |
| **UX Effect** | 사용자가 OpenAI/Anthropic/Ollama 자유롭게 선택하고, MCP 서버로 무한 확장 가능한 CLI Agent |
| **Core Value** | 100% 오픈소스 + 100% 로컬 우선 + 멀티 프로바이더 = 진정한 모델 독립적 개발자 도구 |

---

## 1. 경쟁사 분석

### 1.1 주요 경쟁 CLI Agent 비교

| 기능 | **Goose** (Block) | **Aider** | **Cline** | **Locky** (현재) |
|------|:-:|:-:|:-:|:-:|
| **GitHub Stars** | 18K+ | 39K+ | 5M+ installs | - |
| **언어** | Rust | Python | TypeScript | Python |
| **Multi-Provider** | 25+ 프로바이더 | 75+ (litellm) | OpenRouter 등 | Ollama only |
| **MCP 지원** | 네이티브 (핵심) | X | 제한적 | X |
| **확장 시스템** | MCP Extensions | X | VS Code Extension | `~/.locky/plugins/` (기초) |
| **세션 관리** | 대화 이력 저장/재개 | Git-aware context | VS Code 내장 | `.locky/session.json` (기초) |
| **샌드박싱** | macOS seatbelt | X | 승인 기반 | `MCP_FILESYSTEM_ROOT` (기초) |
| **Desktop UI** | Electron App | X | VS Code 내장 | Chainlit (기초) |
| **자동 커밋** | X | O (핵심) | X | O |
| **코드베이스 맵** | X | O (repo-map) | O | X |
| **다언어 포맷** | X | X | X | O (7개 언어) |
| **보안 스캔** | X | X | X | O (OWASP) |
| **pre-commit 훅** | X | X | X | O |
| **Jira 통합** | X | X | X | O |

### 1.2 Goose 핵심 강점 (벤치마크 대상)

1. **MCP-First 아키텍처**: 모든 확장이 MCP 서버. 3,000+ MCP 서버 생태계 즉시 활용
2. **25+ LLM 프로바이더**: OpenAI, Anthropic, Google, Ollama, vLLM 등 자유 전환
3. **Summon 시스템**: Skills(컨텍스트 로딩) + Delegate(서브에이전트 위임) 통합
4. **Rich UI 렌더링**: MCP 앱이 Desktop에서 HTML/JS 인라인 렌더링
5. **macOS 샌드박싱**: seatbelt 기반 파일시스템/네트워크 격리
6. **Deeplink 설치**: `goose://extension` URL로 원클릭 MCP 서버 설치
7. **Rust 성능**: 네이티브 바이너리, 즉시 시작

### 1.3 Aider 핵심 강점

1. **75+ 프로바이더** (litellm): 세션 중 모델 전환 가능
2. **Repo-map**: 전체 코드베이스의 구조적 맵 자동 생성
3. **Git-native**: 모든 변경이 의미 있는 커밋으로 자동 기록
4. **100+ 언어**: 프로그래밍 언어 지원 범위
5. **Voice-to-code**: 음성 입력으로 코딩

---

## 2. Locky 현재 상태 (v2.0.1)

### 2.1 강점 (유지해야 할 것)

| 강점 | 상세 |
|------|------|
| **자동화 명령 8개** | commit, format, test, todo, scan, clean, deps, env — LLM 없이 즉시 실행 |
| **다언어 포맷터** | 7개 언어 자동 감지 + 포맷 (경쟁사에 없음) |
| **보안 스캔** | OWASP 패턴 기반 정적 분석 (경쟁사에 없음) |
| **pre-commit 훅** | format→test→scan 파이프라인 (경쟁사에 없음) |
| **Jira 통합** | 이슈 list/create/update/link (경쟁사에 없음) |
| **테스트 품질** | 351개 테스트, 100% 통과, 67% 커버리지 |
| **100% 로컬** | 클라우드 의존성 없음 |

### 2.2 약점 (개선해야 할 것)

| 약점 | 심각도 | 상세 |
|------|:------:|------|
| **Ollama-only** | Critical | 단일 프로바이더, 모델 전환 불가, API 키 기반 서비스 미지원 |
| **MCP 미지원** | Critical | 확장 생태계 접근 불가, 도구 추가 시 코드 수정 필요 |
| **코드베이스 인식 부재** | High | repo-map 없음, 대형 프로젝트에서 컨텍스트 제한 |
| **세션 관리 미흡** | High | 대화 이력 저장/재개/검색 없음 |
| **플러그인 시스템 미약** | High | Click 내부 지식 필요, 선언적 인터페이스 없음 |
| **성능** | Medium | Python 기반, 시작 시간 느림 (vs Rust/Go 네이티브) |
| **에러 복구** | Medium | 재시도/fallback 로직 없음 |
| **보안 샌드박싱** | Medium | ContextVar 경로 제한만 존재, OS 수준 격리 없음 |

---

## 3. 개선 로드맵 (우선순위 순)

### Phase 1: 핵심 인프라 (P0 — Must Have)

#### 3.1 Multi-Provider LLM 지원

**현재**: Ollama 단일 프로바이더, `OllamaClient` 하드코딩

**목표**: OpenAI, Anthropic, Google, Ollama, OpenRouter 등 5+ 프로바이더 지원

**구현 방안**:
```
tools/
├── llm/
│   ├── __init__.py          # LLMClient 추상 인터페이스
│   ├── base.py              # BaseLLMClient (chat, stream, health_check)
│   ├── ollama.py            # 기존 OllamaClient 리팩토링
│   ├── openai.py            # OpenAI/OpenRouter 클라이언트
│   ├── anthropic.py         # Anthropic Claude 클라이언트
│   ├── litellm_adapter.py   # litellm 통합 (75+ 프로바이더 일괄 지원)
│   └── registry.py          # 프로바이더 레지스트리 + 팩토리
```

**설정**:
```yaml
# .locky/config.yaml
llm:
  provider: openai          # ollama | openai | anthropic | litellm
  model: gpt-4o
  api_key_env: OPENAI_API_KEY  # 환경변수 참조 (키 직접 저장 안 함)
  fallback:
    provider: ollama
    model: qwen2.5-coder:7b
```

**핵심 결정**: litellm 통합 vs 직접 구현?
- **권장: litellm 어댑터** — 75+ 프로바이더 즉시 지원, 유지보수 부담 최소화
- 직접 구현은 OpenAI + Anthropic + Ollama 3개만 (litellm 없는 경량 모드)

#### 3.2 MCP 클라이언트 지원

**현재**: 내부 MCP 유틸리티만 존재 (filesystem, git). 외부 MCP 서버 연결 불가

**목표**: 표준 MCP 서버를 도구로 등록하여 agent/ask/edit에서 활용

**구현 방안**:
```
tools/
├── mcp/
│   ├── client.py            # MCP 클라이언트 (stdio/SSE 프로토콜)
│   ├── registry.py          # 등록된 MCP 서버 관리
│   └── config.py            # MCP 서버 설정 로더
```

**설정**:
```yaml
# .locky/config.yaml
mcp_servers:
  - name: filesystem
    command: ["npx", "@modelcontextprotocol/server-filesystem", "/path"]
  - name: github
    command: ["npx", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
```

**범위**: Phase 1에서는 stdio 프로토콜 MCP 클라이언트만. SSE/Streamable HTTP는 Phase 2

#### 3.3 코드베이스 인식 (Repo Map)

**현재**: 없음. Agent가 파일 하나씩 읽어야 함

**목표**: Aider의 repo-map처럼 코드베이스 구조를 자동으로 인덱싱

**구현 방안**:
```python
# tools/repo_map.py
class RepoMap:
    def build(self, root: Path) -> dict:
        """git ls-files → AST 파싱 → 함수/클래스/import 그래프"""
    def get_context(self, query: str, max_tokens: int) -> str:
        """쿼리 관련 파일/함수만 선택하여 컨텍스트 생성"""
    def update_incremental(self, changed_files: list[str]):
        """변경된 파일만 재인덱싱"""
```

- Python: `ast` 모듈로 파싱 (외부 의존성 없음)
- JS/TS: tree-sitter 또는 정규식 기반 (선택)
- 캐시: `.locky/repo-map.json` (git hash 기반 무효화)

---

### Phase 2: 사용자 경험 (P1 — Should Have)

#### 3.4 세션 관리 고도화

**현재**: `.locky/session.json`에 기초적 이력만 저장

**목표**: 대화 이력 저장/재개/검색, 멀티 세션

```
locky session list              # 이전 세션 목록
locky session resume <id>       # 세션 재개 (컨텍스트 복원)
locky session export <id>       # 마크다운 내보내기
```

#### 3.5 스트리밍 출력 개선

**현재**: commit은 동기, ask/edit만 스트리밍

**목표**: 모든 LLM 호출에 실시간 스트리밍 + 진행률 표시

#### 3.6 `locky init` 개선

**현재**: 기초적 설정 마법사

**목표**:
- 프로바이더 자동 감지 (Ollama 실행 중? API 키 있음?)
- MCP 서버 추천 (프로젝트 언어 기반)
- `.locky/config.yaml` 자동 생성 + 검증

#### 3.7 에러 복구 및 재시도

**현재**: 실패 시 에러 반환만

**목표**:
- LLM 호출 재시도 (exponential backoff)
- 모델 fallback (주 모델 실패 → 대체 모델)
- 네트워크 에러 시 로컬 모델 자동 전환

#### 3.8 Lead/Worker 멀티모델 전략

**현재**: 단일 모델만 사용

**목표**: Goose처럼 복잡도에 따라 모델 자동 선택

```yaml
# .locky/config.yaml
llm:
  lead:                        # 복잡한 추론 (ask, agent, edit)
    provider: anthropic
    model: claude-sonnet-4-6
  worker:                      # 단순 작업 (commit 메시지, 요약)
    provider: ollama
    model: qwen2.5-coder:7b
```

#### 3.9 토큰/비용 추적

**현재**: 없음

**목표**: LLM 호출마다 토큰 수/비용 표시 (시장 표준 기능)

```
locky ask "이 함수 뭐 하는 거야?"
[...응답...]
─── 토큰: 1,234 입력 / 567 출력 | 비용: $0.003 ───
```

---

### Phase 3: 확장성 (P2 — Nice to Have)

#### 3.10 플러그인 시스템 v2

**현재**: `~/.locky/plugins/*.py`에서 `register(cli)` 호출

**목표**: 선언적 플러그인 매니페스트 + 마켓플레이스

```yaml
# ~/.locky/plugins/my-plugin/plugin.yaml
name: my-custom-linter
version: 1.0.0
commands:
  - name: lint
    description: "Custom linting rules"
    entry: my_plugin.lint:run
```

#### 3.11 Recipes (워크플로 템플릿)

**현재**: 없음

**목표**: Goose Recipes처럼 재사용 가능한 워크플로 YAML 템플릿

```yaml
# ~/.locky/recipes/pr-ready.yaml
name: PR Ready Check
description: PR 전 전체 검증 파이프라인
steps:
  - format --check
  - test
  - scan --severity high
  - deps
  - commit --dry-run
```

```bash
locky recipe run pr-ready          # 레시피 실행
locky recipe list                  # 등록된 레시피 목록
```

#### 3.12 MCP 서버 내보내기

**현재**: 내부 도구만

**목표**: Locky의 format/scan/test/deps 기능을 MCP 서버로 노출

```bash
locky serve-mcp                 # Locky 기능을 MCP 서버로 실행
# 다른 에이전트(Goose, Claude Code)에서 Locky 도구 사용 가능
```

#### 3.13 보안 샌드박싱

**현재**: ContextVar 기반 경로 제한만

**목표**: macOS seatbelt / Linux seccomp 기반 OS 수준 격리

#### 3.14 Web UI 현대화

**현재**: Chainlit 기반 (기초)

**목표**: React 기반 데스크톱 앱 또는 Terminal UI (Textual/Rich)

---

## 4. 우선순위 매트릭스

| # | 항목 | 영향도 | 난이도 | 우선순위 | 예상 기간 |
|---|------|:------:|:------:|:--------:|:---------:|
| 3.1 | Multi-Provider LLM | 10 | 6 | **P0** | 2주 |
| 3.2 | MCP 클라이언트 | 9 | 7 | **P0** | 2주 |
| 3.3 | Repo Map | 8 | 5 | **P0** | 1주 |
| 3.4 | 세션 관리 (SQLite) | 7 | 4 | **P1** | 1주 |
| 3.5 | 스트리밍 개선 | 6 | 3 | **P1** | 3일 |
| 3.6 | init 개선 | 5 | 3 | **P1** | 3일 |
| 3.7 | 에러 복구/Fallback | 6 | 4 | **P1** | 1주 |
| 3.8 | Lead/Worker 멀티모델 | 7 | 4 | **P1** | 1주 |
| 3.9 | 토큰/비용 추적 | 5 | 2 | **P1** | 2일 |
| 3.10 | 플러그인 v2 | 5 | 6 | **P2** | 2주 |
| 3.11 | Recipes (워크플로 템플릿) | 5 | 4 | **P2** | 1주 |
| 3.12 | MCP 서버 내보내기 | 4 | 5 | **P2** | 1주 |
| 3.13 | 샌드박싱 | 4 | 8 | **P2** | 2주 |
| 3.14 | Web UI 현대화 | 3 | 7 | **P2** | 3주 |

---

## 5. Locky 차별화 전략

### Goose/Aider와 직접 경쟁하지 않는 포지셔닝:

| 경쟁사 | 포지셔닝 | Locky 차별점 |
|--------|---------|------------|
| **Goose** | 범용 AI 에이전트 (MCP 플랫폼) | **자동화 + 에이전트 하이브리드** — format/scan/hook/deps 즉시 실행 |
| **Aider** | 코드 생성 페어 프로그래머 | **DevOps 자동화 내장** — 보안 스캔, 의존성 확인, Jira 통합 |
| **Claude Code** | 프리미엄 CLI (유료) | **100% 무료 + 로컬 우선** |

### Locky의 고유 가치 (Unique Value):

> **"코드 생성 에이전트가 아니라, 개발 워크플로 자동화 플랫폼"**

1. **Automation-First**: LLM 없이 즉시 실행되는 8개 자동화 명령 (경쟁사에 없음)
2. **Multi-Language DevOps**: 7개 언어 포맷터 + OWASP 스캔 + 의존성 확인 통합
3. **Git Pipeline**: pre-commit 훅 → format → test → scan → commit 원스톱
4. **Project Management**: Jira 연동으로 이슈 관리까지 CLI에서 처리
5. **Model Freedom**: litellm으로 75+ 프로바이더 지원하되 로컬 모델 우선

---

## 6. 기술 결정 사항

### 6.1 litellm 도입 여부

| 옵션 | 장점 | 단점 |
|------|------|------|
| **A: litellm 채택** | 75+ 프로바이더 즉시, 유지보수 최소 | 의존성 추가 (무거움), 로컬 전용 철학과 충돌 |
| **B: 직접 구현 3개** | 경량, 의존성 최소 | 프로바이더 추가 시 수동 작업 |
| **C: 하이브리드** | litellm optional, 기본 3개 내장 | 두 경로 유지보수 |

**권장: Option C (하이브리드)** — OpenAI + Anthropic + Ollama 내장, `pip install locky-agent[litellm]`으로 확장

### 6.2 MCP 구현 범위

| 옵션 | 장점 | 단점 |
|------|------|------|
| **A: stdio만** | 구현 간단, 대부분 MCP 서버 지원 | SSE/HTTP 서버 미지원 |
| **B: stdio + SSE** | 원격 MCP 서버 지원 | 복잡도 증가 |

**권장: Option A (stdio)** — Phase 1에서는 stdio만, SSE는 Phase 2

### 6.3 Rust 전환 여부

| 옵션 | 장점 | 단점 |
|------|------|------|
| **A: Python 유지** | 기존 코드 활용, 빠른 개발 | 시작 시간, 메모리 |
| **B: Rust 전환** | Goose 급 성능 | 전면 재작성, 6개월+ |
| **C: 핵심만 Rust** | 성능 크리티컬 부분만 | PyO3 복잡도 |

**권장: Option A (Python 유지)** — 현 단계에서 Rust 전환은 ROI 낮음. 기능 완성이 우선

---

## 7. 성공 기준

| 지표 | 현재 | 목표 (v3) |
|------|------|-----------|
| LLM 프로바이더 수 | 1 (Ollama) | 5+ (OpenAI, Anthropic, Google, Ollama, OpenRouter) |
| MCP 서버 연결 | 0 | stdio 프로토콜 지원, 설정 기반 등록 |
| CLI 명령어 수 | 15 | 20+ (session, mcp, config 추가) |
| 코드베이스 인식 | 없음 | repo-map 생성 + 쿼리 기반 컨텍스트 선택 |
| 세션 관리 | 기초 | 이력 저장/재개/검색 |
| 테스트 통과율 | 100% | 100% 유지 |
| 커버리지 | 67% | 80%+ |

---

## 8. 참고 자료

- [Goose GitHub](https://github.com/block/goose) — Block의 오픈소스 AI 에이전트
- [Goose v1.25.0 Release](https://block.github.io/goose/blog/2026/02/23/goose-v1-25-0/) — 샌드박싱, Summon 통합
- [Aider](https://aider.chat/docs/) — 75+ 프로바이더, repo-map
- [2026 CLI Tools Comparison](https://www.tembo.io/blog/coding-cli-tools-comparison) — 15개 CLI 에이전트 비교
- [Top 5 CLI Agents 2026](https://pinggy.io/blog/top_cli_based_ai_coding_agents/) — 주요 에이전트 비교
- [Goose MCP Deep Dive](https://dev.to/lymah/deep-dive-into-gooses-extension-system-and-model-context-protocol-mcp-3ehl) — MCP 확장 아키텍처
- [Goose vs Claude Code](https://www.morphllm.com/comparisons/goose-vs-claude-code) — 기능 비교
