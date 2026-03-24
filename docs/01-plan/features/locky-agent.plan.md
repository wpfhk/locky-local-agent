# locky-agent v0.4.0~v1.0.0 Planning Document

> **Summary**: 로컬 AI 개발자 자동화 도구 — 컨텍스트 기억·pre-commit 자동화·다언어 지원으로 "매일 쓰는 도구"로 진화
>
> **Project**: locky-agent
> **Version**: 0.3.0 → 1.0.0
> **Author**: youngsang.kwon
> **Date**: 2026-03-24
> **Status**: Draft
> **PRD**: docs/00-pm/locky-agent.prd.md

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | v0.3.0은 세션 간 컨텍스트 없음, 멀티스텝 불가, Python 전용, pre-commit hook 없음으로 인해 개발자가 매일 쓰기엔 기능이 파편화되어 있다. |
| **Solution** | `.locky/` 프로젝트 컨텍스트 캐시 + pre-commit hook 통합 + 언어 자동감지 포맷터 + 파이프라인 체이닝으로 반복 작업의 80%를 자동화한다. |
| **Function/UX Effect** | `locky hook install` 한 번으로 커밋마다 format→test→scan이 자동 실행되고, 어떤 언어 프로젝트에서도 `locky` 명령이 동작한다. |
| **Core Value** | 100% 로컬, 클라우드 의존 없이 — "개발자의 귀찮음을 로컬 AI가 해결" |

---

## Context Anchor

> 세션 간 컨텍스트 연속성을 위해 Design/Do 문서에 전파됩니다.

| Key | Value |
|-----|-------|
| **WHY** | 세션 간 기억 없음·멀티스텝 불가·Python 전용으로 "매일 쓰는 도구"가 되지 못하고 있다. |
| **WHO** | 로컬 LLM(Ollama) 사용 개발자, 프라이버시 중시, 한국어 사용자 |
| **RISK** | Ollama 서버 미기동 시 AI 기능 전체 무력화 / 다언어 감지 오탐 |
| **SUCCESS** | pre-commit hook 2주 유지율 70%↑ / 커밋 메시지 수정 없이 수용률 80%↑ |
| **SCOPE** | v0.4.0(컨텍스트+hook) → v0.5.0(다언어+파이프라인) → v1.0.0(플러그인+Ollama자동관리) |

---

## 1. Overview

### 1.1 Purpose

locky-agent를 8개 독립 명령의 집합에서, 프로젝트를 기억하고 워크플로를 자동화하는 **개발자 일상 도구**로 진화시킨다.

### 1.2 Background

v0.3.0에서 자연어→셸 명령 변환(REPL)을 추가했지만, 핵심 한계가 남아 있다:
- **컨텍스트 없음**: 매 세션마다 프로젝트를 처음부터 인식
- **멀티스텝 불가**: format 후 test 후 commit 같은 체이닝 미지원
- **Python 전용**: scan/todo/format이 `.py` 파일만 처리
- **Hook 없음**: 커밋 전 자동 품질 검증 없음

PM 분석(PRD)에서 "세션 간 컨텍스트 유지"와 "pre-commit hook"이 가장 높은 Impact×Risk 점수를 기록했다.

### 1.3 Related Documents

- PRD: `docs/00-pm/locky-agent.prd.md`
- 기존 개발 계획: `docs/Locky_agent_dev_plan_requirement.md`

---

## 2. Scope

### 2.1 In Scope

#### v0.4.0 — 컨텍스트 & 자동화 기반
- [ ] `.locky/` 디렉토리 기반 프로젝트 컨텍스트 캐시 (`profile.json`)
  - 감지 항목: 언어, 주요 파일 패턴, 커밋 메시지 스타일, 마지막 실행 정보
- [ ] `locky hook install / uninstall` — git pre-commit hook 설치·제거
- [ ] hook 실행 흐름: format → test → scan → commit (실패 시 중단)
- [ ] 레거시 코드 제거: `agents/`, `states/`, `graph.py`, `pipeline/` (미사용)
- [ ] `actions/` 패키지 단위 테스트 추가 (pytest, coverage ≥ 70%)

#### v0.5.0 — 다언어 & 파이프라인
- [ ] 파일 확장자 기반 언어 자동 감지 (git-tracked 파일 분석)
- [ ] 언어별 포맷터 자동 선택 및 실행
  - Python: black + isort + ruff
  - JS/TS: prettier + eslint
  - Go: gofmt + golint
  - Rust: rustfmt + clippy
- [ ] `locky run "format test commit"` — 멀티스텝 파이프라인 체이닝
- [ ] deps 명령 확장: pyproject.toml, package.json, go.mod 지원

#### v1.0.0 — 플러그인 & 안정화
- [ ] 플러그인 아키텍처: `~/.locky/plugins/` 자동 감지·로드
- [ ] Ollama 헬스체크 + 자동 시작 (`ollama serve` 백그라운드)
- [ ] 모델 미설치 시 `ollama pull <model>` 안내
- [ ] `locky init` — 첫 실행 시 프로젝트 셋업 가이드 (Ollama 설치 안내 포함)

### 2.2 Out of Scope

- 클라우드 LLM 연동 (OpenAI, Claude API 등) — 100% 로컬 원칙 유지
- GUI / 웹 UI (Chainlit `ui/app.py`는 유지하되 신규 개발 없음)
- 멀티 레포지토리 동시 관리
- Windows 공식 지원 (macOS/Linux 우선)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Version | Status |
|----|-------------|----------|---------|--------|
| FR-01 | `locky` 최초 실행 시 `.locky/profile.json` 자동 생성 (언어·프레임워크·커밋 패턴 감지) | High | v0.4.0 | Pending |
| FR-02 | `locky hook install` — `.git/hooks/pre-commit` 에 locky 체이닝 hook 설치 | High | v0.4.0 | Pending |
| FR-03 | `locky hook uninstall` — hook 제거 및 원래 hook 복원 | High | v0.4.0 | Pending |
| FR-04 | hook 실행: format → test → scan 순서로 실행, 실패 시 커밋 중단 + 이유 출력 | High | v0.4.0 | Pending |
| FR-05 | `actions/` 모듈별 단위 테스트 (pytest) + coverage ≥ 70% | High | v0.4.0 | Pending |
| FR-06 | 레거시 모듈 (agents/, states/, graph.py, pipeline/) 제거 및 import 정리 | Medium | v0.4.0 | Pending |
| FR-07 | git-tracked 파일 확장자 분석으로 프로젝트 언어 자동 감지 | High | v0.5.0 | Pending |
| FR-08 | 언어별 포맷터 실행 (Python/JS/TS/Go/Rust 우선 지원) | High | v0.5.0 | Pending |
| FR-09 | `locky run "<cmd1> <cmd2> ..."` 멀티스텝 파이프라인 | Medium | v0.5.0 | Pending |
| FR-10 | deps 명령: pyproject.toml, package.json, go.mod 파서 추가 | Medium | v0.5.0 | Pending |
| FR-11 | `~/.locky/plugins/` 디렉토리 자동 감지 및 actions/ 에 동적 로드 | Medium | v1.0.0 | Pending |
| FR-12 | Ollama 헬스체크 실패 시 `ollama serve` 자동 시작 시도 | Medium | v1.0.0 | Pending |
| FR-13 | `locky init` 대화형 설정 가이드 (언어, 모델, hook 여부) | Low | v1.0.0 | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement |
|----------|----------|-------------|
| Performance | 자연어→셸 변환 응답 시간 < 3s (7b 모델 기준) | 실측 타이머 |
| Reliability | hook 실행 실패 시 원래 커밋 흐름 영향 없음 | 통합 테스트 |
| Compatibility | Python 3.10+, macOS/Linux | CI matrix |
| Test Coverage | actions/ 모듈 coverage ≥ 70% | pytest-cov |
| Install | `pipx install locky-agent` 한 번으로 완료 | 설치 테스트 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] 모든 FR 구현 완료 (버전별)
- [ ] `pytest` 전체 통과, coverage ≥ 70%
- [ ] `locky --help` 및 각 서브커맨드 help 문서 최신 상태
- [ ] README 업데이트 (설치, 사용법, 다언어 지원 현황)
- [ ] CLAUDE.md 업데이트 (신규 아키텍처 반영)

### 4.2 Acceptance Experiments (PRD A1~A4 기반)

| 가정 | 실험 | 성공 기준 |
|------|------|---------|
| A2 | `locky hook install` 후 2주 유지율 측정 | ≥ 70% |
| A4 | 커밋 메시지 수정 없이 수용 비율 | ≥ 80% |
| A3 | 멀티스텝 vs 수동 실행 시간 비교 | 50%↑ 시간 절감 |

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Ollama 미기동으로 AI 기능 무력화 | High | Medium | FR-12: 자동 시작 + 명확한 오류 메시지 |
| 다언어 포맷터 미설치 시 오류 | Medium | High | 포맷터 존재 여부 확인 후 skip + 설치 안내 |
| pre-commit hook이 기존 hook과 충돌 | Medium | Medium | 기존 hook 백업 후 체이닝, uninstall 시 복원 |
| 레거시 제거 시 숨겨진 의존성 | Low | Low | 제거 전 import 전수 검사 (grep) |
| Python 외 언어 감지 오탐 | Low | Medium | .locky/config.yaml 수동 오버라이드 허용 |

---

## 6. Impact Analysis

### 6.1 Changed Resources

| Resource | Type | Change |
|----------|------|--------|
| `actions/__init__.py` | Python module | shell_command export 기추가, run 명령 추가 예정 |
| `locky_cli/main.py` | Python module | `hook`, `run` 서브커맨드 추가 |
| `locky_cli/repl.py` | Python module | 컨텍스트 캐시 로드 통합 |
| `config.py` | Python module | 언어 감지 설정 추가 |
| `pyproject.toml` | Config | 의존성 추가 (선택적 dev deps) |
| `.gitignore` | Config | `.locky/` 일부 항목 제외 처리 |

### 6.2 Current Consumers

| Resource | Code Path | Impact |
|----------|-----------|--------|
| `actions/__init__.py` | `locky_cli/main.py` 전체 | Needs verification |
| `config.py` | `actions/commit.py`, `actions/shell_command.py`, `tools/ollama_client.py` | None |
| `locky_cli/main.py` | `cli.py` (위임 진입점) | None |

### 6.3 Verification

- [ ] 레거시 제거 전 `grep -r "from agents\|from states\|import graph"` 전수 확인
- [ ] `locky hook install` 후 기존 커밋 플로우 정상 동작 확인
- [ ] `.locky/` gitignore 처리로 팀 개발 시 충돌 없음 확인

---

## 7. Architecture Considerations

### 7.1 Project Level

**Dynamic** — 독립 모듈 구조, 외부 서비스(Ollama) 연동, 로컬 상태 관리

### 7.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| 컨텍스트 저장 | JSON / SQLite / YAML | JSON (.locky/profile.json) | 단순, 사람이 읽기 쉬움, 의존성 없음 |
| Hook 설치 | symlink / 파일 쓰기 | 파일 쓰기 + 백업 | symlink는 상대경로 문제 발생 가능 |
| 언어 감지 | 파일 확장자 / linguist | 파일 확장자 집계 | 의존성 없이 git ls-files로 충분 |
| 플러그인 로드 | importlib / entry_points | importlib.import_module | 표준 라이브러리, setuptools 불필요 |
| 다언어 포맷터 | subprocess / pre-installed | subprocess + 존재 확인 | 포맷터는 개발자가 이미 설치한 것 사용 |
| 테스트 | pytest / unittest | pytest + pytest-cov | 기존 test_runner.py와 일관성 |

### 7.3 디렉토리 구조 변경 (v1.0.0 목표)

```
locky-agent/
├── actions/                    # 자동화 모듈 (확장됨)
│   ├── commit.py
│   ├── format_code.py          # 다언어 포맷터로 확장
│   ├── shell_command.py
│   ├── hook.py                 # NEW: pre-commit hook 관리
│   └── pipeline.py             # NEW: 멀티스텝 체이닝
│
├── locky_cli/
│   ├── main.py                 # hook, run 서브커맨드 추가
│   ├── context.py              # NEW: .locky/ 컨텍스트 캐시
│   └── lang_detect.py          # NEW: 언어 자동 감지
│
├── .locky/                     # 프로젝트별 로컬 상태 (gitignore 가능)
│   ├── profile.json            # 프로젝트 메타
│   └── config.yaml             # 사용자 오버라이드 (선택)
│
├── tests/                      # NEW: 단위 테스트
│   ├── test_commit.py
│   ├── test_shell_command.py
│   ├── test_hook.py
│   └── test_lang_detect.py
│
└── [제거 대상]
    ├── agents/                 # 레거시 → 삭제
    ├── states/                 # 레거시 → 삭제
    ├── graph.py                # 레거시 → 삭제
    └── pipeline/               # 레거시 → 삭제
```

---

## 8. Convention Prerequisites

### 8.1 Existing Conventions (CLAUDE.md 기준)

- [x] `CLAUDE.md` — 아키텍처, 환경변수, 설계 결정 문서화됨
- [x] `run(root: Path, **opts) -> dict` — actions/ 모듈 인터페이스 표준
- [x] `status` 키 ("ok"/"pass"/"clean" 등) — 결과 딕셔너리 컨벤션
- [ ] `tests/` 디렉토리 및 pytest 설정 — **신규 추가 필요**

### 8.2 Conventions to Define

| Category | Current | To Define |
|----------|---------|-----------|
| 테스트 파일 | 없음 | `tests/test_{module}.py` 패턴 |
| .locky/ 파일 포맷 | 없음 | JSON (profile.json), YAML (config.yaml) |
| 언어 감지 결과 | 없음 | `{"primary": "python", "all": [...]}` |
| hook 설치 경로 | 없음 | `.git/hooks/pre-commit` |

### 8.3 Environment Variables (추가 예정 없음)

기존 `OLLAMA_*` 환경변수로 충분. `.locky/config.yaml`로 프로젝트별 오버라이드 지원.

---

## 9. Release Roadmap

| Version | 주요 기능 | 예상 작업량 |
|---------|---------|-----------|
| **v0.4.0** | .locky/ 컨텍스트 캐시, pre-commit hook, 레거시 제거, 테스트 추가 | 중 (4~6일) |
| **v0.5.0** | 다언어 감지·포맷터, 파이프라인 체이닝, deps 확장 | 중 (3~5일) |
| **v1.0.0** | 플러그인 아키텍처, Ollama 자동 관리, locky init | 중상 (4~6일) |

---

## 10. Next Steps

1. [ ] `/pdca design locky-agent` — v0.4.0 설계 문서 작성
2. [ ] 레거시 제거 범위 grep 확인
3. [ ] `tests/` 디렉토리 및 `pytest.ini` 설정

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-03-24 | Initial draft (PRD 기반 v0.4.0~v1.0.0 로드맵) | youngsang.kwon |
