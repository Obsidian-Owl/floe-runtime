"""Unit tests for floe-iceberg custom exceptions.

Tests for TableExistsError, SchemaEvolutionError, WriteError, and ScanError.
"""

from __future__ import annotations

from floe_iceberg.errors import (
    FloeStorageError,
    ScanError,
    SchemaEvolutionError,
    TableExistsError,
    TableNotFoundError,
    WriteError,
)


class TestTableExistsError:
    """Tests for TableExistsError exception."""

    def test_basic_creation(self) -> None:
        """Test creating TableExistsError with table name."""
        error = TableExistsError(table="bronze.customers")

        assert error.table == "bronze.customers"
        assert "bronze.customers" in str(error)
        assert "already exists" in str(error)

    def test_custom_message(self) -> None:
        """Test TableExistsError with custom message."""
        error = TableExistsError(
            table="bronze.orders",
            message="Cannot create table: bronze.orders already exists",
        )

        assert error.table == "bronze.orders"
        assert "Cannot create table" in str(error)

    def test_inherits_from_floe_storage_error(self) -> None:
        """Test that TableExistsError inherits from FloeStorageError."""
        error = TableExistsError(table="test.table")

        assert isinstance(error, FloeStorageError)


class TestSchemaEvolutionError:
    """Tests for SchemaEvolutionError exception."""

    def test_basic_creation(self) -> None:
        """Test creating SchemaEvolutionError with default message."""
        error = SchemaEvolutionError()

        assert "Schema evolution failed" in str(error)

    def test_with_all_details(self) -> None:
        """Test SchemaEvolutionError with all optional details."""
        error = SchemaEvolutionError(
            message="Column type mismatch",
            table="bronze.customers",
            column="age",
            expected_type="int",
            actual_type="string",
        )

        assert error.table == "bronze.customers"
        assert error.column == "age"
        assert error.expected_type == "int"
        assert error.actual_type == "string"
        assert "Column type mismatch" in str(error)

    def test_partial_details(self) -> None:
        """Test SchemaEvolutionError with partial details."""
        error = SchemaEvolutionError(
            message="Missing required column",
            table="bronze.orders",
            column="customer_id",
        )

        assert error.table == "bronze.orders"
        assert error.column == "customer_id"
        assert error.expected_type is None
        assert error.actual_type is None

    def test_inherits_from_floe_storage_error(self) -> None:
        """Test that SchemaEvolutionError inherits from FloeStorageError."""
        error = SchemaEvolutionError()

        assert isinstance(error, FloeStorageError)


class TestWriteError:
    """Tests for WriteError exception."""

    def test_basic_creation(self) -> None:
        """Test creating WriteError with default message."""
        error = WriteError()

        assert "Write operation failed" in str(error)

    def test_with_all_details(self) -> None:
        """Test WriteError with all optional details."""
        error = WriteError(
            message="Commit conflict",
            table="bronze.customers",
            operation="append",
            cause="Concurrent modification detected",
        )

        assert error.table == "bronze.customers"
        assert error.operation == "append"
        assert error.cause == "Concurrent modification detected"
        assert "Commit conflict" in str(error)

    def test_partial_details(self) -> None:
        """Test WriteError with partial details."""
        error = WriteError(
            message="S3 write failed",
            table="bronze.orders",
        )

        assert error.table == "bronze.orders"
        assert error.operation is None
        assert error.cause is None

    def test_inherits_from_floe_storage_error(self) -> None:
        """Test that WriteError inherits from FloeStorageError."""
        error = WriteError()

        assert isinstance(error, FloeStorageError)


class TestScanError:
    """Tests for ScanError exception."""

    def test_basic_creation(self) -> None:
        """Test creating ScanError with default message."""
        error = ScanError()

        assert "Scan operation failed" in str(error)

    def test_with_all_details(self) -> None:
        """Test ScanError with all optional details."""
        error = ScanError(
            message="Snapshot not found",
            table="bronze.customers",
            snapshot_id=12345678901234,
            cause="Invalid snapshot ID",
        )

        assert error.table == "bronze.customers"
        assert error.snapshot_id == 12345678901234
        assert error.cause == "Invalid snapshot ID"
        assert "Snapshot not found" in str(error)

    def test_partial_details(self) -> None:
        """Test ScanError with partial details."""
        error = ScanError(
            message="Filter parse error",
            table="bronze.orders",
        )

        assert error.table == "bronze.orders"
        assert error.snapshot_id is None
        assert error.cause is None

    def test_inherits_from_floe_storage_error(self) -> None:
        """Test that ScanError inherits from FloeStorageError."""
        error = ScanError()

        assert isinstance(error, FloeStorageError)


class TestReExports:
    """Test that base exceptions are re-exported correctly."""

    def test_floe_storage_error_reexported(self) -> None:
        """Test FloeStorageError is re-exported."""
        # Should be importable from floe_iceberg.errors
        assert FloeStorageError is not None

    def test_table_not_found_error_reexported(self) -> None:
        """Test TableNotFoundError is re-exported."""
        # Should be importable from floe_iceberg.errors
        assert TableNotFoundError is not None
