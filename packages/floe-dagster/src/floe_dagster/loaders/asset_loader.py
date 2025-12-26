"""Asset loader for auto-discovering assets from Python modules.

T028: [010-orchestration-auto-discovery] Create asset loader
Covers: 010-FR-001 through 010-FR-003

This module auto-discovers and loads assets from Python modules listed in
orchestration config, enabling declarative asset registration without explicit imports.
"""

from __future__ import annotations

import importlib
import inspect
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dagster import AssetsDefinition


def load_assets_from_modules(module_paths: list[str]) -> list[AssetsDefinition]:
    """Auto-discover and load assets from Python modules.

    Dynamically imports Python modules and extracts all Dagster asset definitions.
    Supports @asset, @multi_asset, and other asset decorators from Dagster.

    Args:
        module_paths: List of Python module paths to import and scan for assets.
                     Must be valid importable Python module paths.

    Returns:
        List of Dagster AssetsDefinition objects found in the modules.

    Raises:
        ImportError: If module cannot be imported.
        AttributeError: If module is invalid.

    Example:
        >>> asset_modules = ["demo.assets.bronze", "demo.assets.silver"]
        >>> assets = load_assets_from_modules(asset_modules)
        >>> len(assets)
        5
    """
    if not module_paths:
        return []

    from dagster import AssetsDefinition

    all_assets: list[AssetsDefinition] = []

    for module_path in module_paths:
        try:
            module = importlib.import_module(module_path)

            for _name, obj in inspect.getmembers(module):
                if isinstance(obj, AssetsDefinition):
                    all_assets.append(obj)

        except ImportError as e:
            msg = f"Cannot import asset module {module_path}: {e}"
            raise ImportError(msg) from e
        except AttributeError as e:
            msg = f"Invalid asset module {module_path}: {e}"
            raise AttributeError(msg) from e

    return all_assets


def load_assets_from_module_dict(modules_config: dict[str, Any]) -> list[AssetsDefinition]:
    """Load assets from module configuration dictionary.

    Convenience wrapper for loading assets from a config dict with 'asset_modules' key.

    Args:
        modules_config: Dictionary containing 'asset_modules' key with list of module paths.

    Returns:
        List of Dagster AssetsDefinition objects.

    Example:
        >>> config = {"asset_modules": ["demo.assets.bronze"]}
        >>> assets = load_assets_from_module_dict(config)
    """
    module_paths = modules_config.get("asset_modules", [])
    return load_assets_from_modules(module_paths)
