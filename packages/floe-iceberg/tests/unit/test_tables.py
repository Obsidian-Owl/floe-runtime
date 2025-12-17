"""Unit tests for IcebergTableManager.

Tests for:
- T058: IcebergTableManager initialization tests
- T059: create_table tests
- T060: load_table tests
- T061: partition spec building tests
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, PropertyMock

import pyarrow as pa
import pytest

from floe_iceberg.config import (
    PartitionTransform,
    PartitionTransformType,
    SnapshotInfo,
    TableIdentifier,
)
from floe_iceberg.errors import (
    ScanError,
    TableExistsError,
    TableNotFoundError,
    WriteError,
)
from floe_iceberg.tables import IcebergTableManager, build_partition_spec

if TYPE_CHECKING:
    pass


@pytest.fixture
def mock_catalog() -> MagicMock:
    """Create a mock PolarisCatalog."""
    catalog = MagicMock()
    catalog.inner_catalog = MagicMock()
    return catalog


@pytest.fixture
def manager(mock_catalog: MagicMock) -> IcebergTableManager:
    """Create IcebergTableManager with mock catalog."""
    return IcebergTableManager(mock_catalog)


@pytest.fixture
def sample_schema() -> pa.Schema:
    """Create a sample PyArrow schema for testing."""
    return pa.schema([
        pa.field("id", pa.int64()),
        pa.field("name", pa.string()),
        pa.field("created_at", pa.timestamp("us")),
    ])


@pytest.fixture
def sample_data() -> pa.Table:
    """Create sample PyArrow Table for testing."""
    return pa.Table.from_pydict({
        "id": [1, 2, 3],
        "name": ["Alice", "Bob", "Charlie"],
    })


class TestIcebergTableManagerInit:
    """Tests for IcebergTableManager initialization."""

    def test_init_with_catalog(self, mock_catalog: MagicMock) -> None:
        """Test basic initialization with catalog."""
        manager = IcebergTableManager(mock_catalog)

        assert manager.catalog is mock_catalog
        assert manager._catalog is mock_catalog

    def test_catalog_property_returns_catalog(self, manager: IcebergTableManager) -> None:
        """Test catalog property returns the underlying catalog."""
        assert manager.catalog is manager._catalog


class TestCreateTable:
    """Tests for create_table method."""

    def test_create_table_with_string_identifier(
        self, manager: IcebergTableManager, sample_schema: pa.Schema
    ) -> None:
        """Test creating table with string identifier."""
        mock_table = MagicMock()
        manager._catalog.inner_catalog.create_table.return_value = mock_table

        result = manager.create_table("bronze.customers", sample_schema)

        assert result is mock_table
        manager._catalog.inner_catalog.create_table.assert_called_once()
        call_kwargs = manager._catalog.inner_catalog.create_table.call_args
        assert call_kwargs.kwargs["identifier"] == ("bronze", "customers")

    def test_create_table_with_table_identifier(
        self, manager: IcebergTableManager, sample_schema: pa.Schema
    ) -> None:
        """Test creating table with TableIdentifier object."""
        mock_table = MagicMock()
        manager._catalog.inner_catalog.create_table.return_value = mock_table
        table_id = TableIdentifier(namespace="silver", name="orders")

        result = manager.create_table(table_id, sample_schema)

        assert result is mock_table
        call_kwargs = manager._catalog.inner_catalog.create_table.call_args
        assert call_kwargs.kwargs["identifier"] == ("silver", "orders")

    def test_create_table_with_properties(
        self, manager: IcebergTableManager, sample_schema: pa.Schema
    ) -> None:
        """Test creating table with properties."""
        mock_table = MagicMock()
        manager._catalog.inner_catalog.create_table.return_value = mock_table
        properties = {"owner": "data_team", "env": "prod"}

        manager.create_table("bronze.customers", sample_schema, properties=properties)

        call_kwargs = manager._catalog.inner_catalog.create_table.call_args
        assert call_kwargs.kwargs["properties"] == properties

    def test_create_table_already_exists(
        self, manager: IcebergTableManager, sample_schema: pa.Schema
    ) -> None:
        """Test TableExistsError when table already exists."""
        from pyiceberg.exceptions import TableAlreadyExistsError

        manager._catalog.inner_catalog.create_table.side_effect = (
            TableAlreadyExistsError("Table already exists")
        )

        with pytest.raises(TableExistsError) as exc_info:
            manager.create_table("bronze.customers", sample_schema)

        assert "bronze.customers" in str(exc_info.value)

    def test_create_table_namespace_not_found(
        self, manager: IcebergTableManager, sample_schema: pa.Schema
    ) -> None:
        """Test NamespaceNotFoundError when namespace doesn't exist."""
        from pyiceberg.exceptions import NoSuchNamespaceError

        manager._catalog.inner_catalog.create_table.side_effect = (
            NoSuchNamespaceError("Namespace not found")
        )

        from floe_polaris.errors import NamespaceNotFoundError

        with pytest.raises(NamespaceNotFoundError):
            manager.create_table("nonexistent.customers", sample_schema)


class TestCreateTableIfNotExists:
    """Tests for create_table_if_not_exists method."""

    def test_creates_new_table(
        self, manager: IcebergTableManager, sample_schema: pa.Schema
    ) -> None:
        """Test creates table when it doesn't exist."""
        from pyiceberg.exceptions import NoSuchTableError

        # First call (table_exists check) raises NoSuchTableError
        # Second call (create_table) returns mock table
        mock_table = MagicMock()
        manager._catalog.inner_catalog.load_table.side_effect = NoSuchTableError(
            "Table not found"
        )
        manager._catalog.inner_catalog.create_table.return_value = mock_table

        result = manager.create_table_if_not_exists("bronze.customers", sample_schema)

        assert result is mock_table
        manager._catalog.inner_catalog.create_table.assert_called_once()

    def test_returns_existing_table(
        self, manager: IcebergTableManager, sample_schema: pa.Schema
    ) -> None:
        """Test returns existing table without creating."""
        mock_table = MagicMock()
        manager._catalog.inner_catalog.load_table.return_value = mock_table

        result = manager.create_table_if_not_exists("bronze.customers", sample_schema)

        assert result is mock_table
        manager._catalog.inner_catalog.create_table.assert_not_called()


class TestLoadTable:
    """Tests for load_table method."""

    def test_load_existing_table(self, manager: IcebergTableManager) -> None:
        """Test loading an existing table."""
        mock_table = MagicMock()
        manager._catalog.inner_catalog.load_table.return_value = mock_table

        result = manager.load_table("bronze.customers")

        assert result is mock_table
        manager._catalog.inner_catalog.load_table.assert_called_once_with(
            ("bronze", "customers")
        )

    def test_load_table_not_found(self, manager: IcebergTableManager) -> None:
        """Test TableNotFoundError when table doesn't exist."""
        from pyiceberg.exceptions import NoSuchTableError

        manager._catalog.inner_catalog.load_table.side_effect = NoSuchTableError(
            "Table not found"
        )

        with pytest.raises(TableNotFoundError) as exc_info:
            manager.load_table("bronze.nonexistent")

        assert "bronze.nonexistent" in str(exc_info.value)

    def test_load_table_with_nested_namespace(self, manager: IcebergTableManager) -> None:
        """Test loading table with nested namespace."""
        mock_table = MagicMock()
        manager._catalog.inner_catalog.load_table.return_value = mock_table

        manager.load_table("bronze.raw.customers")

        manager._catalog.inner_catalog.load_table.assert_called_once_with(
            ("bronze.raw", "customers")
        )


class TestDropTable:
    """Tests for drop_table method."""

    def test_drop_table(self, manager: IcebergTableManager) -> None:
        """Test dropping a table."""
        manager.drop_table("bronze.customers")

        # Note: PyIceberg's base Catalog.drop_table doesn't accept purge param
        manager._catalog.inner_catalog.drop_table.assert_called_once_with(
            ("bronze", "customers")
        )

    def test_drop_table_with_purge(self, manager: IcebergTableManager) -> None:
        """Test dropping table with purge=True (purge is logged but not passed to catalog)."""
        manager.drop_table("bronze.customers", purge=True)

        # Note: purge param is logged but not passed to PyIceberg catalog
        manager._catalog.inner_catalog.drop_table.assert_called_once_with(
            ("bronze", "customers")
        )

    def test_drop_table_not_found(self, manager: IcebergTableManager) -> None:
        """Test TableNotFoundError when dropping nonexistent table."""
        from pyiceberg.exceptions import NoSuchTableError

        manager._catalog.inner_catalog.drop_table.side_effect = NoSuchTableError(
            "Table not found"
        )

        with pytest.raises(TableNotFoundError):
            manager.drop_table("bronze.nonexistent")


class TestTableExists:
    """Tests for table_exists method."""

    def test_table_exists_true(self, manager: IcebergTableManager) -> None:
        """Test returns True when table exists."""
        mock_table = MagicMock()
        manager._catalog.inner_catalog.load_table.return_value = mock_table

        assert manager.table_exists("bronze.customers") is True

    def test_table_exists_false(self, manager: IcebergTableManager) -> None:
        """Test returns False when table doesn't exist."""
        from pyiceberg.exceptions import NoSuchTableError

        manager._catalog.inner_catalog.load_table.side_effect = NoSuchTableError(
            "Table not found"
        )

        assert manager.table_exists("bronze.nonexistent") is False


class TestListTables:
    """Tests for list_tables method."""

    def test_list_tables(self, manager: IcebergTableManager) -> None:
        """Test listing tables in a namespace."""
        manager._catalog.inner_catalog.list_tables.return_value = [
            ("bronze", "customers"),
            ("bronze", "orders"),
            ("bronze", "products"),
        ]

        result = manager.list_tables("bronze")

        assert result == ["customers", "orders", "products"]
        manager._catalog.inner_catalog.list_tables.assert_called_once_with(("bronze",))

    def test_list_tables_nested_namespace(self, manager: IcebergTableManager) -> None:
        """Test listing tables in nested namespace."""
        manager._catalog.inner_catalog.list_tables.return_value = [
            ("bronze", "raw", "events"),
        ]

        result = manager.list_tables("bronze.raw")

        assert result == ["events"]
        manager._catalog.inner_catalog.list_tables.assert_called_once_with(
            ("bronze", "raw")
        )

    def test_list_tables_empty(self, manager: IcebergTableManager) -> None:
        """Test listing tables in empty namespace."""
        manager._catalog.inner_catalog.list_tables.return_value = []

        result = manager.list_tables("empty")

        assert result == []


class TestAppend:
    """Tests for append method."""

    def test_append_data(
        self, manager: IcebergTableManager, sample_data: pa.Table
    ) -> None:
        """Test appending data to table."""
        mock_table = MagicMock()
        mock_snapshot = MagicMock()
        mock_snapshot.snapshot_id = 123456
        mock_snapshot.timestamp_ms = 1702857600000
        mock_snapshot.operation = "append"
        mock_snapshot.summary = {"added-records": "3"}
        mock_snapshot.manifest_list = None
        mock_table.current_snapshot.return_value = mock_snapshot
        mock_table.schema.return_value = MagicMock(fields=[])
        manager._catalog.inner_catalog.load_table.return_value = mock_table

        result = manager.append("bronze.customers", sample_data)

        assert isinstance(result, SnapshotInfo)
        assert result.snapshot_id == 123456
        mock_table.append.assert_called_once()

    def test_append_table_not_found(
        self, manager: IcebergTableManager, sample_data: pa.Table
    ) -> None:
        """Test TableNotFoundError when appending to nonexistent table."""
        from pyiceberg.exceptions import NoSuchTableError

        manager._catalog.inner_catalog.load_table.side_effect = NoSuchTableError(
            "Table not found"
        )

        with pytest.raises(TableNotFoundError):
            manager.append("bronze.nonexistent", sample_data)

    def test_append_write_error(
        self, manager: IcebergTableManager, sample_data: pa.Table
    ) -> None:
        """Test WriteError when append fails."""
        mock_table = MagicMock()
        mock_table.schema.return_value = MagicMock(fields=[])
        mock_table.append.side_effect = RuntimeError("Write failed")
        manager._catalog.inner_catalog.load_table.return_value = mock_table

        with pytest.raises(WriteError) as exc_info:
            manager.append("bronze.customers", sample_data)

        assert "bronze.customers" in str(exc_info.value)


class TestOverwrite:
    """Tests for overwrite method."""

    def test_overwrite_data(
        self, manager: IcebergTableManager, sample_data: pa.Table
    ) -> None:
        """Test overwriting table data."""
        mock_table = MagicMock()
        mock_snapshot = MagicMock()
        mock_snapshot.snapshot_id = 123456
        mock_snapshot.timestamp_ms = 1702857600000
        mock_snapshot.operation = "overwrite"
        mock_snapshot.summary = {}
        mock_snapshot.manifest_list = None
        mock_table.current_snapshot.return_value = mock_snapshot
        mock_table.schema.return_value = MagicMock(fields=[])
        manager._catalog.inner_catalog.load_table.return_value = mock_table

        result = manager.overwrite("bronze.customers", sample_data)

        assert isinstance(result, SnapshotInfo)
        assert result.operation == "overwrite"
        mock_table.overwrite.assert_called_once()


class TestScan:
    """Tests for scan method."""

    def test_scan_all_columns(self, manager: IcebergTableManager) -> None:
        """Test scanning all columns."""
        mock_table = MagicMock()
        mock_scan = MagicMock()
        expected_result = pa.Table.from_pydict({"id": [1, 2]})
        mock_scan.to_arrow.return_value = expected_result
        mock_table.scan.return_value = mock_scan
        manager._catalog.inner_catalog.load_table.return_value = mock_table

        result = manager.scan("bronze.customers")

        assert result is expected_result
        mock_table.scan.assert_called_once()

    def test_scan_with_columns(self, manager: IcebergTableManager) -> None:
        """Test scanning specific columns."""
        mock_table = MagicMock()
        mock_scan = MagicMock()
        mock_scan.to_arrow.return_value = pa.Table.from_pydict({"id": [1]})
        mock_table.scan.return_value = mock_scan
        manager._catalog.inner_catalog.load_table.return_value = mock_table

        manager.scan("bronze.customers", columns=["id", "name"])

        call_kwargs = mock_table.scan.call_args.kwargs
        assert call_kwargs["selected_fields"] == ("id", "name")

    def test_scan_with_snapshot_id(self, manager: IcebergTableManager) -> None:
        """Test scanning at specific snapshot (time travel)."""
        mock_table = MagicMock()
        mock_scan = MagicMock()
        mock_scan.to_arrow.return_value = pa.Table.from_pydict({"id": [1]})
        mock_table.scan.return_value = mock_scan
        manager._catalog.inner_catalog.load_table.return_value = mock_table

        manager.scan("bronze.customers", snapshot_id=123456789)

        call_kwargs = mock_table.scan.call_args.kwargs
        assert call_kwargs["snapshot_id"] == 123456789

    def test_scan_error(self, manager: IcebergTableManager) -> None:
        """Test ScanError when scan fails."""
        mock_table = MagicMock()
        mock_table.scan.side_effect = RuntimeError("Scan failed")
        manager._catalog.inner_catalog.load_table.return_value = mock_table

        with pytest.raises(ScanError) as exc_info:
            manager.scan("bronze.customers")

        assert "bronze.customers" in str(exc_info.value)


class TestListSnapshots:
    """Tests for list_snapshots method."""

    def test_list_snapshots(self, manager: IcebergTableManager) -> None:
        """Test listing table snapshots."""
        mock_table = MagicMock()
        mock_snap1 = MagicMock()
        mock_snap1.snapshot_id = 1
        mock_snap1.timestamp_ms = 1702857600000
        mock_snap1.operation = "append"
        mock_snap1.summary = {}
        mock_snap1.manifest_list = None

        mock_snap2 = MagicMock()
        mock_snap2.snapshot_id = 2
        mock_snap2.timestamp_ms = 1702857700000  # Newer
        mock_snap2.operation = "overwrite"
        mock_snap2.summary = {}
        mock_snap2.manifest_list = None

        mock_metadata = MagicMock()
        mock_metadata.snapshots = [mock_snap1, mock_snap2]
        type(mock_table).metadata = PropertyMock(return_value=mock_metadata)
        manager._catalog.inner_catalog.load_table.return_value = mock_table

        result = manager.list_snapshots("bronze.customers")

        assert len(result) == 2
        # Should be sorted newest first
        assert result[0].snapshot_id == 2
        assert result[1].snapshot_id == 1

    def test_list_snapshots_with_limit(self, manager: IcebergTableManager) -> None:
        """Test listing snapshots with limit."""
        mock_table = MagicMock()
        mock_snaps = []
        for i in range(5):
            snap = MagicMock()
            snap.snapshot_id = i
            snap.timestamp_ms = 1702857600000 + i * 1000
            snap.operation = "append"
            snap.summary = {}
            snap.manifest_list = None
            mock_snaps.append(snap)

        mock_metadata = MagicMock()
        mock_metadata.snapshots = mock_snaps
        type(mock_table).metadata = PropertyMock(return_value=mock_metadata)
        manager._catalog.inner_catalog.load_table.return_value = mock_table

        result = manager.list_snapshots("bronze.customers", limit=2)

        assert len(result) == 2


class TestGetCurrentSnapshot:
    """Tests for get_current_snapshot method."""

    def test_get_current_snapshot(self, manager: IcebergTableManager) -> None:
        """Test getting current snapshot."""
        mock_table = MagicMock()
        mock_snapshot = MagicMock()
        mock_snapshot.snapshot_id = 123456
        mock_snapshot.timestamp_ms = 1702857600000
        mock_snapshot.operation = "append"
        mock_snapshot.summary = {}
        mock_snapshot.manifest_list = None
        mock_table.current_snapshot.return_value = mock_snapshot
        manager._catalog.inner_catalog.load_table.return_value = mock_table

        result = manager.get_current_snapshot("bronze.customers")

        assert result is not None
        assert result.snapshot_id == 123456

    def test_get_current_snapshot_none(self, manager: IcebergTableManager) -> None:
        """Test returns None when no snapshots."""
        mock_table = MagicMock()
        mock_table.current_snapshot.return_value = None
        manager._catalog.inner_catalog.load_table.return_value = mock_table

        result = manager.get_current_snapshot("bronze.customers")

        assert result is None


class TestBuildPartitionSpec:
    """Tests for build_partition_spec function."""

    def test_build_day_partition(self, sample_schema: pa.Schema) -> None:
        """Test building day partition spec."""
        transforms = [
            PartitionTransform(
                source_column="created_at",
                transform_type=PartitionTransformType.DAY,
            ),
        ]

        spec = build_partition_spec(transforms, sample_schema)

        assert len(spec.fields) == 1
        assert spec.fields[0].name == "created_at_day"

    def test_build_bucket_partition(self) -> None:
        """Test building bucket partition spec."""
        schema = pa.schema([
            pa.field("customer_id", pa.int64()),
        ])
        transforms = [
            PartitionTransform(
                source_column="customer_id",
                transform_type=PartitionTransformType.BUCKET,
                param=16,
            ),
        ]

        spec = build_partition_spec(transforms, schema)

        assert len(spec.fields) == 1
        assert spec.fields[0].name == "customer_id_bucket"

    def test_build_multiple_partitions(self, sample_schema: pa.Schema) -> None:
        """Test building multi-field partition spec."""
        transforms = [
            PartitionTransform(
                source_column="created_at",
                transform_type=PartitionTransformType.YEAR,
            ),
            PartitionTransform(
                source_column="created_at",
                transform_type=PartitionTransformType.MONTH,
            ),
        ]

        spec = build_partition_spec(transforms, sample_schema)

        assert len(spec.fields) == 2

    def test_build_partition_column_not_found(self) -> None:
        """Test error when source column not in schema."""
        schema = pa.schema([pa.field("id", pa.int64())])
        transforms = [
            PartitionTransform(
                source_column="nonexistent",
                transform_type=PartitionTransformType.DAY,
            ),
        ]

        with pytest.raises(ValueError) as exc_info:
            build_partition_spec(transforms, schema)

        assert "nonexistent" in str(exc_info.value)


class TestNormalizeIdentifier:
    """Tests for _normalize_identifier helper."""

    def test_normalize_string(self) -> None:
        """Test normalizing string identifier."""
        result = IcebergTableManager._normalize_identifier("bronze.customers")

        assert isinstance(result, TableIdentifier)
        assert result.namespace == "bronze"
        assert result.name == "customers"

    def test_normalize_table_identifier(self) -> None:
        """Test normalizing TableIdentifier (passthrough)."""
        tid = TableIdentifier(namespace="bronze", name="customers")

        result = IcebergTableManager._normalize_identifier(tid)

        assert result is tid


class TestNormalizeNamespace:
    """Tests for _normalize_namespace helper."""

    def test_normalize_string(self) -> None:
        """Test normalizing string namespace."""
        result = IcebergTableManager._normalize_namespace("bronze.raw")

        assert result == ("bronze", "raw")

    def test_normalize_tuple(self) -> None:
        """Test normalizing tuple namespace (passthrough)."""
        ns = ("bronze", "raw")

        result = IcebergTableManager._normalize_namespace(ns)

        assert result is ns


class TestToArrow:
    """Tests for _to_arrow helper."""

    def test_arrow_table_passthrough(self, sample_data: pa.Table) -> None:
        """Test PyArrow Table passes through."""
        result = IcebergTableManager._to_arrow(sample_data)

        assert result is sample_data

    def test_dataframe_conversion(self) -> None:
        """Test pandas DataFrame is converted."""
        import pandas as pd

        df = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})

        result = IcebergTableManager._to_arrow(df)

        assert isinstance(result, pa.Table)
        assert result.num_rows == 2


class TestExpireSnapshots:
    """Tests for expire_snapshots method."""

    def test_expire_snapshots_requires_parameter(
        self, mock_catalog: MagicMock
    ) -> None:
        """Test that at least one parameter is required."""
        manager = IcebergTableManager(mock_catalog)

        with pytest.raises(ValueError) as exc_info:
            manager.expire_snapshots("bronze.customers")

        assert "At least one of older_than or retain_last" in str(exc_info.value)

    def test_expire_snapshots_with_retain_last(
        self, mock_catalog: MagicMock
    ) -> None:
        """Test expire_snapshots with retain_last parameter."""
        manager = IcebergTableManager(mock_catalog)

        # Create mock snapshots
        mock_snap1 = MagicMock()
        mock_snap1.snapshot_id = 1
        mock_snap1.timestamp_ms = 1000000

        mock_snap2 = MagicMock()
        mock_snap2.snapshot_id = 2
        mock_snap2.timestamp_ms = 2000000

        mock_snap3 = MagicMock()
        mock_snap3.snapshot_id = 3
        mock_snap3.timestamp_ms = 3000000  # Most recent

        mock_table = MagicMock()
        mock_table.metadata.snapshots = [mock_snap1, mock_snap2, mock_snap3]
        mock_table.current_snapshot.return_value = mock_snap3
        mock_catalog.inner_catalog.load_table.return_value = mock_table

        # Retain only 2 most recent (snap2, snap3)
        expired_count = manager.expire_snapshots(
            "bronze.customers", retain_last=2
        )

        # snap1 should be expired
        assert expired_count == 1

    def test_expire_snapshots_with_older_than(
        self, mock_catalog: MagicMock
    ) -> None:
        """Test expire_snapshots with older_than parameter."""
        from datetime import datetime

        manager = IcebergTableManager(mock_catalog)

        # Create mock snapshots with specific timestamps
        mock_snap1 = MagicMock()
        mock_snap1.snapshot_id = 1
        mock_snap1.timestamp_ms = 1000  # Very old

        mock_snap2 = MagicMock()
        mock_snap2.snapshot_id = 2
        mock_snap2.timestamp_ms = int(datetime(2024, 1, 1).timestamp() * 1000)

        mock_snap3 = MagicMock()
        mock_snap3.snapshot_id = 3
        mock_snap3.timestamp_ms = int(datetime(2024, 6, 1).timestamp() * 1000)

        mock_table = MagicMock()
        mock_table.metadata.snapshots = [mock_snap1, mock_snap2, mock_snap3]
        mock_table.current_snapshot.return_value = mock_snap3
        mock_catalog.inner_catalog.load_table.return_value = mock_table

        # Expire snapshots older than 2024-03-01
        cutoff = datetime(2024, 3, 1)
        expired_count = manager.expire_snapshots(
            "bronze.customers", older_than=cutoff
        )

        # snap1 and snap2 are older than cutoff
        # But snap3 is current, so it's kept even if older
        # snap2 should be expired (snap1 too, but snap3 is current)
        assert expired_count == 2

    def test_expire_snapshots_with_both_parameters(
        self, mock_catalog: MagicMock
    ) -> None:
        """Test expire_snapshots with both older_than and retain_last."""
        from datetime import datetime

        manager = IcebergTableManager(mock_catalog)

        # Create 5 mock snapshots with timestamps in seconds * 1000 (milliseconds)
        # snap1: 1000ms, snap2: 2000ms, snap3: 3000ms, snap4: 4000ms, snap5: 5000ms
        snapshots = []
        for i in range(5):
            mock_snap = MagicMock()
            mock_snap.snapshot_id = i + 1
            mock_snap.timestamp_ms = (i + 1) * 1000  # milliseconds
            snapshots.append(mock_snap)

        mock_table = MagicMock()
        mock_table.metadata.snapshots = snapshots
        mock_table.current_snapshot.return_value = snapshots[-1]  # Most recent (snap5)
        mock_catalog.inner_catalog.load_table.return_value = mock_table

        # retain_last=2 keeps snapshots 4,5 (most recent)
        # older_than=3.5s means cutoff_ms=3500, so snap4 (4000ms) and snap5 (5000ms) are newer
        # Combined: keep snap4, snap5 (retain_last=2 OR newer than 3.5s)
        cutoff = datetime.fromtimestamp(3.5)  # 3500ms cutoff
        expired_count = manager.expire_snapshots(
            "bronze.customers", older_than=cutoff, retain_last=2
        )

        # Snapshots 1, 2, 3 should be expired (snap4, snap5 kept by both criteria)
        assert expired_count == 3

    def test_expire_snapshots_current_always_retained(
        self, mock_catalog: MagicMock
    ) -> None:
        """Test that current snapshot is always retained."""
        from datetime import datetime

        manager = IcebergTableManager(mock_catalog)

        # Create a single snapshot that is also current
        mock_snap = MagicMock()
        mock_snap.snapshot_id = 1
        mock_snap.timestamp_ms = 1000  # Very old

        mock_table = MagicMock()
        mock_table.metadata.snapshots = [mock_snap]
        mock_table.current_snapshot.return_value = mock_snap
        mock_catalog.inner_catalog.load_table.return_value = mock_table

        # Even with retain_last=0 (if that were allowed), current is kept
        # With older_than in the future, nothing should expire
        cutoff = datetime(2099, 1, 1)
        expired_count = manager.expire_snapshots(
            "bronze.customers", older_than=cutoff
        )

        # Current snapshot is always retained
        assert expired_count == 0

    def test_expire_snapshots_no_snapshots(
        self, mock_catalog: MagicMock
    ) -> None:
        """Test expire_snapshots with no existing snapshots."""
        manager = IcebergTableManager(mock_catalog)

        mock_table = MagicMock()
        mock_table.metadata.snapshots = []
        mock_table.current_snapshot.return_value = None
        mock_catalog.inner_catalog.load_table.return_value = mock_table

        expired_count = manager.expire_snapshots(
            "bronze.customers", retain_last=5
        )

        assert expired_count == 0

    def test_expire_snapshots_with_table_identifier(
        self, mock_catalog: MagicMock
    ) -> None:
        """Test expire_snapshots accepts TableIdentifier."""
        manager = IcebergTableManager(mock_catalog)

        mock_table = MagicMock()
        mock_table.metadata.snapshots = []
        mock_table.current_snapshot.return_value = None
        mock_catalog.inner_catalog.load_table.return_value = mock_table

        table_id = TableIdentifier(namespace="bronze", name="customers")
        expired_count = manager.expire_snapshots(table_id, retain_last=5)

        assert expired_count == 0
        mock_catalog.inner_catalog.load_table.assert_called_once()
