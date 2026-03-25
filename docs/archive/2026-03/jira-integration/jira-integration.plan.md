# Plan: jira-integration

> **Feature**: jira-integration
> **Created**: 2026-03-25
> **Status**: Planning
> **Author**: Claude (PDCA Plan Phase)

---

## Executive Summary

| 항목 | 내용 |
|------|------|
| **Feature** | jira-integration |
| **시작일** | 2026-03-25 |
| **예상 완료** | 2026-03-27 |
| **예상 기간** | 2일 |

### Value Delivered (4-Perspective)

| 관점 | 내용 |
|------|------|
| **Problem** | 개발자가 Jira와 CLI 사이를 오가며 이슈를 확인·정리하는 컨텍스트 전환 비용이 크고, 이슈 현황을 문서화하려면 수동 복사가 필요함 |
| **Solution** | `locky jira` 서브커맨드로 Jira REST API를 호출해 이슈를 조회·정리하고 `.md`로 자동 저장하며, 이슈 신규 생성까지 CLI에서 완결 |
| **Function UX Effect** | 터미널을 떠나지 않고 이슈 조회 → 마크다운 리포트 생성 → 신규 이슈 생성을 단일 흐름으로 완료; 기존 `actions/` 패턴과 동일한 UX |
| **Core Value** | 로컬 개발자 자동화 도구(locky)의 범위를 워크플로 문서화까지 확장하여 Jira를 CLI 네이티브로 통합 |

---

## Context Anchor

| 항목 | 내용 |
|------|------|
| **WHY** | 개발자 워크플로 자동화 툴에서 Jira 이슈 조회·생성을 CLI로 처리해 컨텍스트 전환 제거 |
| **WHO** | locky를 사용하는 개발자 — Jira를 주 이슈 트래커로 사용하고 터미널 중심 워크플로를 선호 |
| **RISK** | Jira API Token 노출 위험, Jira Cloud vs Server API 버전 차이, 네트워크 오류 핸들링 |
| **SUCCESS** | `locky jira list` → .md 생성 성공; `locky jira create` → 이슈 생성 확인; 테스트 커버리지 ≥80% |
| **SCOPE** | 조회(list) + .md 저장 + 기본 생성(create); JQL 직접 입력·이슈 수정·코멘트는 제외 |

---

## 1. 배경 및 목적

### 1.1 문제 정의

locky-agent는 현재 git 커밋, 포맷팅, 보안 스캔 등 로컬 자동화에 집중되어 있으며 Jira와 같은 외부 이슈 트래커와의 연동이 없다. 개발자는 이슈 현황 파악을 위해 브라우저로 전환해야 하고, 이슈를 문서화할 때는 수동으로 복사해야 한다.

### 1.2 목표

- Jira REST API를 통해 이슈 목록 조회 및 `.md` 파일 저장
- CLI에서 신규 Jira 이슈 생성
- 기존 `actions/` 독립 모듈 패턴 완전 준수

### 1.3 범위

**포함 (In Scope)**
- `locky jira list` — 프로젝트/상태/담당자 필터로 이슈 조회 후 `.md` 저장
- `locky jira create` — 기본 필드(제목, 설명, 타입, 우선순위)로 이슈 생성
- `locky jira status` — Jira 연결 상태 확인
- 인증 정보: `config.yaml`(URL, email) + 환경변수 `JIRA_API_TOKEN`
- 저장 경로: `.locky/jira/{date}-{project}.md`

**제외 (Out of Scope)**
- JQL 직접 입력 (`--jql` 옵션)
- 이슈 수정 (update/edit)
- 코멘트 추가
- 첨부파일, 워크로그
- Jira Server/DC의 OAuth 인증

---

## 2. 요구사항

### 2.1 기능 요구사항

#### FR-01: 이슈 조회 (jira list)

```
locky jira list [OPTIONS]

Options:
  --project TEXT    Jira 프로젝트 키 (예: MYPROJ)
  --status TEXT     이슈 상태 필터 (예: "In Progress", "To Do")
  --assignee TEXT   담당자 필터 (현재 사용자: "me")
  --max INTEGER     최대 조회 건수 (기본: 50)
  --output FILE     저장 경로 지정 (기본: .locky/jira/{date}-{project}.md)
  --no-save         .md 저장 없이 터미널 출력만
```

**출력 필드**: key, summary, status, assignee, description

**결과 dict**:
```python
{
  "status": "ok" | "error",
  "count": int,
  "saved_to": str | None,
  "issues": [{"key": ..., "summary": ..., "status": ..., "assignee": ..., "description": ...}]
}
```

#### FR-02: 이슈 생성 (jira create)

```
locky jira create [OPTIONS]

Options:
  --project TEXT    [필수] 프로젝트 키
  --summary TEXT    [필수] 이슈 제목
  --description TEXT 이슈 설명
  --type TEXT       이슈 타입 (기본: Task; Bug/Story/Task/Epic)
  --priority TEXT   우선순위 (기본: Medium; Highest/High/Medium/Low/Lowest)
  --dry-run         실제 생성 없이 페이로드만 출력
```

**결과 dict**:
```python
{
  "status": "ok" | "dry_run" | "error",
  "key": str | None,
  "url": str | None,
  "message": str
}
```

#### FR-03: 연결 상태 확인 (jira status)

```
locky jira status
```

Jira URL, 인증 유효 여부, 접근 가능한 프로젝트 수 출력.

#### FR-04: .md 파일 포맷

```markdown
# Jira Issues — {PROJECT} ({date})

> 조회 조건: status={status}, assignee={assignee}
> 총 {count}건

---

## {KEY}: {summary}

- **상태**: {status}
- **담당자**: {assignee}
- **우선순위**: {priority}
- **타입**: {issuetype}

{description}

---
```

### 2.2 비기능 요구사항

| 항목 | 요건 |
|------|------|
| **보안** | `JIRA_API_TOKEN`은 환경변수로만 관리, 로그·파일에 절대 기록 안 함 |
| **에러 처리** | 인증 실패(401), 권한 없음(403), 프로젝트 없음(404) 각각 명확한 메시지 |
| **성능** | 기본 50건 조회 시 5초 이내 |
| **테스트** | `tests/test_jira.py` — mocked httpx 기반 단위 테스트, 커버리지 ≥80% |
| **호환성** | Jira Cloud REST API v3 기준 (v2 fallback 고려) |

---

## 3. 아키텍처 개요

### 3.1 파일 구조

```
locky-agent/
├── actions/
│   └── jira.py              # NEW: run_list(), run_create(), run_status()
├── tools/
│   └── jira_client.py       # NEW: JiraClient (httpx 기반 REST API 래퍼)
├── locky_cli/
│   └── main.py              # MODIFY: jira 서브커맨드 그룹 등록
├── config.py                # MODIFY: JIRA_BASE_URL, JIRA_EMAIL 추가
├── tests/
│   └── test_jira.py         # NEW: 단위 테스트
└── requirements.txt         # MODIFY: httpx 이미 있으면 추가 없음
```

### 3.2 의존성

- **httpx**: 이미 사용 중 (Ollama 클라이언트) — 추가 의존성 없음
- **Jira REST API v3**: `https://{domain}.atlassian.net/rest/api/3/`
- **인증**: Basic Auth (`email:api_token` base64 인코딩)

### 3.3 모듈 설계

```python
# tools/jira_client.py
class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str): ...
    def search_issues(self, jql: str, max_results: int = 50) -> list[dict]: ...
    def create_issue(self, project: str, summary: str, **opts) -> dict: ...
    def get_projects(self) -> list[dict]: ...
    def health_check(self) -> bool: ...

# actions/jira.py
def run_list(root: Path, **opts) -> dict: ...
def run_create(root: Path, **opts) -> dict: ...
def run_status(root: Path, **opts) -> dict: ...
```

---

## 4. 구현 계획

### 4.1 단계별 구현 순서

1. **config.py 확장** — `JIRA_BASE_URL`, `JIRA_EMAIL` 환경변수 추가
2. **tools/jira_client.py** — `JiraClient` 클래스, Basic Auth, search/create/health
3. **actions/jira.py** — `run_list()`, `run_create()`, `run_status()`, `.md` 렌더러
4. **locky_cli/main.py** — `@main.group('jira')` + `list`, `create`, `status` 서브커맨드
5. **tests/test_jira.py** — mocked httpx 단위 테스트 (≥20개)
6. **문서** — README 업데이트 (jira 섹션 추가)

### 4.2 .md 저장 경로

```
{root}/.locky/jira/
  2026-03-25-MYPROJ.md
  2026-03-25-MYPROJ-2.md  ← 같은 날 중복 시 suffix
```

---

## 5. 리스크 및 대응

| 리스크 | 가능성 | 영향 | 대응 |
|--------|--------|------|------|
| API Token 환경변수 미설정 | 높음 | 차단 | 명확한 에러 메시지 + 설정 가이드 출력 |
| Jira Cloud vs Server API 차이 | 중간 | 부분 | v3 우선, 에러 시 v2 엔드포인트 fallback |
| description 필드 ADF 포맷 | 중간 | 중간 | ADF → plain text 변환 유틸 작성 |
| 네트워크 타임아웃 | 낮음 | 중간 | httpx timeout=30s, 명확한 에러 메시지 |
| 대용량 이슈(100+) 페이지네이션 | 낮음 | 낮음 | --max 옵션으로 제한, 페이지네이션은 v2에서 고려 |

---

## 6. 성공 기준

| 기준 | 측정 방법 |
|------|----------|
| `locky jira list --project PROJ` 실행 시 .md 파일 생성 | 수동 테스트 |
| `locky jira create --project PROJ --summary "..."` 실행 시 Jira 이슈 생성 | Jira UI 확인 |
| `locky jira status` 연결 상태 출력 | 수동 테스트 |
| 단위 테스트 ≥20개, 커버리지 ≥80% | `pytest --cov` |
| 인증 실패 시 명확한 에러 메시지 | 수동 테스트 |
| API Token이 로그/파일에 노출되지 않음 | 코드 리뷰 |

---

## 7. 참고

- [Jira REST API v3 공식 문서](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [Jira API Token 생성](https://id.atlassian.com/manage-profile/security/api-tokens)
- 기존 `tools/ollama_client.py` — httpx 사용 패턴 참고
- 기존 `actions/todo_collector.py` — .md 파일 저장 패턴 참고
