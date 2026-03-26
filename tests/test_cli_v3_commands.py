"""tests/test_cli_v3_commands.py — Phase 3 CLI command tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from locky_cli.main import cli


class TestRecipeCommands:
    def test_recipe_list_empty(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["recipe", "list", "-w", str(tmp_path)])
        assert result.exit_code == 0
        assert "등록된 레시피가 없습니다" in result.output or "레시피" in result.output

    def test_recipe_run_not_found(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["recipe", "run", "nonexistent", "-w", str(tmp_path)])
        assert result.exit_code == 0
        assert "찾을 수 없습니다" in result.output

    @patch("tools.recipes.runner.RecipeRunner.run")
    def test_recipe_run_success(self, mock_run, tmp_path):
        # Create a recipe file
        recipe_dir = tmp_path / ".locky" / "recipes"
        recipe_dir.mkdir(parents=True)
        (recipe_dir / "test-recipe.yaml").write_text(
            "name: Test Recipe\nsteps:\n  - action: format\n"
        )

        mock_run.return_value = {
            "status": "ok",
            "recipe": "Test Recipe",
            "results": [{"step": "format", "status": "ok"}],
            "failed_at": None,
            "executed": 1,
            "total": 1,
        }

        runner = CliRunner()
        result = runner.invoke(cli, ["recipe", "run", "test-recipe", "-w", str(tmp_path)])
        assert result.exit_code == 0

    def test_recipe_list_with_recipes(self, tmp_path):
        recipe_dir = tmp_path / ".locky" / "recipes"
        recipe_dir.mkdir(parents=True)
        (recipe_dir / "pr-ready.yaml").write_text(
            "name: PR Ready\nsteps:\n  - action: format\n  - action: test\n"
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["recipe", "list", "-w", str(tmp_path)])
        assert result.exit_code == 0
        assert "PR Ready" in result.output


class TestServeMCPCommand:
    def test_serve_mcp_exists(self):
        """Verify serve-mcp command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["serve-mcp", "--help"])
        assert result.exit_code == 0
        assert "MCP" in result.output


class TestTUICommand:
    def test_tui_exists(self):
        """Verify tui command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["tui", "--help"])
        assert result.exit_code == 0
        assert "TUI" in result.output
