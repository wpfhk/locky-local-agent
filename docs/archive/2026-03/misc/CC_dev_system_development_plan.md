# CC_dev_system_development_plan.md

## 1. 프로젝트 개요
- **목표:** Sub-agent와 Skills 기반의 계층적(Hierarchical) 자동화 개발 파이프라인 구축.
- **핵심 아키텍처:** `/develop` 스킬을 진입점으로 하여, 각 단계를 책임지는 '수장(Lead)' 에이전트가 하위(Sub) 에이전트들을 호출하여 작업을 세분화하고 수행하는 팀 기반 워크플로우 설계.

## 2. Skills 및 Entry Point 설계
- **Custom Skill:** `/develop {CMD}`
- **동작 방식:** 사용자가 CLI에 해당 명령어를 입력하면, 오케스트레이터(메인 라우터)가 트리거되어 `{CMD}`(요구사항 또는 티켓 내용)를 파싱하고 **Planner Lead**에게 작업을 인계함.

## 3. 계층적 Sub-agent 팀 구조 (Hierarchical Teams)
각 단계의 수장(Lead) 에이전트는 독립적인 컨텍스트를 가지며, 자신의 팀에 속한 하위 서브 에이전트들을 호출하여 세부 작업을 병렬 또는 순차적으로 처리한 뒤 결과를 취합합니다.

### 단계 1: Planner Team (계획 및 분석)
- **Lead Agent (Planner):** 요구사항 전체를 분석하고 개발 마일스톤을 수립.
- **Sub-agents:**
  - `Context_Analyzer`: 기존 코드베이스, 파일 구조, 의존성 등을 분석.
  - `Task_Breaker`: 구현해야 할 기능을 원자 단위(Atomic Tasks)의 작업 지시서로 분할.
- **Output:** 구체적인 개발 스펙 및 작업 지시서(Plan Document).

### 단계 2: Coder Team (구현 및 작성)
- **Lead Agent (Coder):** Planner의 지시서를 바탕으로 실제 코드 변경을 총괄.
- **Sub-agents:**
  - `Core_Developer`: 핵심 비즈니스 로직 작성 및 파일 수정 수행.
  - `Refactor_Formatter`: 코드 컨벤션 적용, 주석 작성, 불필요한 코드 최적화.
- **Output:** 작성/수정된 소스 코드 및 Git Diff 초안.

### 단계 3: Tester Team (검증 및 피드백)
- **Lead Agent (Tester):** Coder가 작성한 코드를 넘겨받아 품질과 안정성을 검증.
- **Sub-agents:**
  - `QA_Validator`: 단위 테스트(Unit Test) 작성 및 로컬 테스트 스크립트 실행.
  - `Security_Auditor`: 잠재적 보안 취약점, 하드코딩된 시크릿 키 등을 정적 분석.
- **Output:**
  - 검증 통과 시: 최종 승인(Approve) 및 커밋 준비 완료 메시지.
  - 검증 실패 시: 에러 로그 및 수정 가이드라인을 Coder Team으로 반환(Feedback Loop).

## 4. Workflow State & Routing 로직
- 각 팀 간의 데이터(State) 전달 규격을 정의해야 함 (예: JSON 기반의 Context 공유).
- **Cyclic Loop:** Tester의 검증 결과가 'Fail'일 경우, 워크플로우가 종료되지 않고 Coder Lead에게 반려되어 코드를 수정하는 순환 구조(Loop) 필수 구현.

## 5. 단계별 구현 지침 (Action Items)
클로드 코드, 당신은 이 문서를 기반으로 다음 작업을 순차적으로 수행하십시오.

1. **Scaffolding:** 에이전트 오케스트레이션을 위한 기본 디렉토리 구조 생성.
2. **Skills 구현:** 커맨드라인에서 `/develop {CMD}` 입력을 인터셉트하고 파싱하는 트리거 모듈 작성.
3. **Sub-agent 라우팅 로직:** Planner, Coder, Tester 수장 에이전트와 각각의 하위 에이전트 클래스/함수 구조(Skeleton Code) 작성.
4. **상태 관리(State Management):** 각 수장 에이전트가 하위 에이전트의 결과를 취합하여 다음 단계로 넘기는 데이터 파이프라인 구현.