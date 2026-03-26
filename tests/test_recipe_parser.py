"""tests/test_recipe_parser.py — Recipe parser tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.recipes.parser import (
    MAX_STEPS,
    Recipe,
    RecipeStep,
    _parse_cli_args,
    parse_recipe,
    validate_recipe,
)


class TestValidateRecipe:
    def test_valid_minimal(self):
        data = {"name": "test", "steps": [{"action": "format"}]}
        assert validate_recipe(data) == []

    def test_valid_string_steps(self):
        data = {"name": "test", "steps": ["format --check", "test", "scan"]}
        assert validate_recipe(data) == []

    def test_missing_name(self):
        errors = validate_recipe({"steps": [{"action": "format"}]})
        assert any("name" in e for e in errors)

    def test_empty_steps(self):
        errors = validate_recipe({"name": "test", "steps": []})
        assert any("at least one" in e for e in errors)

    def test_steps_not_list(self):
        errors = validate_recipe({"name": "test", "steps": "format"})
        assert any("list" in e for e in errors)

    def test_unknown_action(self):
        errors = validate_recipe({"name": "test", "steps": [{"action": "unknown_xyz"}]})
        assert any("unknown" in e.lower() for e in errors)

    def test_unknown_string_action(self):
        errors = validate_recipe({"name": "test", "steps": ["unknown_xyz"]})
        assert any("unknown" in e.lower() for e in errors)

    def test_missing_action_key(self):
        errors = validate_recipe({"name": "test", "steps": [{"args": {}}]})
        assert any("action" in e for e in errors)

    def test_args_not_dict(self):
        errors = validate_recipe(
            {"name": "test", "steps": [{"action": "format", "args": "bad"}]}
        )
        assert any("dict" in e for e in errors)

    def test_step_invalid_type(self):
        errors = validate_recipe({"name": "test", "steps": [123]})
        assert any("string or dict" in e for e in errors)

    def test_max_steps_exceeded(self):
        steps = [{"action": "format"} for _ in range(MAX_STEPS + 1)]
        errors = validate_recipe({"name": "test", "steps": steps})
        assert any("maximum" in e for e in errors)

    def test_all_valid_actions(self):
        from tools.recipes.parser import VALID_ACTIONS

        steps = [{"action": a} for a in VALID_ACTIONS]
        data = {"name": "test", "steps": steps}
        assert validate_recipe(data) == []


class TestParseRecipe:
    def test_parse_dict_steps(self, tmp_path):
        (tmp_path / "test.yaml").write_text(
            "name: Test\ndescription: A test\nsteps:\n"
            "  - action: format\n    args:\n      check: true\n"
            "  - action: test\n"
        )
        recipe = parse_recipe(tmp_path / "test.yaml")
        assert recipe.name == "Test"
        assert len(recipe.steps) == 2
        assert recipe.steps[0].action == "format"
        assert recipe.steps[0].args == {"check": True}

    def test_parse_string_steps(self, tmp_path):
        (tmp_path / "test.yaml").write_text(
            "name: Quick Check\nsteps:\n  - format --check\n  - test\n  - scan --severity high\n"
        )
        recipe = parse_recipe(tmp_path / "test.yaml")
        assert len(recipe.steps) == 3
        assert recipe.steps[0].args == {"check": True}
        assert recipe.steps[2].args == {"severity": "high"}

    def test_parse_fail_fast(self, tmp_path):
        (tmp_path / "test.yaml").write_text(
            "name: NoFail\nsteps:\n  - action: test\nfail_fast: false\n"
        )
        recipe = parse_recipe(tmp_path / "test.yaml")
        assert recipe.fail_fast is False

    def test_parse_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            parse_recipe(tmp_path / "missing.yaml")

    def test_parse_invalid_format(self, tmp_path):
        (tmp_path / "test.yaml").write_text("- list\n- not dict\n")
        with pytest.raises(ValueError, match="Invalid recipe format"):
            parse_recipe(tmp_path / "test.yaml")

    def test_parse_validation_fails(self, tmp_path):
        (tmp_path / "test.yaml").write_text("name: test\nsteps: []\n")
        with pytest.raises(ValueError, match="Invalid recipe"):
            parse_recipe(tmp_path / "test.yaml")

    def test_source_path_set(self, tmp_path):
        (tmp_path / "test.yaml").write_text(
            "name: Test\nsteps:\n  - action: format\n"
        )
        recipe = parse_recipe(tmp_path / "test.yaml")
        assert recipe.source_path == tmp_path / "test.yaml"

    def test_version_defaults(self, tmp_path):
        (tmp_path / "test.yaml").write_text(
            "name: Test\nsteps:\n  - action: format\n"
        )
        recipe = parse_recipe(tmp_path / "test.yaml")
        assert recipe.version == "1.0"


class TestParseCLIArgs:
    def test_flag(self):
        assert _parse_cli_args(["--check"]) == {"check": True}

    def test_key_value(self):
        assert _parse_cli_args(["--severity", "high"]) == {"severity": "high"}

    def test_mixed(self):
        result = _parse_cli_args(["--check", "--severity", "high"])
        assert result == {"check": True, "severity": "high"}

    def test_empty(self):
        assert _parse_cli_args([]) == {}

    def test_dashes_to_underscores(self):
        assert _parse_cli_args(["--dry-run"]) == {"dry_run": True}

    def test_non_flag_ignored(self):
        assert _parse_cli_args(["path/to/file"]) == {}


class TestRecipeDataclass:
    def test_defaults(self):
        r = Recipe(name="test")
        assert r.description == ""
        assert r.version == "1.0"
        assert r.steps == []
        assert r.fail_fast is True
        assert r.source_path is None

    def test_step_defaults(self):
        s = RecipeStep(action="format")
        assert s.args == {}
