"""tests/test_ollama_stream.py — OllamaClient.stream() 테스트 (4개)"""

import json
from unittest.mock import MagicMock, patch

import pytest

from tools.ollama_client import OllamaClient


def _make_line(content="", done=False):
    return json.dumps({"message": {"content": content}, "done": done})


def test_stream_yields_tokens(tmp_path):
    lines = [
        _make_line("안녕"),
        _make_line("하세요"),
        _make_line("", done=True),
    ]

    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.raise_for_status = MagicMock()
    mock_resp.iter_lines = MagicMock(return_value=iter(lines))

    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: s
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.stream = MagicMock(return_value=mock_resp)

    with patch("httpx.Client", return_value=mock_client):
        client = OllamaClient()
        tokens = list(client.stream([{"role": "user", "content": "안녕"}]))

    assert tokens == ["안녕", "하세요"]


def test_stream_stops_on_done(tmp_path):
    lines = [
        _make_line("첫번째"),
        _make_line("", done=True),
        _make_line("이후는무시"),  # done 이후는 처리 안 됨
    ]

    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.raise_for_status = MagicMock()
    mock_resp.iter_lines = MagicMock(return_value=iter(lines))

    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: s
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.stream = MagicMock(return_value=mock_resp)

    with patch("httpx.Client", return_value=mock_client):
        client = OllamaClient()
        tokens = list(client.stream([{"role": "user", "content": "질문"}]))

    assert tokens == ["첫번째"]


def test_stream_empty_content_skipped():
    lines = [
        _make_line(""),  # 빈 content → skip
        _make_line("내용"),
        _make_line("", done=True),
    ]

    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.raise_for_status = MagicMock()
    mock_resp.iter_lines = MagicMock(return_value=iter(lines))

    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: s
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.stream = MagicMock(return_value=mock_resp)

    with patch("httpx.Client", return_value=mock_client):
        client = OllamaClient()
        tokens = list(client.stream([{"role": "user", "content": "질문"}]))

    assert tokens == ["내용"]


def test_stream_with_system():
    lines = [_make_line("응답", done=True)]

    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.raise_for_status = MagicMock()
    mock_resp.iter_lines = MagicMock(return_value=iter(lines))

    mock_client = MagicMock()
    mock_client.__enter__ = lambda s: s
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.stream = MagicMock(return_value=mock_resp)

    with patch("httpx.Client", return_value=mock_client):
        client = OllamaClient()
        tokens = list(
            client.stream(
                [{"role": "user", "content": "질문"}], system="시스템 프롬프트"
            )
        )

    # system 파라미터가 payload에 포함됐는지 확인
    call_kwargs = mock_client.stream.call_args[1]
    assert call_kwargs["json"]["system"] == "시스템 프롬프트"
