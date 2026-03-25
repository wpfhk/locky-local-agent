# Design: jira-integration

> **Feature**: jira-integration
> **Created**: 2026-03-25
> **Architecture**: Option B — Clean Architecture
> **Status**: Design Complete

---

## Context Anchor

| 항목 | 내용 |
|------|------|
| **WHY** | 개발자 워크플로 자동화 툴에서 Jira 이슈 조회·생성을 CLI로 처리해 컨텍스트 전환 제거 |
| **WHO** | locky를 사용하는 개발자 — Jira를 주 이슈 트래커로 사용하고 터미널 중심 워크플로를 선호 |
| **RISK** | Jira API Token 노출, ADF description 파싱, Jira Cloud vs Server API 차이 |
| **SUCCESS** | `locky jira list` .md 생성 + `locky jira create` 이슈 생성 + 테스트 ≥20개 |
| **SCOPE** | 조회+저장+생성; JQL 직접입력·수정·코멘트 제외 |

---

## 1. 아키텍처 개요

### 선택: Option B — Clean Architecture

기존 `tools/ollama_client.py` → `actions/commit.py` 패턴과 동일.

```
tools/jira_client.py        ← Jira REST API 래퍼 (httpx 기반)
actions/jira.py             ← 비즈니스 로직 + .md 렌더링 (run_list/run_create/run_status)
locky_cli/main.py           ← Click CLI 그룹 등록 (jira group)
config.py                   ← JIRA_BASE_URL, JIRA_EMAIL 환경변수 로딩
tests/test_jira.py          ← mocked httpx 단위 테스트
```

---

## 2. 파일 설계

### 2.1 `tools/jira_client.py` (신규)

```python
class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str, timeout: int = 30)

    def search_issues(self, jql: str, max_results: int = 50) -> list[dict]
    # GET /rest/api/3/search?jql={jql}&maxResults={max}
    # 반환: [{"key": "PROJ-1", "summary": ..., "status": ..., "assignee": ..., "description": ...}]

    def create_issue(self, project: str, summary: str, description: str = "",
                     issue_type: str = "Task", priority: str = "Medium") -> dict
    # POST /rest/api/3/issue
    # 반환: {"key": "PROJ-2", "id": "12345", "url": "..."}

    def get_projects(self) -> list[dict]
    # GET /rest/api/3/project
    # 반환: [{"key": "PROJ", "name": "..."}]

    def health_check(self) -> bool
    # GET /rest/api/3/myself

    @staticmethod
    def _adf_to_text(adf: dict | None) -> str
    # Atlassian Document Format → plain text 변환
```

**인증**: `Authorization: Basic base64(email:api_token)`

**에러 코드 처리**:
| 코드 | 의미 | 메시지 |
|------|------|--------|
| 401 | 인증 실패 | "Jira 인증 실패: JIRA_API_TOKEN 또는 JIRA_EMAIL을 확인하세요." |
| 403 | 권한 없음 | "Jira 권한 없음: 해당 프로젝트 접근 권한이 없습니다." |
| 404 | 프로젝트 없음 | "Jira 프로젝트를 찾을 수 없습니다: {project}" |

### 2.2 `actions/jira.py` (신규)

세 함수 모두 `run(root, **opts) -> dict` 패턴 준수:

```python
def run_list(root: Path, project: str = "", status: str = "",
             assignee: str = "", max_results: int = 50,
             output_file: str | None = None, no_save: bool = False) -> dict
# 반환:
# {"status": "ok"|"error", "count": int, "saved_to": str|None, "issues": [...]}

def run_create(root: Path, project: str, summary: str,
               description: str = "", issue_type: str = "Task",
               priority: str = "Medium", dry_run: bool = False) -> dict
# 반환:
# {"status": "ok"|"dry_run"|"error", "key": str|None, "url": str|None, "message": str}

def run_status(root: Path) -> dict
# 반환:
# {"status": "ok"|"error", "url": str, "user": str, "projects": int}
```

**JQL 빌더** (내부 함수):
```python
def _build_jql(project: str, status: str, assignee: str) -> str:
    # "project = PROJ AND status = 'In Progress' AND assignee = currentUser()"
```

**저장 경로 로직**:
```python
def _resolve_output(root: Path, project: str, output_file: str | None) -> Path:
    # .locky/jira/{date}-{project}.md
    # 중복 시 suffix: {date}-{project}-2.md
```

**.md 렌더러**:
```python
def _render_md(issues: list[dict], project: str, filters: dict) -> str:
    # "# Jira Issues — {PROJECT} ({date})" + 이슈별 섹션
```

### 2.3 `locky_cli/main.py` 수정

```python
@cli.group("jira")
def jira_grp(): """Jira 이슈 관리."""

@jira_grp.command("list")
@click.option("--project", "-p", default="")
@click.option("--status", "-s", "status_filter", default="")
@click.option("--assignee", "-a", default="")
@click.option("--max", "max_results", default=50, type=int)
@click.option("--output", default=None)
@click.option("--no-save", is_flag=True)
def jira_list_cmd(...): ...

@jira_grp.command("create")
@click.option("--project", "-p", required=True)
@click.option("--summary", required=True)
@click.option("--description", "-d", default="")
@click.option("--type", "issue_type", default="Task")
@click.option("--priority", default="Medium")
@click.option("--dry-run", is_flag=True)
def jira_create_cmd(...): ...

@jira_grp.command("status")
def jira_status_cmd(): ...
```

### 2.4 `config.py` 수정

```python
# Jira 설정
JIRA_BASE_URL = _cfg("JIRA_BASE_URL", ["jira", "base_url"], "")
JIRA_EMAIL = _cfg("JIRA_EMAIL", ["jira", "email"], "")
# JIRA_API_TOKEN: 환경변수 전용 (config.yaml에 저장 금지)
```

---

## 3. 데이터 흐름

```
사용자: locky jira list --project MYPROJ --status "In Progress"
         │
         ▼
locky_cli/main.py (jira_list_cmd)
         │ _get_root()
         │ _maybe_refresh_profile()
         ▼
actions/jira.py (run_list)
         │ _get_jira_client(root)  ← config.py + os.getenv("JIRA_API_TOKEN")
         │ _build_jql(project, status, assignee)
         ▼
tools/jira_client.py (search_issues)
         │ GET /rest/api/3/search?jql=...
         │ httpx.Client.get()
         ▼
Jira Cloud REST API
         │ JSON 응답
         ▼
actions/jira.py
         │ _parse_issues(raw)     ← fields 추출 + ADF→text
         │ _render_md(issues, ...)
         │ _resolve_output(root, project, output_file)
         │ Path.write_text(md_content)
         ▼
locky_cli/main.py
         │ _print_result(console, result)
         ▼
사용자: Rich Panel 출력 + .locky/jira/2026-03-25-MYPROJ.md 저장
```

---

## 4. 테스트 설계 (`tests/test_jira.py`)

| 테스트 | 설명 |
|--------|------|
| `test_list_basic` | project 필터로 이슈 2건 반환, .md 저장 확인 |
| `test_list_no_save` | `--no-save` 시 파일 미생성 확인 |
| `test_list_empty_result` | 0건일 때 `"status": "ok"`, `"count": 0` |
| `test_list_auth_error` | 401 응답 시 에러 메시지 확인 |
| `test_list_jql_build` | project+status+assignee 조합 JQL 검증 |
| `test_create_basic` | `--dry-run` False, 이슈 생성 성공 |
| `test_create_dry_run` | `--dry-run` True, API 호출 없음 확인 |
| `test_create_missing_project` | project 없을 때 에러 |
| `test_status_ok` | health_check 성공 |
| `test_status_error` | 연결 실패 시 에러 |
| `test_adf_to_text_paragraph` | ADF paragraph → 텍스트 변환 |
| `test_adf_to_text_none` | None 입력 시 빈 문자열 |
| `test_md_render_format` | .md 파일 헤더/섹션 구조 확인 |
| `test_output_path_default` | `.locky/jira/{date}-{project}.md` 경로 |
| `test_output_path_conflict` | 중복 시 suffix 추가 |
| `test_config_missing_token` | JIRA_API_TOKEN 미설정 시 에러 |
| `test_jira_client_search` | mocked HTTP 정상 응답 파싱 |
| `test_jira_client_create` | mocked POST 응답 key 반환 |
| `test_jira_client_health_ok` | /myself 200 → True |
| `test_jira_client_health_fail` | 연결 실패 → False |

---

## 5. 보안 설계

1. `JIRA_API_TOKEN`은 `os.getenv()` 전용 — `config.yaml` 키에 없음
2. `_get_jira_client()` 내부에서 token 없으면 즉시 raise (로그에 값 출력 금지)
3. `_print_result()` 호출 전 result dict에서 token 키 제거
4. httpx Basic Auth → Authorization 헤더에만 존재, 로그 미출력

---

## 6. 구현 가이드 (Session Guide)

### Module Map

| 모듈 | 파일 | 우선순위 |
|------|------|--------|
| M1: JiraClient | `tools/jira_client.py` | 1 |
| M2: actions | `actions/jira.py` | 2 |
| M3: config | `config.py` | 2 (병렬) |
| M4: CLI | `locky_cli/main.py` | 3 |
| M5: tests | `tests/test_jira.py` | 4 |

### 구현 순서

```
M1 → (M2 + M3 병렬) → M4 → M5
```

1. `tools/jira_client.py` — JiraClient 클래스
2. `config.py` — JIRA_BASE_URL, JIRA_EMAIL 추가
3. `actions/jira.py` — run_list, run_create, run_status
4. `locky_cli/main.py` — jira group + 3 서브커맨드 등록
5. `tests/test_jira.py` — 20개 테스트
