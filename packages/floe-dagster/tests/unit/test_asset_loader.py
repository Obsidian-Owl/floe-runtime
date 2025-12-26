"""Unit tests for asset loader.

T029: [010-orchestration-auto-discovery] asset loader tests
Covers: 010-FR-001 through 010-FR-003

Tests the load_assets_from_modules function that auto-discovers assets from Python modules.
"""

from __future__ import annotations

from unittest.mock import patch

from dagster import asset
import pytest


class TestLoadAssetsFromModules:
    """Tests for load_assets_from_modules function."""

    def test_load_assets_from_modules_with_empty_list(self) -> None:
        """load_assets_from_modules should return empty list for empty input."""
        from floe_dagster.loaders.asset_loader import load_assets_from_modules

        result = load_assets_from_modules([])

        assert result == []

    def test_load_assets_from_modules_with_single_module(self) -> None:
        """load_assets_from_modules should discover assets from module."""
        from types import ModuleType

        from floe_dagster.loaders.asset_loader import load_assets_from_modules

        @asset
        def bronze_asset() -> dict[str, int]:
            return {"rows": 100}

        mock_module = ModuleType("demo.assets.bronze")
        mock_module.bronze_asset = bronze_asset
        mock_module.other_var = "not_an_asset"

        with patch("floe_dagster.loaders.asset_loader.importlib.import_module") as mock_import:
            mock_import.return_value = mock_module

            result = load_assets_from_modules(["demo.assets.bronze"])

            assert len(result) == 1
            assert result[0] == bronze_asset
            mock_import.assert_called_once_with("demo.assets.bronze")

    def test_load_assets_from_modules_with_multiple_modules(self) -> None:
        """load_assets_from_modules should discover assets from multiple modules."""
        from types import ModuleType

        from floe_dagster.loaders.asset_loader import load_assets_from_modules

        @asset
        def bronze_asset() -> dict[str, int]:
            return {"rows": 100}

        @asset
        def silver_asset() -> dict[str, int]:
            return {"rows": 50}

        bronze_module = ModuleType("demo.assets.bronze")
        bronze_module.bronze_asset = bronze_asset

        silver_module = ModuleType("demo.assets.silver")
        silver_module.silver_asset = silver_asset

        def mock_import_side_effect(module_path: str) -> ModuleType:
            if module_path == "demo.assets.bronze":
                return bronze_module
            return silver_module

        with patch("floe_dagster.loaders.asset_loader.importlib.import_module") as mock_import:
            mock_import.side_effect = mock_import_side_effect

            result = load_assets_from_modules(["demo.assets.bronze", "demo.assets.silver"])

            assert len(result) == 2

    def test_load_assets_from_modules_filters_non_assets(self) -> None:
        """load_assets_from_modules should only include AssetsDefinition instances."""
        from types import ModuleType

        from floe_dagster.loaders.asset_loader import load_assets_from_modules

        @asset
        def valid_asset() -> dict[str, int]:
            return {"rows": 100}

        def regular_function() -> str:
            return "hello"

        mock_module = ModuleType("demo.assets")
        mock_module.valid_asset = valid_asset
        mock_module.regular_function = regular_function
        mock_module.string_var = "hello"
        mock_module.number_var = 42

        with patch("floe_dagster.loaders.asset_loader.importlib.import_module") as mock_import:
            mock_import.return_value = mock_module

            result = load_assets_from_modules(["demo.assets"])

            assert len(result) == 1
            assert result[0] == valid_asset

    def test_load_assets_from_modules_raises_on_import_error(self) -> None:
        """load_assets_from_modules should raise ImportError if module cannot be imported."""
        from floe_dagster.loaders.asset_loader import load_assets_from_modules

        with patch("floe_dagster.loaders.asset_loader.importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("No module named 'nonexistent'")

            with pytest.raises(ImportError) as exc_info:
                load_assets_from_modules(["nonexistent.module"])

            assert "Cannot import asset module" in str(exc_info.value)
            assert "nonexistent.module" in str(exc_info.value)

    def test_load_assets_from_modules_handles_module_without_raising(self) -> None:
        """load_assets_from_modules should gracefully handle modules with no assets."""
        from types import ModuleType

        from floe_dagster.loaders.asset_loader import load_assets_from_modules

        mock_module = ModuleType("demo.invalid")
        mock_module.regular_var = "not an asset"

        with patch("floe_dagster.loaders.asset_loader.importlib.import_module") as mock_import:
            mock_import.return_value = mock_module

            result = load_assets_from_modules(["demo.invalid"])

            assert result == []


class TestLoadAssetsFromModuleDict:
    """Tests for load_assets_from_module_dict function."""

    def test_load_assets_from_module_dict_with_asset_modules_key(self) -> None:
        """load_assets_from_module_dict should extract asset_modules from config."""
        from types import ModuleType

        from floe_dagster.loaders.asset_loader import load_assets_from_module_dict

        @asset
        def bronze_asset() -> dict[str, int]:
            return {"rows": 100}

        config = {"asset_modules": ["demo.assets.bronze"]}

        mock_module = ModuleType("demo.assets.bronze")
        mock_module.bronze_asset = bronze_asset

        with patch("floe_dagster.loaders.asset_loader.importlib.import_module") as mock_import:
            mock_import.return_value = mock_module

            result = load_assets_from_module_dict(config)

            assert len(result) == 1
            mock_import.assert_called_once_with("demo.assets.bronze")

    def test_load_assets_from_module_dict_with_empty_config(self) -> None:
        """load_assets_from_module_dict should return empty list for empty config."""
        from floe_dagster.loaders.asset_loader import load_assets_from_module_dict

        result = load_assets_from_module_dict({})

        assert result == []

    def test_load_assets_from_module_dict_with_missing_key(self) -> None:
        """load_assets_from_module_dict should handle missing asset_modules key."""
        from floe_dagster.loaders.asset_loader import load_assets_from_module_dict

        config = {"other_key": "value"}

        result = load_assets_from_module_dict(config)

        assert result == []

    def test_load_assets_from_module_dict_with_multiple_modules(self) -> None:
        """load_assets_from_module_dict should handle multiple module paths."""
        from types import ModuleType

        from floe_dagster.loaders.asset_loader import load_assets_from_module_dict

        @asset
        def bronze_asset() -> dict[str, int]:
            return {"rows": 100}

        @asset
        def silver_asset() -> dict[str, int]:
            return {"rows": 50}

        config = {"asset_modules": ["demo.assets.bronze", "demo.assets.silver"]}

        bronze_module = ModuleType("demo.assets.bronze")
        bronze_module.bronze_asset = bronze_asset

        silver_module = ModuleType("demo.assets.silver")
        silver_module.silver_asset = silver_asset

        def mock_import_side_effect(module_path: str) -> ModuleType:
            if module_path == "demo.assets.bronze":
                return bronze_module
            return silver_module

        with patch("floe_dagster.loaders.asset_loader.importlib.import_module") as mock_import:
            mock_import.side_effect = mock_import_side_effect

            result = load_assets_from_module_dict(config)

            assert len(result) == 2
