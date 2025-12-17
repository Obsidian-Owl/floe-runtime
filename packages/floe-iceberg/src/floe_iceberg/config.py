"""Pydantic configuration models for floe-iceberg.

This module provides:
- WriteMode: Enum for write operation modes
- TableIdentifier: Table identifier model
- PartitionTransformType: Enum for partition transform types
- PartitionTransform: Partition transform configuration
- SnapshotInfo: Iceberg snapshot information model
- MaterializationMetadata: Dagster asset materialization metadata
- IcebergIOManagerConfig: IOManager configuration
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator
from typing_extensions import Self


class WriteMode(str, Enum):
    """Write mode for table operations.

    Determines how data is written to Iceberg tables:
    - APPEND: Add new rows to existing data
    - OVERWRITE: Replace all existing rows with new data
    """

    APPEND = "append"
    OVERWRITE = "overwrite"


class TableIdentifier(BaseModel):
    """Iceberg table identifier with namespace and name.

    Represents a fully qualified table identifier in the format
    "namespace.table_name". Supports nested namespaces.

    Attributes:
        namespace: Namespace (can be nested, e.g., "bronze.raw").
        name: Table name without namespace prefix.

    Example:
        >>> tid = TableIdentifier(namespace="bronze", name="customers")
        >>> str(tid)
        'bronze.customers'
        >>> TableIdentifier.from_string("bronze.customers")
        TableIdentifier(namespace='bronze', name='customers')
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    namespace: str = Field(
        ...,
        min_length=1,
        description="Namespace (can be nested with dots)",
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Table name",
    )

    def __str__(self) -> str:
        """Return fully qualified table identifier."""
        return f"{self.namespace}.{self.name}"

    @classmethod
    def from_string(cls, identifier: str) -> TableIdentifier:
        """Parse table identifier from string.

        Args:
            identifier: Table identifier string (namespace.table).

        Returns:
            TableIdentifier instance.

        Raises:
            ValueError: If identifier format is invalid.

        Example:
            >>> TableIdentifier.from_string("bronze.raw.customers")
            TableIdentifier(namespace='bronze.raw', name='customers')
        """
        parts = identifier.rsplit(".", 1)
        if len(parts) != 2:
            msg = f"Invalid table identifier format: {identifier}. Expected 'namespace.table'"
            raise ValueError(msg)
        return cls(namespace=parts[0], name=parts[1])

    @field_validator("name")
    @classmethod
    def validate_name_no_dots(cls, v: str) -> str:
        """Validate that table name doesn't contain dots."""
        if "." in v:
            msg = f"Table name cannot contain dots: {v}"
            raise ValueError(msg)
        return v


class PartitionTransformType(str, Enum):
    """Iceberg partition transform types.

    Defines how partition values are computed from source columns:
    - IDENTITY: Use column value as-is
    - YEAR: Extract year from timestamp
    - MONTH: Extract year-month from timestamp
    - DAY: Extract date from timestamp
    - HOUR: Extract hour from timestamp
    - BUCKET: Hash into N buckets
    - TRUNCATE: Truncate to width W
    """

    IDENTITY = "identity"
    YEAR = "year"
    MONTH = "month"
    DAY = "day"
    HOUR = "hour"
    BUCKET = "bucket"
    TRUNCATE = "truncate"


class PartitionTransform(BaseModel):
    """Partition transform specification for Iceberg tables.

    Defines how a source column is transformed into partition values.

    Attributes:
        source_column: Column to partition on.
        transform_type: Type of transform to apply.
        param: Optional parameter (num_buckets for BUCKET, width for TRUNCATE).

    Example:
        >>> # Partition by day
        >>> pt = PartitionTransform(source_column="created_at", transform_type=PartitionTransformType.DAY)

        >>> # Bucket partitioning
        >>> pt = PartitionTransform(
        ...     source_column="customer_id",
        ...     transform_type=PartitionTransformType.BUCKET,
        ...     param=16
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_column: str = Field(
        ...,
        min_length=1,
        description="Source column name to partition on",
    )
    transform_type: PartitionTransformType = Field(
        ...,
        description="Type of partition transform",
    )
    param: int | None = Field(
        default=None,
        ge=1,
        description="Transform parameter (buckets for BUCKET, width for TRUNCATE)",
    )

    @model_validator(mode="after")
    def validate_param_required(self) -> Self:
        """Validate param is provided for transforms that require it."""
        requires_param = {PartitionTransformType.BUCKET, PartitionTransformType.TRUNCATE}
        if self.transform_type in requires_param and self.param is None:
            msg = f"Transform type {self.transform_type.value} requires 'param'"
            raise ValueError(msg)
        return self


class SnapshotInfo(BaseModel):
    """Information about an Iceberg table snapshot.

    Represents metadata about a specific table snapshot, including
    when it was created and statistics about the operation.

    Attributes:
        snapshot_id: Unique snapshot identifier.
        timestamp_ms: Snapshot creation timestamp in milliseconds since epoch.
        operation: Operation that created the snapshot (append, overwrite, delete).
        summary: Snapshot summary statistics (added-data-files, added-records, etc.).
        manifest_list: Path to the manifest list file (optional).

    Example:
        >>> snap = SnapshotInfo(
        ...     snapshot_id=123456789,
        ...     timestamp_ms=1702857600000,
        ...     operation="append",
        ...     summary={"added-records": "100"},
        ... )
        >>> snap.timestamp
        datetime.datetime(2023, 12, 18, 0, 0, tzinfo=datetime.timezone.utc)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    snapshot_id: int = Field(
        ...,
        description="Unique snapshot identifier",
    )
    timestamp_ms: int = Field(
        ...,
        ge=0,
        description="Snapshot creation timestamp in milliseconds since epoch",
    )
    operation: str = Field(
        ...,
        description="Operation that created the snapshot",
    )
    summary: dict[str, str] = Field(
        default_factory=dict,
        description="Snapshot summary statistics",
    )
    manifest_list: str | None = Field(
        default=None,
        description="Path to manifest list file",
    )

    @property
    def timestamp(self) -> datetime:
        """Return snapshot creation time as datetime.

        Returns:
            datetime in UTC timezone.
        """
        return datetime.fromtimestamp(self.timestamp_ms / 1000, tz=timezone.utc)

    @property
    def added_records(self) -> int:
        """Return number of records added in this snapshot."""
        return int(self.summary.get("added-records", "0"))

    @property
    def deleted_records(self) -> int:
        """Return number of records deleted in this snapshot."""
        return int(self.summary.get("deleted-records", "0"))


class MaterializationMetadata(BaseModel):
    """Metadata attached to Dagster asset materializations.

    Contains information about the Iceberg table write operation
    that can be viewed in Dagster's asset catalog UI.

    Attributes:
        table: Fully qualified table identifier.
        namespace: Table namespace.
        table_name: Table name without namespace.
        snapshot_id: Snapshot ID created by this materialization.
        num_rows: Number of rows written.
        write_mode: Write mode used (append or overwrite).
        schema_evolved: Whether schema evolution occurred.

    Example:
        >>> meta = MaterializationMetadata(
        ...     table="bronze.customers",
        ...     namespace="bronze",
        ...     table_name="customers",
        ...     snapshot_id=123456789,
        ...     num_rows=1000,
        ...     write_mode=WriteMode.APPEND,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    table: str = Field(
        ...,
        description="Fully qualified table identifier",
    )
    namespace: str = Field(
        ...,
        description="Table namespace",
    )
    table_name: str = Field(
        ...,
        description="Table name",
    )
    snapshot_id: int = Field(
        ...,
        description="Snapshot ID created by this write",
    )
    num_rows: int = Field(
        ...,
        ge=0,
        description="Number of rows written",
    )
    write_mode: WriteMode = Field(
        ...,
        description="Write mode used",
    )
    schema_evolved: bool = Field(
        default=False,
        description="Whether schema evolution occurred",
    )


class IcebergIOManagerConfig(BaseModel):
    """Configuration for IcebergIOManager.

    Configures how Dagster assets are stored in Iceberg tables,
    including catalog connection, write behavior, and schema handling.

    Attributes:
        catalog_uri: Polaris REST API endpoint (required).
        warehouse: Warehouse name (required).
        client_id: OAuth2 client ID (optional if using token).
        client_secret: OAuth2 client secret (optional if using token).
        token: Pre-fetched bearer token (alternative to client credentials).
        default_namespace: Namespace for single-part asset keys (default "public").
        write_mode: Default write mode (default APPEND).
        schema_evolution_enabled: Enable automatic schema evolution (default True).
        auto_create_tables: Create tables on first write (default True).
        partition_column: Default partition column for time-based partitioning.

    Example:
        >>> config = IcebergIOManagerConfig(
        ...     catalog_uri="http://localhost:8181/api/catalog",
        ...     warehouse="my_warehouse",
        ...     default_namespace="bronze",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    catalog_uri: str = Field(
        ...,
        min_length=1,
        description="Polaris REST API endpoint URL",
    )
    warehouse: str = Field(
        ...,
        min_length=1,
        description="Warehouse name",
    )
    client_id: str | None = Field(
        default=None,
        description="OAuth2 client ID",
    )
    client_secret: SecretStr | None = Field(
        default=None,
        description="OAuth2 client secret",
    )
    token: SecretStr | None = Field(
        default=None,
        description="Pre-fetched bearer token",
    )
    default_namespace: str = Field(
        default="public",
        min_length=1,
        description="Default namespace for single-part asset keys",
    )
    write_mode: WriteMode = Field(
        default=WriteMode.APPEND,
        description="Default write mode for table operations",
    )
    schema_evolution_enabled: bool = Field(
        default=True,
        description="Enable automatic schema evolution",
    )
    auto_create_tables: bool = Field(
        default=True,
        description="Create tables automatically on first write",
    )
    partition_column: str | None = Field(
        default=None,
        description="Default partition column for time-based partitioning",
    )

    @field_validator("catalog_uri")
    @classmethod
    def validate_uri_format(cls, v: str) -> str:
        """Validate URI format (must be http:// or https://)."""
        if not v.startswith(("http://", "https://")):
            msg = f"URI must start with http:// or https://, got: {v}"
            raise ValueError(msg)
        return v.rstrip("/")  # Normalize by removing trailing slash
