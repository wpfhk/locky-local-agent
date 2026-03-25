# locky-agent v1.1.0 Planning Document

> **Summary**: 프로젝트 설정 파일·REPL 컨텍스트·자동 업데이트로 "설정 한 번, 매일 사용" 완성
>
> **Project**: locky-agent
> **Version**: 1.0.0 → 1.1.0
> **Author**: youngsang.kwon
> **Date**: 2026-03-24
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | v1.0.0은 매번 환경변수로 설정을 바꿔야 하고, REPL 진입 시 프로젝트 컨텍스트가 없으며, 업데이트를 수동으로 해야 한다. |
| **Solution** | `.locky/config.yaml` 프로젝트 설정 파일 + REPL 컨텍스트 로드 + `locky init` 대화형 + `locky update` 자동 업데이트로 초기 설정 1회, 이후 유지보수 최소화. |
| **Function/UX Effect** | `locky init`으로 프로젝트별 config.yaml 생성, REPL 진입 시 프로젝트 정보 자동 표시, `locky update` 한 줄로 최신 버전 유지. |
| **Core Value** | "설정 한 번, 매일 쓴다" — 프로젝트마다 `.locky/config.yaml`만 있으면 별도 환경변수 없이 동작 |

---

## Context Anchor

| Key | Value |
|-----|-------|
| **WHY** | 환경변수 설정 반복, REPL 컨텍스트 부재, 수동 업데이트가 매일 사용의 마찰을 높인다. |
| **WHO** | 로컬 LLM(Ollama) 사용 개발자, 여러 프로젝트를 오가며 작업, 한국어 사용자 |
| **RISK** | config.yaml 우선순위가 환경변수와 충돌 시 예측 불가 동작 / git pull 실패 시 업데이트 중단 |
| **SUCCESS** | `locky init` 후 환경변수 없이 `locky commit` 정상 동작 / `locky update`로 1분 내 최신 버전 적용 |
| **SCOPE** | config.yaml 로더·init 대화형·REPL context 통합·update 명령·profile 자동갱신 |

---

## 1. Overview

### 1.1 Purpose

v1.0.0에서 남은 마찰 요소를 제거하여 "처음 한 번 설정하면 이후는 자동"인 경험을 완성한다.

### 1.2 Background

v1.0.0 Gap Analysis의 Remaining Items:

| Gap | Severity | 내용 |
|-----|:--------:|------|
| #5 | Important | `.locky/config.yaml` 미구현 |
| #7 | Important | `repl.py` context 미통합 |
| #10 | Minor | `locky init` 비대화형 |
| FR-01 | Partial | `profile.json` 자동 생성 (init 명시 호출 시만) |
| FR-13 | Partial | `locky init` 설정 가이드 (비대화형) |

추가 신규 기능:
- `locky update`: git pull + pip 재설치로 자동 업데이트

### 1.3 Related Documents

- v1.0.0 Analysis: `docs/archive/2026-03/locky-agent/locky-agent.analysis.md`
- v1.0.0 Report: `docs/archive/2026-03/locky-agent/locky-agent.report.md`

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | 기능 | 우선순위 |
|----|------|:--------:|
| FR-01 | `.locky/config.yaml` 로더 — 환경변수보다 낮은 우선순위로 설정 적용 | Must |
| FR-02 | `locky init` 대화형 — 질문-답변으로 config.yaml 자동 생성 | Must |
| FR-03 | REPL 진입 시 profile.json + config.yaml 자동 로드 및 헤더 표시 | Must |
| FR-04 | `locky update` — git pull + pip install -e . 자동 실행, 버전 비교 표시 | Must |
| FR-05 | profile.json 자동 갱신 — 서브커맨드 실행 시 `detect_and_save()` 자동 호출 | Should |
| FR-06 | `locky update --check` — 업데이트 없이 최신 버전 확인만 | Should |

### 2.2 Non-Functional Requirements

| ID | 요건 |
|----|------|
| NFR-01 | config.yaml 없을 때 기존 동작 완전 호환 (breaking change 없음) |
| NFR-02 | `locky update` — 네트워크/git 오류 시 현재 버전 유지, 에러 메시지 안내 |
| NFR-03 | 신규 모듈 단위 테스트 추가 (커버리지 ≥ 80%) |

---

## 3. Scope

### In Scope

- `locky_cli/config_loader.py` — config.yaml 파서 및 병합 로직
- `locky_cli/main.py` — init 대화형 재작성, `locky update` 서브커맨드 추가
- `locky_cli/repl.py` — 진입 시 context 로드 및 헤더 표시
- `locky_cli/context.py` — `detect_and_save()` 자동 호출 훅
- `actions/update.py` — git pull + pip 재설치 + 버전 비교
- `config.py` — config.yaml 우선순위 병합 로직
- `tests/test_config_loader.py`, `tests/test_update.py`

### Out of Scope

- PyPI 배포 (`pip install locky-agent`)
- GitHub Releases API를 통한 버전 확인 (git tag 기반으로 충분)
- Windows 지원 (macOS/Linux 우선)

---

## 4. Architecture Overview

```
.locky/config.yaml          ← 프로젝트별 설정 (git 제외)
  ↓ (우선순위: env > config.yaml > 기본값)
config_loader.py             ← YAML 파싱 + 환경변수 병합
  ↓
config.py                    ← 전역 상수 (OLLAMA_MODEL, OLLAMA_BASE_URL 등)
  ↓
actions/* / locky_cli/*      ← 모든 모듈이 config.py 통해 설정 읽기
```

```
locky update
  ↓
actions/update.py
  ├── _find_repo_root()      ← __file__ 기반으로 git 저장소 경로 탐색
  ├── _get_current_version() ← pyproject.toml 파싱
  ├── _git_pull()            ← subprocess git pull origin main
  └── _reinstall()           ← pip install -e . (또는 pipx upgrade)
```

---

## 5. Config YAML 명세

```yaml
# .locky/config.yaml (프로젝트 루트)
ollama:
  model: qwen2.5-coder:14b   # 기본값: qwen2.5-coder:7b
  base_url: http://localhost:11434
  timeout: 300

hook:
  steps:
    - format
    - test
    - scan

init:
  auto_profile: true         # 서브커맨드 실행 시 profile 자동 갱신
```

---

## 6. `locky update` 동작 명세

```
$ locky update

Checking for updates...
  현재 버전: 1.0.0
  최신 커밋: a1b2c3d (2026-03-25)

Pulling from origin/main...
  ✓ Already up to date.  (또는)
  ✓ 3 files changed, 42 insertions(+)

Reinstalling...
  ✓ locky-agent 1.1.0 installed

업데이트 완료: 1.0.0 → 1.1.0
```

---

## 7. `locky init` 대화형 명세

```
$ locky init

Locky 프로젝트 설정을 시작합니다.

? Ollama 모델을 선택하세요 [qwen2.5-coder:7b]:
  > qwen2.5-coder:14b

? pre-commit 훅을 설치할까요? [Y/n]: Y

? 훅 실행 스텝을 선택하세요 (쉼표 구분) [format,test,scan]:
  > format,scan

✓ .locky/config.yaml 생성 완료
✓ pre-commit 훅 설치 완료
```

---

## 8. REPL 컨텍스트 헤더 명세

```
╭──────────────── Locky v1.1.0 ─────────────────╮
│  프로젝트    /Users/you/myproject              │
│  언어        python                            │
│  모델        qwen2.5-coder:7b (config.yaml)   │
│  훅          format → test → scan             │
╰─ /help로 명령어 확인 ────────────────────────╯
```

---

## 9. Success Criteria (DoD)

- [ ] `locky init` 실행 → `.locky/config.yaml` 생성 → `locky commit`이 환경변수 없이 config.yaml 모델로 동작
- [ ] `locky` (REPL) 진입 시 프로젝트 정보 헤더 표시
- [ ] `locky update` 실행 → 최신 git 커밋으로 업데이트
- [ ] `locky update --check` 실행 → 버전 정보만 표시 (파일 변경 없음)
- [ ] 신규 테스트 추가 (test_config_loader.py, test_update.py)
- [ ] 전체 테스트 pass (기존 132개 + 신규)
- [ ] config.yaml 없는 환경에서 기존 동작 완전 유지

---

## 10. Risks

| Risk | 대응 |
|------|------|
| config.yaml 우선순위 충돌 | 명확한 우선순위: 환경변수 > config.yaml > 기본값, 문서화 |
| git pull 실패 (네트워크/충돌) | try-except로 감싸고 현재 버전 유지, 상세 에러 출력 |
| pipx vs pip 설치 환경 분기 | `which locky` + `shutil.which("pipx")` 로 설치 방식 감지 |
| REPL 헤더 렌더링 에러 | config.yaml/profile.json 없을 때 graceful fallback |
