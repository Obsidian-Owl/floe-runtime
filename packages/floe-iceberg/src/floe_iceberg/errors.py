"""Custom exceptions for floe-iceberg.

This module defines the exception hierarchy:
- FloeStorageError (base, re-exported from floe-polaris)
- TableNotFoundError (re-exported from floe-polaris)
- TableExistsError
- SchemaEvolutionError
- WriteError
- ScanError
"""

from __future__ import annotations

# Re-export base exceptions from floe-polaris for convenience
from floe_polaris.errors import FloeStorageError, TableNotFoundError

__all__ = [
    "FloeStorageError",
    "TableNotFoundError",
    "TableExistsError",
    "SchemaEvolutionError",
    "WriteError",
    "ScanError",
]


class TableExistsError(FloeStorageError):
    """Table already exists in the catalog.

    Raised when attempting to create a table that already exists
    (when not using the idempotent create_table_if_not_exists method).

    Example:
        >>> try:
        ...     manager.create_table("bronze.customers", schema)  # Already exists
        ... except TableExistsError as e:
        ...     print(f"Table exists: {e.table}")
    """

    def __init__(
        self,
        table: str,
        message: str | None = None,
    ) -> None:
        """Initialize TableExistsError.

        Args:
            table: The table identifier that already exists.
            message: Optional custom error message.
        """
        msg = message or f"Table already exists: {table}"
        super().__init__(msg, details={"table": table})
        self.table = table


class SchemaEvolutionError(FloeStorageError):
    """Schema evolution is not possible due to incompatible changes.

    Raised when:
    - A required column is missing in new data
    - Column type change is incompatible (e.g., string -> int)
    - Schema evolution is disabled and schemas don't match

    Example:
        >>> try:
        ...     manager.append("bronze.customers", incompatible_data)
        ... except SchemaEvolutionError as e:
        ...     print(f"Schema mismatch: {e}")
    """

    def __init__(
        self,
        message: str = "Schema evolution failed",
        *,
        table: str | None = None,
        column: str | None = None,
        expected_type: str | None = None,
        actual_type: str | None = None,
    ) -> None:
        """Initialize SchemaEvolutionError.

        Args:
            message: Human-readable error description.
            table: The table where schema evolution failed.
            column: The column with the incompatible change.
            expected_type: The expected column type.
            actual_type: The actual column type in new data.
        """
        details: dict[str, str] = {}
        if table:
            details["table"] = table
        if column:
            details["column"] = column
        if expected_type:
            details["expected_type"] = expected_type
        if actual_type:
            details["actual_type"] = actual_type
        super().__init__(message, details=details)
        self.table = table
        self.column = column
        self.expected_type = expected_type
        self.actual_type = actual_type


class WriteError(FloeStorageError):
    """Write operation to Iceberg table failed.

    Raised when:
    - Data file writing fails
    - Commit to catalog fails (e.g., conflict)
    - Storage backend is unavailable

    Example:
        >>> try:
        ...     manager.append("bronze.customers", data)
        ... except WriteError as e:
        ...     print(f"Write failed: {e}")
    """

    def __init__(
        self,
        message: str = "Write operation failed",
        *,
        table: str | None = None,
        operation: str | None = None,
        cause: str | None = None,
    ) -> None:
        """Initialize WriteError.

        Args:
            message: Human-readable error description.
            table: The table that was being written to.
            operation: The type of write operation (append, overwrite).
            cause: The underlying cause of the failure.
        """
        details: dict[str, str] = {}
        if table:
            details["table"] = table
        if operation:
            details["operation"] = operation
        if cause:
            details["cause"] = cause
        super().__init__(message, details=details)
        self.table = table
        self.operation = operation
        self.cause = cause


class ScanError(FloeStorageError):
    """Scan operation on Iceberg table failed.

    Raised when:
    - Data file reading fails
    - Filter expression is invalid
    - Snapshot does not exist (time travel)

    Example:
        >>> try:
        ...     manager.scan("bronze.customers", snapshot_id=12345)
        ... except ScanError as e:
        ...     print(f"Scan failed: {e}")
    """

    def __init__(
        self,
        message: str = "Scan operation failed",
        *,
        table: str | None = None,
        snapshot_id: int | None = None,
        cause: str | None = None,
    ) -> None:
        """Initialize ScanError.

        Args:
            message: Human-readable error description.
            table: The table that was being scanned.
            snapshot_id: The snapshot ID that was requested.
            cause: The underlying cause of the failure.
        """
        details: dict[str, str] = {}
        if table:
            details["table"] = table
        if snapshot_id is not None:
            details["snapshot_id"] = str(snapshot_id)
        if cause:
            details["cause"] = cause
        super().__init__(message, details=details)
        self.table = table
        self.snapshot_id = snapshot_id
        self.cause = cause
