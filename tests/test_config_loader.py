"""tests/test_config_loader.py — config_loader.py 단위 테스트 (v1.1.0)."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from locky_cli.config_loader import (
    get_auto_profile,
    get_hook_steps,
    get_ollama_base_url,
    get_ollama_model,
    get_ollama_timeout,
    load_config,
)


# ── load_config ────────────────────────────────────────────────────────────────


def test_load_config_no_file(tmp_path):
    assert load_config(tmp_path) == {}


def test_load_config_valid_yaml(tmp_path):
    (tmp_path / ".locky").mkdir()
    (tmp_path / ".locky" / "config.yaml").write_text(
        "ollama:\n  model: qwen2.5-coder:14b\n"
    )
    cfg = load_config(tmp_path)
    assert cfg["ollama"]["model"] == "qwen2.5-coder:14b"


def test_load_config_invalid_yaml(tmp_path):
    (tmp_path / ".locky").mkdir()
    # 들여쓰기 오류로 파싱 실패를 유도
    (tmp_path / ".locky" / "config.yaml").write_text("key:\n  - item\n bad_indent")
    assert load_config(tmp_path) == {}


def test_load_config_empty_file(tmp_path):
    (tmp_path / ".locky").mkdir()
    (tmp_path / ".locky" / "config.yaml").write_text("")
    assert load_config(tmp_path) == {}


def test_load_config_partial(tmp_path):
    (tmp_path / ".locky").mkdir()
    (tmp_path / ".locky" / "config.yaml").write_text("hook:\n  steps:\n    - format\n")
    cfg = load_config(tmp_path)
    assert cfg["hook"]["steps"] == ["format"]


# ── get_ollama_model ───────────────────────────────────────────────────────────


def test_get_ollama_model_default(tmp_path):
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OLLAMA_MODEL", None)
        assert get_ollama_model(tmp_path) == "qwen2.5-coder:7b"


def test_get_ollama_model_from_env(tmp_path):
    with patch.dict(os.environ, {"OLLAMA_MODEL": "codellama:7b"}):
        assert get_ollama_model(tmp_path) == "codellama:7b"


def test_get_ollama_model_from_yaml(tmp_path):
    (tmp_path / ".locky").mkdir()
    (tmp_path / ".locky" / "config.yaml").write_text(
        "ollama:\n  model: qwen2.5-coder:14b\n"
    )
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OLLAMA_MODEL", None)
        assert get_ollama_model(tmp_path) == "qwen2.5-coder:14b"


def test_get_ollama_model_env_overrides_yaml(tmp_path):
    (tmp_path / ".locky").mkdir()
    (tmp_path / ".locky" / "config.yaml").write_text(
        "ollama:\n  model: qwen2.5-coder:14b\n"
    )
    with patch.dict(os.environ, {"OLLAMA_MODEL": "deepseek-coder:6.7b"}):
        assert get_ollama_model(tmp_path) == "deepseek-coder:6.7b"


# ── get_ollama_base_url ────────────────────────────────────────────────────────


def test_get_ollama_base_url_default(tmp_path):
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OLLAMA_BASE_URL", None)
        assert get_ollama_base_url(tmp_path) == "http://localhost:11434"


def test_get_ollama_base_url_from_env(tmp_path):
    with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://remote:11434"}):
        assert get_ollama_base_url(tmp_path) == "http://remote:11434"


def test_get_ollama_base_url_from_yaml(tmp_path):
    (tmp_path / ".locky").mkdir()
    (tmp_path / ".locky" / "config.yaml").write_text(
        "ollama:\n  base_url: http://192.168.1.100:11434\n"
    )
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OLLAMA_BASE_URL", None)
        assert get_ollama_base_url(tmp_path) == "http://192.168.1.100:11434"


# ── get_ollama_timeout ─────────────────────────────────────────────────────────


def test_get_ollama_timeout_default(tmp_path):
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OLLAMA_TIMEOUT", None)
        assert get_ollama_timeout(tmp_path) == 300


def test_get_ollama_timeout_from_yaml(tmp_path):
    (tmp_path / ".locky").mkdir()
    (tmp_path / ".locky" / "config.yaml").write_text("ollama:\n  timeout: 600\n")
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("OLLAMA_TIMEOUT", None)
        assert get_ollama_timeout(tmp_path) == 600


# ── get_hook_steps ─────────────────────────────────────────────────────────────


def test_get_hook_steps_default(tmp_path):
    assert get_hook_steps(tmp_path) == ["format", "test", "scan"]


def test_get_hook_steps_from_yaml(tmp_path):
    (tmp_path / ".locky").mkdir()
    (tmp_path / ".locky" / "config.yaml").write_text(
        "hook:\n  steps:\n    - format\n    - scan\n"
    )
    assert get_hook_steps(tmp_path) == ["format", "scan"]


def test_get_hook_steps_empty_list(tmp_path):
    (tmp_path / ".locky").mkdir()
    (tmp_path / ".locky" / "config.yaml").write_text("hook:\n  steps: []\n")
    # 빈 리스트는 기본값으로 fallback
    assert get_hook_steps(tmp_path) == ["format", "test", "scan"]


# ── get_auto_profile ───────────────────────────────────────────────────────────


def test_get_auto_profile_default(tmp_path):
    assert get_auto_profile(tmp_path) is True


def test_get_auto_profile_from_yaml(tmp_path):
    (tmp_path / ".locky").mkdir()
    (tmp_path / ".locky" / "config.yaml").write_text("init:\n  auto_profile: false\n")
    assert get_auto_profile(tmp_path) is False
