# Locky v3 Phase 2: UX & Reliability — Design v0.0.1

> Date: 2026-03-26
> Feature: locky-v3-ux-reliability
> Architecture: Option C (Pragmatic Balance)

---

## 1. Session Management

### 1.1 SQLite Schema (`tools/session/store.py`)

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    metadata    TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    role        TEXT NOT NULL,    -- 'user' | 'assistant' | 'system'
    content     TEXT NOT NULL,
    provider    TEXT DEFAULT '',
    model       TEXT DEFAULT '',
    tokens_in   INTEGER DEFAULT 0,
    tokens_out  INTEGER DEFAULT 0,
    cost        REAL DEFAULT 0.0,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
```

### 1.2 SessionStore API

```python
class SessionStore:
    def __init__(self, db_path: Path)
    def create_session(self, title: str = "", metadata: dict | None = None) -> str
    def add_message(self, session_id: str, role: str, content: str, **kwargs) -> int
    def get_session(self, session_id: str) -> dict | None
    def list_sessions(self, limit: int = 20) -> list[dict]
    def get_messages(self, session_id: str) -> list[dict]
    def delete_session(self, session_id: str) -> bool
    def update_session(self, session_id: str, **kwargs) -> bool
```

### 1.3 SessionManager API

```python
class SessionManager:
    def __init__(self, root: Path)
    def create(self, title: str = "") -> str
    def resume(self, session_id: str) -> dict
    def export_markdown(self, session_id: str) -> str
    def list_recent(self, limit: int = 20) -> list[dict]
```

DB path: `{root}/.locky/sessions.db`

## 2. Unified Streaming (`tools/llm/streaming.py`)

### 2.1 UnifiedStreamer

```python
class StreamEvent:
    """Single streaming event."""
    token: str
    provider: str
    model: str
    done: bool = False
    usage: dict | None = None

class UnifiedStreamer:
    def __init__(self, client: BaseLLMClient, tracker: TokenTracker | None = None)
    def stream_chat(self, messages, system="") -> Generator[StreamEvent, None, None]
    def stream_to_console(self, messages, system="", console=None) -> LLMResponse
```

- Wraps any `BaseLLMClient.stream()` call
- Emits `StreamEvent` objects with metadata
- `stream_to_console` prints tokens in real-time and returns aggregated response
- Integrates with TokenTracker for automatic usage tracking

## 3. Error Recovery / Retry (`tools/llm/retry.py`)

### 3.1 RetryConfig

```python
@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    retryable_errors: tuple = (LLMConnectionError, LLMTimeoutError)
```

### 3.2 RetryHandler

```python
class RetryHandler:
    def __init__(self, config: RetryConfig | None = None,
                 fallback_client: BaseLLMClient | None = None)
    def execute(self, fn: Callable, *args, **kwargs) -> Any
    def chat_with_retry(self, client, messages, system="") -> LLMResponse
    def stream_with_retry(self, client, messages, system="") -> Generator
```

- Exponential backoff: `delay = min(base * (exp_base ** attempt), max_delay)`
- On exhausted retries with fallback_client: tries fallback once
- Fallback triggers on any LLMError (not just retryable ones after max retries)

## 4. Lead/Worker Multi-Model

### 4.1 Config Schema

```yaml
llm:
  lead:
    provider: anthropic
    model: claude-sonnet-4-6
    api_key_env: ANTHROPIC_API_KEY
  worker:
    provider: ollama
    model: qwen2.5-coder:7b
  fallback:
    provider: ollama
    model: qwen2.5-coder:7b
```

### 4.2 Registry Enhancement

```python
# tools/llm/registry.py additions
class LLMRegistry:
    @staticmethod
    def get_lead_client(root=None) -> BaseLLMClient
    @staticmethod
    def get_worker_client(root=None) -> BaseLLMClient
```

- `get_lead_client`: returns `llm.lead` config or falls back to `get_client()`
- `get_worker_client`: returns `llm.worker` config or falls back to `get_client()`
- `commit.py` uses worker; `ask/edit/agent` uses lead

## 5. Token/Cost Tracking (`tools/llm/tracker.py`)

### 5.1 TokenTracker

```python
@dataclass
class UsageRecord:
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost: float
    timestamp: str

class TokenTracker:
    def record(self, provider, model, prompt_tokens, completion_tokens) -> UsageRecord
    def get_session_total(self) -> dict
    def format_summary(self) -> str
    def reset(self)
```

### 5.2 Pricing (approximation, per 1M tokens)

```python
_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-3": {"input": 0.25, "output": 1.25},
    # Ollama/local models: 0.0
}
```

- Local models (ollama) always return cost=0.0
- Unknown models return cost=0.0 with a warning

## 6. `locky init` Enhancement

### 6.1 Auto-Detection Logic

1. Check Ollama: `GET http://localhost:11434/api/tags` -> list available models
2. Check env vars: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
3. Suggest best provider based on availability
4. Validate config before writing

### 6.2 Config Validation

```python
def validate_config(config: dict) -> list[str]:
    """Returns list of warning/error messages. Empty = valid."""
```

## 7. CLI Commands

```
locky session list              # Recent sessions (table)
locky session resume <id>       # Print session context
locky session export <id>       # Export as markdown
```
