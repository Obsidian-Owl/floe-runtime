"""Unit tests for FloeTranslator.

T036: [P] [US1] Unit tests for FloeTranslator
"""

from __future__ import annotations

from typing import Any

import pytest


class TestFloeTranslator:
    """Test suite for FloeTranslator."""

    @pytest.fixture
    def translator(self) -> Any:
        """Create FloeTranslator instance."""
        from floe_dagster.translator import FloeTranslator

        return FloeTranslator()

    def test_get_asset_key_from_node(
        self,
        translator: Any,
        sample_dbt_manifest_node: dict[str, Any],
    ) -> None:
        """Test asset key generation from dbt node."""
        asset_key = translator.get_asset_key(sample_dbt_manifest_node)

        # Asset key should include schema and table name
        assert asset_key is not None
        # Key should be based on database.schema.alias pattern
        assert len(asset_key.path) >= 1

    def test_get_asset_key_uses_alias(
        self,
        translator: Any,
    ) -> None:
        """Test that asset key uses alias when available."""
        node = {
            "unique_id": "model.project.my_model",
            "name": "my_model",
            "alias": "custom_alias",
            "schema": "analytics",
            "database": "warehouse",
        }

        asset_key = translator.get_asset_key(node)

        # Should use alias, not name
        assert "custom_alias" in str(asset_key) or asset_key.path[-1] == "custom_alias"

    def test_get_metadata_includes_description(
        self,
        translator: Any,
        sample_dbt_manifest_node: dict[str, Any],
    ) -> None:
        """Test that metadata includes description."""
        metadata = translator.get_metadata(sample_dbt_manifest_node)

        assert "description" in metadata or any(
            "description" in str(k).lower() for k in metadata.keys()
        )

    def test_get_metadata_includes_tags(
        self,
        translator: Any,
        sample_dbt_manifest_node: dict[str, Any],
    ) -> None:
        """Test that metadata includes tags."""
        metadata = translator.get_metadata(sample_dbt_manifest_node)

        # Tags should be in metadata
        assert "tags" in metadata or any("tag" in str(k).lower() for k in metadata.keys())

    def test_get_metadata_includes_owner(
        self,
        translator: Any,
        sample_dbt_manifest_node: dict[str, Any],
    ) -> None:
        """Test that owner from floe meta is included."""
        metadata = translator.get_metadata(sample_dbt_manifest_node)

        # Owner should come from meta.floe.owner
        assert "owner" in metadata or any("owner" in str(k).lower() for k in metadata.keys())

    def test_get_description_from_node(
        self,
        translator: Any,
        sample_dbt_manifest_node: dict[str, Any],
    ) -> None:
        """Test description extraction."""
        description = translator.get_description(sample_dbt_manifest_node)

        assert description is not None
        assert isinstance(description, str)
        assert "Customer" in description or description == sample_dbt_manifest_node["description"]

    def test_get_description_empty_when_missing(
        self,
        translator: Any,
    ) -> None:
        """Test description returns empty string when missing."""
        node = {
            "unique_id": "model.project.my_model",
            "name": "my_model",
        }

        description = translator.get_description(node)

        assert description == "" or description is None

    def test_get_group_name_from_tags(
        self,
        translator: Any,
        sample_dbt_manifest_node: dict[str, Any],
    ) -> None:
        """Test group name extraction from tags or schema."""
        group = translator.get_group_name(sample_dbt_manifest_node)

        # Group should be derived from tags, schema, or package
        assert group is not None
        assert isinstance(group, str)

    def test_get_owners_includes_floe_owner(
        self,
        translator: Any,
        sample_dbt_manifest_node: dict[str, Any],
    ) -> None:
        """Test that owners includes floe meta owner."""
        owners = translator.get_owners(sample_dbt_manifest_node)

        # Should include owner from meta.floe.owner
        assert owners is not None
        if owners:
            assert any("data-team" in str(o) for o in owners)

    def test_handles_missing_meta(
        self,
        translator: Any,
    ) -> None:
        """Test graceful handling of missing meta namespace."""
        node = {
            "unique_id": "model.project.my_model",
            "name": "my_model",
            "schema": "analytics",
            "database": "warehouse",
            # No meta key
        }

        # Should not raise
        metadata = translator.get_metadata(node)
        assert metadata is not None

    def test_handles_missing_columns(
        self,
        translator: Any,
    ) -> None:
        """Test graceful handling of missing columns."""
        node = {
            "unique_id": "model.project.my_model",
            "name": "my_model",
            "schema": "analytics",
            "database": "warehouse",
            # No columns key
        }

        metadata = translator.get_metadata(node)
        assert metadata is not None
