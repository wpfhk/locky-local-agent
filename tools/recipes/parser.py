"""tools/recipes/parser.py — Recipe YAML parsing and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Valid action names matching actions/pipeline.py _STEP_RUNNERS + extras
VALID_ACTIONS = {
    "format",
    "test",
    "scan",
    "commit",
    "clean",
    "deps",
    "env",
    "todo",
}

MAX_STEPS = 50


@dataclass
class RecipeStep:
    """A single step in a recipe."""

    action: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class Recipe:
    """Parsed recipe definition."""

    name: str
    description: str = ""
    version: str = "1.0"
    steps: list[RecipeStep] = field(default_factory=list)
    fail_fast: bool = True
    source_path: Path | None = None


def validate_recipe(data: dict[str, Any]) -> list[str]:
    """Validate raw recipe dict. Returns list of errors; empty = valid."""
    errors: list[str] = []

    if not data.get("name") or not isinstance(data.get("name"), str):
        errors.append("'name' is required and must be a string")

    steps = data.get("steps", [])
    if not isinstance(steps, list):
        errors.append("'steps' must be a list")
    elif not steps:
        errors.append("'steps' must contain at least one step")
    elif len(steps) > MAX_STEPS:
        errors.append(f"'steps' exceeds maximum of {MAX_STEPS}")
    else:
        for i, step in enumerate(steps):
            if isinstance(step, str):
                # Simple string format: "format --check"
                action = step.split()[0]
                if action not in VALID_ACTIONS:
                    errors.append(
                        f"steps[{i}]: unknown action '{action}'. "
                        f"Valid: {sorted(VALID_ACTIONS)}"
                    )
            elif isinstance(step, dict):
                action = step.get("action", "")
                if not action:
                    errors.append(f"steps[{i}].action is required")
                elif action not in VALID_ACTIONS:
                    errors.append(
                        f"steps[{i}]: unknown action '{action}'. "
                        f"Valid: {sorted(VALID_ACTIONS)}"
                    )
                args = step.get("args")
                if args is not None and not isinstance(args, dict):
                    errors.append(f"steps[{i}].args must be a dict")
            else:
                errors.append(f"steps[{i}] must be a string or dict")

    return errors


def parse_recipe(path: Path) -> Recipe:
    """Load and validate a recipe YAML file.

    Args:
        path: Path to recipe YAML

    Returns:
        Recipe

    Raises:
        FileNotFoundError: if path doesn't exist
        ValueError: if recipe is invalid
    """
    if not path.exists():
        raise FileNotFoundError(f"Recipe not found: {path}")

    try:
        import yaml  # type: ignore
    except ImportError:
        raise ImportError("PyYAML is required for recipes")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid recipe format in {path}")

    errors = validate_recipe(raw)
    if errors:
        raise ValueError(f"Invalid recipe {path}: {'; '.join(errors)}")

    steps: list[RecipeStep] = []
    for step_data in raw.get("steps", []):
        if isinstance(step_data, str):
            # Parse "format --check" -> action="format", args={"check": True}
            parts = step_data.split()
            action = parts[0]
            args = _parse_cli_args(parts[1:])
            steps.append(RecipeStep(action=action, args=args))
        elif isinstance(step_data, dict):
            steps.append(
                RecipeStep(
                    action=step_data["action"],
                    args=step_data.get("args", {}),
                )
            )

    return Recipe(
        name=raw["name"],
        description=raw.get("description", ""),
        version=str(raw.get("version", "1.0")),
        steps=steps,
        fail_fast=raw.get("fail_fast", True),
        source_path=path,
    )


def _parse_cli_args(parts: list[str]) -> dict[str, Any]:
    """Parse CLI-style args like ['--check', '--severity', 'high'] into dict."""
    args: dict[str, Any] = {}
    i = 0
    while i < len(parts):
        part = parts[i]
        if part.startswith("--"):
            key = part[2:].replace("-", "_")
            # Check if next part is a value or another flag
            if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                args[key] = parts[i + 1]
                i += 2
            else:
                args[key] = True
                i += 1
        else:
            i += 1
    return args
