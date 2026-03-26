# Locky v2 개선 기획 — PRD

> **PM Analysis** | 2026-03-25
> **Feature**: locky-v2-improvement
> **Scope**: 100% 로컬 + CLI 환경 기반 locky 경쟁력 강화

---

## Executive Summary

| 관점 | 내용 |
|------|------|
| **Problem** | Claude Code·aider·Cline CLI 2.0 등 AI 코딩 어시스턴트 생태계가 빠르게 성장하는 반면, locky v1은 워크플로 자동화 번들에 머물러 있어 "AI 협업"과 "확장성"이 부재하다. 인터넷 의존 도구(Claude Code)와 달리 100% 로컬을 지키면서 어떻게 AI 협업 기능을 추가하느냐가 핵심 과제다. |
| **Solution** | Ollama 기반 AI 코드 어시스턴트 모드(aider 패턴) + MCP 서버 연동 에코시스템 + REPL 강화(대화형 AI 협업) + 플러그인 Hook API — 모두 100% 로컬·오프라인 동작 보장 |
| **Target User** | 터미널 중심 워크플로 + 프라이버시 우선 + Ollama 사용 개발자 (beachhead: 한국어 사용 Python·Go 개발자) |
| **Core Value** | "클라우드 없이 Claude Code 수준의 AI 협업을 터미널에서" — 로컬 LLM으로 코드 편집·질의·자동화를 한 곳에서 |

---

## Context Anchor

| 항목 | 내용 |
|------|------|
| **WHY** | Claude Code·aider 등 AI 코딩 도구가 39K~68K GitHub stars를 얻고 있는 반면 locky는 워크플로 자동화 번들로서 AI 협업 부재 — 사용자 이탈 위험 |
| **WHO** | 개인정보 중시 + 오프라인 환경 + 터미널 중심 한국어 개발자 (Python/Go/JS 혼용, Ollama 보유) |
| **RISK** | Ollama 로컬 LLM 품질 한계, aider 오픈소스와의 직접 경쟁, REPL 복잡도 증가로 기존 단순성 훼손 |
| **SUCCESS** | `locky ask`, `locky edit` 동작 + MCP 서버 1개 이상 연동 + 기존 11개 명령 하위 호환 유지 + 테스트 커버리지 ≥75% |
| **SCOPE** | AI 질의·편집·REPL 강화·MCP 연동·Hook API; IDE 통합·Docker 에이전트·웹 UI 제외 |

---

## 1. 현황 분석 — locky v1.1.0 기능 인벤토리

### 1.1 현재 기능 (11개 자동화 명령)

| 명령 | 설명 | AI 사용 |
|------|------|---------|
| `locky commit` | git diff → Ollama → Conventional Commits | ✅ Ollama |
| `locky format` | 다언어 포매터 (7개 언어) | ❌ |
| `locky test` | pytest 실행·파싱 | ❌ |
| `locky todo` | TODO/FIXME 수집·md 저장 | ❌ |
| `locky scan` | OWASP 패턴 정적 스캔 | ❌ |
| `locky clean` | 캐시·임시파일 정리 | ❌ |
| `locky deps` | 의존성 버전 확인 | ❌ |
| `locky env` | .env → .env.example 생성 | ❌ |
| `locky hook` | pre-commit 훅 관리 | ❌ |
| `locky run` | 멀티스텝 파이프라인 | ❌ |
| `locky jira` | Jira 이슈 조회·생성 (v1.2) | ❌ |

**REPL**: `locky` 단독 실행 시 대화형 모드 — `/commit`, `/format` 슬래시 명령 + 자연어 → 셸 변환 (Ollama)

### 1.2 현재 강점

- 100% 로컬·오프라인 동작 보장
- AI-optional: Ollama 없어도 9개 명령 즉시 실행
- 단순한 아키텍처 (`actions/` 독립 모듈 패턴)
- 다언어 포매터 번들 (7개 언어)
- pre-commit 훅 통합

### 1.3 현재 약점 (Gap)

| 약점 | 심각도 | 경쟁사 대안 |
|------|--------|------------|
| AI 코드 편집 불가 | Critical | aider, Claude Code, Cline |
| 대화형 AI Q&A 없음 | High | aider (ask mode), Claude Code |
| MCP 에코시스템 없음 | High | Claude Code, Cline CLI 2.0 |
| Hook/이벤트 API 없음 | Medium | Claude Code (PreToolUse/PostToolUse) |
| 보안 스캔이 regex 한계 | Medium | Semgrep, bandit |
| IDE 통합 없음 | Low (scope out) | continue.dev, Cline |

---

## 2. 경쟁사 분석 (2026-03)

### 2.1 Claude Code (Anthropic)

| 항목 | 내용 |
|------|------|
| **강점** | MCP Elicitation, PreToolUse/PostToolUse Hook API, 플러그인(/plugin), 에이전트 팀 |
| **약점** | 인터넷 필수, API 유료, 로컬 LLM 미지원 |
| **locky 차용 포인트** | Hook 이벤트 API 패턴, 플러그인 로더 확장, REPL 슬래시 명령 체계 |

### 2.2 aider (39K GitHub Stars)

| 항목 | 내용 |
|------|------|
| **강점** | 100% 로컬 (Ollama), Code/Architect/Ask 3가지 모드, 자동 커밋, 멀티파일 편집 |
| **약점** | 워크플로 자동화(포매팅·스캔·Jira 등) 없음, CLI 전용 |
| **locky 차용 포인트** | Ask 모드 (AI Q&A without edit), architect 패턴 (계획 후 편집), diff 기반 파일 편집 |

### 2.3 Cline CLI 2.0

| 항목 | 내용 |
|------|------|
| **강점** | 터미널 우선 재설계, MCP 네이티브, 명시적 승인 철학 |
| **약점** | 복잡도 높음, 로컬 LLM 성능 의존 |
| **locky 차용 포인트** | 명시적 승인(--dry-run 패턴 강화), MCP 클라이언트 통합 |

### 2.4 Goose (Block.inc → Linux Foundation)

| 항목 | 내용 |
|------|------|
| **강점** | 25+ LLM 제공자, 데스크톱+CLI, Extension 아키텍처 |
| **약점** | 무겁고 Docker 기반 에이전트 |
| **locky 차용 포인트** | Extension/플러그인 아키텍처 (이미 `~/.locky/plugins/` 존재) |

### 2.5 OpenHands (68.6K Stars, $18.8M Series A)

| 항목 | 내용 |
|------|------|
| **강점** | 완전 자율 에이전트, Docker 샌드박스, 웹 UI |
| **locky 포지셔닝** | "OpenHands 경량 CLI 버전" — 에이전트 자율성은 낮추고 개발자 통제권 유지 |

---

## 3. 개선 기회 — Opportunity Solution Tree

### 기회 1: AI 코드 편집 (Highest Priority)

```
Opportunity: 개발자가 터미널에서 코드 수정을 AI에게 위임하고 싶다
  ├── Solution A: locky edit (aider 스타일 diff 기반 파일 편집)
  │     - Ollama에게 변경 요청 → unified diff 생성 → 적용
  │     - --dry-run으로 미리보기
  ├── Solution B: locky ask (코드 Q&A, 편집 없음)
  │     - 파일 컨텍스트 + 질문 → Ollama → 답변 출력
  └── Solution C: REPL 내 /edit, /ask 명령
        - 기존 REPL에 통합 (최소 변경)
```

### 기회 2: MCP 에코시스템 연동 (High Priority)

```
Opportunity: 외부 도구(DB·파일·검색)를 AI 워크플로에 통합하고 싶다
  ├── Solution A: MCP 클라이언트 내장 (STDIO 방식, 인터넷 불필요)
  │     - tools/mcp_filesystem.py 이미 존재 → MCP 서버로 승격
  ├── Solution B: 플러그인 MCP 래퍼
  │     - ~/.locky/plugins/에 MCP 서버 연결 설정
  └── Solution C: locky mcp 서브커맨드
        - list / call / test 기능
```

### 기회 3: Hook/이벤트 API (Medium Priority)

```
Opportunity: 특정 이벤트(커밋 전·포맷 후)에 사용자 정의 로직 삽입
  ├── Solution A: .locky/hooks.yaml 설정
  │     - before_commit, after_format 등 이벤트 정의
  ├── Solution B: Python 콜백 플러그인
  │     - register_hook("before_commit", fn) API
  └── Solution C: 환경변수 기반 간단한 pre/post script
        - LOCKY_BEFORE_COMMIT=./scripts/check.sh
```

### 기회 4: 보안 스캔 강화 (Medium Priority)

```
Opportunity: regex 보안 스캔의 한계를 극복하고 싶다
  ├── Solution A: Semgrep CLI 통합 (로컬 설치 감지, optional)
  ├── Solution B: bandit 통합 (Python 전용, pip install)
  └── Solution C: AI 기반 보안 리뷰 (Ollama, opt-in)
```

---

## 4. 우선순위 매트릭스

| 기능 | 임팩트 | 구현 난이도 | 로컬 친화성 | 우선순위 |
|------|--------|------------|------------|---------|
| `locky ask` (AI Q&A) | High | Low | ✅ | P1 |
| `locky edit` (AI 코드 편집) | High | Medium | ✅ | P1 |
| REPL `/ask`, `/edit` 통합 | Medium | Low | ✅ | P1 |
| Hook/이벤트 API | Medium | Medium | ✅ | P2 |
| MCP 클라이언트 | High | High | ✅ (STDIO) | P2 |
| 보안 스캔 강화 (Semgrep) | Medium | Low | ✅ (optional) | P3 |
| 멀티파일 컨텍스트 | Medium | High | ✅ | P3 |
| IDE 통합 | Low | Very High | ❌ scope out | - |

---

## 5. 기능 요구사항

### FR-01: `locky ask` — AI 코드 질의 (P1)

```
locky ask "이 코드의 시간복잡도는?" [FILE...]
locky ask --context src/ "버그 원인을 찾아줘"
```

- 지정 파일(들)을 컨텍스트로 Ollama에 전달
- 파일 미지정 시 git diff 또는 현재 디렉터리 상위 파일
- 응답은 Markdown 렌더링 (Rich)
- 로컬 전용: Ollama 가드 통과 후 실행

**성공 기준**: 단일 파일 Q&A 응답 시간 ≤ 30초 (Ollama qwen2.5-coder:7b 기준)

### FR-02: `locky edit` — AI 코드 편집 (P1)

```
locky edit "함수명을 snake_case로 변경해줘" [FILE]
locky edit --dry-run "타입 힌트 추가" src/main.py
locky edit --apply "docstring 추가" src/utils.py
```

- Ollama에게 unified diff 포맷으로 변경 요청
- `--dry-run`: diff 출력만 (기본)
- `--apply`: 실제 파일 수정 후 git diff 표시
- 수정 후 자동 포매터 실행 옵션 (`--format`)

**성공 기준**: `--dry-run` 동작, `--apply` 후 파일 수정 확인, 단위 테스트 ≥8개

### FR-03: REPL `/ask`, `/edit` 통합 (P1)

```
locky> /ask 이 프로젝트의 테스트 커버리지를 높이려면?
locky> /edit src/main.py 에러 처리 추가
```

- 기존 `repl.py` 슬래시 명령 테이블에 추가
- 컨텍스트: 현재 워크스페이스 (`MCP_FILESYSTEM_ROOT`)

### FR-04: Hook/이벤트 API (P2)

```yaml
# .locky/hooks.yaml
before_commit:
  - script: ./scripts/lint.sh
after_format:
  - command: locky test
on_scan_critical:
  - notify: slack  # 플러그인 필요
```

- `actions/` 각 `run()` 호출 전후에 이벤트 발화
- 환경변수 방식 fallback: `LOCKY_BEFORE_COMMIT=./check.sh`
- 기존 pre-commit 훅(`hook.py`)과 별개 레이어

### FR-05: MCP 클라이언트 (P2)

```
locky mcp list                    # 등록된 MCP 서버 목록
locky mcp call filesystem read_file --path src/main.py
```

- `tools/mcp_filesystem.py` 기반 확장
- STDIO 방식 MCP 서버 연결 (인터넷 불필요)
- `.locky/config.yaml`에 MCP 서버 설정 추가

### FR-06: 보안 스캔 강화 (P3)

```
locky scan --engine semgrep  # Semgrep CLI 위임 (optional)
locky scan --engine bandit   # Python 전용
locky scan --ai              # Ollama AI 리뷰 (opt-in)
```

- 기존 OWASP regex 스캔 유지 (기본)
- Semgrep/bandit은 설치 감지 후 optional 실행
- AI 스캔은 `--ai` 플래그 명시 시만

---

## 6. 비기능 요구사항

| 항목 | 요구사항 |
|------|---------|
| **로컬 전용** | 모든 신규 기능은 인터넷 연결 없이 동작해야 함 |
| **AI 선택적** | Ollama 없어도 기존 9개 명령 동작 유지 |
| **하위 호환** | v1.1.0 모든 명령 인터페이스 변경 없음 |
| **성능** | `locky ask` 첫 응답 ≤ 5초 (스트리밍) |
| **테스트** | 신규 기능 커버리지 ≥ 75% |
| **의존성** | 신규 pip 패키지 최소화 (기존 httpx·click·rich 최대 활용) |

---

## 7. 사용자 스토리

### Epic 1: AI 코드 어시스턴트

| ID | As a | I want to | So that |
|----|------|-----------|---------|
| US-01 | 개발자 | `locky ask "이 함수의 역할은?" utils.py`를 실행하면 | 파일을 열지 않고 터미널에서 바로 코드를 이해할 수 있다 |
| US-02 | 개발자 | `locky edit --dry-run "에러 처리 추가" main.py`를 실행하면 | 실제 수정 전에 AI 제안을 미리 확인할 수 있다 |
| US-03 | 개발자 | REPL에서 `/ask 이 버그 원인이 뭔가요?`를 입력하면 | 컨텍스트 전환 없이 AI에게 질문할 수 있다 |

### Epic 2: 확장성

| ID | As a | I want to | So that |
|----|------|-----------|---------|
| US-04 | 파워유저 | `.locky/hooks.yaml`에 `before_commit` 훅을 설정하면 | 커밋 전 자동으로 내 스크립트가 실행된다 |
| US-05 | 개발자 | `locky mcp list`로 등록된 MCP 서버를 확인하면 | 어떤 도구가 AI 워크플로에 연결되어 있는지 파악할 수 있다 |

---

## 8. 구현 로드맵

### Phase 1 — AI 어시스턴트 코어 (v1.2 목표)

```
Week 1-2:
  - actions/ask.py: run(root, question, files) -> dict
  - actions/edit.py: run(root, instruction, file, dry_run) -> dict
  - locky_cli/main.py에 ask/edit 서브커맨드 추가
  - REPL /ask, /edit 슬래시 명령 통합
  - 단위 테스트 ≥15개

Week 3:
  - 멀티파일 컨텍스트 지원 (최대 3파일)
  - 스트리밍 응답 (OllamaClient 기존 streaming=True 활용)
  - 통합 테스트
```

### Phase 2 — 확장성 (v1.3 목표)

```
Week 4-5:
  - .locky/hooks.yaml 파서 + HookRunner
  - actions/ 각 run() before/after 이벤트 발화
  - locky hook 커맨드 확장 (list, run, test)

Week 6:
  - MCP 클라이언트 기본 (tools/mcp_client.py)
  - locky mcp 서브커맨드
  - .locky/config.yaml mcp_servers 섹션
```

### Phase 3 — 스캔 강화 (v1.4 목표)

```
Week 7:
  - Semgrep/bandit optional 통합
  - AI 보안 리뷰 모드 (--ai)
  - 보안 리포트 포맷 개선
```

---

## 9. 리스크 & Pre-mortem

| 리스크 | 가능성 | 영향 | 대응 |
|--------|--------|------|------|
| Ollama 로컬 LLM 코드 편집 품질 낮음 | High | High | --dry-run 기본, 사용자 확인 필수 + aider처럼 명시적 apply 분리 |
| `locky edit` diff 포맷 파싱 실패 | Medium | High | JSON 구조화 응답 옵션, fallback: 원본 출력 |
| 기존 단순성 훼손 (복잡도 증가) | Medium | Medium | 신규 명령은 모두 선택적, 기존 명령 변경 없음 |
| aider와 직접 기능 중복 | High | Medium | locky의 포지셔닝: "워크플로 자동화 + AI 편집" 번들 — aider는 편집만 |
| MCP 서버 설정 복잡도 | Medium | Low | 기본값으로 mcp_filesystem만 내장 |

---

## 10. 성공 지표 (KPI)

| 지표 | 현재 (v1.1) | 목표 (v2.0) |
|------|-------------|-------------|
| AI 사용 명령 비율 | 1/11 (9%) | 3/13 (23%) |
| REPL 슬래시 명령 수 | 7개 | 9개+ |
| 단위 테스트 수 | 167개 | 200개+ |
| 신규 기능 커버리지 | - | ≥75% |
| 인터넷 의존 기능 수 | 0 | 0 (유지) |
| pip 신규 의존성 | 0 | ≤2개 |

---

## 결론

**locky v2 핵심 포지셔닝**: "aider의 AI 코드 편집 + locky의 워크플로 자동화 번들" — 완전 로컬·오프라인 CLI 도구로 Claude Code가 채울 수 없는 프라이버시 우선 개발자 시장을 공략한다.

**즉시 시작할 수 있는 1순위 구현**: `actions/ask.py` + `locky ask` 명령 (기존 `OllamaClient` + `Click` 재사용, 새 의존성 없음, 1-2일 구현 가능)

→ **다음 단계**: `/pdca plan locky-ask` 또는 `/pdca plan locky-edit`
