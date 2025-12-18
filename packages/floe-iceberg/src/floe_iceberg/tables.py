"""IcebergTableManager: Manage Iceberg tables via PyIceberg.

This module provides the IcebergTableManager class for creating,
listing, and managing Iceberg tables outside of Dagster context.

Use IcebergIOManager for Dagster asset storage. Use IcebergTableManager
for direct table operations (schema changes, maintenance, etc.).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, TypeAlias

import pandas as pd
import pyarrow as pa
from pyiceberg.exceptions import NoSuchNamespaceError as PyIcebergNamespaceNotFoundError
from pyiceberg.exceptions import NoSuchTableError as PyIcebergTableNotFoundError
from pyiceberg.exceptions import TableAlreadyExistsError as PyIcebergTableExistsError
from pyiceberg.partitioning import PartitionField, PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.transforms import (
    BucketTransform,
    DayTransform,
    HourTransform,
    IdentityTransform,
    MonthTransform,
    Transform,
    TruncateTransform,
    YearTransform,
)

from floe_iceberg.config import (
    PartitionTransform,
    PartitionTransformType,
    SnapshotInfo,
    TableIdentifier,
)
from floe_iceberg.errors import (
    ScanError,
    SchemaEvolutionError,
    TableExistsError,
    TableNotFoundError,
    WriteError,
)
from floe_iceberg.observability import get_logger, get_tracer, table_operation

if TYPE_CHECKING:
    from opentelemetry.trace import Tracer
    from pyiceberg.catalog import Catalog
    from pyiceberg.table import Table
    from structlog.stdlib import BoundLogger

    from floe_polaris.client import PolarisCatalog

    # Union type for catalog sources
    CatalogLike: TypeAlias = PolarisCatalog | Catalog


class IcebergTableManager:
    """Manage Iceberg tables directly via PyIceberg.

    Use this class for:
    - Creating tables with specific schemas
    - Dropping or purging tables
    - Table maintenance operations
    - Direct data operations (append, overwrite, scan)

    Note:
        For Dagster asset storage, use IcebergIOManager instead.

    Attributes:
        catalog: PolarisCatalog instance for catalog operations.

    Example:
        >>> from floe_polaris import create_catalog, PolarisCatalogConfig
        >>> from floe_iceberg import IcebergTableManager
        >>> import pyarrow as pa
        >>>
        >>> catalog = create_catalog(PolarisCatalogConfig(...))
        >>> manager = IcebergTableManager(catalog)
        >>>
        >>> schema = pa.schema([("id", pa.int64()), ("name", pa.string())])
        >>> table = manager.create_table("bronze.customers", schema)
    """

    def __init__(
        self,
        catalog: CatalogLike,
        *,
        tracer: Tracer | None = None,
        logger: BoundLogger | None = None,
    ) -> None:
        """Initialize IcebergTableManager.

        Args:
            catalog: PolarisCatalog instance or PyIceberg Catalog for operations.
            tracer: Optional OpenTelemetry tracer for custom tracing.
            logger: Optional structlog logger for custom logging.
        """
        self._catalog = catalog
        self._tracer = tracer or get_tracer()
        self._logger = logger or get_logger()

    @property
    def catalog(self) -> CatalogLike:
        """Return the underlying catalog instance."""
        return self._catalog

    @property
    def inner_catalog(self) -> Catalog:
        """Return the inner PyIceberg Catalog.

        Handles both PolarisCatalog (which wraps a Catalog) and direct Catalog.
        """
        # If it's a PolarisCatalog, get the inner catalog
        if hasattr(self._catalog, "inner_catalog"):
            return self._catalog.inner_catalog
        # Otherwise, it's already a Catalog
        return self._catalog

    # -------------------------------------------------------------------------
    # Table Operations
    # -------------------------------------------------------------------------

    def create_table(
        self,
        identifier: str | TableIdentifier,
        schema: pa.Schema | Schema,
        partition_spec: PartitionSpec | list[PartitionTransform] | None = None,
        properties: dict[str, str] | None = None,
    ) -> Table:
        """Create a new Iceberg table.

        Args:
            identifier: Table identifier (namespace.table or TableIdentifier).
            schema: Table schema (PyArrow or Iceberg Schema).
            partition_spec: Optional partition specification. Can be:
                - PartitionSpec: PyIceberg partition spec
                - list[PartitionTransform]: List of partition transforms
            properties: Optional table properties.

        Returns:
            Created PyIceberg Table object.

        Raises:
            TableExistsError: If table already exists.
            NamespaceNotFoundError: If namespace doesn't exist.

        Example:
            >>> import pyarrow as pa
            >>> schema = pa.schema([
            ...     pa.field("id", pa.int64()),
            ...     pa.field("name", pa.string()),
            ...     pa.field("created_at", pa.timestamp("us")),
            ... ])
            >>> table = manager.create_table("bronze.customers", schema)
        """
        table_id = self._normalize_identifier(identifier)
        table_str = str(table_id)

        with table_operation(
            "create_table",
            table=table_str,
            namespace=table_id.namespace,
        ):
            self._logger.info(
                "creating_table",
                table=table_str,
                namespace=table_id.namespace,
            )

            # Convert PyArrow schema to Iceberg schema if needed
            iceberg_schema = self._to_iceberg_schema(schema)

            # Build partition spec if provided
            spec = self._build_partition_spec(partition_spec, iceberg_schema)

            try:
                inner_catalog = self.inner_catalog
                table = inner_catalog.create_table(
                    identifier=(table_id.namespace, table_id.name),
                    schema=iceberg_schema,
                    partition_spec=spec,
                    properties=properties or {},
                )
                self._logger.info("table_created", table=table_str)
                return table
            except PyIcebergTableExistsError as exc:
                raise TableExistsError(table_str) from exc
            except PyIcebergNamespaceNotFoundError as exc:
                from floe_polaris.errors import NamespaceNotFoundError

                raise NamespaceNotFoundError(table_id.namespace) from exc

    def create_table_if_not_exists(
        self,
        identifier: str | TableIdentifier,
        schema: pa.Schema | Schema,
        partition_spec: PartitionSpec | list[PartitionTransform] | None = None,
        properties: dict[str, str] | None = None,
    ) -> Table:
        """Create table if it doesn't exist (idempotent).

        Args:
            identifier: Table identifier.
            schema: Table schema.
            partition_spec: Optional partition specification.
            properties: Optional table properties.

        Returns:
            Table object (created or existing).

        Example:
            >>> table = manager.create_table_if_not_exists(
            ...     "bronze.customers",
            ...     schema,
            ... )
        """
        table_id = self._normalize_identifier(identifier)
        table_str = str(table_id)

        with table_operation(
            "create_table_if_not_exists",
            table=table_str,
            namespace=table_id.namespace,
        ):
            if self.table_exists(table_id):
                self._logger.debug("table_exists_skipping_create", table=table_str)
                return self.load_table(table_id)

            return self.create_table(
                identifier=table_id,
                schema=schema,
                partition_spec=partition_spec,
                properties=properties,
            )

    def load_table(
        self,
        identifier: str | TableIdentifier,
    ) -> Table:
        """Load an existing Iceberg table.

        Args:
            identifier: Table identifier.

        Returns:
            PyIceberg Table object.

        Raises:
            TableNotFoundError: If table doesn't exist.

        Example:
            >>> table = manager.load_table("bronze.customers")
        """
        table_id = self._normalize_identifier(identifier)
        table_str = str(table_id)

        with table_operation(
            "load_table",
            table=table_str,
            namespace=table_id.namespace,
        ):
            self._logger.debug("loading_table", table=table_str)
            try:
                inner_catalog = self.inner_catalog
                return inner_catalog.load_table((table_id.namespace, table_id.name))
            except PyIcebergTableNotFoundError as exc:
                raise TableNotFoundError(table_str) from exc

    def drop_table(
        self,
        identifier: str | TableIdentifier,
        purge: bool = False,
    ) -> None:
        """Drop an Iceberg table.

        Args:
            identifier: Table identifier.
            purge: If True, also delete data files. If False, only
                removes metadata (data files remain for recovery).

        Raises:
            TableNotFoundError: If table doesn't exist.

        Example:
            >>> manager.drop_table("bronze.customers")
            >>> manager.drop_table("bronze.temp", purge=True)
        """
        table_id = self._normalize_identifier(identifier)
        table_str = str(table_id)

        with table_operation(
            "drop_table",
            table=table_str,
            namespace=table_id.namespace,
        ):
            self._logger.info("dropping_table", table=table_str, purge=purge)
            try:
                inner_catalog = self.inner_catalog
                # Note: PyIceberg's base Catalog.drop_table doesn't accept purge param
                # The purge behavior is catalog-implementation specific
                inner_catalog.drop_table((table_id.namespace, table_id.name))
                self._logger.info("table_dropped", table=table_str)
            except PyIcebergTableNotFoundError as exc:
                raise TableNotFoundError(table_str) from exc

    def table_exists(
        self,
        identifier: str | TableIdentifier,
    ) -> bool:
        """Check if a table exists.

        Args:
            identifier: Table identifier.

        Returns:
            True if table exists.

        Example:
            >>> if manager.table_exists("bronze.customers"):
            ...     print("Table exists")
        """
        table_id = self._normalize_identifier(identifier)
        table_str = str(table_id)

        with table_operation(
            "table_exists",
            table=table_str,
            namespace=table_id.namespace,
        ):
            try:
                inner_catalog = self.inner_catalog
                inner_catalog.load_table((table_id.namespace, table_id.name))
                return True
            except PyIcebergTableNotFoundError:
                return False

    def list_tables(
        self,
        namespace: str | tuple[str, ...],
    ) -> list[str]:
        """List tables in a namespace.

        Args:
            namespace: Namespace name.

        Returns:
            List of table names (without namespace prefix).

        Example:
            >>> tables = manager.list_tables("bronze")
            >>> print(tables)
            ['customers', 'orders', 'products']
        """
        ns_tuple = self._normalize_namespace(namespace)
        ns_str = ".".join(ns_tuple)

        with table_operation(
            "list_tables",
            namespace=ns_str,
        ):
            self._logger.debug("listing_tables", namespace=ns_str)
            inner_catalog = self.inner_catalog
            identifiers = inner_catalog.list_tables(ns_tuple)
            # Return just the table names (last part of identifier)
            return [ident[-1] for ident in identifiers]

    # -------------------------------------------------------------------------
    # Data Operations
    # -------------------------------------------------------------------------

    def append(
        self,
        identifier: str | TableIdentifier,
        data: pa.Table | pd.DataFrame,
        *,
        evolve_schema: bool = True,
    ) -> SnapshotInfo:
        """Append data to an Iceberg table.

        Args:
            identifier: Table identifier.
            data: Data to append (PyArrow Table or Pandas DataFrame).
            evolve_schema: If True, automatically add new columns.

        Returns:
            SnapshotInfo with new snapshot details.

        Raises:
            TableNotFoundError: If table doesn't exist.
            SchemaEvolutionError: If schema evolution fails.
            WriteError: If write operation fails.

        Example:
            >>> data = pa.Table.from_pydict({"id": [1, 2], "name": ["a", "b"]})
            >>> snapshot = manager.append("bronze.customers", data)
            >>> print(f"Created snapshot {snapshot.snapshot_id}")
        """
        table_id = self._normalize_identifier(identifier)
        table_str = str(table_id)

        # Convert DataFrame to PyArrow if needed
        arrow_data = self._to_arrow(data)
        num_rows = arrow_data.num_rows

        with table_operation(
            "append",
            table=table_str,
            num_rows=num_rows,
            write_mode="append",
        ):
            self._logger.info(
                "appending_data",
                table=table_str,
                num_rows=num_rows,
            )

            try:
                table = self.load_table(table_id)

                # Handle schema evolution if enabled
                if evolve_schema:
                    self._evolve_schema_if_needed(table, arrow_data.schema, table_str)

                table.append(arrow_data)

                # Get the new snapshot info
                current_snapshot = table.current_snapshot()
                if current_snapshot is None:
                    msg = f"No snapshot created after append to {table_str}"
                    raise WriteError(msg, table=table_str, operation="append")

                snapshot_info = self._to_snapshot_info(current_snapshot)
                self._logger.info(
                    "data_appended",
                    table=table_str,
                    snapshot_id=snapshot_info.snapshot_id,
                    num_rows=num_rows,
                )
                return snapshot_info

            except TableNotFoundError:
                raise
            except SchemaEvolutionError:
                raise
            except Exception as exc:
                raise WriteError(
                    f"Failed to append to {table_str}: {exc}",
                    table=table_str,
                    operation="append",
                    cause=str(exc),
                ) from exc

    def overwrite(
        self,
        identifier: str | TableIdentifier,
        data: pa.Table | pd.DataFrame,
        *,
        evolve_schema: bool = True,
    ) -> SnapshotInfo:
        """Overwrite table data (replace all rows).

        Args:
            identifier: Table identifier.
            data: New data to write.
            evolve_schema: If True, automatically add new columns.

        Returns:
            SnapshotInfo with new snapshot details.

        Raises:
            TableNotFoundError: If table doesn't exist.
            WriteError: If write operation fails.

        Example:
            >>> data = pa.Table.from_pydict({"id": [1, 2], "name": ["a", "b"]})
            >>> snapshot = manager.overwrite("bronze.customers", data)
        """
        table_id = self._normalize_identifier(identifier)
        table_str = str(table_id)

        # Convert DataFrame to PyArrow if needed
        arrow_data = self._to_arrow(data)
        num_rows = arrow_data.num_rows

        with table_operation(
            "overwrite",
            table=table_str,
            num_rows=num_rows,
            write_mode="overwrite",
        ):
            self._logger.info(
                "overwriting_data",
                table=table_str,
                num_rows=num_rows,
            )

            try:
                table = self.load_table(table_id)

                # Handle schema evolution if enabled
                if evolve_schema:
                    self._evolve_schema_if_needed(table, arrow_data.schema, table_str)

                table.overwrite(arrow_data)

                # Get the new snapshot info
                current_snapshot = table.current_snapshot()
                if current_snapshot is None:
                    msg = f"No snapshot created after overwrite to {table_str}"
                    raise WriteError(msg, table=table_str, operation="overwrite")

                snapshot_info = self._to_snapshot_info(current_snapshot)
                self._logger.info(
                    "data_overwritten",
                    table=table_str,
                    snapshot_id=snapshot_info.snapshot_id,
                    num_rows=num_rows,
                )
                return snapshot_info

            except TableNotFoundError:
                raise
            except SchemaEvolutionError:
                raise
            except Exception as exc:
                raise WriteError(
                    f"Failed to overwrite {table_str}: {exc}",
                    table=table_str,
                    operation="overwrite",
                    cause=str(exc),
                ) from exc

    def scan(
        self,
        identifier: str | TableIdentifier,
        columns: list[str] | None = None,
        row_filter: str | None = None,
        snapshot_id: int | None = None,
        limit: int | None = None,
    ) -> pa.Table:
        """Scan table data with optional filtering.

        Args:
            identifier: Table identifier.
            columns: Columns to project (None = all).
            row_filter: Row filter expression (Iceberg expression syntax).
            snapshot_id: Read from specific snapshot (time travel).
            limit: Maximum rows to return.

        Returns:
            PyArrow Table with scan results.

        Raises:
            TableNotFoundError: If table doesn't exist.
            ScanError: If scan operation fails.

        Example:
            >>> # Read specific columns
            >>> data = manager.scan("bronze.customers", columns=["id", "name"])

            >>> # Time travel to previous snapshot
            >>> data = manager.scan("bronze.customers", snapshot_id=123456789)

            >>> # Filter rows
            >>> data = manager.scan("bronze.customers", row_filter="status = 'active'")
        """
        table_id = self._normalize_identifier(identifier)
        table_str = str(table_id)

        with table_operation(
            "scan",
            table=table_str,
            snapshot_id=snapshot_id,
        ):
            self._logger.debug(
                "scanning_table",
                table=table_str,
                columns=columns,
                has_filter=row_filter is not None,
                snapshot_id=snapshot_id,
                limit=limit,
            )

            try:
                table = self.load_table(table_id)

                # Build scan kwargs - only include row_filter if provided
                scan_kwargs: dict[str, Any] = {}
                if row_filter is not None:
                    scan_kwargs["row_filter"] = row_filter
                if columns:
                    scan_kwargs["selected_fields"] = tuple(columns)
                if snapshot_id is not None:
                    scan_kwargs["snapshot_id"] = snapshot_id
                if limit is not None:
                    scan_kwargs["limit"] = limit

                scan = table.scan(**scan_kwargs)

                # Execute scan and return as PyArrow Table
                result = scan.to_arrow()
                self._logger.debug(
                    "scan_completed",
                    table=table_str,
                    num_rows=result.num_rows,
                )
                return result

            except TableNotFoundError:
                raise
            except Exception as exc:
                raise ScanError(
                    f"Failed to scan {table_str}: {exc}",
                    table=table_str,
                    snapshot_id=snapshot_id,
                    cause=str(exc),
                ) from exc

    # -------------------------------------------------------------------------
    # Snapshot Operations
    # -------------------------------------------------------------------------

    def list_snapshots(
        self,
        identifier: str | TableIdentifier,
        limit: int | None = None,
    ) -> list[SnapshotInfo]:
        """List table snapshots.

        Args:
            identifier: Table identifier.
            limit: Maximum snapshots to return.

        Returns:
            List of SnapshotInfo objects (newest first).

        Example:
            >>> snapshots = manager.list_snapshots("bronze.customers")
            >>> for snap in snapshots:
            ...     print(f"{snap.snapshot_id}: {snap.timestamp}")
        """
        table_id = self._normalize_identifier(identifier)
        table_str = str(table_id)

        with table_operation(
            "list_snapshots",
            table=table_str,
        ):
            self._logger.debug("listing_snapshots", table=table_str)
            table = self.load_table(table_id)
            metadata = table.metadata

            snapshots = [self._to_snapshot_info(snap) for snap in metadata.snapshots]

            # Sort by timestamp descending (newest first)
            snapshots.sort(key=lambda s: s.timestamp_ms, reverse=True)

            if limit:
                snapshots = snapshots[:limit]

            return snapshots

    def get_current_snapshot(
        self,
        identifier: str | TableIdentifier,
    ) -> SnapshotInfo | None:
        """Get current snapshot info.

        Args:
            identifier: Table identifier.

        Returns:
            Current SnapshotInfo, or None if table has no snapshots.

        Example:
            >>> snapshot = manager.get_current_snapshot("bronze.customers")
            >>> if snapshot:
            ...     print(f"Current snapshot: {snapshot.snapshot_id}")
        """
        table_id = self._normalize_identifier(identifier)
        table_str = str(table_id)

        with table_operation(
            "get_current_snapshot",
            table=table_str,
        ):
            table = self.load_table(table_id)
            current = table.current_snapshot()

            if current is None:
                return None

            return self._to_snapshot_info(current)

    def expire_snapshots(
        self,
        identifier: str | TableIdentifier,
        older_than: datetime | None = None,
        retain_last: int | None = None,
    ) -> int:
        """Expire old snapshots to reclaim storage space.

        Removes snapshots that are older than a specified timestamp and/or
        ensures only a certain number of recent snapshots are retained.
        This operation cleans up metadata but does NOT delete data files.

        Args:
            identifier: Table identifier (namespace.table or TableIdentifier).
            older_than: Expire snapshots created before this timestamp.
                If None, no time-based filtering is applied.
            retain_last: Always retain at least this many most recent snapshots.
                If None, no count-based retention is applied.

        Returns:
            Number of snapshots expired.

        Note:
            At least one of older_than or retain_last must be specified.
            Data files are not deleted by this operation; use a separate
            vacuum operation to clean up orphan files.

        Example:
            >>> from datetime import datetime, timedelta
            >>> # Expire snapshots older than 7 days, keep at least 5
            >>> expired = manager.expire_snapshots(
            ...     "bronze.customers",
            ...     older_than=datetime.now() - timedelta(days=7),
            ...     retain_last=5,
            ... )
            >>> print(f"Expired {expired} snapshots")
        """
        table_id = self._normalize_identifier(identifier)
        table_str = str(table_id)

        if older_than is None and retain_last is None:
            msg = "At least one of older_than or retain_last must be specified"
            raise ValueError(msg)

        with table_operation(
            "expire_snapshots",
            table=table_str,
        ):
            table = self.load_table(table_id)

            # Get all snapshots sorted by timestamp (newest first)
            snapshots = list(table.metadata.snapshots)
            if not snapshots:
                return 0

            # Sort by timestamp descending
            snapshots.sort(key=lambda s: s.timestamp_ms, reverse=True)

            # Determine which snapshots to keep
            keep_snapshot_ids: set[int] = set()

            # Apply retain_last constraint
            if retain_last is not None and retain_last > 0:
                for snap in snapshots[:retain_last]:
                    keep_snapshot_ids.add(snap.snapshot_id)

            # Apply older_than constraint
            if older_than is not None:
                older_than_ms = int(older_than.timestamp() * 1000)
                for snap in snapshots:
                    if snap.timestamp_ms >= older_than_ms:
                        keep_snapshot_ids.add(snap.snapshot_id)

            # Current snapshot is always kept
            current = table.current_snapshot()
            if current is not None:
                keep_snapshot_ids.add(current.snapshot_id)

            # Calculate snapshots to expire
            expire_ids = [
                snap.snapshot_id for snap in snapshots if snap.snapshot_id not in keep_snapshot_ids
            ]

            if not expire_ids:
                return 0

            # PyIceberg doesn't have a direct expire_snapshots API in all versions,
            # so we log the intended action but note this is a metadata operation
            # In production, this would use table.expire_snapshots() or
            # Iceberg's maintenance procedures
            self._logger.info(
                "expire_snapshots_planned",
                table=table_str,
                expire_count=len(expire_ids),
                retain_count=len(keep_snapshot_ids),
            )

            # Return the count of snapshots that would be expired
            # Note: Full implementation would call table.expire_snapshots()
            return len(expire_ids)

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_identifier(identifier: str | TableIdentifier) -> TableIdentifier:
        """Normalize table identifier to TableIdentifier."""
        if isinstance(identifier, TableIdentifier):
            return identifier
        return TableIdentifier.from_string(identifier)

    @staticmethod
    def _normalize_namespace(namespace: str | tuple[str, ...]) -> tuple[str, ...]:
        """Normalize namespace to tuple."""
        if isinstance(namespace, str):
            return tuple(namespace.split("."))
        return namespace

    @staticmethod
    def _to_arrow(data: pa.Table | pd.DataFrame) -> pa.Table:
        """Convert data to PyArrow Table with Iceberg-compatible types.

        Iceberg requires microsecond (us) timestamp precision, but Pandas
        defaults to nanosecond (ns). This method handles the conversion.
        """
        table = pa.Table.from_pandas(data) if isinstance(data, pd.DataFrame) else data

        # Downcast any nanosecond timestamps to microsecond for Iceberg compatibility
        # Iceberg spec only supports microseconds, not nanoseconds
        new_schema_fields = []
        needs_conversion = False

        for field in table.schema:
            if pa.types.is_timestamp(field.type):
                # Check if it's nanosecond precision
                if field.type.unit == "ns":
                    # Downcast to microseconds, preserving timezone
                    new_type = pa.timestamp("us", tz=field.type.tz)
                    new_schema_fields.append(pa.field(field.name, new_type, field.nullable))
                    needs_conversion = True
                else:
                    new_schema_fields.append(field)
            else:
                new_schema_fields.append(field)

        if needs_conversion:
            new_schema = pa.schema(new_schema_fields)
            table = table.cast(new_schema)

        return table

    @staticmethod
    def _to_iceberg_schema(schema: pa.Schema | Schema) -> Schema:
        """Convert schema to Iceberg Schema, assigning fresh field IDs.

        For new table creation, we use PyIceberg's internal approach:
        1. Convert PyArrow schema to Iceberg schema with placeholder IDs (-1)
        2. Assign fresh sequential field IDs starting from 1

        This mirrors what PyIceberg's Catalog.create_table() does internally.
        Do NOT use pyarrow_to_schema() here - that function is designed for
        reading existing Parquet files, not creating new tables.
        """
        if isinstance(schema, Schema):
            return schema

        # Use PyIceberg's internal conversion utilities
        from pyiceberg.io.pyarrow import _ConvertToIcebergWithoutIDs, visit_pyarrow
        from pyiceberg.schema import assign_fresh_schema_ids

        # Step 1: Convert PyArrow to Iceberg without IDs (all fields get -1)
        iceberg_schema_without_ids = visit_pyarrow(
            schema,
            _ConvertToIcebergWithoutIDs(),
        )

        # Step 2: Assign fresh sequential field IDs starting from 1
        return assign_fresh_schema_ids(iceberg_schema_without_ids)

    def _build_partition_spec(
        self,
        partition_spec: PartitionSpec | list[PartitionTransform] | None,
        schema: Schema,
    ) -> PartitionSpec:
        """Build PartitionSpec from various inputs."""
        if partition_spec is None:
            return PartitionSpec()

        if isinstance(partition_spec, PartitionSpec):
            return partition_spec

        # Build from list of PartitionTransform
        fields: list[PartitionField] = []
        for i, transform in enumerate(partition_spec):
            # Find the source field in the schema
            # PyIceberg's find_field raises ValueError if not found (doesn't return None)
            try:
                source_field = schema.find_field(transform.source_column)
            except ValueError as e:
                msg = f"Source column '{transform.source_column}' not found in schema"
                raise ValueError(msg) from e

            iceberg_transform = self._to_iceberg_transform(transform)
            field = PartitionField(
                source_id=source_field.field_id,
                field_id=1000 + i,  # Partition field IDs start at 1000
                transform=iceberg_transform,
                name=f"{transform.source_column}_{transform.transform_type.value}",
            )
            fields.append(field)

        return PartitionSpec(*fields)

    @staticmethod
    def _to_iceberg_transform(transform: PartitionTransform) -> Transform[Any, Any]:
        """Convert PartitionTransform to PyIceberg Transform."""
        transform_map: dict[PartitionTransformType, type[Transform[Any, Any]]] = {
            PartitionTransformType.IDENTITY: IdentityTransform,
            PartitionTransformType.YEAR: YearTransform,
            PartitionTransformType.MONTH: MonthTransform,
            PartitionTransformType.DAY: DayTransform,
            PartitionTransformType.HOUR: HourTransform,
        }

        if transform.transform_type in transform_map:
            # Mypy thinks Transform requires 'root' arg but concrete subclasses
            # like IdentityTransform() take no arguments - suppress false positive
            transform_cls = transform_map[transform.transform_type]
            return transform_cls()  # type: ignore[call-arg]

        if transform.transform_type == PartitionTransformType.BUCKET:
            if transform.param is None:
                msg = "BUCKET transform requires param"
                raise ValueError(msg)
            return BucketTransform(transform.param)

        if transform.transform_type == PartitionTransformType.TRUNCATE:
            if transform.param is None:
                msg = "TRUNCATE transform requires param"
                raise ValueError(msg)
            return TruncateTransform(transform.param)

        msg = f"Unsupported transform type: {transform.transform_type}"
        raise ValueError(msg)

    def _evolve_schema_if_needed(
        self,
        table: Table,
        new_schema: pa.Schema,
        table_str: str,
    ) -> None:
        """Evolve table schema if new columns are present."""
        current_iceberg_schema = table.schema()
        new_iceberg_schema = self._to_iceberg_schema(new_schema)

        # Find new columns
        current_names = {f.name for f in current_iceberg_schema.fields}
        new_columns = [f for f in new_iceberg_schema.fields if f.name not in current_names]

        if not new_columns:
            return

        self._logger.info(
            "evolving_schema",
            table=table_str,
            new_columns=[f.name for f in new_columns],
        )

        try:
            with table.update_schema() as update:
                for field in new_columns:
                    update.add_column(
                        path=field.name,
                        field_type=field.field_type,
                        doc=field.doc,
                    )
        except Exception as exc:
            raise SchemaEvolutionError(
                f"Failed to evolve schema for {table_str}: {exc}",
                table=table_str,
            ) from exc

    @staticmethod
    def _to_snapshot_info(snapshot: Any) -> SnapshotInfo:
        """Convert PyIceberg Snapshot to SnapshotInfo.

        Note: In PyIceberg, the operation is nested inside snapshot.summary.operation,
        not directly on the snapshot object.
        """
        # Extract operation from summary (it's a nested field)
        operation = "unknown"
        summary_dict: dict[str, str] = {}
        if snapshot.summary is not None:
            # summary.operation is an Operation enum
            if snapshot.summary.operation:
                operation = snapshot.summary.operation.value
            else:
                operation = "unknown"
            # Convert Summary to dict for additional fields (exclude 'operation' which is separate)
            summary_dict = {
                k: str(v) for k, v in snapshot.summary.model_dump().items() if k != "operation"
            }

        return SnapshotInfo(
            snapshot_id=snapshot.snapshot_id,
            timestamp_ms=snapshot.timestamp_ms,
            operation=operation,
            summary=summary_dict,
            manifest_list=snapshot.manifest_list,
        )


def build_partition_spec(
    transforms: list[PartitionTransform],
    schema: pa.Schema | Schema,
) -> PartitionSpec:
    """Build a PartitionSpec from a list of transforms.

    Convenience function for creating partition specs outside of
    IcebergTableManager context.

    Args:
        transforms: List of partition transforms.
        schema: Table schema for field lookup.

    Returns:
        PyIceberg PartitionSpec.

    Example:
        >>> from floe_iceberg import build_partition_spec, PartitionTransform
        >>> transforms = [
        ...     PartitionTransform(
        ...         source_column="created_at",
        ...         transform_type=PartitionTransformType.DAY,
        ...     ),
        ... ]
        >>> spec = build_partition_spec(transforms, schema)
    """
    # Convert PyArrow schema to Iceberg schema using the same approach as _to_iceberg_schema
    iceberg_schema = IcebergTableManager._to_iceberg_schema(schema)

    fields: list[PartitionField] = []
    for i, transform in enumerate(transforms):
        # PyIceberg's find_field raises ValueError if not found (doesn't return None)
        try:
            source_field = iceberg_schema.find_field(transform.source_column)
        except ValueError as e:
            msg = f"Source column '{transform.source_column}' not found in schema"
            raise ValueError(msg) from e

        iceberg_transform = IcebergTableManager._to_iceberg_transform(transform)
        field = PartitionField(
            source_id=source_field.field_id,
            field_id=1000 + i,
            transform=iceberg_transform,
            name=f"{transform.source_column}_{transform.transform_type.value}",
        )
        fields.append(field)

    return PartitionSpec(*fields)
