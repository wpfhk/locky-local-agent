# locky-agent v1.1.0 Design Document

> **Feature**: locky-agent-v1.1
> **Date**: 2026-03-24
> **Phase**: Design

---

## Context Anchor

| Key | Value |
|-----|-------|
| **WHY** | 환경변수 반복 설정, REPL 컨텍스트 부재, 수동 업데이트가 매일 사용의 마찰을 높인다. |
| **WHO** | 로컬 LLM(Ollama) 사용 개발자, 여러 프로젝트를 오가며 작업, 한국어 사용자 |
| **RISK** | config.yaml 우선순위 충돌 / git pull 실패 시 업데이트 중단 |
| **SUCCESS** | `locky init` 후 환경변수 없이 `locky commit` 동작 / `locky update`로 1분 내 최신 버전 |
| **SCOPE** | config_loader, init 대화형, repl context, update 명령, profile 자동갱신 |

---

## 1. Architecture — Option C (Pragmatic Balance) 채택

3가지 옵션 중 **Option C — Pragmatic Balance**를 채택합니다.

| 옵션 | 설명 | 판단 |
|------|------|------|
| A — Minimal | config.py에 yaml 로딩 직접 추가 | 결합도 높아 테스트 어려움 |
| B — Clean | 완전 DI 컨테이너, 전체 리팩터 | 과도한 복잡성 |
| **C — Pragmatic** | 전용 `config_loader.py` 모듈 + 기존 `config.py` 유지 | 추천 ✅ |

---

## 2. 신규 파일 구조

```
locky-agent/
├── locky_cli/
│   ├── config_loader.py    # NEW: config.yaml 파서 + 환경변수 병합
│   ├── main.py             # MOD: init 대화형, update 서브커맨드 추가
│   └── repl.py             # MOD: 진입 시 context 로드 + 헤더 표시
├── actions/
│   └── update.py           # NEW: git pull + pip 재설치 + 버전 비교
├── config.py               # MOD: config_loader 통해 설정 오버라이드
└── tests/
    ├── test_config_loader.py  # NEW
    └── test_update.py         # NEW
```

---

## 3. Module Design

### 3.1 `locky_cli/config_loader.py` (NEW)

```python
"""locky_cli/config_loader.py — .locky/config.yaml 로더"""

_CONFIG_FILE = ".locky/config.yaml"

def load_config(root: Path) -> dict:
    """config.yaml을 읽어 dict 반환. 파일 없으면 빈 dict."""

def get_ollama_model(root: Path) -> str:
    """우선순위: 환경변수 > config.yaml > 기본값(qwen2.5-coder:7b)"""

def get_ollama_base_url(root: Path) -> str:
    """우선순위: 환경변수 > config.yaml > http://localhost:11434"""

def get_hook_steps(root: Path) -> list[str]:
    """우선순위: config.yaml > 기본값(["format","test","scan"])"""
```

**의존성**: PyYAML (`pyyaml` 추가 필요)

---

### 3.2 `actions/update.py` (NEW)

```python
"""actions/update.py — git pull + pip 재설치 자동 업데이트"""

def run(root: Path, check_only: bool = False) -> dict:
    """
    Returns:
        {
          "status": "ok"|"up_to_date"|"error",
          "current_version": str,
          "new_version": str | None,
          "updated": bool,
          "message": str
        }
    """

def _find_locky_repo() -> Path:
    """locky-agent 패키지 설치 경로에서 git 루트 탐색"""

def _get_version(repo_root: Path) -> str:
    """pyproject.toml에서 version 읽기"""

def _git_pull(repo_root: Path) -> tuple[bool, str]:
    """git pull origin main → (changed: bool, output: str)"""

def _reinstall(repo_root: Path) -> bool:
    """pip install -e . 또는 pipx upgrade"""
```

---

### 3.3 `locky_cli/main.py` — init 대화형 개선

기존 `init` 명령을 Click의 `prompt` 옵션으로 대화형 전환:

```python
@main.command("init")
@click.option("--hook/--no-hook", default=None)
def init_cmd(hook):
    # 1. Ollama 모델 선택 (prompt)
    # 2. 훅 설치 여부 (confirm)
    # 3. 훅 스텝 선택 (prompt)
    # 4. .locky/config.yaml 생성
    # 5. 훅 설치 (선택 시)
```

새 `update` 서브커맨드 추가:

```python
@main.command("update")
@click.option("--check", is_flag=True, help="버전 확인만 (설치 안 함)")
def update_cmd(check):
    from actions.update import run
    result = run(Path.cwd(), check_only=check)
    _print_result(console, result)
```

---

### 3.4 `locky_cli/repl.py` — context 헤더

REPL 진입 시 `_print_context_header()` 추가:

```python
def _print_context_header(root: Path, console: Console):
    from locky_cli.config_loader import load_config, get_ollama_model
    from locky_cli.context import load_profile

    config = load_config(root)
    profile = load_profile(root)  # .locky/profile.json

    model = get_ollama_model(root)
    lang = profile.get("primary_language", "unknown") if profile else "unknown"
    hook_steps = config.get("hook", {}).get("steps", [])

    console.print(Panel(
        f"프로젝트  [cyan]{root.name}[/]\n"
        f"언어      [green]{lang}[/]\n"
        f"모델      [yellow]{model}[/]\n"
        f"훅        [dim]{' → '.join(hook_steps) if hook_steps else '미설치'}[/]",
        title=f"Locky v{VERSION}",
        ...
    ))
```

---

### 3.5 `config.py` — config_loader 통합

```python
# 기존
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

# 변경 후
def _get_setting(env_key: str, config_key_path: list[str], default: str) -> str:
    if env_val := os.getenv(env_key):
        return env_val
    try:
        from locky_cli.config_loader import load_config
        cfg = load_config(Path.cwd())
        val = cfg
        for k in config_key_path:
            val = val[k]
        return str(val)
    except (KeyError, Exception):
        return default

OLLAMA_MODEL = _get_setting("OLLAMA_MODEL", ["ollama", "model"], "qwen2.5-coder:7b")
OLLAMA_BASE_URL = _get_setting("OLLAMA_BASE_URL", ["ollama", "base_url"], "http://localhost:11434")
```

---

## 4. 우선순위

```
환경변수 > .locky/config.yaml > config.py 기본값
```

---

## 5. 의존성 변경

`requirements.txt` + `pyproject.toml`에 `pyyaml>=6.0` 추가.

---

## 6. 테스트 설계

### `tests/test_config_loader.py` (목표: 15개 이상)

| 테스트 | 내용 |
|--------|------|
| config.yaml 없을 때 빈 dict | `load_config` fallback |
| 유효한 yaml 파싱 | ollama.model 읽기 |
| 환경변수 > yaml 우선순위 | `get_ollama_model` |
| yaml > 기본값 우선순위 | 환경변수 없을 때 |
| 잘못된 yaml (syntax error) | graceful fallback |
| hook.steps 읽기 | `get_hook_steps` |

### `tests/test_update.py` (목표: 12개 이상)

| 테스트 | 내용 |
|--------|------|
| `_find_locky_repo` — 정상 경로 | git 루트 탐색 |
| `_get_version` | pyproject.toml 파싱 |
| `_git_pull` — 이미 최신 | "Already up to date" |
| `_git_pull` — 변경 있음 | mock subprocess |
| `run(check_only=True)` | 파일 변경 없음 확인 |
| `run()` — git 없는 경로 | error status |

---

## 7. Implementation Guide

### 7.1 구현 순서

1. **Module-1**: `config_loader.py` + `requirements.txt`/`pyproject.toml` 업데이트
2. **Module-2**: `config.py` 통합
3. **Module-3**: `locky_cli/main.py` — init 대화형 + update 서브커맨드
4. **Module-4**: `actions/update.py`
5. **Module-5**: `locky_cli/repl.py` — context 헤더
6. **Module-6**: 테스트 작성 (test_config_loader.py, test_update.py)

### 7.2 주의사항

- `config.py`는 모듈 임포트 시점에 평가됨 → `_get_setting()`은 순환 임포트 방지를 위해 `try-except`로 config_loader 임포트
- `locky update`는 현재 실행 중인 Python 인터프리터를 재시작하지 않음 → 업데이트 후 재실행 안내 메시지 표시
- `pyyaml` 없을 때 `config_loader.py`가 graceful fallback

### 7.3 Session Guide

| Module | 파일 | 예상 라인 |
|--------|------|:--------:|
| Module-1 | config_loader.py (신규) | ~80줄 |
| Module-2 | config.py 수정 | ~20줄 |
| Module-3 | main.py 수정 (init + update) | ~60줄 |
| Module-4 | actions/update.py (신규) | ~100줄 |
| Module-5 | repl.py 수정 | ~40줄 |
| Module-6 | test_config_loader.py + test_update.py (신규) | ~200줄 |
