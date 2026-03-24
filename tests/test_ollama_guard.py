"""tools/ollama_guard.py 단위 테스트."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tools.ollama_guard import _check_model, _fetch_tags, _try_start_ollama, ensure_ollama


# ── _check_model ──────────────────────────────────────────────────────────────


def test_check_model_exact_match():
    tags = [{"name": "qwen2.5-coder:7b"}, {"name": "llama3:latest"}]
    assert _check_model(tags, "qwen2.5-coder:7b") is True


def test_check_model_base_name_match():
    tags = [{"name": "qwen2.5-coder:latest"}]
    assert _check_model(tags, "qwen2.5-coder:7b") is True  # base name 매칭


def test_check_model_not_found():
    tags = [{"name": "llama3:latest"}]
    assert _check_model(tags, "qwen2.5-coder:7b") is False


def test_check_model_empty_tags():
    assert _check_model([], "any-model") is False


# ── _fetch_tags ───────────────────────────────────────────────────────────────


def test_fetch_tags_success():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"models": [{"name": "qwen2.5-coder:7b"}]}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_cls.return_value = mock_client

        result = _fetch_tags("http://localhost:11434", 5)

    assert result == [{"name": "qwen2.5-coder:7b"}]


def test_fetch_tags_connection_error():
    with patch("httpx.Client") as mock_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("connection refused")
        mock_cls.return_value = mock_client

        result = _fetch_tags("http://localhost:11434", 5)

    assert result is None


def test_fetch_tags_returns_none_on_import_error():
    with patch.dict("sys.modules", {"httpx": None}):
        result = _fetch_tags("http://localhost:11434", 5)
    assert result is None


# ── _try_start_ollama ─────────────────────────────────────────────────────────


def test_try_start_ollama_no_binary():
    with patch("shutil.which", return_value=None):
        assert _try_start_ollama() is False


def test_try_start_ollama_success():
    with patch("shutil.which", return_value="/usr/bin/ollama"):
        with patch("subprocess.Popen") as mock_popen:
            result = _try_start_ollama()
    assert result is True
    mock_popen.assert_called_once()


# ── ensure_ollama ─────────────────────────────────────────────────────────────


def test_ensure_ollama_server_already_running():
    tags = [{"name": "qwen2.5-coder:7b"}]

    with patch("tools.ollama_guard._fetch_tags", return_value=tags):
        result = ensure_ollama("http://localhost:11434", "qwen2.5-coder:7b")

    assert result["status"] == "ok"
    assert result["model_available"] is True


def test_ensure_ollama_model_not_installed():
    tags = [{"name": "llama3:latest"}]  # 원하는 모델 없음

    with patch("tools.ollama_guard._fetch_tags", return_value=tags):
        result = ensure_ollama("http://localhost:11434", "qwen2.5-coder:7b")

    assert result["model_available"] is False
    assert "ollama pull" in result["message"]


def test_ensure_ollama_server_not_running_starts_it():
    tags = [{"name": "qwen2.5-coder:7b"}]

    # 1차 요청 실패, 2차 요청 성공 (서버 시작 후)
    call_count = [0]

    def fake_fetch(*a, **kw):
        call_count[0] += 1
        return None if call_count[0] == 1 else tags

    with patch("tools.ollama_guard._fetch_tags", side_effect=fake_fetch):
        with patch("tools.ollama_guard._try_start_ollama", return_value=True):
            with patch("time.sleep"):
                result = ensure_ollama("http://localhost:11434", "qwen2.5-coder:7b")

    assert result["status"] == "started"
    assert result["model_available"] is True


def test_ensure_ollama_server_not_running_no_binary():
    with patch("tools.ollama_guard._fetch_tags", return_value=None):
        with patch("tools.ollama_guard._try_start_ollama", return_value=False):
            result = ensure_ollama("http://localhost:11434", "qwen2.5-coder:7b")

    assert result["status"] == "error"
    assert result["model_available"] is False


def test_ensure_ollama_start_but_still_fails():
    with patch("tools.ollama_guard._fetch_tags", return_value=None):
        with patch("tools.ollama_guard._try_start_ollama", return_value=True):
            with patch("time.sleep"):
                result = ensure_ollama("http://localhost:11434", "qwen2.5-coder:7b")

    assert result["status"] == "error"
    assert result["model_available"] is False
