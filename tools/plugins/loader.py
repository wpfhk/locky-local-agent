"""tools/plugins/loader.py — Plugin discovery and dynamic import."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Callable

from .manifest import PluginManifest, load_manifest


class PluginLoader:
    """Discovers plugins and imports their entry points."""

    @staticmethod
    def discover(plugins_dir: Path) -> list[Path]:
        """Find directories containing plugin.yaml.

        Args:
            plugins_dir: Root directory to scan (e.g. ~/.locky/plugins/)

        Returns:
            List of paths to plugin.yaml files
        """
        if not plugins_dir.is_dir():
            return []

        manifests = []
        for child in sorted(plugins_dir.iterdir()):
            if not child.is_dir():
                continue
            manifest_path = child / "plugin.yaml"
            if manifest_path.is_file():
                manifests.append(manifest_path)
        return manifests

    @staticmethod
    def load(manifest_path: Path) -> PluginManifest:
        """Parse and validate a plugin manifest.

        Args:
            manifest_path: Path to plugin.yaml

        Returns:
            PluginManifest
        """
        return load_manifest(manifest_path)

    @staticmethod
    def import_entry(entry: str, plugin_path: Path | None = None) -> Callable:
        """Dynamically import 'module.path:function' from a plugin.

        Args:
            entry: Entry point string like 'my_plugin.lint:run'
            plugin_path: Optional plugin directory to add to sys.path

        Returns:
            The callable function

        Raises:
            ImportError: if module or function not found
            ValueError: if entry format is invalid
        """
        if ":" not in entry:
            raise ValueError(
                f"Invalid entry format: '{entry}'. Expected 'module.path:function'"
            )

        module_path, func_name = entry.rsplit(":", 1)

        # Temporarily add plugin_path to sys.path
        added_path = False
        if plugin_path and str(plugin_path) not in sys.path:
            sys.path.insert(0, str(plugin_path))
            added_path = True

        try:
            # Try direct import first
            try:
                mod = importlib.import_module(module_path)
            except ImportError:
                # Try loading as file from plugin_path
                if plugin_path:
                    parts = module_path.split(".")
                    file_path = plugin_path / "/".join(parts[:-1]) / f"{parts[-1]}.py"
                    if not file_path.exists():
                        file_path = plugin_path / f"{module_path.replace('.', '/')}.py"
                    if file_path.exists():
                        spec = importlib.util.spec_from_file_location(
                            module_path, file_path
                        )
                        if spec and spec.loader:
                            mod = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(mod)  # type: ignore[union-attr]
                        else:
                            raise
                    else:
                        raise
                else:
                    raise

            if not hasattr(mod, func_name):
                raise ImportError(
                    f"Function '{func_name}' not found in module '{module_path}'"
                )

            return getattr(mod, func_name)
        finally:
            if added_path and str(plugin_path) in sys.path:
                sys.path.remove(str(plugin_path))
