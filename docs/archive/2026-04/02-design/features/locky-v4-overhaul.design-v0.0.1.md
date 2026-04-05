# locky-v4-overhaul Design Document

> **Summary**: v4 전면 리라이트 -- shell_command 하나만 남기고 나머지 전부 제거
>
> **Project**: locky-agent
> **Version**: 4.0.0
> **Date**: 2026-03-26
> **Status**: Approved
> **Planning Doc**: [locky-v4-overhaul.plan-v0.0.1.md](../01-plan/features/locky-v4-overhaul.plan-v0.0.1.md)

---

## Context Anchor

| Key | Value |
|-----|-------|
| **WHY** | v3 복잡도 폭증으로 핵심 기능이 깨짐. 단순함이 신뢰성을 만든다. |
| **WHO** | 터미널에서 자연어로 셸 명령을 빠르게 실행하고 싶은 개발자 |
| **RISK** | Ollama 모델 품질 의존성 -- 나쁜 모델은 여전히 잘못된 명령 생성 가능 |
| **SUCCESS** | 자연어 입력 시 유효한 셸 명령 생성률 >= 95%, Python/의사코드 출력 0건 |
| **SCOPE** | REPL + shell_command action 만 유지, 나머지 전부 제거 |

---

## 1. Architecture: Pragmatic Balance (Option C)

v4는 단 하나의 기능에 집중하므로, 과도한 추상화 없이 최소한의 파일만 유지합니다.

### 1.1 Target Structure

```
locky-agent/
├── locky_cli/
│   ├── __init__.py       # 패키지 마커
│   ├── main.py           # Click CLI (REPL 진입점만)
│   └── repl.py           # REPL 루프 (자연어 -> shell_command -> 확인 -> 실행)
├── actions/
│   ├── __init__.py       # shell_command만 export
│   └── shell_command.py  # 핵심: 자연어 -> 셸 명령 변환
├── tools/
│   ├── __init__.py       # OllamaClient만 export
│   ├── ollama_client.py  # Ollama HTTP 클라이언트
│   └── ollama_guard.py   # Ollama 헬스체크 + 자동 시작
├── config.py             # 환경변수 기반 단순 설정 (3개 변수)
├── tests/
│   ├── __init__.py
│   ├── conftest.py       # pytest 공통 픽스처
│   └── test_shell_command.py  # 핵심 테스트
├── requirements.txt
└── pyproject.toml
```

### 1.2 Dependency Graph

```
locky_cli/main.py
  └── locky_cli/repl.py
        └── actions/shell_command.py
              ├── tools/ollama_guard.py
              ├── tools/ollama_client.py (indirect via config)
              └── config.py (OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT)
```

---

## 2. Deletion Plan

### 2.1 Directories to Remove (rm -rf)

| Directory | Reason |
|-----------|--------|
| `locky/` | 레거시 agents/core/runtime/tools |
| `tools/llm/` | 멀티 LLM 레지스트리 -- Ollama 직접 호출로 대체 |
| `tools/mcp/` | MCP 서버/클라이언트 |
| `tools/plugins/` | 플러그인 시스템 |
| `tools/recipes/` | 레시피 실행기 |
| `tools/sandbox/` | 샌드박스 |
| `tools/session/` | 세션 관리 |
| `agents/` | 레거시 에이전트 |
| `states/` | 레거시 상태 |
| `pipeline/` | 파이프라인 (존재하지 않으면 skip) |
| `ui/` | Chainlit + TUI |

### 2.2 Files to Remove

| File | Reason |
|------|--------|
| `actions/commit.py` | v4 범위 외 |
| `actions/format_code.py` | v4 범위 외 |
| `actions/hook.py` | v4 범위 외 |
| `actions/pipeline.py` | v4 범위 외 |
| `actions/test_runner.py` | v4 범위 외 |
| `actions/todo_collector.py` | v4 범위 외 |
| `actions/security_scan.py` | v4 범위 외 |
| `actions/cleanup.py` | v4 범위 외 |
| `actions/deps_check.py` | v4 범위 외 |
| `actions/env_template.py` | v4 범위 외 |
| `actions/update.py` | v4 범위 외 |
| `actions/jira.py` | v4 범위 외 |
| `tools/mcp_filesystem.py` | 불필요 |
| `tools/mcp_git.py` | 불필요 |
| `tools/repo_map.py` | 불필요 |
| `tools/jira_client.py` | 불필요 |
| `locky_cli/config_loader.py` | 복잡한 설정 체계 -- 환경변수로 대체 |
| `locky_cli/context.py` | 언어 감지 프로파일 -- 불필요 |
| `locky_cli/lang_detect.py` | 언어 감지 -- 불필요 |
| `locky_cli/fs_context.py` | MCP 루트 관리 -- 불필요 |
| `locky_cli/permissions.py` | 권한 모드 -- 불필요 |
| `cli.py` | 호환 진입점 -- 불필요 |
| `graph.py` | 미사용 shim (존재하지 않으면 skip) |

### 2.3 Test Files to Remove

모든 테스트 파일 삭제 (test_shell_command.py 제외):
- `test_agents_ask.py`, `test_agents_edit.py`
- `test_cleanup.py`, `test_cli_commands.py`, `test_cli_v2_commands.py`, `test_cli_v3_commands.py`
- `test_config_loader.py`, `test_config_loader_v3p2.py`
- `test_context.py`, `test_core_agent.py`, `test_core_context.py`, `test_core_session.py`
- `test_deps_check.py`, `test_env_template.py`, `test_format_code.py`
- `test_hook.py`, `test_jira.py`, `test_lang_detect.py`
- `test_llm_*.py` (8개), `test_mcp_*.py` (3개)
- `test_ollama_guard.py`, `test_ollama_stream.py`
- `test_pipeline.py`, `test_plugin_*.py` (3개)
- `test_recipe_*.py` (2개), `test_repo_map.py`
- `test_runtime_local.py`, `test_sandbox.py`
- `test_security_scan.py`, `test_session_*.py` (2개)
- `test_test_runner.py`, `test_todo_collector.py`
- `test_tools_base.py`, `test_tools_file.py`, `test_tools_format.py`, `test_tools_git.py`
- `test_tools_zero_coverage.py`, `test_tui.py`, `test_update.py`

---

## 3. shell_command.py Bug Fix Design

### 3.1 Problem

Ollama가 Python 코드(`import os`)를 셸 명령으로 출력. `_is_valid_command`가 이를 통과시킴.

### 3.2 Solution

**A. 프롬프트 강화**:
- Few-shot 예시 추가 (good examples + bad examples)
- "NEVER output programming language code" 명시
- 코드 작성 요청 거부 지시 추가
- temperature=0, num_predict=80 (legacy fallback에서 이미 적용, LLM Registry 경로에도 적용)

**B. _is_valid_command 검증 강화**:
```python
_CODE_KEYWORDS = {"import ", "from ", "class ", "def ", "function ", "const ", "let ", "var ", "print(", "console.log("}

def _is_valid_command(cmd: str) -> bool:
    # 기존 검증 유지
    if not cmd: return False
    if re.search(r"[가-힣ㄱ-ㅎㅏ-ㅣ]", cmd): return False
    if not re.match(r"^[a-zA-Z./~$_(]", cmd): return False
    # NEW: 프로그래밍 언어 코드 감지
    cmd_lower = cmd.lower()
    for kw in _CODE_KEYWORDS:
        if cmd_lower.startswith(kw):
            return False
    return True
```

**C. LLM Registry 제거**: shell_command.py에서 `tools.llm.registry` 의존 제거. Ollama 직접 호출만 사용.

### 3.3 Prompt Design

```
You are a shell command generator for macOS/Linux.
Output ONLY a single executable shell command.
No explanations, no markdown, no code blocks.

RULES:
1. Output must be a valid shell command (bash/zsh/sh)
2. NEVER output programming language code (Python, JavaScript, etc.)
3. If the user asks to "write code" or "implement a program", output: echo 'Use a code editor for programming tasks'
4. If truly impossible, output: echo 'cannot determine command'

EXAMPLES:
User: 현재 디렉토리의 파일 목록을 보여줘
Output: ls -la

User: app.aab를 연결된 기기에 설치해줘
Output: adb install app.aab

User: 파이썬 프로그램을 만들어줘
Output: echo 'Use a code editor for programming tasks'

User: git 로그를 보여줘
Output: git log --oneline -20
```

---

## 4. Module Changes

### 4.1 config.py (Rewrite)

- `fs_context` 의존 제거
- `config_loader` 의존 제거
- 환경변수 3개만 (OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT)
- Jira, pipeline 설정 제거

### 4.2 locky_cli/main.py (Rewrite)

- Click 그룹 -> 단순 Click 커맨드 1개 (REPL 진입)
- 모든 sub-command 제거
- `_print_result`, `_maybe_refresh_profile`, `_load_plugins` 제거
- `_human_size` 제거

### 4.3 locky_cli/repl.py (Simplify)

- `permissions` import 제거 -> 직접 Path.cwd() 사용
- `config_loader`, `context` import 제거
- 슬래시 명령 전부 제거 (commit/format/test/todo/scan/clean/deps/env/update/ask/edit)
- help_text 단순화
- `_banner()` 단순화 (config_loader 없이)
- `/help`, `/clear`, `/exit` 만 유지

### 4.4 actions/__init__.py (Rewrite)

- `shell_command`만 export

### 4.5 tools/__init__.py (Rewrite)

- `OllamaClient`만 export

### 4.6 pyproject.toml (Update)

- version: 4.0.0
- description 변경
- dependencies 최소화 (httpx, click, rich, prompt-toolkit)
- setuptools packages: actions, tools, locky_cli만
- pytest coverage 대상 축소
- optional-dependencies 제거

### 4.7 requirements.txt (Rewrite)

- httpx, click, rich, prompt-toolkit만

---

## 5. Implementation Order

| Step | Task | Files | Dependency |
|------|------|-------|------------|
| 1 | 디렉터리 삭제 | locky/, tools/llm/ 등 | None |
| 2 | 파일 삭제 | actions/*.py, tests/*.py 등 | Step 1 |
| 3 | shell_command.py 버그 수정 | actions/shell_command.py | Step 2 |
| 4 | config.py 단순화 | config.py | Step 2 |
| 5 | actions/__init__.py 재작성 | actions/__init__.py | Step 2 |
| 6 | tools/__init__.py 재작성 | tools/__init__.py | Step 1 |
| 7 | repl.py 단순화 | locky_cli/repl.py | Step 2 |
| 8 | main.py 단순화 | locky_cli/main.py | Step 7 |
| 9 | pyproject.toml + requirements.txt | pyproject.toml, requirements.txt | Step 2 |
| 10 | 테스트 보강 + 실행 | tests/test_shell_command.py | Step 3 |

---

## 11. Implementation Guide

### 11.1 Module Map

| Module | Key | Scope |
|--------|-----|-------|
| Deletion | module-1 | 불필요 파일/디렉터리 전부 삭제 |
| shell_command fix | module-2 | 프롬프트 강화 + 검증 로직 + LLM Registry 제거 |
| Core simplification | module-3 | config.py + main.py + repl.py + __init__.py 단순화 |
| Packaging | module-4 | pyproject.toml + requirements.txt 정리 |
| Testing | module-5 | 테스트 보강 + 전체 통과 확인 |

### 11.2 Session Guide

단일 세션으로 충분 (총 변경량 ~500줄 미만).
