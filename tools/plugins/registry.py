"""tools/plugins/registry.py — Plugin registration and management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from .loader import PluginLoader
from .manifest import PluginManifest

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Central registry for loaded plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginManifest] = {}
        self._commands: dict[str, Callable] = {}
        self._loader = PluginLoader()

    def register(self, manifest: PluginManifest) -> None:
        """Register a plugin and import its commands.

        Args:
            manifest: Validated PluginManifest

        Raises:
            ValueError: if plugin name already registered
        """
        if manifest.name in self._plugins:
            raise ValueError(f"Plugin '{manifest.name}' is already registered")

        # Import command entry points
        for cmd in manifest.commands:
            if cmd.entry:
                try:
                    func = self._loader.import_entry(
                        cmd.entry, manifest.plugin_path
                    )
                    self._commands[cmd.name] = func
                except (ImportError, ValueError) as exc:
                    logger.warning(
                        "Failed to import command '%s' from plugin '%s': %s",
                        cmd.name,
                        manifest.name,
                        exc,
                    )

        # Call on_load hook
        on_load = manifest.hooks.get("on_load")
        if on_load:
            try:
                hook_func = self._loader.import_entry(
                    on_load, manifest.plugin_path
                )
                hook_func()
            except Exception as exc:
                logger.warning(
                    "on_load hook failed for plugin '%s': %s", manifest.name, exc
                )

        self._plugins[manifest.name] = manifest

    def unregister(self, name: str) -> bool:
        """Remove a plugin and its commands.

        Args:
            name: Plugin name

        Returns:
            True if removed, False if not found
        """
        manifest = self._plugins.get(name)
        if not manifest:
            return False

        # Call on_unload hook
        on_unload = manifest.hooks.get("on_unload")
        if on_unload:
            try:
                hook_func = self._loader.import_entry(
                    on_unload, manifest.plugin_path
                )
                hook_func()
            except Exception as exc:
                logger.warning(
                    "on_unload hook failed for plugin '%s': %s", name, exc
                )

        # Remove commands
        for cmd in manifest.commands:
            self._commands.pop(cmd.name, None)

        del self._plugins[name]
        return True

    def get_command(self, name: str) -> Callable | None:
        """Get a command function by name.

        Args:
            name: Command name

        Returns:
            Callable or None
        """
        return self._commands.get(name)

    def list_plugins(self) -> list[PluginManifest]:
        """Return all registered plugins."""
        return list(self._plugins.values())

    def list_commands(self) -> dict[str, str]:
        """Return command name -> plugin name mapping."""
        result: dict[str, str] = {}
        for manifest in self._plugins.values():
            for cmd in manifest.commands:
                if cmd.name in self._commands:
                    result[cmd.name] = manifest.name
        return result

    def load_all(self, *plugin_dirs: Path) -> dict[str, str | None]:
        """Discover, load, and register all plugins from directories.

        Args:
            plugin_dirs: One or more directories to scan

        Returns:
            {plugin_name: None (success) or error_message}
        """
        results: dict[str, str | None] = {}

        for plugins_dir in plugin_dirs:
            manifest_paths = self._loader.discover(plugins_dir)
            for manifest_path in manifest_paths:
                try:
                    manifest = self._loader.load(manifest_path)
                    self.register(manifest)
                    results[manifest.name] = None
                except Exception as exc:
                    dir_name = manifest_path.parent.name
                    results[dir_name] = str(exc)

        return results
