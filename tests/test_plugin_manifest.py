"""tests/test_plugin_manifest.py — Plugin manifest parsing and validation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.plugins.manifest import (
    PluginCommand,
    PluginManifest,
    load_manifest,
    validate_manifest,
)


# ---------------------------------------------------------------------------
# validate_manifest tests
# ---------------------------------------------------------------------------


class TestValidateManifest:
    def test_valid_minimal(self):
        data = {"name": "my-plugin", "version": "1.0.0"}
        assert validate_manifest(data) == []

    def test_valid_full(self):
        data = {
            "name": "my-plugin",
            "version": "1.0.0",
            "description": "A test plugin",
            "author": "Test",
            "commands": [
                {"name": "lint", "description": "Run linter", "entry": "my_plugin.lint:run"}
            ],
            "hooks": {"on_load": "my_plugin.hooks:on_load"},
        }
        assert validate_manifest(data) == []

    def test_missing_name(self):
        errors = validate_manifest({"version": "1.0.0"})
        assert any("name" in e for e in errors)

    def test_invalid_name_format(self):
        errors = validate_manifest({"name": "MyPlugin", "version": "1.0.0"})
        assert any("kebab-case" in e for e in errors)

    def test_name_starts_with_number(self):
        errors = validate_manifest({"name": "1plugin", "version": "1.0.0"})
        assert any("kebab-case" in e for e in errors)

    def test_missing_version(self):
        errors = validate_manifest({"name": "my-plugin"})
        assert any("version" in e for e in errors)

    def test_invalid_version_format(self):
        errors = validate_manifest({"name": "my-plugin", "version": "abc"})
        assert any("semver" in e for e in errors)

    def test_commands_not_list(self):
        errors = validate_manifest(
            {"name": "my-plugin", "version": "1.0.0", "commands": "lint"}
        )
        assert any("list" in e for e in errors)

    def test_command_missing_name(self):
        errors = validate_manifest(
            {"name": "my-plugin", "version": "1.0.0", "commands": [{"entry": "m:f"}]}
        )
        assert any("name" in e for e in errors)

    def test_command_invalid_entry(self):
        errors = validate_manifest(
            {
                "name": "my-plugin",
                "version": "1.0.0",
                "commands": [{"name": "lint", "entry": "invalid-format"}],
            }
        )
        assert any("module.path:function" in e for e in errors)

    def test_hooks_not_dict(self):
        errors = validate_manifest(
            {"name": "my-plugin", "version": "1.0.0", "hooks": "on_load"}
        )
        assert any("dict" in e for e in errors)

    def test_hooks_unknown_key(self):
        errors = validate_manifest(
            {
                "name": "my-plugin",
                "version": "1.0.0",
                "hooks": {"on_start": "m:f"},
            }
        )
        assert any("Unknown hook" in e for e in errors)

    def test_hooks_invalid_entry(self):
        errors = validate_manifest(
            {
                "name": "my-plugin",
                "version": "1.0.0",
                "hooks": {"on_load": "bad"},
            }
        )
        assert any("module.path:function" in e for e in errors)

    def test_command_not_dict(self):
        errors = validate_manifest(
            {"name": "my-plugin", "version": "1.0.0", "commands": ["lint"]}
        )
        assert any("dict" in e for e in errors)


# ---------------------------------------------------------------------------
# load_manifest tests
# ---------------------------------------------------------------------------


class TestLoadManifest:
    def test_load_valid(self, tmp_path):
        (tmp_path / "plugin.yaml").write_text(
            "name: test-plugin\nversion: 1.0.0\ncommands:\n  - name: hello\n    entry: test_mod:run\n"
        )
        manifest = load_manifest(tmp_path / "plugin.yaml")
        assert manifest.name == "test-plugin"
        assert manifest.version == "1.0.0"
        assert len(manifest.commands) == 1
        assert manifest.commands[0].name == "hello"
        assert manifest.plugin_path == tmp_path

    def test_load_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_manifest(tmp_path / "missing.yaml")

    def test_load_invalid_yaml(self, tmp_path):
        (tmp_path / "plugin.yaml").write_text("- not\n- a\n- dict")
        with pytest.raises(ValueError, match="Invalid manifest format"):
            load_manifest(tmp_path / "plugin.yaml")

    def test_load_validation_fails(self, tmp_path):
        (tmp_path / "plugin.yaml").write_text("name: INVALID\nversion: abc")
        with pytest.raises(ValueError, match="Invalid manifest"):
            load_manifest(tmp_path / "plugin.yaml")

    def test_load_with_hooks(self, tmp_path):
        (tmp_path / "plugin.yaml").write_text(
            "name: hook-plugin\nversion: 2.0.0\nhooks:\n  on_load: hooks:init\n"
        )
        manifest = load_manifest(tmp_path / "plugin.yaml")
        assert manifest.hooks == {"on_load": "hooks:init"}

    def test_load_empty_commands(self, tmp_path):
        (tmp_path / "plugin.yaml").write_text(
            "name: empty-cmds\nversion: 1.0.0\ncommands: []\n"
        )
        manifest = load_manifest(tmp_path / "plugin.yaml")
        assert manifest.commands == []


# ---------------------------------------------------------------------------
# PluginManifest / PluginCommand dataclass tests
# ---------------------------------------------------------------------------


class TestDataclasses:
    def test_plugin_command_defaults(self):
        cmd = PluginCommand(name="test")
        assert cmd.description == ""
        assert cmd.entry == ""

    def test_plugin_manifest_defaults(self):
        m = PluginManifest(name="test", version="1.0.0")
        assert m.description == ""
        assert m.author == ""
        assert m.commands == []
        assert m.hooks == {}
        assert m.plugin_path is None
