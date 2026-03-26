"""tools/recipes/runner.py — Execute recipe workflows."""

from __future__ import annotations

from pathlib import Path

import actions

from .parser import Recipe, parse_recipe

# Action name -> actions module function name mapping
_ACTION_MAP: dict[str, str] = {
    "format": "format_code",
    "test": "test_runner",
    "scan": "security_scan",
    "commit": "commit",
    "clean": "cleanup",
    "deps": "deps_check",
    "env": "env_template",
    "todo": "todo_collector",
}


class RecipeRunner:
    """Executes recipe workflows by delegating to actions/ modules."""

    @staticmethod
    def run(recipe: Recipe, root: Path) -> dict:
        """Execute a recipe.

        Args:
            recipe: Parsed Recipe
            root: Project root path

        Returns:
            {
                "status": "ok"|"partial"|"error",
                "recipe": str,
                "results": [...],
                "failed_at": str|None,
                "executed": int,
                "total": int,
            }
        """
        root = Path(root).resolve()
        results: list[dict] = []
        failed_at: str | None = None

        for step in recipe.steps:
            action_name = step.action
            runner_module = _ACTION_MAP.get(action_name)

            if not runner_module:
                step_result = {
                    "step": action_name,
                    "status": "error",
                    "message": f"Unknown action: {action_name}",
                }
                results.append(step_result)
                failed_at = action_name
                if recipe.fail_fast:
                    break
                continue

            try:
                runner_func = getattr(actions, runner_module)
                result = runner_func(root, **step.args)
            except Exception as exc:
                result = {"status": "error", "message": str(exc)}

            step_result = {"step": action_name, **result}
            results.append(step_result)

            status = result.get("status", "error")
            if status not in ("ok", "pass", "clean", "nothing_to_commit"):
                failed_at = action_name
                if recipe.fail_fast:
                    break

        executed = len(results)
        total = len(recipe.steps)

        if failed_at is not None:
            overall = "partial" if executed > 1 else "error"
        else:
            overall = "ok"

        return {
            "status": overall,
            "recipe": recipe.name,
            "results": results,
            "failed_at": failed_at,
            "executed": executed,
            "total": total,
        }

    @staticmethod
    def list_recipes(*recipe_dirs: Path) -> list[Recipe]:
        """Discover recipes from directories.

        Args:
            recipe_dirs: Directories to scan for *.yaml files

        Returns:
            List of parsed Recipe objects
        """
        recipes: list[Recipe] = []
        for d in recipe_dirs:
            if not d.is_dir():
                continue
            for yaml_file in sorted(d.glob("*.yaml")):
                try:
                    recipe = parse_recipe(yaml_file)
                    recipes.append(recipe)
                except Exception:
                    pass  # Skip invalid recipes
            for yml_file in sorted(d.glob("*.yml")):
                try:
                    recipe = parse_recipe(yml_file)
                    recipes.append(recipe)
                except Exception:
                    pass
        return recipes
