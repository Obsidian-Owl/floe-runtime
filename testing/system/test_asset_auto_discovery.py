"""Integration tests for asset module auto-discovery.

T031: [010-orchestration-auto-discovery] Test asset module auto-discovery integration
Covers: 010-FR-001, 010-FR-002, 010-FR-003

Tests that assets defined in Python modules are automatically discovered and loaded
when specified in orchestration.asset_modules configuration.

This validates the end-to-end asset auto-discovery flow using real asset modules
from testing/fixtures/test_assets/.
"""

from __future__ import annotations

from dagster import Definitions
import pytest

from floe_dagster.definitions import FloeDefinitions
from testing.base_classes import IntegrationTestBase


class TestAssetAutoDiscovery(IntegrationTestBase):
    """Integration tests for asset module auto-discovery."""

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-001", "010-FR-002", "010-FR-003")
    def test_discovers_assets_from_single_module(self) -> None:
        """Verify assets are discovered from a single Python module.

        Requirements:
            - FR-001: Auto-discover assets from Python modules
            - FR-002: Support @asset decorator
            - FR-003: Load assets into Dagster Definitions
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "asset_modules": [
                    "testing.fixtures.test_assets.bronze_assets",
                ]
            },
        }

        defs = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

        assert isinstance(defs, Definitions)
        assert defs.assets is not None

        asset_keys = {asset.key for asset in defs.assets}
        assert len(asset_keys) == 3

        expected_keys = {"bronze_customers", "bronze_orders", "bronze_products"}
        actual_keys = {key.path[0] for key in asset_keys}
        assert actual_keys == expected_keys

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-001", "010-FR-002", "010-FR-003")
    def test_discovers_assets_from_multiple_modules(self) -> None:
        """Verify assets are discovered from multiple Python modules.

        Requirements:
            - FR-001: Auto-discover assets from multiple modules
            - FR-002: Support @asset decorator across modules
            - FR-003: Combine assets from all modules
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "asset_modules": [
                    "testing.fixtures.test_assets.bronze_assets",
                    "testing.fixtures.test_assets.silver_assets",
                ]
            },
        }

        defs = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

        assert isinstance(defs, Definitions)
        assert defs.assets is not None

        asset_keys = {asset.key for asset in defs.assets}
        assert len(asset_keys) == 5

        expected_keys = {
            "bronze_customers",
            "bronze_orders",
            "bronze_products",
            "silver_customer_metrics",
            "silver_order_summary",
        }
        actual_keys = {key.path[0] for key in asset_keys}
        assert actual_keys == expected_keys

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-001")
    def test_graceful_degradation_on_invalid_module(self) -> None:
        """Verify graceful degradation when module cannot be imported.

        Requirements:
            - FR-001: System handles invalid module paths gracefully
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "asset_modules": [
                    "nonexistent.module.path",
                ]
            },
        }

        defs = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

        assert isinstance(defs, Definitions)

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-001", "010-FR-002")
    def test_combines_auto_discovered_with_inline_assets(self) -> None:
        """Verify auto-discovered assets combine with inline assets.

        Requirements:
            - FR-001: Auto-discovered assets work alongside inline definitions
            - FR-002: Both @asset types are included
        """
        from dagster import asset

        @asset
        def inline_asset() -> dict[str, int]:
            return {"rows": 10}

        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "asset_modules": [
                    "testing.fixtures.test_assets.bronze_assets",
                ]
            },
        }

        defs = FloeDefinitions.from_compiled_artifacts(
            artifacts_dict=artifacts,
            assets=[inline_asset],
        )

        assert isinstance(defs, Definitions)
        assert defs.assets is not None

        asset_keys = {asset.key for asset in defs.assets}
        assert len(asset_keys) == 4

        expected_keys = {
            "bronze_customers",
            "bronze_orders",
            "bronze_products",
            "inline_asset",
        }
        actual_keys = {key.path[0] for key in asset_keys}
        assert actual_keys == expected_keys

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-001")
    def test_empty_module_list_does_not_error(self) -> None:
        """Verify empty asset_modules list does not cause errors.

        Requirements:
            - FR-001: Empty configuration is valid
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "asset_modules": [],
            },
        }

        defs = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

        assert isinstance(defs, Definitions)

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-001")
    def test_missing_asset_modules_key_does_not_error(self) -> None:
        """Verify missing asset_modules key does not cause errors.

        Requirements:
            - FR-001: Missing configuration is valid
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {},
        }

        defs = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

        assert isinstance(defs, Definitions)
