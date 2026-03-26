"""tests/test_recipe_runner.py — Recipe runner tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.recipes.parser import Recipe, RecipeStep
from tools.recipes.runner import RecipeRunner


class TestRecipeRunner:
    def _make_recipe(self, steps, fail_fast=True):
        return Recipe(
            name="test-recipe",
            steps=[RecipeStep(action=s) for s in steps],
            fail_fast=fail_fast,
        )

    @patch("tools.recipes.runner.actions")
    def test_run_all_ok(self, mock_actions, tmp_path):
        mock_actions.format_code = MagicMock(return_value={"status": "ok"})
        mock_actions.test_runner = MagicMock(return_value={"status": "pass"})

        recipe = self._make_recipe(["format", "test"])
        result = RecipeRunner.run(recipe, tmp_path)

        assert result["status"] == "ok"
        assert result["executed"] == 2
        assert result["total"] == 2
        assert result["failed_at"] is None
        assert result["recipe"] == "test-recipe"

    @patch("tools.recipes.runner.actions")
    def test_run_fail_fast(self, mock_actions, tmp_path):
        mock_actions.format_code = MagicMock(return_value={"status": "error", "message": "fail"})
        mock_actions.test_runner = MagicMock(return_value={"status": "pass"})

        recipe = self._make_recipe(["format", "test"], fail_fast=True)
        result = RecipeRunner.run(recipe, tmp_path)

        assert result["status"] == "error"
        assert result["executed"] == 1
        assert result["failed_at"] == "format"
        mock_actions.test_runner.assert_not_called()

    @patch("tools.recipes.runner.actions")
    def test_run_no_fail_fast(self, mock_actions, tmp_path):
        mock_actions.format_code = MagicMock(return_value={"status": "error"})
        mock_actions.test_runner = MagicMock(return_value={"status": "pass"})

        recipe = self._make_recipe(["format", "test"], fail_fast=False)
        result = RecipeRunner.run(recipe, tmp_path)

        assert result["status"] == "partial"
        assert result["executed"] == 2

    @patch("tools.recipes.runner.actions")
    def test_run_with_args(self, mock_actions, tmp_path):
        mock_actions.format_code = MagicMock(return_value={"status": "ok"})

        recipe = Recipe(
            name="test",
            steps=[RecipeStep(action="format", args={"check_only": True})],
        )
        RecipeRunner.run(recipe, tmp_path)
        mock_actions.format_code.assert_called_once_with(tmp_path.resolve(), check_only=True)

    def test_run_unknown_action(self, tmp_path):
        recipe = Recipe(
            name="test",
            steps=[RecipeStep(action="nonexistent_xyz")],
        )
        result = RecipeRunner.run(recipe, tmp_path)
        assert result["status"] == "error"
        assert result["failed_at"] == "nonexistent_xyz"

    @patch("tools.recipes.runner.actions")
    def test_run_exception(self, mock_actions, tmp_path):
        mock_actions.format_code = MagicMock(side_effect=RuntimeError("boom"))

        recipe = self._make_recipe(["format"])
        result = RecipeRunner.run(recipe, tmp_path)
        assert result["status"] == "error"
        assert "boom" in result["results"][0]["message"]

    @patch("tools.recipes.runner.actions")
    def test_partial_status(self, mock_actions, tmp_path):
        mock_actions.format_code = MagicMock(return_value={"status": "ok"})
        mock_actions.test_runner = MagicMock(return_value={"status": "error"})

        recipe = self._make_recipe(["format", "test"], fail_fast=True)
        result = RecipeRunner.run(recipe, tmp_path)
        assert result["status"] == "partial"
        assert result["executed"] == 2

    @patch("tools.recipes.runner.actions")
    def test_nothing_to_commit_ok(self, mock_actions, tmp_path):
        mock_actions.commit = MagicMock(return_value={"status": "nothing_to_commit"})

        recipe = self._make_recipe(["commit"])
        result = RecipeRunner.run(recipe, tmp_path)
        assert result["status"] == "ok"


class TestRecipeRunnerListRecipes:
    def test_list_empty(self, tmp_path):
        recipes = RecipeRunner.list_recipes(tmp_path)
        assert recipes == []

    def test_list_nonexistent_dir(self, tmp_path):
        recipes = RecipeRunner.list_recipes(tmp_path / "missing")
        assert recipes == []

    def test_list_finds_yaml(self, tmp_path):
        (tmp_path / "pr-ready.yaml").write_text(
            "name: PR Ready\nsteps:\n  - action: format\n"
        )
        recipes = RecipeRunner.list_recipes(tmp_path)
        assert len(recipes) == 1
        assert recipes[0].name == "PR Ready"

    def test_list_finds_yml(self, tmp_path):
        (tmp_path / "check.yml").write_text(
            "name: Check\nsteps:\n  - action: test\n"
        )
        recipes = RecipeRunner.list_recipes(tmp_path)
        assert len(recipes) == 1

    def test_list_skips_invalid(self, tmp_path):
        (tmp_path / "good.yaml").write_text(
            "name: Good\nsteps:\n  - action: test\n"
        )
        (tmp_path / "bad.yaml").write_text("not: valid: yaml: [")
        recipes = RecipeRunner.list_recipes(tmp_path)
        assert len(recipes) == 1

    def test_list_multiple_dirs(self, tmp_path):
        d1 = tmp_path / "d1"
        d1.mkdir()
        (d1 / "a.yaml").write_text("name: A\nsteps:\n  - action: format\n")

        d2 = tmp_path / "d2"
        d2.mkdir()
        (d2 / "b.yaml").write_text("name: B\nsteps:\n  - action: test\n")

        recipes = RecipeRunner.list_recipes(d1, d2)
        assert len(recipes) == 2
