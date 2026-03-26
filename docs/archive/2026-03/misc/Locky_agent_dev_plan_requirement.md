# Project Locky: Master Development Guidelines for Claude Code

## 1. Mission Statement
당신(Claude Code)은 완벽한 사내 보안을 유지하는 100% 로컬 AI 개발 에이전트, 'Locky(로키)'의 아키텍처를 설계하고 코드를 구현하는 수석 개발자입니다. 아래의 기술 스택과 계층적 서브 에이전트 파이프라인 규칙을 엄격히 준수하여 프로젝트의 뼈대와 로직을 구축하십시오.

## 2. Core Tech Stack
- **Language:** Python 3.10+
- **LLM Engine:** Ollama (로컬 실행 환경, 외부 LLM API 호출 절대 금지)
- **Orchestration:** LangGraph (상태 기반 워크플로우 및 순환 라우팅 제어)
- **Tools & Interface:** 오픈소스 MCP 서버 (Filesystem, Git), Chainlit (웹 UI), GitPython
- **Entry Point:** CLI 스킬 `/develop {CMD}`

## 3. Hierarchical Sub-Agent Pipeline
Locky는 3개의 팀과 각 팀의 수장(Lead)으로 구성됩니다. 각 Lead는 LangGraph의 Node 또는 SubGraph로 구현되며, 자신이 맡은 하위 에이전트(Sub-agents)를 호출하여 세부 작업을 병렬 또는 순차적으로 처리합니다.

### A. Planner Team (Lead: Strategic Planner)
- **역할:** 사용자의 `{CMD}`를 분석하고 개발 마일스톤 및 작업 계획 수립
- **Sub-agents:**
  1. `Context_Analyzer`: MCP를 활용해 현재 프로젝트의 코드베이스, 파일 구조, 의존성 파악
  2. `Task_Breaker`: 분석 결과를 바탕으로 구현 스펙을 원자 단위의 작업 지시서(JSON 등)로 분할

### B. Coder Team (Lead: Tech Lead)
- **역할:** Planner의 지시서를 바탕으로 실제 코드 작성 및 수정
- **Sub-agents:**
  1. `Core_Developer`: MCP Filesystem을 사용하여 실제 소스 코드 작성 및 파일 수정
  2. `Refactor_Formatter`: 코드 컨벤션 적용, 주석 작성 및 Conventional Commits 규격의 커밋 메시지 초안 작성

### C. Tester Team (Lead: QA Lead)
- **역할:** Coder가 수정한 코드의 품질, 안정성, 보안을 검증
- **Sub-agents:**
  1. `QA_Validator`: 단위 테스트 작성 및 로컬 테스트 스크립트 실행 후 결과 확인
  2. `Security_Auditor`: 잠재적 보안 취약점 및 하드코딩된 시크릿 키 등을 정적 분석
- **Routing Rule (Cyclic Loop):** Tester의 검증 결과가 'Fail'일 경우 워크플로우를 종료하지 않고, 에러 리포트와 함께 `Coder Team`으로 강제 회귀(Feedback Loop) 시키는 조건부 엣지(Conditional Edge)를 반드시 구현할 것.

## 4. Development Constraints & Rules
- **데이터 주권 (보안):** OpenAI, Anthropic 등 외부 클라우드 LLM으로 향하는 네트워크 연결은 일절 허용하지 않습니다. LangChain/LangGraph의 LLM 객체는 오직 `http://localhost:11434` (Ollama) 엔드포인트만 바라보도록 구성하십시오.
- **State Management:** LangGraph의 `TypedDict`를 활용하여 전체 파이프라인을 관통하는 전역 상태(Global State)와 각 팀 내부에서만 사용하는 로컬 상태(Local State)를 명확히 분리하여 설계하십시오.
- **Modular Design:** 코드를 단일 파일에 몰아넣지 말고 `agents/`, `tools/`, `states/`, `ui/` 등 명확한 디렉토리 구조로 모듈화하십시오.

## 5. Your First Task (Immediate Action)
이 문서를 완벽히 숙지했다면, 지체 없이 다음 작업을 순서대로 실행하십시오:
1. Locky 프로젝트의 스캐폴딩(Scaffolding)을 위한 **디렉토리 트리 구조**를 터미널에 출력하여 제안하십시오.
2. LangGraph에서 사용할 핵심 **상태 체계(`states.py`)** 와 세 팀이 순환하는 **메인 그래프 라우터 로직(`graph.py`)** 의 파이썬 뼈대 코드를 작성하십시오.
3. 사용자가 터미널에서 `/develop {CMD}`를 입력했을 때 이 LangGraph 워크플로우를 트리거하는 **초기 진입점 스크립트(`main.py` 또는 `cli.py`)** 를 구현하십시오.