"""Unit tests for IcebergIOManager.

Tests for US4 (Write Operations):
- IcebergIOManager initialization and configuration
- handle_output for Pandas DataFrame and PyArrow Table
- Asset key to table identifier mapping
- Write modes (append and overwrite)
- Auto table creation
- Schema evolution support
- Materialization metadata
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pyarrow as pa
import pytest
from dagster import AssetKey

from floe_iceberg.config import (
    IcebergIOManagerConfig,
    SnapshotInfo,
    WriteMode,
)
from floe_iceberg.errors import TableNotFoundError, WriteError
from floe_iceberg.io_manager import IcebergIOManager, create_io_manager

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_config() -> IcebergIOManagerConfig:
    """Create a sample IOManager configuration."""
    return IcebergIOManagerConfig(
        catalog_uri="http://localhost:8181/api/catalog",
        warehouse="test_warehouse",
        default_namespace="bronze",
    )


@pytest.fixture
def io_manager() -> IcebergIOManager:
    """Create an IcebergIOManager instance for testing."""
    return IcebergIOManager(
        catalog_uri="http://localhost:8181/api/catalog",
        warehouse="test_warehouse",
        default_namespace="bronze",
        write_mode="append",
        schema_evolution_enabled=True,
        auto_create_tables=True,
    )


@pytest.fixture
def mock_catalog() -> MagicMock:
    """Create a mock PyIceberg catalog."""
    return MagicMock()


@pytest.fixture
def mock_table_manager() -> MagicMock:
    """Create a mock IcebergTableManager."""
    manager = MagicMock()
    manager.table_exists.return_value = True
    manager.append.return_value = SnapshotInfo(
        snapshot_id=123456789,
        timestamp_ms=1702857600000,
        operation="append",
        summary={"added-records": "100"},
    )
    manager.overwrite.return_value = SnapshotInfo(
        snapshot_id=987654321,
        timestamp_ms=1702857600000,
        operation="overwrite",
        summary={"added-records": "100"},
    )
    return manager


@pytest.fixture
def sample_arrow_table() -> pa.Table:
    """Create a sample PyArrow table."""
    return pa.Table.from_pydict({
        "id": [1, 2, 3],
        "name": ["Alice", "Bob", "Charlie"],
    })


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """Create a sample Pandas DataFrame."""
    return pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Alice", "Bob", "Charlie"],
    })


def create_output_context(
    asset_key: list[str],
    metadata: dict[str, Any] | None = None,
    partition_key: str | None = None,
) -> MagicMock:
    """Create a mock OutputContext."""
    context = MagicMock()
    context.asset_key = AssetKey(asset_key)
    context.metadata = metadata or {}
    context.partition_key = partition_key
    context.add_output_metadata = MagicMock()
    return context


def create_input_context(
    asset_key: list[str],
    partition_key: str | None = None,
) -> MagicMock:
    """Create a mock InputContext."""
    context = MagicMock()
    context.asset_key = AssetKey(asset_key)
    context.partition_key = partition_key
    return context


# =============================================================================
# Test IcebergIOManager Initialization
# =============================================================================


class TestIcebergIOManagerInit:
    """Tests for IcebergIOManager initialization."""

    def test_init_with_defaults(self) -> None:
        """Test IOManager initialization with default values."""
        io_manager = IcebergIOManager(
            catalog_uri="http://localhost:8181/api/catalog",
            warehouse="test_warehouse",
        )

        assert io_manager.catalog_uri == "http://localhost:8181/api/catalog"
        assert io_manager.warehouse == "test_warehouse"
        assert io_manager.default_namespace == "public"
        assert io_manager.write_mode == "append"
        assert io_manager.schema_evolution_enabled is True
        assert io_manager.auto_create_tables is True

    def test_init_with_custom_values(self) -> None:
        """Test IOManager initialization with custom values."""
        io_manager = IcebergIOManager(
            catalog_uri="http://polaris:8181/api/catalog",
            warehouse="prod_warehouse",
            default_namespace="gold",
            write_mode="overwrite",
            schema_evolution_enabled=False,
            auto_create_tables=False,
            partition_column="created_at",
        )

        assert io_manager.catalog_uri == "http://polaris:8181/api/catalog"
        assert io_manager.warehouse == "prod_warehouse"
        assert io_manager.default_namespace == "gold"
        assert io_manager.write_mode == "overwrite"
        assert io_manager.schema_evolution_enabled is False
        assert io_manager.auto_create_tables is False
        assert io_manager.partition_column == "created_at"

    def test_init_with_credentials(self) -> None:
        """Test IOManager initialization with OAuth credentials."""
        io_manager = IcebergIOManager(
            catalog_uri="http://localhost:8181/api/catalog",
            warehouse="test_warehouse",
            client_id="my_client",
            client_secret="my_secret",
        )

        assert io_manager.client_id == "my_client"
        assert io_manager.client_secret == "my_secret"

    def test_init_with_token(self) -> None:
        """Test IOManager initialization with bearer token."""
        io_manager = IcebergIOManager(
            catalog_uri="http://localhost:8181/api/catalog",
            warehouse="test_warehouse",
            token="my_bearer_token",
        )

        assert io_manager.token == "my_bearer_token"


# =============================================================================
# Test Asset Key to Table Identifier Mapping
# =============================================================================


class TestGetTableIdentifier:
    """Tests for get_table_identifier method."""

    def test_single_part_key_uses_default_namespace(
        self, io_manager: IcebergIOManager
    ) -> None:
        """Test single-part asset key uses default namespace."""
        context = create_output_context(["customers"])
        result = io_manager.get_table_identifier(context)
        assert result == "bronze.customers"

    def test_two_part_key_uses_first_as_namespace(
        self, io_manager: IcebergIOManager
    ) -> None:
        """Test two-part asset key uses first part as namespace."""
        context = create_output_context(["silver", "orders"])
        result = io_manager.get_table_identifier(context)
        assert result == "silver.orders"

    def test_multi_part_key_joins_with_underscore(
        self, io_manager: IcebergIOManager
    ) -> None:
        """Test multi-part asset key joins tail parts with underscore."""
        context = create_output_context(["gold", "metrics", "daily"])
        result = io_manager.get_table_identifier(context)
        assert result == "gold.metrics_daily"

    def test_four_part_key(self, io_manager: IcebergIOManager) -> None:
        """Test four-part asset key."""
        context = create_output_context(["gold", "dim", "customer", "scd2"])
        result = io_manager.get_table_identifier(context)
        assert result == "gold.dim_customer_scd2"

    def test_raises_for_missing_asset_key(
        self, io_manager: IcebergIOManager
    ) -> None:
        """Test raises ValueError if asset key is None."""
        context = MagicMock()
        context.asset_key = None

        with pytest.raises(ValueError, match="Asset key is required"):
            io_manager.get_table_identifier(context)

    def test_input_context_works_same_as_output(
        self, io_manager: IcebergIOManager
    ) -> None:
        """Test InputContext works the same as OutputContext."""
        context = create_input_context(["bronze", "raw_events"])
        result = io_manager.get_table_identifier(context)
        assert result == "bronze.raw_events"


# =============================================================================
# Test handle_output for PyArrow Table
# =============================================================================


class TestHandleOutputArrow:
    """Tests for handle_output with PyArrow Table."""

    def test_handle_output_arrow_append(
        self,
        io_manager: IcebergIOManager,
        mock_table_manager: MagicMock,
        sample_arrow_table: pa.Table,
    ) -> None:
        """Test handle_output with PyArrow Table in append mode."""
        io_manager._table_manager = mock_table_manager
        io_manager._logger = MagicMock()
        context = create_output_context(["bronze", "customers"])

        io_manager.handle_output(context, sample_arrow_table)

        mock_table_manager.append.assert_called_once()
        call_args = mock_table_manager.append.call_args
        assert call_args[0][0] == "bronze.customers"
        assert call_args[0][1].num_rows == 3

    def test_handle_output_arrow_overwrite(
        self,
        mock_table_manager: MagicMock,
        sample_arrow_table: pa.Table,
    ) -> None:
        """Test handle_output with PyArrow Table in overwrite mode."""
        # Create IOManager with overwrite mode (can't mutate frozen config)
        io_manager = IcebergIOManager(
            catalog_uri="http://localhost:8181/api/catalog",
            warehouse="test_warehouse",
            default_namespace="bronze",
            write_mode="overwrite",
        )
        io_manager._table_manager = mock_table_manager
        io_manager._logger = MagicMock()
        context = create_output_context(["bronze", "customers"])

        io_manager.handle_output(context, sample_arrow_table)

        mock_table_manager.overwrite.assert_called_once()

    def test_handle_output_attaches_metadata(
        self,
        io_manager: IcebergIOManager,
        mock_table_manager: MagicMock,
        sample_arrow_table: pa.Table,
    ) -> None:
        """Test handle_output attaches metadata to context."""
        io_manager._table_manager = mock_table_manager
        io_manager._logger = MagicMock()
        context = create_output_context(["bronze", "customers"])

        io_manager.handle_output(context, sample_arrow_table)

        context.add_output_metadata.assert_called_once()
        metadata = context.add_output_metadata.call_args[0][0]
        assert metadata["table"] == "bronze.customers"
        assert metadata["namespace"] == "bronze"
        assert metadata["table_name"] == "customers"
        assert metadata["snapshot_id"] == 123456789
        assert metadata["num_rows"] == 3
        assert metadata["write_mode"] == "append"


# =============================================================================
# Test handle_output for Pandas DataFrame
# =============================================================================


class TestHandleOutputDataFrame:
    """Tests for handle_output with Pandas DataFrame."""

    def test_handle_output_dataframe_converts_to_arrow(
        self,
        io_manager: IcebergIOManager,
        mock_table_manager: MagicMock,
        sample_dataframe: pd.DataFrame,
    ) -> None:
        """Test handle_output converts DataFrame to PyArrow."""
        io_manager._table_manager = mock_table_manager
        io_manager._logger = MagicMock()
        context = create_output_context(["bronze", "customers"])

        io_manager.handle_output(context, sample_dataframe)

        mock_table_manager.append.assert_called_once()
        call_args = mock_table_manager.append.call_args
        assert isinstance(call_args[0][1], pa.Table)

    def test_handle_output_dataframe_preserves_data(
        self,
        io_manager: IcebergIOManager,
        mock_table_manager: MagicMock,
        sample_dataframe: pd.DataFrame,
    ) -> None:
        """Test handle_output preserves DataFrame data when converting."""
        io_manager._table_manager = mock_table_manager
        io_manager._logger = MagicMock()
        context = create_output_context(["bronze", "customers"])

        io_manager.handle_output(context, sample_dataframe)

        call_args = mock_table_manager.append.call_args
        arrow_table = call_args[0][1]
        assert arrow_table.num_rows == len(sample_dataframe)
        assert set(arrow_table.column_names) >= {"id", "name"}


# =============================================================================
# Test Write Mode Selection
# =============================================================================


class TestWriteModeSelection:
    """Tests for write mode selection logic."""

    def test_default_write_mode_from_config(
        self, io_manager: IcebergIOManager
    ) -> None:
        """Test default write mode comes from config."""
        context = create_output_context(["customers"])
        result = io_manager._get_write_mode(context)
        assert result == WriteMode.APPEND

    def test_write_mode_from_metadata_string(
        self, io_manager: IcebergIOManager
    ) -> None:
        """Test write mode from metadata as string."""
        context = create_output_context(
            ["customers"],
            metadata={"write_mode": "overwrite"},
        )
        result = io_manager._get_write_mode(context)
        assert result == WriteMode.OVERWRITE

    def test_write_mode_from_metadata_enum(
        self, io_manager: IcebergIOManager
    ) -> None:
        """Test write mode from metadata as WriteMode enum."""
        context = create_output_context(
            ["customers"],
            metadata={"write_mode": WriteMode.OVERWRITE},
        )
        result = io_manager._get_write_mode(context)
        assert result == WriteMode.OVERWRITE

    def test_write_mode_overwrite_config(self) -> None:
        """Test IOManager with overwrite as default."""
        io_manager = IcebergIOManager(
            catalog_uri="http://localhost:8181/api/catalog",
            warehouse="test",
            write_mode="overwrite",
        )
        context = create_output_context(["customers"])
        result = io_manager._get_write_mode(context)
        assert result == WriteMode.OVERWRITE


# =============================================================================
# Test Auto Table Creation
# =============================================================================


class TestAutoTableCreation:
    """Tests for auto table creation."""

    def test_creates_table_when_not_exists(
        self,
        io_manager: IcebergIOManager,
        sample_arrow_table: pa.Table,
    ) -> None:
        """Test auto-creates table when it doesn't exist."""
        mock_manager = MagicMock()
        mock_manager.table_exists.return_value = False
        mock_manager.append.return_value = SnapshotInfo(
            snapshot_id=123,
            timestamp_ms=1702857600000,
            operation="append",
            summary={},
        )
        io_manager._table_manager = mock_manager
        io_manager._logger = MagicMock()
        context = create_output_context(["bronze", "new_table"])

        io_manager.handle_output(context, sample_arrow_table)

        mock_manager.create_table.assert_called_once()

    def test_skips_create_when_table_exists(
        self,
        io_manager: IcebergIOManager,
        mock_table_manager: MagicMock,
        sample_arrow_table: pa.Table,
    ) -> None:
        """Test skips table creation when table exists."""
        io_manager._table_manager = mock_table_manager
        io_manager._logger = MagicMock()
        context = create_output_context(["bronze", "customers"])

        io_manager.handle_output(context, sample_arrow_table)

        mock_table_manager.create_table.assert_not_called()

    def test_raises_when_auto_create_disabled(
        self,
        sample_arrow_table: pa.Table,
    ) -> None:
        """Test raises TableNotFoundError when auto_create disabled."""
        io_manager = IcebergIOManager(
            catalog_uri="http://localhost:8181/api/catalog",
            warehouse="test",
            auto_create_tables=False,
        )
        mock_manager = MagicMock()
        mock_manager.table_exists.return_value = False
        io_manager._table_manager = mock_manager
        io_manager._logger = MagicMock()
        context = create_output_context(["bronze", "missing"])

        with pytest.raises(TableNotFoundError):
            io_manager.handle_output(context, sample_arrow_table)


# =============================================================================
# Test Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in handle_output."""

    def test_raises_write_error_on_append_failure(
        self,
        io_manager: IcebergIOManager,
        sample_arrow_table: pa.Table,
    ) -> None:
        """Test raises WriteError when append fails."""
        mock_manager = MagicMock()
        mock_manager.table_exists.return_value = True
        mock_manager.append.side_effect = Exception("Connection failed")
        io_manager._table_manager = mock_manager
        io_manager._logger = MagicMock()
        context = create_output_context(["bronze", "customers"])

        with pytest.raises(WriteError) as exc_info:
            io_manager.handle_output(context, sample_arrow_table)

        assert "bronze.customers" in str(exc_info.value)

    def test_raises_write_error_for_unsupported_type(
        self,
        io_manager: IcebergIOManager,
        mock_table_manager: MagicMock,
    ) -> None:
        """Test raises WriteError for unsupported output type."""
        io_manager._table_manager = mock_table_manager
        io_manager._logger = MagicMock()
        context = create_output_context(["bronze", "customers"])

        with pytest.raises(WriteError, match="Unsupported output type"):
            io_manager.handle_output(context, {"not": "a table"})


# =============================================================================
# Test load_input (US5 - Read Operations)
# =============================================================================


class TestLoadInput:
    """Tests for load_input method."""

    def test_load_input_returns_table(
        self,
        io_manager: IcebergIOManager,
        sample_arrow_table: pa.Table,
    ) -> None:
        """Test load_input returns PyArrow Table."""
        mock_manager = MagicMock()
        mock_manager.table_exists.return_value = True
        mock_manager.scan.return_value = sample_arrow_table
        io_manager._table_manager = mock_manager
        io_manager._logger = MagicMock()
        context = create_input_context(["bronze", "customers"])

        result = io_manager.load_input(context)

        assert isinstance(result, pa.Table)
        assert result.num_rows == 3

    def test_load_input_raises_for_missing_table(
        self,
        io_manager: IcebergIOManager,
    ) -> None:
        """Test load_input raises TableNotFoundError for missing table."""
        mock_manager = MagicMock()
        mock_manager.table_exists.return_value = False
        io_manager._table_manager = mock_manager
        io_manager._logger = MagicMock()
        context = create_input_context(["bronze", "missing"])

        with pytest.raises(TableNotFoundError):
            io_manager.load_input(context)

    def test_load_input_with_column_projection(
        self,
        io_manager: IcebergIOManager,
        sample_arrow_table: pa.Table,
    ) -> None:
        """Test load_input passes column projection to scan."""
        mock_manager = MagicMock()
        mock_manager.table_exists.return_value = True
        mock_manager.scan.return_value = sample_arrow_table
        io_manager._table_manager = mock_manager
        io_manager._logger = MagicMock()

        # Create context with columns metadata
        context = MagicMock()
        context.asset_key = MagicMock()
        context.asset_key.path = ["bronze", "customers"]
        context.partition_key = None
        context.metadata = {"columns": ["id", "name"]}

        io_manager.load_input(context)

        mock_manager.scan.assert_called_once()
        call_kwargs = mock_manager.scan.call_args[1]
        assert call_kwargs["columns"] == ["id", "name"]

    def test_load_input_with_row_filter(
        self,
        io_manager: IcebergIOManager,
        sample_arrow_table: pa.Table,
    ) -> None:
        """Test load_input passes row filter to scan."""
        mock_manager = MagicMock()
        mock_manager.table_exists.return_value = True
        mock_manager.scan.return_value = sample_arrow_table
        io_manager._table_manager = mock_manager
        io_manager._logger = MagicMock()

        # Create context with row_filter metadata
        context = MagicMock()
        context.asset_key = MagicMock()
        context.asset_key.path = ["bronze", "customers"]
        context.partition_key = None
        context.metadata = {"row_filter": "status = 'active'"}

        io_manager.load_input(context)

        mock_manager.scan.assert_called_once()
        call_kwargs = mock_manager.scan.call_args[1]
        assert call_kwargs["row_filter"] == "status = 'active'"

    def test_load_input_with_snapshot_id(
        self,
        io_manager: IcebergIOManager,
        sample_arrow_table: pa.Table,
    ) -> None:
        """Test load_input passes snapshot_id to scan (time travel)."""
        mock_manager = MagicMock()
        mock_manager.table_exists.return_value = True
        mock_manager.scan.return_value = sample_arrow_table
        io_manager._table_manager = mock_manager
        io_manager._logger = MagicMock()

        # Create context with snapshot_id metadata
        context = MagicMock()
        context.asset_key = MagicMock()
        context.asset_key.path = ["bronze", "customers"]
        context.partition_key = None
        context.metadata = {"snapshot_id": 123456789}

        io_manager.load_input(context)

        mock_manager.scan.assert_called_once()
        call_kwargs = mock_manager.scan.call_args[1]
        assert call_kwargs["snapshot_id"] == 123456789

    def test_load_input_with_limit(
        self,
        io_manager: IcebergIOManager,
        sample_arrow_table: pa.Table,
    ) -> None:
        """Test load_input passes limit to scan."""
        mock_manager = MagicMock()
        mock_manager.table_exists.return_value = True
        mock_manager.scan.return_value = sample_arrow_table
        io_manager._table_manager = mock_manager
        io_manager._logger = MagicMock()

        # Create context with limit metadata
        context = MagicMock()
        context.asset_key = MagicMock()
        context.asset_key.path = ["bronze", "customers"]
        context.partition_key = None
        context.metadata = {"limit": 100}

        io_manager.load_input(context)

        mock_manager.scan.assert_called_once()
        call_kwargs = mock_manager.scan.call_args[1]
        assert call_kwargs["limit"] == 100

    def test_load_input_with_all_options(
        self,
        io_manager: IcebergIOManager,
        sample_arrow_table: pa.Table,
    ) -> None:
        """Test load_input with all scan options combined."""
        mock_manager = MagicMock()
        mock_manager.table_exists.return_value = True
        mock_manager.scan.return_value = sample_arrow_table
        io_manager._table_manager = mock_manager
        io_manager._logger = MagicMock()

        # Create context with all metadata options
        context = MagicMock()
        context.asset_key = MagicMock()
        context.asset_key.path = ["bronze", "customers"]
        context.partition_key = None
        context.metadata = {
            "columns": ["id", "name"],
            "row_filter": "status = 'active'",
            "snapshot_id": 123456789,
            "limit": 100,
        }

        io_manager.load_input(context)

        mock_manager.scan.assert_called_once()
        call_kwargs = mock_manager.scan.call_args[1]
        assert call_kwargs["columns"] == ["id", "name"]
        assert call_kwargs["row_filter"] == "status = 'active'"
        assert call_kwargs["snapshot_id"] == 123456789
        assert call_kwargs["limit"] == 100


# =============================================================================
# Test Partitioned Reads
# =============================================================================


class TestPartitionedReads:
    """Tests for partitioned read support in load_input."""

    def test_load_input_with_partition_key(
        self,
        sample_arrow_table: pa.Table,
    ) -> None:
        """Test load_input builds partition filter from partition key."""
        io_manager = IcebergIOManager(
            catalog_uri="http://localhost:8181/api/catalog",
            warehouse="test",
            partition_column="created_at",
        )
        mock_manager = MagicMock()
        mock_manager.table_exists.return_value = True
        mock_manager.scan.return_value = sample_arrow_table
        io_manager._table_manager = mock_manager
        io_manager._logger = MagicMock()

        # Create context with partition key
        context = MagicMock()
        context.asset_key = MagicMock()
        context.asset_key.path = ["bronze", "events"]
        context.partition_key = "2024-01-15"
        context.metadata = {}

        io_manager.load_input(context)

        mock_manager.scan.assert_called_once()
        call_kwargs = mock_manager.scan.call_args[1]
        assert call_kwargs["row_filter"] == "created_at = '2024-01-15'"

    def test_load_input_combines_partition_and_row_filter(
        self,
        sample_arrow_table: pa.Table,
    ) -> None:
        """Test load_input combines partition filter with row filter."""
        io_manager = IcebergIOManager(
            catalog_uri="http://localhost:8181/api/catalog",
            warehouse="test",
            partition_column="created_at",
        )
        mock_manager = MagicMock()
        mock_manager.table_exists.return_value = True
        mock_manager.scan.return_value = sample_arrow_table
        io_manager._table_manager = mock_manager
        io_manager._logger = MagicMock()

        # Create context with both partition key and row filter
        context = MagicMock()
        context.asset_key = MagicMock()
        context.asset_key.path = ["bronze", "events"]
        context.partition_key = "2024-01-15"
        context.metadata = {"row_filter": "status = 'active'"}

        io_manager.load_input(context)

        mock_manager.scan.assert_called_once()
        call_kwargs = mock_manager.scan.call_args[1]
        assert "(status = 'active')" in call_kwargs["row_filter"]
        assert "(created_at = '2024-01-15')" in call_kwargs["row_filter"]
        assert "AND" in call_kwargs["row_filter"]

    def test_load_input_no_partition_filter_without_column(
        self,
        io_manager: IcebergIOManager,
        sample_arrow_table: pa.Table,
    ) -> None:
        """Test load_input doesn't add partition filter without partition_column."""
        mock_manager = MagicMock()
        mock_manager.table_exists.return_value = True
        mock_manager.scan.return_value = sample_arrow_table
        io_manager._table_manager = mock_manager
        io_manager._logger = MagicMock()

        # Create context with partition key but no partition_column configured
        context = MagicMock()
        context.asset_key = MagicMock()
        context.asset_key.path = ["bronze", "events"]
        context.partition_key = "2024-01-15"
        context.metadata = {}

        io_manager.load_input(context)

        mock_manager.scan.assert_called_once()
        call_kwargs = mock_manager.scan.call_args[1]
        assert call_kwargs["row_filter"] is None

    def test_partition_column_from_metadata(
        self,
        io_manager: IcebergIOManager,
        sample_arrow_table: pa.Table,
    ) -> None:
        """Test partition_column can be overridden in metadata."""
        mock_manager = MagicMock()
        mock_manager.table_exists.return_value = True
        mock_manager.scan.return_value = sample_arrow_table
        io_manager._table_manager = mock_manager
        io_manager._logger = MagicMock()

        # Create context with partition_column in metadata
        context = MagicMock()
        context.asset_key = MagicMock()
        context.asset_key.path = ["bronze", "events"]
        context.partition_key = "2024-01"
        context.metadata = {"partition_column": "event_month"}

        io_manager.load_input(context)

        mock_manager.scan.assert_called_once()
        call_kwargs = mock_manager.scan.call_args[1]
        assert call_kwargs["row_filter"] == "event_month = '2024-01'"


# =============================================================================
# Test Helper Methods for Context Extraction
# =============================================================================


class TestContextExtraction:
    """Tests for context extraction helper methods."""

    def test_get_columns_from_context_with_list(
        self, io_manager: IcebergIOManager
    ) -> None:
        """Test column extraction from list."""
        context = MagicMock()
        context.metadata = {"columns": ["id", "name", "email"]}

        result = io_manager._get_columns_from_context(context)

        assert result == ["id", "name", "email"]

    def test_get_columns_from_context_with_tuple(
        self, io_manager: IcebergIOManager
    ) -> None:
        """Test column extraction from tuple."""
        context = MagicMock()
        context.metadata = {"columns": ("id", "name")}

        result = io_manager._get_columns_from_context(context)

        assert result == ["id", "name"]

    def test_get_columns_from_context_none(
        self, io_manager: IcebergIOManager
    ) -> None:
        """Test column extraction returns None when not specified."""
        context = MagicMock()
        context.metadata = {}

        result = io_manager._get_columns_from_context(context)

        assert result is None

    def test_get_row_filter_from_context(
        self, io_manager: IcebergIOManager
    ) -> None:
        """Test row filter extraction."""
        context = MagicMock()
        context.metadata = {"row_filter": "id > 100"}

        result = io_manager._get_row_filter_from_context(context)

        assert result == "id > 100"

    def test_get_snapshot_id_from_context(
        self, io_manager: IcebergIOManager
    ) -> None:
        """Test snapshot ID extraction."""
        context = MagicMock()
        context.metadata = {"snapshot_id": "123456789"}

        result = io_manager._get_snapshot_id_from_context(context)

        assert result == 123456789

    def test_get_limit_from_context(
        self, io_manager: IcebergIOManager
    ) -> None:
        """Test limit extraction."""
        context = MagicMock()
        context.metadata = {"limit": "500"}

        result = io_manager._get_limit_from_context(context)

        assert result == 500

    def test_get_partition_filter_with_key_and_column(self) -> None:
        """Test partition filter generation."""
        io_manager = IcebergIOManager(
            catalog_uri="http://localhost:8181/api/catalog",
            warehouse="test",
            partition_column="event_date",
        )
        context = MagicMock()
        context.metadata = {}

        result = io_manager._get_partition_filter(context, "2024-01-15")

        assert result == "event_date = '2024-01-15'"

    def test_get_partition_filter_no_key(self) -> None:
        """Test partition filter returns None without partition key."""
        io_manager = IcebergIOManager(
            catalog_uri="http://localhost:8181/api/catalog",
            warehouse="test",
            partition_column="event_date",
        )
        context = MagicMock()
        context.metadata = {}

        result = io_manager._get_partition_filter(context, None)

        assert result is None


# =============================================================================
# Test create_io_manager Factory
# =============================================================================


class TestCreateIOManager:
    """Tests for create_io_manager factory function."""

    def test_create_io_manager_from_config(
        self, sample_config: IcebergIOManagerConfig
    ) -> None:
        """Test create_io_manager creates IOManager from config."""
        io_manager = create_io_manager(sample_config)

        assert isinstance(io_manager, IcebergIOManager)
        assert io_manager.catalog_uri == sample_config.catalog_uri
        assert io_manager.warehouse == sample_config.warehouse
        assert io_manager.default_namespace == sample_config.default_namespace

    def test_create_io_manager_with_custom_catalog(
        self,
        sample_config: IcebergIOManagerConfig,
        mock_catalog: MagicMock,
    ) -> None:
        """Test create_io_manager with pre-configured catalog."""
        io_manager = create_io_manager(sample_config, catalog=mock_catalog)

        assert io_manager._catalog is mock_catalog

    def test_create_io_manager_preserves_write_mode(self) -> None:
        """Test create_io_manager preserves write mode from config."""
        config = IcebergIOManagerConfig(
            catalog_uri="http://localhost:8181/api/catalog",
            warehouse="test",
            write_mode=WriteMode.OVERWRITE,
        )

        io_manager = create_io_manager(config)

        assert io_manager.write_mode == "overwrite"

    def test_create_io_manager_preserves_schema_evolution(self) -> None:
        """Test create_io_manager preserves schema_evolution_enabled."""
        config = IcebergIOManagerConfig(
            catalog_uri="http://localhost:8181/api/catalog",
            warehouse="test",
            schema_evolution_enabled=False,
        )

        io_manager = create_io_manager(config)

        assert io_manager.schema_evolution_enabled is False


# =============================================================================
# Test Partition Spec Generation
# =============================================================================


class TestPartitionSpecGeneration:
    """Tests for partition spec generation."""

    def test_no_partition_spec_by_default(
        self, io_manager: IcebergIOManager
    ) -> None:
        """Test no partition spec when partition_column not set."""
        schema = pa.schema([
            pa.field("id", pa.int64()),
            pa.field("name", pa.string()),
        ])
        context = create_output_context(["bronze", "customers"])

        result = io_manager._get_partition_spec(schema, context)

        assert result is None

    def test_partition_spec_created_when_column_exists(self) -> None:
        """Test partition spec created when partition_column matches schema."""
        io_manager = IcebergIOManager(
            catalog_uri="http://localhost:8181/api/catalog",
            warehouse="test",
            partition_column="created_at",
        )
        schema = pa.schema([
            pa.field("id", pa.int64()),
            pa.field("created_at", pa.timestamp("us")),
        ])
        context = create_output_context(["bronze", "events"])

        result = io_manager._get_partition_spec(schema, context)

        assert result is not None

    def test_no_partition_spec_when_column_missing(self) -> None:
        """Test no partition spec when partition_column not in schema."""
        io_manager = IcebergIOManager(
            catalog_uri="http://localhost:8181/api/catalog",
            warehouse="test",
            partition_column="created_at",
        )
        schema = pa.schema([
            pa.field("id", pa.int64()),
            pa.field("name", pa.string()),
        ])
        context = create_output_context(["bronze", "customers"])

        result = io_manager._get_partition_spec(schema, context)

        assert result is None
