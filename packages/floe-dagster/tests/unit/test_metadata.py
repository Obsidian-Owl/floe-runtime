"""Unit tests for DbtModelMetadata.

T038: [P] [US1] Unit tests for DbtModelMetadata.from_manifest_node
"""

from __future__ import annotations

from typing import Any

import pytest


class TestDbtModelMetadata:
    """Test suite for DbtModelMetadata model."""

    @pytest.fixture
    def metadata_class(self) -> Any:
        """Get DbtModelMetadata class."""
        from floe_dagster.models import DbtModelMetadata

        return DbtModelMetadata

    def test_from_manifest_node_basic(
        self,
        metadata_class: Any,
        sample_dbt_manifest_node: dict[str, Any],
    ) -> None:
        """Test basic creation from manifest node."""
        metadata = metadata_class.from_manifest_node(sample_dbt_manifest_node)

        assert metadata.unique_id == "model.my_project.customers"
        assert metadata.name == "customers"
        assert metadata.alias == "customers"
        assert metadata.database == "warehouse"
        assert metadata.schema_name == "analytics"

    def test_from_manifest_node_description(
        self,
        metadata_class: Any,
        sample_dbt_manifest_node: dict[str, Any],
    ) -> None:
        """Test description extraction."""
        metadata = metadata_class.from_manifest_node(sample_dbt_manifest_node)

        assert metadata.description == "Customer dimension table"

    def test_from_manifest_node_tags(
        self,
        metadata_class: Any,
        sample_dbt_manifest_node: dict[str, Any],
    ) -> None:
        """Test tags extraction."""
        metadata = metadata_class.from_manifest_node(sample_dbt_manifest_node)

        assert "pii" in metadata.tags
        assert "customers" in metadata.tags

    def test_from_manifest_node_owner(
        self,
        metadata_class: Any,
        sample_dbt_manifest_node: dict[str, Any],
    ) -> None:
        """Test owner extraction from meta.floe."""
        metadata = metadata_class.from_manifest_node(sample_dbt_manifest_node)

        assert metadata.owner == "data-team"

    def test_from_manifest_node_depends_on(
        self,
        metadata_class: Any,
        sample_dbt_manifest_node: dict[str, Any],
    ) -> None:
        """Test dependencies extraction."""
        metadata = metadata_class.from_manifest_node(sample_dbt_manifest_node)

        assert "source.my_project.raw.raw_customers" in metadata.depends_on

    def test_from_manifest_node_columns(
        self,
        metadata_class: Any,
        sample_dbt_manifest_node: dict[str, Any],
    ) -> None:
        """Test columns extraction."""
        metadata = metadata_class.from_manifest_node(sample_dbt_manifest_node)

        assert "customer_id" in metadata.columns
        assert "email" in metadata.columns

    def test_from_manifest_node_column_metadata(
        self,
        metadata_class: Any,
        sample_dbt_manifest_node: dict[str, Any],
    ) -> None:
        """Test column metadata extraction."""
        metadata = metadata_class.from_manifest_node(sample_dbt_manifest_node)

        email_col = metadata.columns["email"]
        assert email_col.name == "email"
        assert email_col.description == "Customer email address"
        assert email_col.floe_meta.get("classification") == "pii"
        assert email_col.floe_meta.get("pii_type") == "email"

    def test_from_manifest_node_materialization(
        self,
        metadata_class: Any,
        sample_dbt_manifest_node: dict[str, Any],
    ) -> None:
        """Test materialization extraction."""
        metadata = metadata_class.from_manifest_node(sample_dbt_manifest_node)

        assert metadata.materialization == "table"

    def test_from_manifest_node_alias_fallback(
        self,
        metadata_class: Any,
    ) -> None:
        """Test alias falls back to name when not specified."""
        node = {
            "unique_id": "model.proj.my_model",
            "name": "my_model",
            # No alias
            "schema": "public",
            "database": "db",
        }

        metadata = metadata_class.from_manifest_node(node)
        assert metadata.alias == "my_model"

    def test_from_manifest_node_missing_optional_fields(
        self,
        metadata_class: Any,
    ) -> None:
        """Test handling of missing optional fields."""
        node = {
            "unique_id": "model.proj.minimal",
            "name": "minimal",
        }

        metadata = metadata_class.from_manifest_node(node)

        assert metadata.description == ""
        assert metadata.tags == []
        assert metadata.owner is None
        assert metadata.depends_on == []
        assert metadata.columns == {}
        assert metadata.materialization == "view"


class TestColumnMetadata:
    """Test suite for ColumnMetadata model."""

    @pytest.fixture
    def column_class(self) -> Any:
        """Get ColumnMetadata class."""
        from floe_dagster.models import ColumnMetadata

        return ColumnMetadata

    def test_create_column_metadata(self, column_class: Any) -> None:
        """Test creating ColumnMetadata."""
        col = column_class(
            name="email",
            data_type="varchar",
            description="Email address",
            floe_meta={"classification": "pii"},
        )

        assert col.name == "email"
        assert col.data_type == "varchar"
        assert col.description == "Email address"
        assert col.floe_meta["classification"] == "pii"

    def test_column_metadata_defaults(self, column_class: Any) -> None:
        """Test default values."""
        col = column_class(name="id")

        assert col.data_type is None
        assert col.description is None
        assert col.floe_meta == {}


class TestAssetMaterializationResult:
    """Test suite for AssetMaterializationResult model."""

    @pytest.fixture
    def result_class(self) -> Any:
        """Get AssetMaterializationResult class."""
        from floe_dagster.models import AssetMaterializationResult

        return AssetMaterializationResult

    def test_create_success_result(self, result_class: Any) -> None:
        """Test creating success result."""
        result = result_class(
            model_unique_id="model.proj.customers",
            status="success",
            execution_time=1.5,
            rows_affected=1000,
        )

        assert result.status == "success"
        assert result.execution_time == pytest.approx(1.5)
        assert result.rows_affected == 1000
        assert result.error_message is None

    def test_create_error_result(self, result_class: Any) -> None:
        """Test creating error result."""
        result = result_class(
            model_unique_id="model.proj.customers",
            status="error",
            execution_time=0.5,
            error_message="Database connection failed",
        )

        assert result.status == "error"
        assert result.error_message == "Database connection failed"
