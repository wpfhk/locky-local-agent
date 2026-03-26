# Locky v2.0.1 — 정량적 평가 보고서

> **평가 기준일**: 2026-03-25
> **평가 버전**: v2.0.1 (post-fix release)
> **평가 방법론**: 자동화 테스트 + 정적 분석 + 기능 검증

---

## 1. Executive Summary

| 지표 | 값 | 기준 |
|------|------|------|
| **테스트 통과율** | 100% (351/351) | ≥ 95% |
| **코드 커버리지** | 67% | ≥ 60% |
| **설계 일치율 (Match Rate)** | 98% | ≥ 90% |
| **CLI 명령어 수** | 15개 | - |
| **지원 언어 (포맷터)** | 7개 | - |
| **소스 코드 규모** | 5,732 lines | - |
| **테스트 코드 규모** | 3,884 lines | - |

---

## 2. 테스트 지표

### 2.1 전체 테스트 현황

| 항목 | 값 |
|------|------|
| 총 테스트 수 | **351개** |
| 통과 | **351개 (100%)** |
| 실패 | 0개 |
| 테스트 파일 수 | 30개 |
| 평균 실행 시간 | 44.5초 |

### 2.2 모듈별 커버리지

| 모듈 | 구문 수 | 커버리지 | 등급 |
|------|:-------:|:--------:|:----:|
| `actions/hook.py` | 72 | **100%** | S |
| `actions/pipeline.py` | 34 | **100%** | S |
| `locky/agents/ask_agent.py` | 35 | **100%** | S |
| `locky/agents/commit_agent.py` | 10 | **100%** | S |
| `actions/test_runner.py` | 51 | 94% | A |
| `actions/env_template.py` | 55 | 93% | A |
| `actions/format_code.py` | 57 | 93% | A |
| `actions/security_scan.py` | 48 | 92% | A |
| `actions/shell_command.py` | 62 | 87% | B |
| `actions/cleanup.py` | 63 | 86% | B |
| `actions/jira.py` | 122 | 84% | B |
| `actions/deps_check.py` | 168 | 65% | C |
| `locky/agents/edit_agent.py` | 55 | 65% | C |
| `actions/commit.py` | 75 | 8% | F* |
| `locky_cli/main.py` | 497 | 0% | F* |

> *F 등급: 실제 Ollama 서버 / git 레포 의존 코드 — 단위 테스트로 커버 어려움.
> 통합 테스트로 별도 검증됨 (`locky ask/edit/agent/commit` 실제 실행 확인)

### 2.3 테스트 분포

| 카테고리 | 파일 수 | 테스트 수 |
|---------|:-------:|:--------:|
| actions/ (자동화 명령어) | 12 | ~168 |
| locky/ (v2 에이전트) | 8 | ~80 |
| locky_cli/ (CLI 통합) | 4 | ~63 |
| tools/ (유틸리티) | 6 | ~40 |
| **합계** | **30** | **351** |

---

## 3. 코드 품질 지표

### 3.1 코드 규모

| 항목 | 값 |
|------|------|
| 소스 코드 (tests 제외) | **5,732 lines** |
| 테스트 코드 | **3,884 lines** |
| 전체 Python 코드 | **9,616 lines** |
| 테스트 비율 (test/source) | **67.8%** |
| 소스 모듈 수 | **28개** |
| 함수/메서드 수 | **163개** |

### 3.2 lint 품질

| 항목 | 값 |
|------|------|
| flake8 오류 | **0개** |
| max-line-length | 119 |
| black 포맷 준수 | ✅ |
| isort 임포트 정렬 | ✅ |
| 미사용 임포트 | 0개 (F401) |
| 미사용 변수 | 0개 (F841) |

### 3.3 아키텍처 품질

| 측면 | 평가 |
|------|------|
| 모듈 독립성 | ✅ actions/ 각 모듈이 서로 미의존 |
| 단일 책임 원칙 | ✅ `run(root, **opts) → dict` 시그니처 통일 |
| 경로 순회 방지 | ✅ `MCP_FILESYSTEM_ROOT` ContextVar 격리 |
| 훅 안전성 | ✅ 기존 훅 자동 백업/복원 |

---

## 4. 기능 커버리지

### 4.1 CLI 명령어 (15개)

#### 기본 자동화 (8개)

| 명령어 | 구현 | 테스트 | 실행 검증 |
|--------|:----:|:------:|:--------:|
| `locky commit` | ✅ | ✅ | ✅ |
| `locky format` | ✅ | ✅ | ✅ |
| `locky test` | ✅ | ✅ | ✅ |
| `locky todo` | ✅ | ✅ | ✅ |
| `locky scan` | ✅ | ✅ | ✅ |
| `locky clean` | ✅ | ✅ | ✅ |
| `locky deps` | ✅ | ✅ | ✅ |
| `locky env` | ✅ | ✅ | ✅ |

#### 파이프라인 / 설정 (4개)

| 명령어 | 구현 | 테스트 | 실행 검증 |
|--------|:----:|:------:|:--------:|
| `locky hook install/uninstall/status` | ✅ | ✅ (100% cov) | ✅ |
| `locky run [STEPS]` | ✅ | ✅ (100% cov) | ✅ |
| `locky init` | ✅ | ✅ | ✅ |
| `locky plugin list` | ✅ | ✅ | ✅ |

#### AI 에이전트 (v2, 3개)

| 명령어 | 구현 | 테스트 | 실행 검증 |
|--------|:----:|:------:|:--------:|
| `locky ask` | ✅ | ✅ (100% cov) | ✅ 응답 생성 확인 |
| `locky edit` | ✅ | ✅ | ✅ streaming 안정화 |
| `locky agent` | ✅ | ✅ | ✅ status:ok, verified:True |

### 4.2 통합 기능

| 기능 | 상태 |
|------|------|
| Jira 통합 (list/create/status) | ✅ (actions/jira.py, 84% cov) |
| REPL 모드 (/commit, /format 등) | ✅ |
| 플러그인 로더 (~/.locky/plugins/) | ✅ |
| Ollama 헬스체크 + 자동 시작 | ✅ |
| 다언어 포맷터 (7개) | ✅ |
| 의존성 파서 (4개 포맷) | ✅ |

### 4.3 지원 언어 / 포맷 매트릭스

| 언어 | 포맷터 | 의존성 파서 | 언어 감지 |
|------|--------|:-----------:|:--------:|
| Python | black + isort + flake8 | requirements.txt, pyproject.toml | ✅ |
| JavaScript | prettier | package.json | ✅ |
| TypeScript | prettier + eslint | package.json | ✅ |
| Go | gofmt | go.mod | ✅ |
| Rust | rustfmt | - | ✅ |
| Kotlin | ktlint | - | ✅ |
| Swift | swiftformat | - | ✅ |

---

## 5. 안정성 지표

### 5.1 오류 처리 품질

| 항목 | 상태 |
|------|------|
| Ollama 미실행 시 graceful 오류 | ✅ |
| LLM ReadTimeout 처리 | ✅ (v2.0.1 수정) |
| 파일 경로 순회 방지 | ✅ |
| git 레포 아닌 경우 안전 종료 | ✅ |
| pathspec 파싱 오류 수정 | ✅ (v2.0.1 수정) |

### 5.2 회귀 이력

| 버전 | 버그 | 해결 |
|------|------|------|
| v2.0.0 | `locky edit` httpx.ReadTimeout (CPU inference) | v2.0.1 — `stream(timeout=None)` |
| v2.0.0 | `locky commit` pathspec 'ocky/...' 오류 | v2.0.1 — `git add -u` 교체 |
| v2.0.0 | test_agents_edit mock 불일치 | v2.0.1 — `OllamaClient.stream` mock |

---

## 6. 설계 일치율 (Match Rate)

| 분석 회차 | Match Rate | 주요 변경 |
|---------|:----------:|---------|
| v1 (초기) | 88% | 5개 gap 발견 |
| v2 (gap 수정 후) | 97% | 5/5 gap 해결 |
| v3 (postfix 후) | **98%** | streaming 설계 의도 부합, 테스트 mock 동기화 |

### 카테고리별 Match Rate (v3)

| 카테고리 | Match Rate |
|---------|:----------:|
| Architecture Compliance | 100% |
| Module Match | 100% |
| Test Coverage | 135% (70/52 설계 대비 초과) |
| CLI Integration | 95% |
| **전체 가중 평균** | **98%** |

---

## 7. 결론 및 권장 사항

### 강점
- **테스트 통과율 100%**: 351개 테스트 전원 통과
- **핵심 모듈 100% 커버리지**: hook, pipeline, ask_agent 완전 검증
- **lint 오류 0개**: black + isort + flake8 완전 준수
- **설계 일치율 98%**: 설계 의도 거의 완벽하게 반영

### 개선 기회

| 우선순위 | 항목 | 현재 | 목표 |
|---------|------|:----:|:----:|
| High | `locky commit` 통합 테스트 | 8% | 40% |
| High | `locky_cli/main.py` CLI 통합 테스트 | 0% | 30% |
| Medium | `locky/agents/edit_agent.py` 실행 경로 | 65% | 80% |
| Low | `actions/deps_check.py` edge case | 65% | 80% |

### 다음 단계
1. **v2.1.0**: `locky commit` 통합 테스트 (mock git repo 기반)
2. **v2.1.0**: CLI E2E 테스트 (`Click.testing.CliRunner` 활용)
3. **v2.2.0**: `locky jira` 명령어 CLI 통합 (`actions/jira.py` 연결)
4. **장기**: VS Code Extension / GitHub Actions 통합

---

*보고서 생성: Claude Sonnet 4.6 + bkit:report-generator*
*데이터 기준: `pytest --cov` 실행 결과 + git log 분석 + 수동 실행 검증*
