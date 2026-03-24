# Locky Agent PRD (Product Requirements Document)

> PM Agent Team Analysis | 2026-03-24
> Feature: locky-agent v0.4.0+ -- 로컬 AI 개발자 자동화 도구 전면 개선 및 확장

---

## Executive Summary

| 관점 | 내용 |
|------|------|
| **Problem** | 현재 Locky는 8개 독립 자동화 명령 + 자연어 셸 변환으로 유용하나, 세션 간 컨텍스트 없음/멀티스텝 불가/단일 언어(Python) 전용/테스트 부재 등의 갭이 존재하여 "매일 쓰는 도구"로의 전환이 어렵다. |
| **Solution** | (1) 프로젝트 컨텍스트 기억 시스템, (2) 멀티스텝 태스크 체이닝, (3) 플러그인 아키텍처로 언어/도구 확장, (4) pre-commit hook 통합으로 자동화 워크플로 완성 |
| **Target User** | 로컬 개발 환경을 선호하는 한국어 사용 개발자 (프라이버시 중시, Ollama 기반 로컬 LLM 사용자) |
| **Core Value** | 클라우드 의존 없이 100% 로컬에서 반복 작업 자동화 -- "개발자의 귀찮음을 로컬 AI가 해결" |

---

## Table of Contents

1. [Discovery Analysis](#1-discovery-analysis)
2. [Strategy Analysis](#2-strategy-analysis)
3. [Market Research](#3-market-research)
4. [ICP & Beachhead](#4-icp--beachhead)
5. [GTM Strategy](#5-gtm-strategy)
6. [Product Requirements](#6-product-requirements)
7. [User Stories & Test Scenarios](#7-user-stories--test-scenarios)
8. [Risk & Pre-mortem](#8-risk--pre-mortem)

---

## 1. Discovery Analysis

### 1.1 Five-Step Discovery Chain

#### Step 1: Brainstorm -- 현재 상태 진단

**현재 보유 기능 (v0.3.0):**

| 명령 | AI 사용 | 성숙도 | 비고 |
|------|---------|--------|------|
| `commit` | Ollama | 중 | Conventional Commits 자동 생성 |
| `format` | - | 고 | black + isort + flake8 |
| `test` | - | 중 | pytest 래퍼 |
| `todo` | - | 고 | TODO/FIXME/HACK/XXX 수집 |
| `scan` | - | 중 | regex 기반 보안 패턴 |
| `clean` | - | 고 | 캐시/임시파일 정리 |
| `deps` | - | 중하 | requirements.txt 비교만 |
| `env` | - | 고 | .env.example 자동 생성 |
| REPL 자연어 | Ollama | 중하 | 단일 셸 명령 변환 |

**발견된 갭:**

| # | 갭 | 심각도 | 설명 |
|---|-----|--------|------|
| G1 | 세션 간 컨텍스트 없음 | Critical | 매번 프로젝트를 새로 인식. 반복 작업 기억 불가 |
| G2 | 멀티스텝 태스크 불가 | High | "포맷 후 테스트 후 커밋" 같은 체이닝 미지원 |
| G3 | Python 파일만 지원 | High | scan/todo가 .py 위주. JS/TS/Go/Rust 등 미커버 |
| G4 | 테스트 코드 부재 | High | actions/ 모듈에 단위 테스트 없음 |
| G5 | Ollama 의존 취약점 | Medium | Ollama 서버 미기동 시 commit/shell 기능 무력화 |
| G6 | 설치 UX 미비 | Medium | pip install locky-agent 후 Ollama 별도 설치 필요 |
| G7 | 레거시 코드 잔존 | Low | agents/, states/, graph.py 등 미사용 모듈 존재 |
| G8 | deps 기능 한계 | Medium | requirements.txt만 지원, pyproject.toml/poetry 미지원 |
| G9 | 커밋 전 자동 검증 없음 | High | format/test/scan을 커밋 전에 자동 실행하는 hook 미지원 |
| G10 | 다국어 커밋 메시지 혼란 | Low | 한국어/영어 혼용으로 일관성 부족 |

#### Step 2: Assumptions Mapping

| ID | 가정 | Impact (1-5) | Risk (1-5) | Score |
|----|------|:----:|:----:|:----:|
| A1 | 개발자는 세션 간 컨텍스트 유지를 강하게 원한다 | 5 | 3 | 15 |
| A2 | pre-commit hook 통합이 채택률을 크게 높인다 | 5 | 2 | 10 |
| A3 | 멀티스텝 체이닝으로 일일 사용 빈도가 2배 증가한다 | 4 | 3 | 12 |
| A4 | 로컬 LLM 품질이 클라우드 대비 70% 이상이면 사용자가 수용한다 | 4 | 4 | 16 |
| A5 | Python 외 언어 지원이 사용자 풀을 3배 확장한다 | 4 | 3 | 12 |
| A6 | Ollama 기동 상태 자동 감지 및 fallback이 UX를 크게 개선한다 | 3 | 2 | 6 |
| A7 | REPL에서 커밋 히스토리 기반 제안이 커밋 품질을 높인다 | 3 | 4 | 12 |

#### Step 3: Assumption Prioritization (Impact x Risk)

1. **A4** (Score 16) -- 로컬 LLM 품질 수용 임계점
2. **A1** (Score 15) -- 세션 간 컨텍스트 유지 요구
3. **A3** (Score 12) -- 멀티스텝 체이닝 효과
4. **A5** (Score 12) -- 다언어 지원 확장 효과
5. **A7** (Score 12) -- 히스토리 기반 제안
6. **A2** (Score 10) -- pre-commit hook 채택 효과

#### Step 4: Experiment Design

| 가정 | 실험 | 성공 지표 | 비용 |
|------|------|-----------|------|
| A4 | qwen2.5-coder:7b vs 14b vs deepseek-coder 커밋 메시지 품질 비교 | 80% 이상 수정 없이 사용 가능 | 1일 |
| A1 | .locky/ 디렉토리에 프로젝트 메타 캐시 MVP | 재사용률 측정 (2주) | 3일 |
| A2 | `locky hook install` MVP + commit 시 format+test 자동 실행 | hook 유지율 2주 후 70% 이상 | 2일 |
| A3 | `locky pipeline "format test commit"` 체이닝 프로토타입 | 1회 사용 vs 3회 수동 실행 시간 비교 | 2일 |

#### Step 5: Opportunity Solution Tree (OST)

```
[Outcome] 개발자의 반복 작업 시간 50% 절감
    |
    +-- [Opportunity 1] 세션 간 컨텍스트 연속성
    |   +-- [Solution 1a] .locky/ 프로젝트 프로파일 캐시
    |   +-- [Solution 1b] 커밋 히스토리 분석 기반 패턴 학습
    |   +-- [Solution 1c] 프로젝트별 커밋 메시지 스타일 템플릿
    |
    +-- [Opportunity 2] 자동화 워크플로 체이닝
    |   +-- [Solution 2a] pre-commit hook 통합 (format -> test -> scan -> commit)
    |   +-- [Solution 2b] 커스텀 파이프라인 정의 (.locky/pipelines.yaml)
    |   +-- [Solution 2c] REPL에서 ";" 또는 "&&" 기반 명령 체이닝
    |
    +-- [Opportunity 3] 언어/도구 확장성
    |   +-- [Solution 3a] 플러그인 시스템 (actions/ 디렉토리 자동 감지)
    |   +-- [Solution 3b] 언어별 포맷터/린터 자동 감지 (ruff, eslint, gofmt 등)
    |   +-- [Solution 3c] .locky/config.yaml로 도구 매핑 커스터마이징
    |
    +-- [Opportunity 4] Ollama 사용 경험 안정화
    |   +-- [Solution 4a] Ollama 헬스체크 + 자동 시작 (ollama serve)
    |   +-- [Solution 4b] 모델 자동 pull (첫 실행 시)
    |   +-- [Solution 4c] Ollama 없이도 동작하는 fallback 메시지 생성
    |
    +-- [Opportunity 5] 코드 품질 내재화
        +-- [Solution 5a] 테스트 커버리지 리포트 통합
        +-- [Solution 5b] 보안 스캔 룰 확장 (JS, Docker, YAML)
        +-- [Solution 5c] AI 코드 리뷰 (diff 기반 제안)
```

---

## 2. Strategy Analysis

### 2.1 JTBD 6-Part Value Proposition

| Part | Content |
|------|---------|
| **1. Job** | 코드 변경 후 반복되는 개발 워크플로(포맷/테스트/보안검사/커밋)를 빠르고 일관되게 처리하고 싶다 |
| **2. Situation** | 로컬 개발 환경에서 프라이버시를 유지하면서 AI를 활용하고 싶을 때 |
| **3. Motivation** | 반복 작업에 들이는 시간을 줄이고 코드 품질을 높이면서도 클라우드에 코드를 노출하고 싶지 않다 |
| **4. Expected Outcome** | 한 번의 명령으로 포맷+테스트+보안스캔+커밋이 자동 완료. 프로젝트 컨텍스트가 기억되어 점점 더 정확해진다 |
| **5. Existing Alternatives** | (a) 수동 git alias/shell script, (b) GitHub Copilot + IDE 내장, (c) Aider CLI, (d) aicommits/OpenCommit |
| **6. Why Us** | 100% 로컬(Ollama), 통합 자동화(8개 명령 단일 CLI), 한국어 네이티브, 오픈소스, pre-commit 워크플로 통합 |

### 2.2 Lean Canvas

| Block | Content |
|-------|---------|
| **Problem** | (1) 코드 작성 후 포맷/테스트/보안/커밋을 각각 수동 실행하는 비효율, (2) 클라우드 AI 도구의 코드 프라이버시 우려, (3) 커밋 메시지 품질 일관성 부족 |
| **Customer Segments** | (1) 프라이버시 중시 한국 개발자, (2) 로컬 LLM 얼리어답터, (3) 1인 개발자/소규모 팀 |
| **Unique Value Proposition** | "100% 로컬에서 개발 워크플로 전체를 자동화하는 유일한 CLI 도구" |
| **Solution** | Ollama 기반 AI 커밋 + 8개 자동화 명령 + pre-commit hook + 멀티스텝 파이프라인 + 프로젝트 컨텍스트 기억 |
| **Channels** | PyPI, GitHub, 한국 개발자 커뮤니티(velog, GeekNews, 커피한잔 등), Ollama 에코시스템 |
| **Revenue Streams** | 오픈소스 (MIT) -- 수익 모델은 v1.0 이후 검토 (Pro 기능, 팀 대시보드 등) |
| **Cost Structure** | 개인 개발 시간, Ollama 서버 리소스 (사용자 부담), PyPI 호스팅 (무료) |
| **Key Metrics** | PyPI 월간 다운로드, GitHub Stars, 일일 활성 CLI 사용 횟수, 커밋 메시지 수정 없이 사용 비율 |
| **Unfair Advantage** | 100% 로컬 실행 (데이터 유출 제로), 한국어 네이티브 UX, 단일 CLI에 통합된 전체 워크플로 |

### 2.3 SWOT Analysis

| | Positive | Negative |
|---|----------|----------|
| **Internal** | **Strengths**: 100% 로컬/프라이버시, 통합 CLI (8개 명령), Conventional Commits 자동화, 한국어 네이티브, 오픈소스 | **Weaknesses**: Python 전용, 테스트 미비, Ollama 의존성, 세션 간 상태 없음, 레거시 코드 잔존, 설치 과정 복잡 |
| **External** | **Opportunities**: 로컬 AI 트렌드 급성장 (2026), EU AI Act 프라이버시 규제 강화, Ollama 에코시스템 확장, 한국 개발자 커뮤니티 로컬 LLM 관심 증가 | **Threats**: Aider/Claude Code 등 강력한 경쟁자, 클라우드 AI 품질 격차, Ollama 모델 품질 한계, 사용자 확보 난이도 |

**SO 전략 (강점+기회):**
- 프라이버시 규제 강화 트렌드를 활용하여 "코드가 로컬을 떠나지 않는" 마케팅
- Ollama 에코시스템 내 공식 도구 목록 등재

**WT 전략 (약점+위협):**
- 다언어 지원으로 경쟁 도구와의 격차 축소
- pre-commit hook 통합으로 기존 워크플로에 자연스럽게 삽입
- 테스트 커버리지 확보로 안정성 증명

### 2.4 Porter's Five Forces

| Force | Level | Analysis |
|-------|-------|----------|
| **기존 경쟁자** | High | Aider, Claude Code, Cursor, Continue.dev 등 강력한 도구 다수 존재 |
| **신규 진입자** | High | AI 코딩 도구 시장 진입 장벽 낮음 (오픈소스 모델 + API 기반) |
| **대체재** | Medium | shell alias, Makefile, husky+commitlint 등 전통적 자동화 |
| **구매자 교섭력** | High | 무료 도구 다수, 전환 비용 낮음 |
| **공급자 교섭력** | Low | Ollama/오픈소스 모델 기반으로 공급자 의존도 낮음 |

**전략적 시사점:** 경쟁이 치열한 시장에서 "100% 로컬" + "통합 워크플로"라는 차별화된 포지셔닝이 핵심. 기능 경쟁보다 워크플로 통합 깊이로 승부해야 함.

---

## 3. Market Research

### 3.1 User Personas

#### Persona 1: "민수" -- 프라이버시 중시 백엔드 개발자

| Attribute | Detail |
|-----------|--------|
| **Age/Role** | 32세, 핀테크 스타트업 백엔드 개발자 (3년차) |
| **Tech Stack** | Python, FastAPI, PostgreSQL, Docker |
| **Pain Points** | 회사 보안 정책상 GitHub Copilot 사용 불가. 커밋 메시지 작성이 귀찮음. 포맷/린트를 매번 잊음 |
| **Goals** | 코드가 외부로 나가지 않으면서 AI 지원을 받고 싶음. 커밋 전 자동 검증 |
| **JTBD** | "보안 규정을 위반하지 않으면서 커밋 워크플로를 자동화하고 싶다" |
| **Current Workflow** | git add -> black -> isort -> flake8 -> pytest -> git commit (수동 5단계) |
| **Locky Fit** | High -- pre-commit hook으로 5단계를 1단계로 줄임 |

#### Persona 2: "지영" -- 로컬 LLM 얼리어답터 풀스택 개발자

| Attribute | Detail |
|-----------|--------|
| **Age/Role** | 28세, 1인 개발자 (프리랜서), 사이드 프로젝트 다수 |
| **Tech Stack** | Python, TypeScript, React, Next.js, Ollama |
| **Pain Points** | 프로젝트마다 도구 설정 반복. 다언어 프로젝트에서 포맷터/린터 통합 어려움 |
| **Goals** | 하나의 도구로 Python+JS 프로젝트 모두 커버. 프로젝트별 설정 기억 |
| **JTBD** | "여러 프로젝트를 오가면서 각각의 컨텍스트에 맞는 자동화를 받고 싶다" |
| **Current Workflow** | 프로젝트별 Makefile 작성 -> 수동 전환 |
| **Locky Fit** | Medium-High -- 다언어 지원 + 프로젝트 프로파일 기능이 추가되면 High |

#### Persona 3: "태호" -- 시니어 DevOps/팀 리드

| Attribute | Detail |
|-----------|--------|
| **Age/Role** | 38세, 10인 규모 팀의 테크리드 |
| **Tech Stack** | Python, Go, Kubernetes, GitHub Actions |
| **Pain Points** | 팀원들의 커밋 메시지 품질 불균일. CI/CD에서 포맷/린트 실패가 빈번. 보안 이슈 사전 탐지 어려움 |
| **Goals** | 팀 전체에 일관된 코드 품질 정책 적용. 로컬에서 CI 실패를 미리 방지 |
| **JTBD** | "팀원 모두가 일관된 커밋 워크플로를 따르도록 강제하고 싶다" |
| **Current Workflow** | husky + commitlint + CI/CD, 하지만 로컬 실행 누락 빈번 |
| **Locky Fit** | Medium -- 팀 설정 공유 + hook 통합이 추가되면 High |

### 3.2 Competitor Analysis

#### 3.2.1 Feature Comparison Matrix

| Feature | Locky Agent | Aider | OpenCommit | aicommits | Claude Code |
|---------|:-----------:|:-----:|:----------:|:---------:|:-----------:|
| 100% 로컬 실행 | O | O (Ollama) | O (Ollama) | X (API) | X |
| AI 커밋 메시지 | O | O | O | O | O |
| 코드 포맷팅 | O | X | X | X | O |
| 테스트 실행 | O | X | X | X | O |
| 보안 스캔 | O | X | X | X | X |
| TODO 수집 | O | X | X | X | X |
| 의존성 체크 | O | X | X | X | X |
| 캐시 정리 | O | X | X | X | X |
| 자연어->셸 변환 | O | O | X | X | O |
| REPL 모드 | O | O | X | X | O |
| 멀티파일 코드 편집 | X | O | X | X | O |
| pre-commit hook | X (계획) | X | X | X | X |
| 프로젝트 컨텍스트 기억 | X (계획) | O | X | X | O |
| 다언어 지원 | Partial | O | O | O | O |
| 한국어 네이티브 | O | X | X | X | X |
| 가격 | Free | Free | Free | Free | $20/mo |

#### 3.2.2 Detailed Competitor Profiles

**1. Aider (github.com/paul-gauthier/aider)**
- 포지셔닝: "AI pair programming in your terminal"
- 강점: git-native, 멀티파일 편집, 다양한 모델 지원, 코드 변경+커밋 원스톱
- 약점: 코드 편집에 특화 (포맷/테스트/보안 등 워크플로 자동화 없음)
- 차별화 포인트: Locky는 코드 생성이 아닌 **워크플로 자동화**에 집중

**2. OpenCommit (github.com/di-sukharev/opencommit)**
- 포지셔닝: "AI commit message generator"
- 강점: Conventional Commits, Ollama 지원, GitHub Action 통합
- 약점: 커밋 메시지 생성 외 기능 없음
- 차별화 포인트: Locky는 커밋 메시지 + 전체 워크플로 자동화

**3. aicommits (github.com/Nutlope/aicommits)**
- 포지셔닝: "CLI that writes your git commit messages"
- 강점: 심플한 UX, 다양한 AI Provider
- 약점: API 키 필요 (로컬 실행 불가), 커밋 외 기능 없음
- 차별화 포인트: Locky는 100% 로컬 + 통합 CLI

**4. Claude Code (Anthropic)**
- 포지셔닝: "Agentic coding tool from Anthropic"
- 강점: 최고 수준의 코드 이해력, 멀티파일 편집, 테스트 작성
- 약점: 클라우드 의존 ($20/mo), 코드가 서버로 전송됨
- 차별화 포인트: Locky는 100% 로컬, 무료, 워크플로 자동화 특화

**5. Continue.dev**
- 포지셔닝: "Open-source AI code assistant for VS Code/JetBrains"
- 강점: IDE 통합, Ollama 지원, 자동 완성
- 약점: IDE 의존, CLI 워크플로 지원 약함
- 차별화 포인트: Locky는 IDE 독립 CLI 도구, 워크플로 자동화

### 3.3 Market Sizing (TAM/SAM/SOM)

#### Method 1: Top-Down

| Tier | Size | Reasoning |
|------|------|-----------|
| **TAM** | $4.65B (2026) | LLM-powered tools 글로벌 시장 (49.6% CAGR) |
| **SAM** | ~$465M | 개발자 생산성 도구 세그먼트 (TAM의 ~10%) |
| **SOM** | ~$4.65M | 한국 시장 + 로컬 AI + CLI 사용자 (SAM의 ~1%) |

#### Method 2: Bottom-Up

| Factor | Value | Reasoning |
|--------|-------|-----------|
| 한국 개발자 수 | ~250,000명 | Stack Overflow 조사 기반 추정 |
| 로컬 LLM 관심자 | ~25,000명 (10%) | Ollama 한국 사용자 추정 |
| CLI 도구 사용자 | ~7,500명 (30%) | CLI 선호 개발자 비율 |
| Locky 채택 가능 | ~750명 (10%) | 초기 1년 채택 목표 |
| 연간 가치/인 | $0 (오픈소스) | v1.0까지 무료 |
| **1차년도 SOM** | 750 Active Users | 수익 이전 사용자 기반 확보 |

#### Method Reconciliation

- 두 방법 모두 초기 시장이 "한국어 사용 로컬 LLM 개발자"로 좁다는 점 일치
- 오픈소스 특성상 1차년도는 사용자 기반 확보에 집중
- PyPI 다운로드 1,000+/월, GitHub Stars 500+ 목표

### 3.4 Customer Journey Map (Persona 1: 민수)

```
[인지]                    [탐색]                    [평가]                   [채택]                    [확장]
  |                        |                        |                        |                        |
  v                        v                        v                        v                        v
velog/GeekNews에서      GitHub README            locky commit              pre-commit hook         팀 도입 제안
"로컬 AI 커밋" 발견     설치 가이드 확인          --dry-run 시도           설치로 일상화           팀 설정 공유

[감정] 흥미              [감정] 기대+불안          [감정] 놀라움            [감정] 편안함            [감정] 자부심
       "이런게 있었어?"         "Ollama 설치 귀찮"         "메시지 품질 괜찮네"      "매일 쓰게 됨"          "팀에도 적용"

[Pain Point]             [Pain Point]             [Pain Point]             [Pain Point]             [Pain Point]
없음                    Ollama+모델 설치         첫 커밋 대기 시간       모델 품질 가끔 아쉬움    팀 설정 표준화 어려움
                        과정 복잡                (첫 로드 느림)

[기회]                   [기회]                   [기회]                   [기회]                   [기회]
커뮤니티 글 작성         원클릭 설치 스크립트      모델 프리로드             다중 모델 선택           팀 config 공유 기능
```

---

## 4. ICP & Beachhead

### 4.1 ICP (Ideal Customer Profile)

| Dimension | Detail |
|-----------|--------|
| **Role** | 백엔드/풀스택 개발자, 1-5년차 |
| **Tech** | Python 메인, Ollama 사용 경험 있음, CLI 선호 |
| **Environment** | macOS/Linux, 로컬 개발 환경 |
| **Pain** | 커밋 워크플로 반복 피로, 클라우드 AI 프라이버시 우려 |
| **Behavior** | 개발 커뮤니티 활발 참여 (velog, GitHub), 새로운 도구 시도에 적극적 |
| **Company** | 스타트업 또는 보안 정책이 엄격한 금융/공공 기관 |
| **Budget** | $0 (무료 도구 선호), 시간 투자 의향 있음 |

### 4.2 Beachhead Segment Selection

| Segment | Urgency (1-5) | Accessibility (1-5) | WTP (1-5) | Strategic Fit (1-5) | Total |
|---------|:----:|:----:|:----:|:----:|:----:|
| **한국 Python 개발자 + Ollama 사용자** | 4 | 5 | 3 | 5 | **17** |
| 한국 풀스택 개발자 (다언어) | 3 | 4 | 3 | 4 | 14 |
| 글로벌 프라이버시 중시 개발자 | 5 | 2 | 4 | 3 | 14 |
| DevOps/팀 리드 | 4 | 3 | 4 | 3 | 14 |

**Selected Beachhead:** 한국 Python 개발자 중 Ollama를 이미 사용하고 있는 CLI 선호 개발자

**Rationale:**
- 가장 높은 접근성 (한국어 네이티브 UI가 즉시 가치 제공)
- Ollama 이미 설치 = 설치 장벽 최소화
- Python 전용 현재 기능과 100% 호환
- 커뮤니티가 형성되어 있어 구전 가능

---

## 5. GTM Strategy

### 5.1 Go-To-Market Plan

| Phase | Timeline | Channel | Action | KPI |
|-------|----------|---------|--------|-----|
| **Phase 0: Foundation** | v0.4.0 (M1-2) | GitHub | 테스트 추가, 레거시 정리, README 영문화 | 테스트 커버리지 80% |
| **Phase 1: Seed** | v0.5.0 (M3-4) | velog, GeekNews | "로컬 AI 커밋 자동화" 소개글, PyPI 릴리스 | PyPI 100 DL/월 |
| **Phase 2: Hook** | v0.6.0 (M5-6) | Ollama Discord, Reddit r/LocalLLaMA | pre-commit hook + pipeline 기능 런칭 | GitHub Stars 100 |
| **Phase 3: Expand** | v0.7.0 (M7-9) | YouTube (한국 개발자), 번개장터 | 다언어 지원 + 프로젝트 컨텍스트 | Stars 300, DL 500/월 |
| **Phase 4: Community** | v1.0 (M10-12) | 오픈소스 컨퍼런서, PyCon Korea | 팀 기능 + 플러그인 시스템 | Stars 500, DL 1000/월 |

### 5.2 Growth Loops

```
[개발자가 Locky 사용]
    |
    v
[커밋 메시지 품질 향상 경험]
    |
    v
[velog/블로그에 사용 후기 작성]  <-- Content Loop
    |
    v
[다른 개발자가 발견 & 설치]
    |
    v
[팀에 도입 제안]  <-- Viral Loop
    |
    v
[팀 설정 공유 (.locky/config)]
    |
    v
[팀원 전체 채택]
```

### 5.3 Battlecard (vs Aider)

| Dimension | Locky Agent | Aider |
|-----------|-------------|-------|
| **Core Focus** | 개발 워크플로 자동화 | AI pair programming (코드 편집) |
| **Commands** | 8개 자동화 명령 + REPL | 자연어 코드 편집 |
| **Format/Test/Scan** | 내장 | 없음 |
| **pre-commit** | 지원 (계획) | 없음 |
| **한국어** | 네이티브 | 영어만 |
| **설치 복잡도** | `pip install locky-agent` + Ollama | `pip install aider-chat` + Ollama |
| **When to Choose Locky** | 커밋 워크플로 자동화, 코드 품질 관리 |
| **When to Choose Aider** | AI 기반 코드 작성/리팩토링 |
| **공존 가능?** | Yes -- Aider로 코드 편집 후 Locky로 포맷/테스트/커밋 |

---

## 6. Product Requirements

### 6.1 Release Roadmap

#### v0.4.0 -- "Foundation" (기반 강화)

| ID | Requirement | Priority | Effort | Description |
|----|------------|:--------:|:------:|-------------|
| R01 | 테스트 스위트 추가 | P0 | M | actions/ 모듈별 단위 테스트 + CI 설정 |
| R02 | 레거시 코드 정리 | P0 | S | agents/, states/, graph.py 제거 또는 deprecated 마킹 |
| R03 | Ollama 헬스체크 강화 | P1 | S | 서버 미기동 시 친절한 안내 + 자동 시작 시도 |
| R04 | pyproject.toml 정합성 | P1 | S | langgraph/langchain 의존성 제거 (실제 미사용) |
| R05 | deps 명령 확장 | P2 | S | pyproject.toml, poetry.lock 지원 |

#### v0.5.0 -- "Pipeline" (워크플로 체이닝)

| ID | Requirement | Priority | Effort | Description |
|----|------------|:--------:|:------:|-------------|
| R06 | pre-commit hook 통합 | P0 | M | `locky hook install/uninstall` -- format+test+scan 자동 실행 |
| R07 | 명령 체이닝 | P0 | M | `locky run "format test commit"` 또는 REPL에서 파이프라인 |
| R08 | .locky/config.yaml | P1 | M | 프로젝트별 설정 (모델, 포맷터, 린터, hook 구성) |
| R09 | 커밋 메시지 언어 설정 | P2 | S | `commit_language: ko|en|auto` 설정 |

#### v0.6.0 -- "Context" (프로젝트 컨텍스트)

| ID | Requirement | Priority | Effort | Description |
|----|------------|:--------:|:------:|-------------|
| R10 | 프로젝트 프로파일 캐시 | P0 | L | .locky/profile.json -- 언어/프레임워크/커밋 패턴 자동 감지 및 캐시 |
| R11 | 커밋 히스토리 학습 | P1 | M | 최근 50개 커밋 패턴 분석, 스타일 미러링 |
| R12 | 모델 자동 관리 | P2 | M | 첫 실행 시 모델 자동 pull, 추천 모델 안내 |

#### v0.7.0 -- "Polyglot" (다언어 확장)

| ID | Requirement | Priority | Effort | Description |
|----|------------|:--------:|:------:|-------------|
| R13 | 언어별 포맷터 자동 감지 | P0 | L | Python(ruff), JS(prettier), Go(gofmt), Rust(rustfmt) 등 |
| R14 | 보안 스캔 룰 확장 | P1 | M | JS, Docker, YAML, Terraform 패턴 추가 |
| R15 | TODO 수집 다언어 | P1 | S | .go, .rs, .java, .rb 등 확장 |
| R16 | 플러그인 시스템 MVP | P2 | L | actions/ 디렉토리 자동 감지 + 커스텀 액션 등록 |

#### v1.0.0 -- "Team" (팀 기능)

| ID | Requirement | Priority | Effort | Description |
|----|------------|:--------:|:------:|-------------|
| R17 | 팀 설정 공유 | P1 | M | .locky/config.yaml를 팀 표준으로 배포 |
| R18 | AI 코드 리뷰 | P2 | L | diff 기반 코드 리뷰 제안 (Ollama 활용) |
| R19 | 대시보드 개선 | P2 | L | Chainlit UI에서 실행 히스토리/통계 시각화 |

### 6.2 Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Performance** | 모든 non-AI 명령 < 3초 완료. AI 명령 (commit/shell) < 15초 (7B 모델 기준) |
| **Privacy** | 네트워크 요청은 localhost:11434 (Ollama)만 허용. 텔레메트리 없음 |
| **Compatibility** | Python 3.10+, macOS/Linux. Windows WSL 지원 |
| **Reliability** | Ollama 미기동 시에도 non-AI 명령은 100% 동작 |
| **Extensibility** | 새로운 action 추가 시 기존 코드 수정 불필요 (Open-Closed) |

---

## 7. User Stories & Test Scenarios

### 7.1 User Stories

#### Epic 1: 워크플로 자동화

| ID | User Story | INVEST Check | Priority |
|----|-----------|:---:|:---:|
| US01 | 개발자로서, `locky commit`을 실행하면 자동으로 format+test+scan을 먼저 실행하고 문제없으면 커밋하고 싶다 | I-N-V-E-S-T | P0 |
| US02 | 개발자로서, `locky hook install`로 pre-commit hook을 설치하면 매 커밋 시 자동 검증되고 싶다 | I-N-V-E-S-T | P0 |
| US03 | 개발자로서, `locky run "format test commit --push"`로 여러 명령을 한 번에 체이닝하고 싶다 | I-N-V-E-S-T | P0 |
| US04 | 개발자로서, REPL에서 `format && test && commit`을 입력하면 순차 실행되고 싶다 | I-N-V-E-S | P1 |

#### Epic 2: 프로젝트 컨텍스트

| ID | User Story | INVEST Check | Priority |
|----|-----------|:---:|:---:|
| US05 | 개발자로서, 프로젝트를 처음 사용할 때 Locky가 자동으로 언어/프레임워크를 감지하고 기억하길 원한다 | I-N-V-E-S | P0 |
| US06 | 개발자로서, 이전 커밋 메시지 스타일을 학습하여 일관된 메시지를 생성받고 싶다 | I-N-V-E-S | P1 |
| US07 | 개발자로서, `.locky/config.yaml`에 프로젝트별 설정(모델, 포맷터)을 저장하고 싶다 | I-N-V-E-S-T | P1 |

#### Epic 3: 안정성 & 확장

| ID | User Story | INVEST Check | Priority |
|----|-----------|:---:|:---:|
| US08 | 개발자로서, Ollama가 꺼져 있어도 format/test/scan/clean 등은 정상 동작하길 원한다 | I-N-V-E-S-T | P0 |
| US09 | 개발자로서, TypeScript 프로젝트에서도 prettier/eslint 기반 포맷과 보안 스캔이 되길 원한다 | I-N-V-E-S | P1 |
| US10 | 개발자로서, 커스텀 액션을 `.locky/actions/` 디렉토리에 추가하면 자동으로 CLI에 등록되길 원한다 | I-N-V-E-S | P2 |

### 7.2 Test Scenarios

| User Story | Test Scenario | Expected Result |
|------------|---------------|-----------------|
| US01 | `locky commit` 실행 시 format 오류가 있는 경우 | 커밋 중단, 오류 리포트 표시, 수정 안내 |
| US01 | `locky commit` 실행 시 모든 검증 통과 | 자동 커밋 완료 + 결과 요약 |
| US02 | `locky hook install` 후 `git commit` 실행 | pre-commit hook이 format+test+scan 실행 |
| US02 | `locky hook uninstall` 후 `git commit` 실행 | hook 없이 일반 커밋 |
| US03 | `locky run "format test commit"` 실행 시 test 실패 | format 완료, test 실패 리포트, commit 미실행 |
| US05 | Python+FastAPI 프로젝트에서 첫 `locky` 실행 | "Python/FastAPI 프로젝트 감지" 메시지 + .locky/profile.json 생성 |
| US06 | 한국어 커밋 히스토리가 있는 프로젝트에서 `locky commit` | 한국어 스타일 커밋 메시지 생성 |
| US07 | `.locky/config.yaml`에 `model: deepseek-coder:6.7b` 설정 | commit 시 해당 모델 사용 |
| US08 | Ollama 서버 중지 상태에서 `locky format` 실행 | 정상 실행 (Ollama 불필요 확인) |
| US08 | Ollama 서버 중지 상태에서 `locky commit` 실행 | "Ollama 서버가 실행되지 않음" 안내 + fallback 메시지 생성 |
| US09 | package.json이 있는 디렉토리에서 `locky format` | prettier 감지 및 실행 |
| US10 | `.locky/actions/my_action.py`에 `run()` 함수 정의 | `locky my-action` 또는 REPL `/my-action`으로 실행 가능 |

---

## 8. Risk & Pre-mortem

### 8.1 Pre-mortem: "Locky v1.0이 실패한 이유"

**시나리오:** 1년 후, Locky의 GitHub Stars는 50개에 머물고 월간 다운로드는 20에 불과합니다.

| # | 실패 원인 | Likelihood | Impact | Mitigation |
|---|-----------|:----:|:----:|------------|
| 1 | **Ollama 모델 품질이 기대 이하** -- 생성된 커밋 메시지를 매번 수정해야 해서 사용자가 이탈 | High | Critical | 다중 모델 지원 + 품질 벤치마크 + 사용자 피드백 루프. 모델 업그레이드 시 자동 알림 |
| 2 | **Aider가 워크플로 기능도 추가** -- 경쟁 도구가 포맷/테스트 통합을 추가하여 차별화 소멸 | Medium | High | 워크플로 통합 깊이에서 선행 우위 유지. 플러그인 생태계로 확장성 확보 |
| 3 | **설치 과정이 너무 복잡** -- Ollama + 모델 + pip install 3단계에서 이탈 | High | High | 원클릭 설치 스크립트 (`curl ... \| sh`), Docker 이미지 제공 |
| 4 | **한국 시장만으로는 사용자 기반 한계** | Medium | Medium | v0.7.0부터 영문 README/docs, 글로벌 커뮤니티 참여 |
| 5 | **테스트 없이 릴리스하여 버그 다발** | Medium | High | v0.4.0에서 테스트 기반 확보 후 기능 추가. CI/CD 파이프라인 |

### 8.2 Stakeholder Map

| Stakeholder | Interest | Influence | Strategy |
|-------------|----------|-----------|----------|
| 프로젝트 메인테이너 (본인) | High | High | 지속적 개발 동기 유지, 커뮤니티 피드백 반영 |
| Ollama 커뮤니티 | Medium | Medium | 에코시스템 도구로 등재, 호환성 유지 |
| 한국 개발자 커뮤니티 | High | Medium | velog/GeekNews 콘텐츠, 사용 후기 유도 |
| PyPI 사용자 | Medium | Low | 명확한 README, 빠른 시작 가이드 |
| 잠재적 기여자 | Medium | Medium | CONTRIBUTING.md, good-first-issue 라벨, 친절한 코드 리뷰 |

---

## Attribution

This PRD was generated by PM Agent Team, integrating frameworks from:
- **Teresa Torres** -- Opportunity Solution Tree (Discovery)
- **Strategyzer** -- Value Proposition Canvas, Lean Canvas
- **Michael Porter** -- Five Forces Analysis
- **Geoffrey Moore** -- Beachhead Market Strategy (Crossing the Chasm)
- **Pawel Huryn / pm-skills** (MIT License) -- JTBD 6-Part VP, Pre-mortem framework

Market research sources:
- [LLM Powered Tools Market Report](https://www.giiresearch.com/report/tbrc1981336-large-language-model-powered-tools-global-market.html)
- [Ollama Alternatives Guide](https://localllm.in/blog/complete-guide-ollama-alternatives)
- [Agentic CLI Tools Compared](https://aimultiple.com/agentic-cli)
- [Best AI Coding Agents 2026](https://www.faros.ai/blog/best-ai-coding-agents-2026)
- [Privacy-First AI Trends 2026](https://techhorizonpro.com/best-privacy-first-ai-apps-2026/)
- [AI Commit Tools Comparison](https://www.hongkiat.com/blog/best-ai-tools-for-git-commit-messages/)
