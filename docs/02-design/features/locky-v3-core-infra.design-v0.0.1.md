# locky-v3-core-infra Design Document

> **Summary**: Multi-provider LLM, MCP stdio client, Repo Map -- Phase 1 핵심 인프라 설계
>
> **Project**: locky-agent
> **Version**: 2.0.0 -> 3.0.0
> **Author**: CTO Lead (PDCA)
> **Date**: 2026-03-26
> **Status**: Draft
> **Planning Doc**: [locky-v3-core-infra.plan-v0.0.1.md](../../01-plan/features/locky-v3-core-infra.plan-v0.0.1.md)

---

## Context Anchor

| Key | Value |
|-----|-------|
| **WHY** | Ollama-only, MCP 미지원, repo-map 부재로 확장성 한계 |
| **WHO** | Locky CLI 사용자 (개발자), 다양한 LLM 프로바이더 사용자 |
| **RISK** | 기존 351개 테스트 회귀, config.yaml 하위 호환성 깨짐, 외부 의존성 증가 |
| **SUCCESS** | 3+ LLM 프로바이더 동작, MCP stdio 서버 연결 성공, repo-map 생성/쿼리 동작, 기존 테스트 100% 통과 |
| **SCOPE** | Phase 1만: LLM 추상화 + MCP stdio client + Repo Map. 세션/스트리밍/UI/샌드박스 제외 |

---

## 1. Overview

### 1.1 Design Goals

1. **모델 독립성**: Ollama/OpenAI/Anthropic 프로바이더를 단일 인터페이스로 추상화
2. **MCP 확장성**: 외부 MCP 서버를 도구로 등록하여 Locky 기능 확장
3. **컨텍스트 품질**: Repo Map으로 코드베이스 구조 인식
4. **하위 호환**: 기존 CLI 동작, config.yaml, 테스트 100% 유지
5. **최소 침습**: 기존 actions/ 아키텍처 변경 없이 tools/ 계층에서 추상화

### 1.2 Design Principles

- **Interface Segregation**: `BaseLLMClient` ABC로 프로바이더 간 계약 정의
- **Open/Closed**: 새 프로바이더는 새 파일 추가만으로 등록 가능
- **Dependency Inversion**: actions/ 모듈은 구체 클라이언트가 아닌 Registry를 통해 LLM 접근
- **Backward Compatibility**: 환경변수/config 없으면 Ollama 기본값으로 fallback
- **Optional Dependencies**: litellm, openai, anthropic SDK는 optional import

---

## 2. Architecture Options

### 2.0 Architecture Comparison

| Criteria | Option A: Minimal | Option B: Clean | Option C: Pragmatic |
|----------|:-:|:-:|:-:|
| **Approach** | OllamaClient에 if/else 분기 추가 | 완전한 DI 컨테이너 + 인터페이스 분리 | ABC + Registry 패턴, 적절한 추상화 |
| **New Files** | 3 | 15+ | 10 |
| **Modified Files** | 3 | 8+ | 4 |
| **Complexity** | Low | High | Medium |
| **Maintainability** | Low (분기 누적) | High | High |
| **Effort** | 1일 | 5일 | 3일 |
| **Risk** | Medium (확장 어려움) | Low (과설계 가능) | Low |
| **Recommendation** | 긴급 패치만 | 대규모 장기 프로젝트 | **Phase 1에 적합** |

**Selected**: **Option C (Pragmatic Balance)**

**Rationale**: Locky는 CLI 도구로 DI 컨테이너까지는 과설계이나, if/else 분기 추가는 유지보수 부담. ABC + Registry 팩토리 패턴이 적절한 추상화와 확장성을 제공하며 기존 코드 변경을 최소화.

### 2.1 Component Diagram

```
┌──────────────────────────────────────────────────────────┐
│                     locky CLI (Click)                     │
│                    locky_cli/main.py                      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  actions/    │  │  actions/     │  │ actions/       │  │
│  │  commit.py   │  │  shell_cmd.py│  │ pipeline.py    │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────────┘  │
│         │                 │                               │
│         ▼                 ▼                               │
│  ┌──────────────────────────────┐                        │
│  │     tools/llm/registry.py    │ ◀── get_llm_client()   │
│  │         LLMRegistry          │                        │
│  └──────┬───────┬───────┬───────┘                        │
│         │       │       │                                │
│    ┌────▼──┐ ┌──▼───┐ ┌─▼────────┐  ┌──────────────┐   │
│    │Ollama │ │OpenAI│ │Anthropic │  │LiteLLM (opt) │   │
│    │Client │ │Client│ │Client    │  │Adapter       │   │
│    └───────┘ └──────┘ └──────────┘  └──────────────┘   │
│         ▲                                                │
│         │                                                │
│  ┌──────┴───────┐                                        │
│  │ ollama_guard  │  (Ollama 전용 헬스체크, 기존 유지)     │
│  └──────────────┘                                        │
│                                                          │
│  ┌──────────────────────────────┐                        │
│  │     tools/mcp/registry.py    │ ◀── get_mcp_tools()    │
│  │         MCPRegistry          │                        │
│  └──────┬───────────────────────┘                        │
│         │                                                │
│    ┌────▼──────────────┐                                 │
│    │ tools/mcp/client.py│  stdio JSON-RPC                │
│    │   MCPClient        │                                │
│    └────────────────────┘                                │
│                                                          │
│  ┌──────────────────────────────┐                        │
│  │     tools/repo_map.py        │ ◀── build/get_context  │
│  │         RepoMap              │                        │
│  └──────────────────────────────┘                        │
│                                                          │
│  ┌──────────────────────────────┐                        │
│  │  locky_cli/config_loader.py  │ ◀── load llm/mcp cfg  │
│  │  .locky/config.yaml          │                        │
│  └──────────────────────────────┘                        │
└──────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
1. LLM 호출 흐름:
   User CLI → actions/commit.py → LLMRegistry.get_client()
     → config_loader.load_config() → detect provider
     → OllamaLLMClient / OpenAILLMClient / AnthropicLLMClient
     → .chat(messages, system) → response string

2. MCP 도구 호출 흐름:
   Config → MCPRegistry.load_servers() → MCPClient(command, args)
     → subprocess.Popen(stdio) → JSON-RPC initialize
     → tools/list → tools/call → response

3. Repo Map 흐름:
   RepoMap.build(root) → git ls-files → filter .py/.js/.ts
     → ast.parse (Python) / regex (JS/TS)
     → {file: {functions, classes, imports}}
     → cache to .locky/repo-map.json
   RepoMap.get_context(query) → search map → return relevant entries
```

### 2.3 Dependencies

| Component | Depends On | Purpose |
|-----------|-----------|---------|
| `LLMRegistry` | `config_loader`, `BaseLLMClient` subclasses | 프로바이더 선택 + 인스턴스 생성 |
| `OllamaLLMClient` | `httpx`, `ollama_guard` | Ollama API 호출 |
| `OpenAILLMClient` | `httpx` (또는 optional `openai` SDK) | OpenAI API 호출 |
| `AnthropicLLMClient` | `httpx` (또는 optional `anthropic` SDK) | Anthropic API 호출 |
| `LiteLLMAdapter` | optional `litellm` | 75+ 프로바이더 통합 |
| `MCPClient` | `subprocess`, `json` (stdlib) | MCP 서버 stdio 통신 |
| `MCPRegistry` | `config_loader`, `MCPClient` | MCP 서버 목록 관리 |
| `RepoMap` | `ast` (stdlib), `subprocess` (git) | 코드 구조 인덱싱 |
| `commit.py` | `LLMRegistry` (신규) | 커밋 메시지 생성 |

---

## 3. Data Model

### 3.1 LLM Configuration Schema

```python
# .locky/config.yaml의 llm 섹션
@dataclass
class LLMConfig:
    provider: str = "ollama"       # ollama | openai | anthropic | litellm
    model: str = "qwen2.5-coder:7b"
    api_key_env: str | None = None # 환경변수 이름 (값 아님)
    base_url: str | None = None    # 커스텀 엔드포인트 (OpenRouter 등)
    timeout: int = 300
```

### 3.2 MCP Server Configuration Schema

```python
@dataclass
class MCPServerConfig:
    name: str                      # 서버 식별자
    command: list[str]             # 실행 명령어 ["npx", "@mcp/server-fs", "/path"]
    env: dict[str, str] | None = None  # 환경변수 (${VAR} 치환 지원)
    timeout: int = 30             # 초기화 타임아웃
```

### 3.3 Repo Map Cache Schema

```json
{
  "version": 1,
  "git_hash": "abc123...",
  "generated_at": "2026-03-26T10:00:00Z",
  "files": {
    "actions/commit.py": {
      "functions": ["run", "_generate_commit_message"],
      "classes": [],
      "imports": ["subprocess", "pathlib.Path"]
    },
    "tools/ollama_client.py": {
      "functions": [],
      "classes": ["OllamaClient"],
      "imports": ["httpx"]
    }
  }
}
```

### 3.4 Config YAML Schema (확장)

```yaml
# .locky/config.yaml -- Phase 1 확장 스키마
# 기존 섹션 (하위 호환)
ollama:
  model: qwen2.5-coder:7b
  base_url: http://localhost:11434
  timeout: 300

# 신규 섹션 (Phase 1)
llm:
  provider: ollama            # ollama | openai | anthropic | litellm
  model: qwen2.5-coder:7b
  api_key_env: null           # OPENAI_API_KEY, ANTHROPIC_API_KEY 등
  base_url: null              # 커스텀 엔드포인트 (null이면 프로바이더 기본값)
  timeout: 300

mcp_servers:
  - name: filesystem
    command: ["npx", "@modelcontextprotocol/server-filesystem", "/path"]
  - name: github
    command: ["npx", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_TOKEN: ${GITHUB_TOKEN}

# 기존 섹션 (유지)
hook:
  steps: [format, test, scan]

init:
  auto_profile: true

jira:
  base_url: ""
  email: ""
```

**Config 우선순위**:
1. `llm` 섹션이 있으면 `llm` 사용
2. `llm` 섹션이 없고 `ollama` 섹션이 있으면 Ollama로 fallback
3. 둘 다 없으면 환경변수 (`OLLAMA_*`) → 기본값

---

## 4. API Specification

### 4.1 BaseLLMClient Interface

```python
# tools/llm/base.py
from abc import ABC, abstractmethod
from typing import Generator
from dataclasses import dataclass

@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    usage: dict | None = None  # {"prompt_tokens": N, "completion_tokens": N}

class LLMError(Exception):
    """LLM 호출 실패 시 발생하는 기본 예외."""
    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message)
        self.provider = provider

class BaseLLMClient(ABC):
    """모든 LLM 프로바이더가 구현해야 하는 인터페이스."""

    @abstractmethod
    def chat(self, messages: list[dict], system: str = "") -> LLMResponse:
        """동기 채팅 호출. messages = [{"role": "user", "content": "..."}]"""
        ...

    @abstractmethod
    def stream(self, messages: list[dict], system: str = "") -> Generator[str, None, None]:
        """동기 스트리밍. 토큰별 yield."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """프로바이더 연결 상태 확인."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """프로바이더 식별자 (예: 'ollama', 'openai')."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """현재 사용 중인 모델명."""
        ...
```

### 4.2 LLMRegistry Interface

```python
# tools/llm/registry.py
class LLMRegistry:
    """프로바이더 레지스트리 + 팩토리."""

    @staticmethod
    def get_client(root: Path | None = None) -> BaseLLMClient:
        """config.yaml / 환경변수 기반으로 적절한 LLM 클라이언트 반환.

        우선순위:
        1. config.yaml llm 섹션
        2. config.yaml ollama 섹션 (하위 호환)
        3. OLLAMA_* 환경변수
        4. 기본값 (Ollama, qwen2.5-coder:7b)
        """
        ...

    @staticmethod
    def get_client_by_provider(
        provider: str,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 300,
    ) -> BaseLLMClient:
        """명시적 프로바이더/모델 지정으로 클라이언트 생성."""
        ...

    @staticmethod
    def list_providers() -> list[str]:
        """사용 가능한 프로바이더 목록 (설치된 것만)."""
        ...
```

### 4.3 MCPClient Interface

```python
# tools/mcp/client.py
@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict

class MCPClient:
    """stdio 기반 MCP 클라이언트. 하나의 MCP 서버 프로세스를 관리."""

    def __init__(self, name: str, command: list[str], env: dict | None = None, timeout: int = 30):
        ...

    def start(self) -> None:
        """MCP 서버 프로세스 시작 + initialize 핸드셰이크."""
        ...

    def stop(self) -> None:
        """MCP 서버 프로세스 종료."""
        ...

    def list_tools(self) -> list[MCPTool]:
        """tools/list 호출로 도구 목록 조회."""
        ...

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """tools/call 호출로 도구 실행."""
        ...

    def __enter__(self): ...
    def __exit__(self, *args): ...
```

### 4.4 RepoMap Interface

```python
# tools/repo_map.py
class RepoMap:
    """코드베이스 구조 맵 생성기."""

    def __init__(self, root: Path):
        self.root = root
        self.cache_path = root / ".locky" / "repo-map.json"

    def build(self) -> dict:
        """전체 코드베이스 스캔 → 구조 맵 생성.
        Returns: {file_path: {functions: [...], classes: [...], imports: [...]}}
        """
        ...

    def get_context(self, query: str, max_tokens: int = 4000) -> str:
        """쿼리 관련 파일/함수만 선택하여 컨텍스트 문자열 반환."""
        ...

    def update_incremental(self, changed_files: list[str] | None = None) -> dict:
        """변경된 파일만 재파싱. changed_files가 None이면 git diff로 감지."""
        ...

    def _load_cache(self) -> dict | None:
        """캐시 로드. git hash 불일치 시 None 반환."""
        ...

    def _save_cache(self, data: dict) -> None:
        """캐시 저장."""
        ...

    def _get_git_hash(self) -> str:
        """현재 HEAD commit hash 반환."""
        ...

    def _parse_python(self, filepath: Path) -> dict:
        """Python AST로 함수/클래스/import 추출."""
        ...

    def _parse_generic(self, filepath: Path) -> dict:
        """정규식 기반 일반 파싱 (JS/TS 등)."""
        ...
```

---

## 5. UI/UX Design

N/A -- Phase 1은 CLI 백엔드 인프라만. UI 변경 없음.

기존 CLI 명령은 동일하게 동작:
```bash
locky commit [--dry-run]     # LLM Registry 통해 프로바이더 자동 선택
locky format                 # 변경 없음 (LLM 미사용)
locky scan                   # 변경 없음 (LLM 미사용)
```

---

## 6. Error Handling

### 6.1 LLM Error Hierarchy

```python
class LLMError(Exception):
    """기본 LLM 에러."""
    provider: str

class LLMConnectionError(LLMError):
    """프로바이더 서버 연결 실패."""

class LLMAuthError(LLMError):
    """API 키 인증 실패."""

class LLMModelNotFoundError(LLMError):
    """지정 모델 없음."""

class LLMTimeoutError(LLMError):
    """응답 타임아웃."""
```

### 6.2 Error Handling Strategy

| Scenario | Handling |
|----------|----------|
| config.yaml에 `llm` 섹션 없음 | `ollama` 섹션 또는 환경변수로 fallback → 기존 동작 유지 |
| OpenAI API 키 미설정 | `LLMAuthError` 발생 → "OPENAI_API_KEY 환경변수를 설정하세요" 안내 |
| Ollama 서버 미실행 | 기존 `ollama_guard.ensure_ollama()` 로직 유지 |
| MCP 서버 프로세스 시작 실패 | MCPError → 로그 + 해당 서버 건너뜀 |
| MCP 서버 타임아웃 | MCPTimeoutError → 프로세스 kill + 에러 반환 |
| litellm 미설치 | `ImportError` catch → "pip install locky-agent[litellm] 필요" 안내 |
| Repo Map 파싱 실패 (개별 파일) | 해당 파일 건너뜀 → 나머지 파일 계속 처리 |

---

## 7. Security Considerations

- [x] API 키를 config.yaml에 직접 저장 금지 → `api_key_env` 패턴 (환경변수 이름만 저장)
- [x] MCP 서버 프로세스 실행 시 config.yaml에 명시된 명령만 허용
- [x] MCP 서버 환경변수의 `${VAR}` 치환은 `os.environ.get()`으로만 처리 (shell injection 방지)
- [x] Repo Map은 `.locky/repo-map.json`에 로컬 캐시만 (네트워크 전송 없음)
- [ ] MCP 서버 실행 경로 검증 (Phase 2 -- 샌드박싱과 함께)

---

## 8. Test Plan

### 8.1 Test Scope

| Type | Target | Tool |
|------|--------|------|
| Unit Test | LLM clients (mock httpx) | pytest + monkeypatch |
| Unit Test | LLMRegistry (config 기반 선택) | pytest |
| Unit Test | MCPClient (mock subprocess) | pytest + monkeypatch |
| Unit Test | MCPRegistry (config 파싱) | pytest |
| Unit Test | RepoMap (build, get_context, cache) | pytest + tmp_path |
| Integration Test | commit.py + LLMRegistry | pytest (기존 테스트 확장) |
| Regression Test | 기존 351개 테스트 전체 | pytest |

### 8.2 Test Cases (Key)

**LLM Tests**:
- [x] `test_ollama_client_chat` -- OllamaLLMClient.chat() 정상 응답
- [x] `test_ollama_client_stream` -- 스트리밍 토큰 yield
- [x] `test_ollama_client_health_check` -- 헬스체크 True/False
- [x] `test_openai_client_chat` -- OpenAI API mock 응답
- [x] `test_openai_auth_error` -- API 키 없을 때 LLMAuthError
- [x] `test_anthropic_client_chat` -- Anthropic API mock 응답
- [x] `test_registry_default_ollama` -- config 없을 때 Ollama 반환
- [x] `test_registry_openai_config` -- llm.provider=openai 시 OpenAI 반환
- [x] `test_registry_fallback` -- llm 섹션 없고 ollama 섹션 있을 때 Ollama
- [x] `test_litellm_import_error` -- litellm 미설치 시 안내 메시지

**MCP Tests**:
- [x] `test_mcp_client_start_stop` -- 프로세스 시작/종료
- [x] `test_mcp_client_list_tools` -- tools/list JSON-RPC 호출
- [x] `test_mcp_client_call_tool` -- tools/call 호출 + 응답 파싱
- [x] `test_mcp_client_timeout` -- 타임아웃 시 프로세스 kill
- [x] `test_mcp_registry_load_config` -- config.yaml에서 서버 목록 로드
- [x] `test_mcp_env_substitution` -- ${VAR} 환경변수 치환

**Repo Map Tests**:
- [x] `test_repo_map_build_python` -- Python AST 파싱 (함수/클래스/import)
- [x] `test_repo_map_build_generic` -- 정규식 파싱 (JS/TS)
- [x] `test_repo_map_get_context` -- 쿼리 기반 컨텍스트 반환
- [x] `test_repo_map_cache_hit` -- 캐시 히트 (같은 git hash)
- [x] `test_repo_map_cache_miss` -- 캐시 미스 (다른 git hash)
- [x] `test_repo_map_incremental` -- 변경 파일만 재파싱

**Integration Tests**:
- [x] `test_commit_with_registry` -- commit.py가 LLMRegistry 사용
- [x] `test_commit_ollama_fallback` -- config 없을 때 기존 Ollama 동작

---

## 9. Clean Architecture

### 9.1 Layer Structure (Locky 맞춤)

| Layer | Responsibility | Location |
|-------|---------------|----------|
| **CLI** | Click 명령 정의, 사용자 입출력 | `locky_cli/main.py`, `locky_cli/repl.py` |
| **Actions** | 자동화 명령 로직 (각각 독립) | `actions/*.py` |
| **Tools** | 외부 서비스 클라이언트 (LLM, MCP, Git) | `tools/llm/`, `tools/mcp/`, `tools/*.py` |
| **Config** | 설정 로딩/해석 | `config.py`, `locky_cli/config_loader.py` |

### 9.2 Dependency Rules

```
CLI ──→ Actions ──→ Tools
              │
              └──→ Config

Rule:
- Actions는 Tools의 public API만 사용 (내부 구현 의존 금지)
- Tools 간 의존은 금지 (llm/이 mcp/에 의존하지 않음)
- Config는 모든 레이어에서 접근 가능
- Actions는 서로 의존하지 않음 (기존 원칙 유지)
```

---

## 10. Coding Convention Reference

### 10.1 Naming Conventions (Python)

| Target | Rule | Example |
|--------|------|---------|
| Module files | snake_case | `ollama.py`, `repo_map.py` |
| Classes | PascalCase | `BaseLLMClient`, `MCPRegistry` |
| Functions | snake_case | `get_client()`, `build()` |
| Constants | UPPER_SNAKE_CASE | `DEFAULT_MODEL`, `MCP_PROTOCOL_VERSION` |
| Private | underscore prefix | `_parse_python()`, `_fetch_tags()` |
| Package `__init__.py` | Public exports only | `from .base import BaseLLMClient` |

### 10.2 Import Order (Python)

```python
# 1. stdlib
import json
import subprocess
from pathlib import Path

# 2. third-party
import httpx

# 3. local (project)
from config import OLLAMA_BASE_URL
from locky_cli.config_loader import load_config

# 4. relative
from .base import BaseLLMClient
```

### 10.3 This Feature's Conventions

| Item | Convention Applied |
|------|-------------------|
| LLM 클라이언트 네이밍 | `{Provider}LLMClient` (예: `OllamaLLMClient`) |
| 에러 클래스 네이밍 | `LLM{Type}Error` (예: `LLMAuthError`) |
| Config key 네이밍 | snake_case YAML key (예: `api_key_env`) |
| 테스트 파일 네이밍 | `test_{module}.py` (예: `test_llm_registry.py`) |

---

## 11. Implementation Guide

### 11.1 File Structure

```
tools/
├── llm/
│   ├── __init__.py          # Export: BaseLLMClient, LLMRegistry, LLMError, LLMResponse
│   ├── base.py              # BaseLLMClient ABC, LLMResponse, LLMError hierarchy
│   ├── ollama.py            # OllamaLLMClient (wraps existing OllamaClient pattern)
│   ├── openai.py            # OpenAILLMClient (httpx-based, no SDK dependency)
│   ├── anthropic.py         # AnthropicLLMClient (httpx-based, no SDK dependency)
│   ├── litellm_adapter.py   # LiteLLMClient (optional import)
│   └── registry.py          # LLMRegistry.get_client(), list_providers()
├── mcp/
│   ├── __init__.py          # Export: MCPClient, MCPRegistry, MCPTool
│   ├── client.py            # MCPClient (subprocess stdio, JSON-RPC 2.0)
│   ├── registry.py          # MCPRegistry (config-based server management)
│   └── config.py            # load_mcp_config(), MCPServerConfig
├── repo_map.py              # RepoMap class (build, get_context, incremental, cache)
├── ollama_client.py         # EXISTING -- unchanged
├── ollama_guard.py          # EXISTING -- unchanged
├── mcp_filesystem.py        # EXISTING -- unchanged
├── mcp_git.py               # EXISTING -- unchanged
└── jira_client.py           # EXISTING -- unchanged

# Modified files:
locky_cli/config_loader.py   # llm, mcp_servers 섹션 파싱 추가
actions/commit.py            # _generate_commit_message() → LLMRegistry 사용
actions/shell_command.py     # Ollama 직접 호출 → LLMRegistry 사용
pyproject.toml               # optional deps 추가

# New test files:
tests/test_llm_base.py       # BaseLLMClient, LLMResponse, LLMError 테스트
tests/test_llm_ollama.py     # OllamaLLMClient 테스트
tests/test_llm_openai.py     # OpenAILLMClient 테스트
tests/test_llm_anthropic.py  # AnthropicLLMClient 테스트
tests/test_llm_registry.py   # LLMRegistry 테스트
tests/test_llm_litellm.py    # LiteLLMAdapter 테스트
tests/test_mcp_client.py     # MCPClient 테스트
tests/test_mcp_registry.py   # MCPRegistry 테스트
tests/test_repo_map.py       # RepoMap 테스트
```

### 11.2 Implementation Order

1. [ ] **Module 1: LLM Base Layer** -- `tools/llm/base.py` (ABC + Error types + LLMResponse)
2. [ ] **Module 2: Ollama LLM Client** -- `tools/llm/ollama.py` (기존 OllamaClient 래핑)
3. [ ] **Module 3: OpenAI LLM Client** -- `tools/llm/openai.py` (httpx 기반)
4. [ ] **Module 4: Anthropic LLM Client** -- `tools/llm/anthropic.py` (httpx 기반)
5. [ ] **Module 5: LiteLLM Adapter** -- `tools/llm/litellm_adapter.py` (optional)
6. [ ] **Module 6: LLM Registry** -- `tools/llm/registry.py` + `__init__.py`
7. [ ] **Module 7: Config Extension** -- `config_loader.py` llm/mcp 섹션 추가
8. [ ] **Module 8: MCP Client** -- `tools/mcp/client.py` (stdio JSON-RPC)
9. [ ] **Module 9: MCP Registry + Config** -- `tools/mcp/registry.py` + `config.py`
10. [ ] **Module 10: Repo Map** -- `tools/repo_map.py` (build + context + cache)
11. [ ] **Module 11: Actions Integration** -- `commit.py`, `shell_command.py` LLM Registry 전환
12. [ ] **Module 12: Tests** -- 전체 신규 모듈 테스트 작성

### 11.3 Session Guide

#### Module Map

| Module | Scope Key | Description | Estimated Lines |
|--------|-----------|-------------|:---------------:|
| LLM Base + Ollama | `module-1` | base.py + ollama.py + tests | ~300 |
| OpenAI + Anthropic + LiteLLM | `module-2` | openai.py + anthropic.py + litellm_adapter.py + tests | ~400 |
| LLM Registry + Config | `module-3` | registry.py + config_loader 확장 + tests | ~250 |
| MCP Client + Registry | `module-4` | client.py + registry.py + config.py + tests | ~400 |
| Repo Map | `module-5` | repo_map.py + tests | ~350 |
| Actions Integration | `module-6` | commit.py + shell_command.py 전환 + pyproject.toml | ~150 |

#### Recommended Session Plan

| Session | Phase | Scope | Est. Lines |
|---------|-------|-------|:----------:|
| Session 1 | Plan + Design | 전체 | Docs only |
| Session 2 | Do | `module-1,module-2,module-3` (LLM 전체) | ~950 |
| Session 3 | Do | `module-4,module-5` (MCP + Repo Map) | ~750 |
| Session 4 | Do + Check | `module-6` + Gap Analysis | ~150 + Docs |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.0.1 | 2026-03-26 | Initial draft -- Option C (Pragmatic) selected | CTO Lead |
