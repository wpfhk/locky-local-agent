"""tools/plugins/manifest.py — Plugin manifest parsing and validation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PluginCommand:
    """A command exposed by a plugin."""

    name: str
    description: str = ""
    entry: str = ""  # "module.path:function"


@dataclass
class PluginManifest:
    """Parsed plugin.yaml manifest."""

    name: str
    version: str
    description: str = ""
    author: str = ""
    commands: list[PluginCommand] = field(default_factory=list)
    hooks: dict[str, str] = field(default_factory=dict)
    plugin_path: Path | None = None


_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9\-]*$")
_ENTRY_PATTERN = re.compile(r"^[\w.]+:\w+$")
_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+")


def validate_manifest(data: dict[str, Any]) -> list[str]:
    """Validate raw manifest dict. Returns list of error strings; empty = valid."""
    errors: list[str] = []

    # name
    name = data.get("name")
    if not name or not isinstance(name, str):
        errors.append("'name' is required and must be a string")
    elif not _NAME_PATTERN.match(name):
        errors.append(f"'name' must be kebab-case (got: '{name}')")

    # version
    version = data.get("version")
    if not version or not isinstance(version, str):
        errors.append("'version' is required and must be a string")
    elif not _SEMVER_PATTERN.match(version):
        errors.append(f"'version' must follow semver (got: '{version}')")

    # commands
    commands = data.get("commands", [])
    if not isinstance(commands, list):
        errors.append("'commands' must be a list")
    else:
        for i, cmd in enumerate(commands):
            if not isinstance(cmd, dict):
                errors.append(f"commands[{i}] must be a dict")
                continue
            if not cmd.get("name"):
                errors.append(f"commands[{i}].name is required")
            entry = cmd.get("entry", "")
            if entry and not _ENTRY_PATTERN.match(entry):
                errors.append(
                    f"commands[{i}].entry must be 'module.path:function' (got: '{entry}')"
                )

    # hooks
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        errors.append("'hooks' must be a dict")
    else:
        valid_hooks = {"on_load", "on_unload"}
        for key, val in hooks.items():
            if key not in valid_hooks:
                errors.append(f"Unknown hook: '{key}'. Valid: {valid_hooks}")
            if val and not _ENTRY_PATTERN.match(str(val)):
                errors.append(f"hooks.{key} must be 'module.path:function'")

    return errors


def load_manifest(path: Path) -> PluginManifest:
    """Load and validate a plugin.yaml file.

    Args:
        path: Path to plugin.yaml

    Returns:
        PluginManifest

    Raises:
        FileNotFoundError: if path doesn't exist
        ValueError: if manifest is invalid
    """
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")

    try:
        import yaml  # type: ignore
    except ImportError:
        raise ImportError("PyYAML is required for plugin manifests")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid manifest format in {path}")

    errors = validate_manifest(raw)
    if errors:
        raise ValueError(f"Invalid manifest {path}: {'; '.join(errors)}")

    commands = []
    for cmd_data in raw.get("commands", []):
        commands.append(
            PluginCommand(
                name=cmd_data.get("name", ""),
                description=cmd_data.get("description", ""),
                entry=cmd_data.get("entry", ""),
            )
        )

    return PluginManifest(
        name=raw["name"],
        version=raw["version"],
        description=raw.get("description", ""),
        author=raw.get("author", ""),
        commands=commands,
        hooks=raw.get("hooks", {}),
        plugin_path=path.parent,
    )
