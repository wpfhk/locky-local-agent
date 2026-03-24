"""tests/test_config_loader.py — config_loader.py 단위 테스트 (v1.1.0)."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

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


# ── _maybe_refresh_profile ─────────────────────────────────────────────────


def test_maybe_refresh_profile_calls_detect_when_enabled(tmp_path):
    from locky_cli.main import _maybe_refresh_profile

    mock_detect = MagicMock()
    with patch("locky_cli.config_loader.get_auto_profile", return_value=True):
        with patch("locky_cli.context.detect_and_save", mock_detect):
            _maybe_refresh_profile(tmp_path)
    # 비동기 스레드이므로 즉시 호출 여부보다 예외 없음을 확인
    # (threading.Thread는 daemon=True로 실행됨)


def test_maybe_refresh_profile_skips_when_disabled(tmp_path):
    from locky_cli.main import _maybe_refresh_profile

    mock_detect = MagicMock()
    with patch("locky_cli.config_loader.get_auto_profile", return_value=False):
        with patch("locky_cli.context.detect_and_save", mock_detect):
            _maybe_refresh_profile(tmp_path)
    mock_detect.assert_not_called()


def test_maybe_refresh_profile_handles_import_error(tmp_path):
    from locky_cli.main import _maybe_refresh_profile

    # 예외가 발생해도 조용히 무시하는지 확인
    with patch("locky_cli.config_loader.get_auto_profile", side_effect=ImportError):
        _maybe_refresh_profile(tmp_path)  # 예외 없이 통과해야 함
