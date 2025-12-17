"""Unit tests for floe-iceberg configuration models.

Tests for:
- T027: TableIdentifier parsing
- T028: PartitionTransform validation
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from floe_iceberg.config import (
    IcebergIOManagerConfig,
    MaterializationMetadata,
    PartitionTransform,
    PartitionTransformType,
    SnapshotInfo,
    TableIdentifier,
    WriteMode,
)


class TestWriteMode:
    """Tests for WriteMode enum."""

    def test_append_value(self) -> None:
        """Test APPEND enum value."""
        assert WriteMode.APPEND.value == "append"

    def test_overwrite_value(self) -> None:
        """Test OVERWRITE enum value."""
        assert WriteMode.OVERWRITE.value == "overwrite"

    def test_string_comparison(self) -> None:
        """Test WriteMode can be compared to strings."""
        assert WriteMode.APPEND == "append"
        assert WriteMode.OVERWRITE == "overwrite"


class TestTableIdentifier:
    """Tests for TableIdentifier Pydantic model."""

    def test_simple_identifier(self) -> None:
        """Test simple namespace.table identifier."""
        tid = TableIdentifier(namespace="bronze", name="customers")

        assert tid.namespace == "bronze"
        assert tid.name == "customers"
        assert str(tid) == "bronze.customers"

    def test_nested_namespace(self) -> None:
        """Test nested namespace identifier."""
        tid = TableIdentifier(namespace="bronze.raw", name="events")

        assert tid.namespace == "bronze.raw"
        assert tid.name == "events"
        assert str(tid) == "bronze.raw.events"

    def test_from_string_simple(self) -> None:
        """Test parsing simple identifier from string."""
        tid = TableIdentifier.from_string("bronze.customers")

        assert tid.namespace == "bronze"
        assert tid.name == "customers"

    def test_from_string_nested_namespace(self) -> None:
        """Test parsing nested namespace from string."""
        tid = TableIdentifier.from_string("bronze.raw.events")

        assert tid.namespace == "bronze.raw"
        assert tid.name == "events"

    def test_from_string_deeply_nested(self) -> None:
        """Test parsing deeply nested namespace from string."""
        tid = TableIdentifier.from_string("a.b.c.d.table")

        assert tid.namespace == "a.b.c.d"
        assert tid.name == "table"

    def test_from_string_invalid_no_dot(self) -> None:
        """Test parsing fails without namespace separator."""
        with pytest.raises(ValueError) as exc_info:
            TableIdentifier.from_string("customers")

        assert "Invalid table identifier" in str(exc_info.value)

    def test_name_cannot_contain_dots(self) -> None:
        """Test table name cannot contain dots."""
        with pytest.raises(ValidationError) as exc_info:
            TableIdentifier(namespace="bronze", name="my.table")

        assert "name" in str(exc_info.value).lower()

    def test_namespace_required(self) -> None:
        """Test namespace is required."""
        with pytest.raises(ValidationError):
            TableIdentifier(name="customers")  # type: ignore[call-arg]

    def test_name_required(self) -> None:
        """Test name is required."""
        with pytest.raises(ValidationError):
            TableIdentifier(namespace="bronze")  # type: ignore[call-arg]

    def test_empty_namespace_rejected(self) -> None:
        """Test empty namespace is rejected."""
        with pytest.raises(ValidationError):
            TableIdentifier(namespace="", name="customers")

    def test_empty_name_rejected(self) -> None:
        """Test empty name is rejected."""
        with pytest.raises(ValidationError):
            TableIdentifier(namespace="bronze", name="")

    def test_frozen(self) -> None:
        """Test TableIdentifier is immutable."""
        tid = TableIdentifier(namespace="bronze", name="customers")

        with pytest.raises(ValidationError):
            tid.name = "orders"  # type: ignore[misc]


class TestPartitionTransformType:
    """Tests for PartitionTransformType enum."""

    def test_all_transform_types(self) -> None:
        """Test all transform type values."""
        assert PartitionTransformType.IDENTITY.value == "identity"
        assert PartitionTransformType.YEAR.value == "year"
        assert PartitionTransformType.MONTH.value == "month"
        assert PartitionTransformType.DAY.value == "day"
        assert PartitionTransformType.HOUR.value == "hour"
        assert PartitionTransformType.BUCKET.value == "bucket"
        assert PartitionTransformType.TRUNCATE.value == "truncate"


class TestPartitionTransform:
    """Tests for PartitionTransform Pydantic model."""

    def test_identity_transform(self) -> None:
        """Test identity transform without param."""
        pt = PartitionTransform(
            source_column="region",
            transform_type=PartitionTransformType.IDENTITY,
        )

        assert pt.source_column == "region"
        assert pt.transform_type == PartitionTransformType.IDENTITY
        assert pt.param is None

    def test_day_transform(self) -> None:
        """Test day transform for timestamps."""
        pt = PartitionTransform(
            source_column="created_at",
            transform_type=PartitionTransformType.DAY,
        )

        assert pt.source_column == "created_at"
        assert pt.transform_type == PartitionTransformType.DAY

    def test_bucket_transform_requires_param(self) -> None:
        """Test bucket transform requires param."""
        with pytest.raises(ValidationError) as exc_info:
            PartitionTransform(
                source_column="customer_id",
                transform_type=PartitionTransformType.BUCKET,
            )

        assert "param" in str(exc_info.value).lower()

    def test_bucket_transform_with_param(self) -> None:
        """Test bucket transform with param."""
        pt = PartitionTransform(
            source_column="customer_id",
            transform_type=PartitionTransformType.BUCKET,
            param=16,
        )

        assert pt.param == 16

    def test_truncate_transform_requires_param(self) -> None:
        """Test truncate transform requires param."""
        with pytest.raises(ValidationError) as exc_info:
            PartitionTransform(
                source_column="name",
                transform_type=PartitionTransformType.TRUNCATE,
            )

        assert "param" in str(exc_info.value).lower()

    def test_truncate_transform_with_param(self) -> None:
        """Test truncate transform with width param."""
        pt = PartitionTransform(
            source_column="name",
            transform_type=PartitionTransformType.TRUNCATE,
            param=10,
        )

        assert pt.param == 10

    def test_param_must_be_positive(self) -> None:
        """Test param must be >= 1."""
        with pytest.raises(ValidationError):
            PartitionTransform(
                source_column="id",
                transform_type=PartitionTransformType.BUCKET,
                param=0,
            )

    def test_source_column_required(self) -> None:
        """Test source_column is required."""
        with pytest.raises(ValidationError):
            PartitionTransform(transform_type=PartitionTransformType.DAY)  # type: ignore[call-arg]

    def test_frozen(self) -> None:
        """Test PartitionTransform is immutable."""
        pt = PartitionTransform(
            source_column="date",
            transform_type=PartitionTransformType.DAY,
        )

        with pytest.raises(ValidationError):
            pt.source_column = "other"  # type: ignore[misc]


class TestSnapshotInfo:
    """Tests for SnapshotInfo Pydantic model."""

    def test_basic_snapshot(self) -> None:
        """Test basic snapshot info."""
        snap = SnapshotInfo(
            snapshot_id=123456789,
            timestamp_ms=1702857600000,
            operation="append",
        )

        assert snap.snapshot_id == 123456789
        assert snap.operation == "append"

    def test_timestamp_property(self) -> None:
        """Test timestamp property conversion."""
        snap = SnapshotInfo(
            snapshot_id=1,
            timestamp_ms=1702857600000,  # 2023-12-18 00:00:00 UTC
            operation="append",
        )

        expected = datetime(2023, 12, 18, 0, 0, 0, tzinfo=timezone.utc)
        assert snap.timestamp == expected

    def test_added_records_property(self) -> None:
        """Test added_records from summary."""
        snap = SnapshotInfo(
            snapshot_id=1,
            timestamp_ms=1000,
            operation="append",
            summary={"added-records": "100", "added-data-files": "1"},
        )

        assert snap.added_records == 100

    def test_added_records_default_zero(self) -> None:
        """Test added_records defaults to 0."""
        snap = SnapshotInfo(
            snapshot_id=1,
            timestamp_ms=1000,
            operation="append",
        )

        assert snap.added_records == 0

    def test_deleted_records_property(self) -> None:
        """Test deleted_records from summary."""
        snap = SnapshotInfo(
            snapshot_id=1,
            timestamp_ms=1000,
            operation="delete",
            summary={"deleted-records": "50"},
        )

        assert snap.deleted_records == 50

    def test_with_manifest_list(self) -> None:
        """Test snapshot with manifest list path."""
        snap = SnapshotInfo(
            snapshot_id=1,
            timestamp_ms=1000,
            operation="append",
            manifest_list="s3://bucket/metadata/snap-1-manifest-list.avro",
        )

        assert snap.manifest_list == "s3://bucket/metadata/snap-1-manifest-list.avro"


class TestMaterializationMetadata:
    """Tests for MaterializationMetadata model."""

    def test_full_metadata(self) -> None:
        """Test full materialization metadata."""
        meta = MaterializationMetadata(
            table="bronze.customers",
            namespace="bronze",
            table_name="customers",
            snapshot_id=123456789,
            num_rows=1000,
            write_mode=WriteMode.APPEND,
            schema_evolved=True,
        )

        assert meta.table == "bronze.customers"
        assert meta.namespace == "bronze"
        assert meta.table_name == "customers"
        assert meta.snapshot_id == 123456789
        assert meta.num_rows == 1000
        assert meta.write_mode == WriteMode.APPEND
        assert meta.schema_evolved is True

    def test_schema_evolved_default_false(self) -> None:
        """Test schema_evolved defaults to False."""
        meta = MaterializationMetadata(
            table="bronze.customers",
            namespace="bronze",
            table_name="customers",
            snapshot_id=1,
            num_rows=100,
            write_mode=WriteMode.OVERWRITE,
        )

        assert meta.schema_evolved is False


class TestIcebergIOManagerConfig:
    """Tests for IcebergIOManagerConfig Pydantic model."""

    def test_minimal_config(self) -> None:
        """Test minimal valid config."""
        config = IcebergIOManagerConfig(
            catalog_uri="http://localhost:8181/api/catalog",
            warehouse="my_warehouse",
        )

        assert config.catalog_uri == "http://localhost:8181/api/catalog"
        assert config.warehouse == "my_warehouse"
        assert config.default_namespace == "public"
        assert config.write_mode == WriteMode.APPEND
        assert config.schema_evolution_enabled is True
        assert config.auto_create_tables is True

    def test_full_config(self) -> None:
        """Test full config with all options."""
        config = IcebergIOManagerConfig(
            catalog_uri="https://polaris.example.com/api/catalog",
            warehouse="production",
            client_id="my_client",
            client_secret="my_secret",
            default_namespace="bronze",
            write_mode=WriteMode.OVERWRITE,
            schema_evolution_enabled=False,
            auto_create_tables=False,
            partition_column="created_at",
        )

        assert config.catalog_uri == "https://polaris.example.com/api/catalog"
        assert config.warehouse == "production"
        assert config.client_id == "my_client"
        assert config.client_secret.get_secret_value() == "my_secret"
        assert config.default_namespace == "bronze"
        assert config.write_mode == WriteMode.OVERWRITE
        assert config.schema_evolution_enabled is False
        assert config.auto_create_tables is False
        assert config.partition_column == "created_at"

    def test_uri_validation(self) -> None:
        """Test URI must start with http:// or https://."""
        with pytest.raises(ValidationError):
            IcebergIOManagerConfig(
                catalog_uri="ftp://invalid.example.com",
                warehouse="test",
            )

    def test_uri_trailing_slash_removed(self) -> None:
        """Test trailing slash is normalized."""
        config = IcebergIOManagerConfig(
            catalog_uri="http://localhost:8181/api/catalog/",
            warehouse="test",
        )

        assert not config.catalog_uri.endswith("/")

    def test_token_auth(self) -> None:
        """Test token-based authentication."""
        config = IcebergIOManagerConfig(
            catalog_uri="http://localhost:8181/api/catalog",
            warehouse="test",
            token="bearer_token",
        )

        assert config.token.get_secret_value() == "bearer_token"
        assert config.client_id is None

    def test_frozen(self) -> None:
        """Test config is immutable."""
        config = IcebergIOManagerConfig(
            catalog_uri="http://localhost:8181/api/catalog",
            warehouse="test",
        )

        with pytest.raises(ValidationError):
            config.warehouse = "other"  # type: ignore[misc]
