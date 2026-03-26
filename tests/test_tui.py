"""tests/test_tui.py — TUI dashboard tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ui.tui import _ACTIONS, _run_action, _show_menu, _show_status


class TestTUIActions:
    def test_actions_defined(self):
        assert len(_ACTIONS) >= 8
        assert "1" in _ACTIONS
        assert "q" not in _ACTIONS  # q is handled separately

    def test_all_actions_have_name_desc(self):
        for key, (action, desc) in _ACTIONS.items():
            assert isinstance(action, str) and action
            assert isinstance(desc, str) and desc

    @patch("ui.tui.actions")
    def test_run_action_format(self, mock_actions):
        mock_actions.format_code = MagicMock(
            return_value={"status": "ok", "language": "python"}
        )
        console = MagicMock()
        _run_action("format", Path("/tmp"), console)
        mock_actions.format_code.assert_called_once()
        console.print.assert_called()

    @patch("ui.tui.actions")
    def test_run_action_test(self, mock_actions):
        mock_actions.test_runner = MagicMock(
            return_value={"status": "pass", "passed": 10}
        )
        console = MagicMock()
        _run_action("test", Path("/tmp"), console)
        mock_actions.test_runner.assert_called_once()

    @patch("ui.tui.actions")
    def test_run_action_exception(self, mock_actions):
        mock_actions.format_code = MagicMock(side_effect=RuntimeError("boom"))
        console = MagicMock()
        _run_action("format", Path("/tmp"), console)
        # Should print error panel, not raise
        console.print.assert_called()

    def test_run_action_unknown(self):
        console = MagicMock()
        _run_action("nonexistent_xyz", Path("/tmp"), console)
        # Should print error message
        assert any("Unknown" in str(call) for call in console.print.call_args_list)


class TestTUIMenu:
    def test_show_menu(self):
        console = MagicMock()
        _show_menu(console)
        console.print.assert_called_once()


class TestTUIStatus:
    @patch("subprocess.run")
    def test_show_status(self, mock_run):
        mock_run.return_value = MagicMock(stdout="M file.py\n", returncode=0)
        console = MagicMock()
        _show_status(console, Path("/tmp"))
        console.print.assert_called_once()

    @patch("subprocess.run", side_effect=Exception("git not found"))
    def test_show_status_no_git(self, _):
        console = MagicMock()
        _show_status(console, Path("/tmp"))
        console.print.assert_called_once()
