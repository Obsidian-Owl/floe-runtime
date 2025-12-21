"""Unit tests for loader models.

Tests for Pydantic models in the loaders module.
The actual I/O operations are tested in integration tests.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from floe_synthetic.loaders.iceberg import IcebergLoaderConfig, LoadResult


class TestIcebergLoaderConfig:
    """Tests for IcebergLoaderConfig Pydantic model."""

    def test_default_values(self) -> None:
        """Config has sensible defaults from environment/defaults."""
        config = IcebergLoaderConfig()
        assert config.catalog_name == "polaris"
        assert config.catalog_uri == "http://localhost:8181/api/catalog"
        assert config.warehouse == "warehouse"
        assert config.credential is None
        assert config.s3_endpoint is None
        assert config.s3_region == "us-east-1"

    def test_custom_values(self) -> None:
        """Config accepts custom values."""
        config = IcebergLoaderConfig(
            catalog_name="my_catalog",
            catalog_uri="http://polaris:8181/api/catalog",
            warehouse="my_warehouse",
            credential="client:secret",
            s3_endpoint="http://localstack:4566",
            s3_region="eu-west-1",
        )
        assert config.catalog_name == "my_catalog"
        assert config.catalog_uri == "http://polaris:8181/api/catalog"
        assert config.warehouse == "my_warehouse"
        assert config.credential == "client:secret"
        assert config.s3_endpoint == "http://localstack:4566"
        assert config.s3_region == "eu-west-1"

    def test_extra_fields_ignored(self) -> None:
        """Extra fields are ignored (not forbidden) per SettingsConfigDict."""
        # BaseSettings with extra="ignore" allows extra fields
        config = IcebergLoaderConfig(
            catalog_name="test",
            extra_field="ignored",  # type: ignore[call-arg]
        )
        assert config.catalog_name == "test"
        assert not hasattr(config, "extra_field")


class TestLoadResult:
    """Tests for LoadResult Pydantic model."""

    def test_valid_load_result(self) -> None:
        """Create valid LoadResult with all fields."""
        result = LoadResult(
            table_name="demo.orders",
            rows_loaded=1000,
            snapshot_id=12345678901234,
            operation="append",
        )
        assert result.table_name == "demo.orders"
        assert result.rows_loaded == 1000
        assert result.snapshot_id == 12345678901234
        assert result.operation == "append"

    def test_load_result_optional_snapshot(self) -> None:
        """LoadResult allows None snapshot_id."""
        result = LoadResult(
            table_name="demo.customers",
            rows_loaded=500,
            snapshot_id=None,
            operation="overwrite",
        )
        assert result.snapshot_id is None

    def test_load_result_frozen(self) -> None:
        """LoadResult is immutable."""
        result = LoadResult(
            table_name="demo.orders",
            rows_loaded=100,
            snapshot_id=123,
            operation="append",
        )
        with pytest.raises(ValidationError):
            result.rows_loaded = 200  # type: ignore[misc]

    def test_load_result_different_operations(self) -> None:
        """LoadResult accepts various operation types."""
        for operation in ["append", "overwrite", "append_stream"]:
            result = LoadResult(
                table_name="demo.table",
                rows_loaded=100,
                snapshot_id=123,
                operation=operation,
            )
            assert result.operation == operation
