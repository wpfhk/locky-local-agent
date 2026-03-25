# locky v2 대규모 개편 — Plan Document

> **Feature**: locky-v2-overhaul
> **Version**: v2.0.0
> **Author**: youngsang.kwon
> **Date**: 2026-03-25
> **Status**: Draft
> **PRD**: docs/00-pm/locky-v2-improvement.prd.md

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | locky v1은 11개 독립 명령 번들로 유용하지만, 명령 간 AI 컨텍스트 공유가 없고 세션이 끊기면 상태가 사라진다. OpenHands(69.7K stars)·Goose가 "자율 에이전트" 시장을 선점하는 동안 locky는 "스크립트 번들"에 머물러 있다. |
| **Solution** | `actions/` → Agent-based 파이프라인으로 재설계. Core(agent+session+context) + Tools(기존 actions 재사용) + Runtime(로컬 실행) 계층 분리. AI가 선택적이 아닌 1등 시민으로 통합. |
| **Function/UX Effect** | `locky` REPL에서 "테스트 실패한 파일 고쳐줘"라고 하면 — test runner가 실패 컨텍스트를 수집 → AI edit agent가 코드 수정 → test 재실행 — 모두 단일 세션에서 자동 완결된다. |
| **Core Value** | "OpenHands처럼 자율적이되, Docker 없이 pip install 하나로" — 100% 로컬 AI 에이전트, 개발자 통제권 유지 |

---

## Context Anchor

| Key | Value |
|-----|-------|
| **WHY** | OpenHands(SDK-first)·Goose(Custom Distribution) 아키텍처를 분석한 결과, locky의 핵심 기회는 "워크플로 자동화 번들 + AI 에이전트"의 결합 — 경쟁사 어느 곳도 이 조합을 가볍게 제공하지 않는다. |
| **WHO** | 터미널 중심 + 100% 로컬 + Ollama 보유 개발자 (한국어 Python/Go 개발자 beachhead) |
| **RISK** | 대규모 재작성으로 v1 하위 호환 깨질 위험 / 로컬 LLM 품질이 autonomous action을 보장 못할 위험 |
| **SUCCESS** | Agent loop 동작 (task→plan→execute→verify) + 기존 11개 명령 하위 호환 + `locky ask/edit` 동작 + 테스트 커버리지 ≥75% |
| **SCOPE** | Core 에이전트 루프, AI ask/edit, Session 컨텍스트; Docker 샌드박스·웹 GUI·클라우드 제외 |

---

## 1. Overview

### 1.1 Background

**경쟁사 분석 요약** (2026-03-25 기준):

| 도구 | Stars | 핵심 아키텍처 | locky 포지셔닝 대비 |
|------|-------|-------------|------------------|
| OpenHands | 69.7K | SDK → CLI/GUI → Cloud 계층 | 우리는 SDK+CLI만 (가벼움) |
| Goose | TBD | Rust core + Custom Distribution + MCP | Profile 시스템 Phase 2에서 채용 |
| aider | 39K | Code/Ask/Architect 모드 | AI 편집은 우리도 추가, 워크플로 자동화는 우리만 |
| Cline CLI 2.0 | TBD | MCP native, 명시적 승인 | 승인 철학 동일 (--dry-run 패턴) |

**선택: Option B — 에이전트 파이프라인 재설계**

기존 `actions/` 모듈을 Tool로 래핑하여 Agent Loop에 연결. OpenHands의 "SDK-first" 철학을 채용하되 Docker/클라우드 없이 로컬에서만 실행.

### 1.2 Version Roadmap

```
v1.1.0 (현재) — 11개 독립 명령 번들
     ↓
v2.0.0 (목표) — Agent Loop + AI ask/edit + Session Context
     ↓
v2.1.0 (Phase 2) — Custom Profile + MCP 클라이언트
     ↓
v3.0.0 (미래) — Multi-agent orchestration
```

---

## 2. Requirements

### 2.1 Functional Requirements

#### FR-01: Core Agent 루프 (`locky/core/`)
```
locky/core/
├── agent.py    # BaseAgent: plan → execute → verify 루프
├── session.py  # LockySession: 세션 상태 + 컨텍스트 누적
└── context.py  # ContextCollector: git diff, test results, file content 수집
```

- `BaseAgent.run(task: str) -> AgentResult` 인터페이스
- 세션 간 컨텍스트 유지 (`.locky/session.json`)
- 최대 반복 횟수: 5회 (무한 루프 방지)

#### FR-02: Tool 레이어 (`locky/tools/`)
기존 `actions/` 모듈을 Tool 인터페이스로 래핑

```
locky/tools/
├── __init__.py    # BaseTool 추상 클래스
├── format.py      # FormatTool(BaseTool) → actions/format_code.py 위임
├── test.py        # TestTool(BaseTool) → actions/test_runner.py 위임
├── scan.py        # ScanTool(BaseTool) → actions/security_scan.py 위임
├── commit.py      # CommitTool(BaseTool) → actions/commit.py 위임
├── git.py         # GitTool(BaseTool) — diff, status, log
└── file.py        # FileTool(BaseTool) — read, write, search
```

**중요**: `actions/` 모듈은 삭제하지 않고 Tool이 위임(delegation) 패턴으로 재사용. 하위 호환 유지.

#### FR-03: AI 에이전트 (`locky/agents/`)

```
locky/agents/
├── ask_agent.py    # 코드 Q&A (편집 없음)
├── edit_agent.py   # 코드 편집 (unified diff 생성 → 적용)
└── commit_agent.py # 기존 commit.py 에이전트화
```

**AskAgent**:
- `locky ask "이 함수의 역할은?" [FILE...]`
- 파일 컨텍스트 → Ollama → 답변 (스트리밍)
- REPL `/ask` 통합

**EditAgent**:
- `locky edit --dry-run "에러 처리 추가" src/main.py`
- `locky edit --apply "docstring 추가" src/utils.py`
- Ollama에게 unified diff 요청 → 파싱 → 적용
- 기본: `--dry-run` (안전)

#### FR-04: Runtime (`locky/runtime/`)

```
locky/runtime/
└── local.py    # LocalRuntime: subprocess 기반 로컬 실행
```

- `LocalRuntime.execute(cmd: str, cwd: Path) -> RunResult`
- `RunResult = {stdout, stderr, returncode, duration}`
- Docker 샌드박스: 제외 (Phase 3 이후)

#### FR-05: 하위 호환 CLI

기존 11개 명령 인터페이스 **변경 없음**. `locky_cli/main.py`에 신규 명령 추가:
```
locky ask    "질문" [FILE...]
locky edit   [--dry-run|--apply] "지시" [FILE]
locky agent  run "복합 태스크"  # Agent Loop 직접 실행
```

#### FR-06: 패키지 구조 재편

```
locky-agent/
├── locky/              # NEW: 핵심 패키지
│   ├── core/           # Agent + Session + Context
│   ├── tools/          # 기존 actions 래퍼
│   ├── agents/         # AI 특화 에이전트
│   └── runtime/        # 실행 환경
├── actions/            # 유지 (하위 호환)
├── tools/              # 유지 (jira_client 등)
├── locky_cli/          # 유지 + 신규 명령 추가
└── tests/              # 기존 + 신규 테스트
```

### 2.2 Non-Functional Requirements

| 항목 | 요구사항 |
|------|---------|
| **로컬 전용** | 모든 기능 인터넷 연결 없이 동작 |
| **AI 선택적** | Ollama 없어도 기존 11개 명령 정상 동작 |
| **하위 호환** | v1.1.0 모든 CLI 인터페이스 변경 없음 |
| **성능** | `locky ask` 첫 토큰 ≤ 3초 (스트리밍) |
| **테스트** | 신규 코드 커버리지 ≥ 75% |
| **의존성** | 신규 pip 패키지 ≤ 2개 |
| **설치** | `pip install locky-agent` 하나로 완결 |

---

## 3. Architecture

### 3.1 계층 다이어그램

```
┌─────────────────────────────────────────────┐
│              locky_cli (CLI Layer)           │
│  locky ask / edit / agent / commit / format  │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│           locky/core (Agent Loop)            │
│  BaseAgent → plan → execute → verify → done │
│  LockySession (세션 컨텍스트 유지)             │
└──────┬───────────────────────┬──────────────┘
       │                       │
┌──────▼──────┐      ┌─────────▼──────────────┐
│ locky/agents│      │    locky/tools          │
│  AskAgent   │      │  FormatTool → actions/  │
│  EditAgent  │      │  TestTool   → actions/  │
│  CommitAgent│      │  ScanTool   → actions/  │
└──────┬──────┘      └─────────┬───────────────┘
       │                       │
┌──────▼───────────────────────▼──────────────┐
│          locky/runtime (LocalRuntime)        │
│        subprocess + OllamaClient             │
└──────────────────────────────────────────────┘
```

### 3.2 Agent Loop 시퀀스

```
사용자: "테스트 실패한 부분 고쳐줘"
  │
  ▼
LockySession.collect_context()
  → git diff, test results, failing files 수집
  │
  ▼
BaseAgent.plan(task, context)
  → Ollama: "어떤 파일의 어떤 부분을 어떻게 수정할지 계획"
  → ActionPlan 반환
  │
  ▼
BaseAgent.execute(plan)
  → EditAgent.run(file, instruction) × N
  → 각 편집 후 --dry-run 결과 표시 → 사용자 승인
  │
  ▼
BaseAgent.verify(plan)
  → TestTool.run() 재실행
  → 성공 여부 확인
  │
  ▼
완료 또는 재시도 (최대 5회)
```

### 3.3 Session Context 구조

```json
// .locky/session.json
{
  "session_id": "20260325-abc123",
  "workspace": "/path/to/project",
  "history": [
    {"type": "test_result", "data": {...}, "timestamp": "..."},
    {"type": "edit", "file": "main.py", "diff": "...", "timestamp": "..."}
  ],
  "profile": "python-dev"
}
```

---

## 4. Implementation Plan

### Phase 1 — Core 인프라 (v2.0.0-alpha)

```
Week 1:
  - locky/core/agent.py — BaseAgent 추상 클래스
  - locky/core/session.py — LockySession
  - locky/core/context.py — ContextCollector
  - locky/runtime/local.py — LocalRuntime

Week 2:
  - locky/tools/ — BaseTool + 기존 actions 래퍼 (Format/Test/Scan/Commit)
  - locky/agents/ask_agent.py — AskAgent
  - 단위 테스트 ≥ 20개
```

### Phase 2 — AI 에이전트 (v2.0.0-beta)

```
Week 3:
  - locky/agents/edit_agent.py — EditAgent (unified diff)
  - locky/agents/commit_agent.py — CommitAgent (기존 이전)
  - locky_cli/main.py — ask/edit/agent 명령 추가
  - REPL /ask, /edit 통합

Week 4:
  - 통합 테스트 (Agent Loop end-to-end)
  - 기존 167개 테스트 회귀 검증
  - 커버리지 측정 ≥ 75%
```

### Phase 3 — 안정화 및 마이그레이션 (v2.0.0)

```
Week 5-6:
  - pyproject.toml 패키지 구조 업데이트
  - MIGRATION.md 작성 (v1 → v2 전환 가이드)
  - 문서 업데이트
  - v2.0.0 릴리즈
```

---

## 5. Success Criteria

| 기준 | 측정 방법 | 목표 |
|------|---------|------|
| Agent Loop 동작 | `locky agent run "test fix"` 실행 시 plan→execute→verify 완료 | ✅ |
| `locky ask` 동작 | 단일 파일 Q&A 응답 | ✅ |
| `locky edit --dry-run` 동작 | diff 출력 후 파일 미변경 | ✅ |
| `locky edit --apply` 동작 | 파일 수정 후 git diff 표시 | ✅ |
| 하위 호환 | 기존 167개 테스트 전원 pass | ✅ |
| 신규 테스트 | ≥ 40개 (Core + Agents + Tools) | ✅ |
| 커버리지 | 신규 코드 ≥ 75% | ✅ |
| 의존성 | 신규 pip 패키지 ≤ 2개 | ✅ |

---

## 6. Risk Matrix

| 리스크 | 가능성 | 영향 | 완화 전략 |
|--------|--------|------|---------|
| 로컬 LLM이 unified diff 생성 실패 | High | High | JSON 구조화 응답 fallback + 사용자 확인 필수 |
| actions/ 하위 호환 깨짐 | Medium | High | Tool 래퍼는 delegation 패턴, 원본 수정 없음 |
| Agent Loop 무한 반복 | Low | Medium | 최대 5회 제한 + 타임아웃 60초 |
| 패키지 구조 변경으로 import 오류 | Medium | Medium | 기존 경로 shim 유지 (`from actions.X import` 계속 작동) |
| 개발 기간 초과 | Medium | Low | Phase별 MVP 릴리즈로 점진적 전환 |

---

## 7. YAGNI 검토 결과

| 아이디어 | 결정 | 이유 |
|---------|------|------|
| Docker 샌드박스 (OpenHands 방식) | ❌ 제외 | locky의 "가벼움" 핵심 가치와 충돌 |
| 웹 GUI / React UI | ❌ 제외 | CLI 우선 철학; Phase 4 이후 검토 |
| Recipe System (Goose 방식, YAML 워크플로) | ⏳ Phase 2 | v2.1.0에서 `.locky/recipes/` 도입 — 코드 없이 파이프라인 정의 |
| Multi-LLM 추상화 (litellm, OpenHands 방식) | ⏳ Phase 2 | v2.1.0에서 40+ provider 지원 |
| MCP 클라이언트 | ⏳ Phase 2 | v2.1.0 이후 도입 |
| 멀티 에이전트 오케스트레이션 | ⏳ v3.0 | 로컬 LLM 품질 성숙 후 |
| 클라우드/엔터프라이즈 옵션 | ❌ 영구 제외 | locky 정체성과 반함 |

---

## 8. Migration Notes (v1 → v2)

v1 사용자에게 영향 없음:
- `locky commit`, `locky format`, `locky test` 등 모든 기존 명령 동일하게 작동
- `actions/` 모듈 그대로 유지 (삭제 없음)
- `locky/tools/` 는 추가 레이어, 기존 import 경로 유효

신규 진입점:
- `from locky.agents import AskAgent, EditAgent`
- `from locky.core import BaseAgent, LockySession`

---

> **다음 단계**: `/pdca design locky-v2-overhaul`
