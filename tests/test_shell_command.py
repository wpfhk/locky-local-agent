"""actions/shell_command.py 단위 테스트."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


from actions.shell_command import _extract_command, _is_valid_command, _scan_directory

# -- _extract_command -----------------------------------------------------------


def test_extract_plain_command():
    assert _extract_command("adb install app.aab") == "adb install app.aab"


def test_extract_strips_backtick_block():
    raw = "```bash\nadb install app.aab\n```"
    assert _extract_command(raw) == "adb install app.aab"


def test_extract_strips_inline_backtick():
    assert _extract_command("`ls -la`") == "ls -la"


def test_extract_skips_comment_lines():
    raw = "# install command\nadb install app.aab"
    assert _extract_command(raw) == "adb install app.aab"


def test_extract_first_non_empty_line():
    raw = "\n\nls -la\npwd"
    assert _extract_command(raw) == "ls -la"


# -- _is_valid_command ----------------------------------------------------------


def test_valid_adb_command():
    assert _is_valid_command("adb install app.aab") is True


def test_valid_ls_command():
    assert _is_valid_command("ls -la") is True


def test_valid_path_command():
    assert _is_valid_command("./gradlew build") is True


def test_valid_echo_command():
    assert _is_valid_command("echo 'hello world'") is True


def test_valid_git_command():
    assert _is_valid_command("git log --oneline -20") is True


def test_valid_docker_command():
    assert _is_valid_command("docker ps -a") is True


def test_invalid_korean_response():
    assert _is_valid_command("죄송합니다, 더 자세한 정보가 필요합니다.") is False


def test_invalid_empty_string():
    assert _is_valid_command("") is False


def test_invalid_starts_with_special_char():
    assert _is_valid_command("@invalid") is False


# -- Numeric-start CLI tools ---------------------------------------------------


def test_valid_7z_command():
    assert _is_valid_command("7z x archive.zip") is True


def test_valid_2to3_command():
    assert _is_valid_command("2to3 script.py") is True


def test_valid_1password_command():
    assert _is_valid_command("1password login") is True


# -- Pipe, redirection, chaining -----------------------------------------------


def test_valid_pipe_command():
    assert _is_valid_command('ls -la | grep ".py"') is True


def test_valid_redirection_command():
    assert _is_valid_command('echo "hello" > output.txt') is True


def test_valid_chained_command():
    assert _is_valid_command("cat file.txt && rm file.txt") is True


def test_valid_complex_pipe():
    assert _is_valid_command('find . -name "*.log" | xargs rm') is True


# -- Code keyword rejection ----------------------------------------------------


def test_invalid_import_statement():
    """Python import 문은 셸 명령이 아니다."""
    assert _is_valid_command("import os") is False


def test_invalid_from_import():
    """Python from-import 문은 셸 명령이 아니다."""
    assert _is_valid_command("from pathlib import Path") is False


def test_invalid_class_definition():
    assert _is_valid_command("class MyClass:") is False


def test_invalid_def_function():
    assert _is_valid_command("def main():") is False


def test_invalid_javascript_function():
    assert _is_valid_command("function doSomething() {") is False


def test_invalid_const_declaration():
    assert _is_valid_command("const x = 5;") is False


def test_invalid_let_declaration():
    assert _is_valid_command("let y = 10;") is False


def test_invalid_var_declaration():
    assert _is_valid_command("var z = 15;") is False


def test_invalid_print_call():
    assert _is_valid_command("print('hello')") is False


def test_invalid_console_log():
    assert _is_valid_command("console.log('hello')") is False


def test_invalid_if_name_main():
    assert _is_valid_command("if __name__ == '__main__':") is False


# -- _scan_directory ------------------------------------------------------------


def test_scan_directory_finds_aab(tmp_path: Path):
    (tmp_path / "app-release.aab").touch()
    (tmp_path / "README.md").touch()
    result = _scan_directory(tmp_path)
    assert "app-release.aab" in result


def test_scan_directory_empty(tmp_path: Path):
    result = _scan_directory(tmp_path)
    assert result == "(empty)"


def test_scan_directory_priority_ext_first(tmp_path: Path):
    (tmp_path / "main.py").touch()
    (tmp_path / "README.md").touch()
    result = _scan_directory(tmp_path)
    # .py 파일이 우선 표시되어야 함
    assert result.index("main.py") < result.index("README.md")


def test_scan_directory_limits_to_15(tmp_path: Path):
    for i in range(20):
        (tmp_path / f"file_{i:02d}.py").touch()
    result = _scan_directory(tmp_path)
    assert "+5 more" in result


# -- run() integration (Ollama mock) -------------------------------------------


def test_run_empty_request(tmp_path: Path):
    from actions.shell_command import run

    result = run(tmp_path, request="")
    assert result["status"] == "error"
    assert result["command"] == ""


def test_run_returns_ok_with_mock(tmp_path: Path):
    from actions.shell_command import run

    with patch("tools.ollama_client.OllamaClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.return_value = "adb install app.aab"
        mock_cls.return_value = mock_client

        result = run(tmp_path, request="aab 파일 설치해줘")

    assert result["status"] == "ok"
    assert result["command"] == "adb install app.aab"


def test_run_rejects_korean_response(tmp_path: Path):
    from actions.shell_command import run

    with patch("tools.ollama_client.OllamaClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.return_value = "죄송합니다, 어떤 명령인지 모르겠습니다."
        mock_cls.return_value = mock_client

        result = run(tmp_path, request="뭔가 해줘")

    assert result["status"] == "error"
    assert result["command"] == ""


def test_run_rejects_python_code_response(tmp_path: Path):
    """Ollama가 Python 코드를 반환하면 거부해야 한다."""
    from actions.shell_command import run

    with patch("tools.ollama_client.OllamaClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.return_value = "import os\nos.makedirs('/temp', exist_ok=True)"
        mock_cls.return_value = mock_client

        result = run(tmp_path, request="파이썬 프로그램 만들어줘")

    assert result["status"] == "error"
    assert result["command"] == ""


def test_run_accepts_echo_refusal(tmp_path: Path):
    """코드 생성 요청에 echo 거부 메시지를 반환하면 유효한 명령으로 인정."""
    from actions.shell_command import run

    with patch("tools.ollama_client.OllamaClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.return_value = "echo 'Use a code editor for programming tasks'"
        mock_cls.return_value = mock_client

        result = run(tmp_path, request="파이썬 프로그램 만들어줘")

    assert result["status"] == "ok"
    assert "echo" in result["command"]


def test_run_handles_connection_error(tmp_path: Path):
    """Ollama 연결 실패 시 에러를 반환해야 한다."""
    from actions.shell_command import run

    with patch("tools.ollama_client.OllamaClient") as mock_cls:
        mock_client = MagicMock()
        mock_client.chat.side_effect = Exception("Connection refused")
        mock_cls.return_value = mock_client

        result = run(tmp_path, request="ls 해줘")

    assert result["status"] == "error"
    assert "명령 생성 실패" in result["message"]
