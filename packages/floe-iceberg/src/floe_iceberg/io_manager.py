"""IcebergIOManager: Dagster IOManager for Iceberg storage.

This module provides a Dagster IOManager that reads and writes
assets to/from Iceberg tables via Polaris catalog.

Features:
- PyArrow Table and Pandas DataFrame support
- Automatic table creation on first write
- Schema evolution support
- Partitioned asset support
- OpenTelemetry tracing and structured logging
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

import pandas as pd
import pyarrow as pa
from dagster import ConfigurableIOManager, InputContext, OutputContext
from dagster._core.errors import DagsterInvalidMetadata

from floe_iceberg.config import (
    IcebergIOManagerConfig,
    TableIdentifier,
    WriteMode,
)
from floe_iceberg.errors import TableNotFoundError, WriteError
from floe_iceberg.observability import dagster_asset_operation, get_logger, log_materialization
from floe_iceberg.tables import IcebergTableManager

if TYPE_CHECKING:
    from pyiceberg.catalog import Catalog


class IcebergIOManager(ConfigurableIOManager):  # type: ignore[misc]
    """Iceberg-backed IOManager for Dagster assets.

    Maps Dagster asset keys to Iceberg table identifiers:
    - ["customers"] -> {default_namespace}.customers
    - ["bronze", "raw_events"] -> bronze.raw_events
    - ["gold", "metrics", "daily"] -> gold.metrics_daily

    Supports:
    - PyArrow Table and Pandas DataFrame outputs
    - Partitioned assets via Dagster partition keys
    - Automatic schema evolution (configurable)
    - Multiple write modes (append, overwrite)

    Attributes:
        catalog_uri: Polaris REST API endpoint.
        warehouse: Warehouse name.
        client_id: OAuth2 client ID (optional).
        client_secret: OAuth2 client secret (optional).
        token: Pre-fetched bearer token (optional).
        default_namespace: Namespace for single-part asset keys.
        write_mode: Default write mode (append or overwrite).
        schema_evolution_enabled: Enable automatic schema evolution.
        auto_create_tables: Create tables automatically on first write.
        partition_column: Default partition column for time-based partitioning.

    Example:
        >>> from dagster import asset, Definitions
        >>> from floe_iceberg import create_io_manager, IcebergIOManagerConfig
        >>>
        >>> config = IcebergIOManagerConfig(
        ...     catalog_uri="http://localhost:8181/api/catalog",
        ...     warehouse="my_warehouse",
        ...     default_namespace="bronze",
        ... )
        >>> defs = Definitions(
        ...     assets=[my_asset],
        ...     resources={"io_manager": create_io_manager(config)},
        ... )
    """

    # Configuration fields (exposed as Dagster resource config)
    catalog_uri: str
    warehouse: str
    client_id: str | None = None
    client_secret: str | None = None
    token: str | None = None
    scope: str | None = None  # OAuth2 scope - set explicitly for least privilege
    default_namespace: str = "public"
    write_mode: str = "append"
    schema_evolution_enabled: bool = True
    auto_create_tables: bool = True
    partition_column: str | None = None
    # S3 configuration for local testing (e.g., LocalStack)
    s3_endpoint: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_region: str = "us-east-1"

    # Internal state (not config)
    _catalog: Catalog | None = None
    _table_manager: IcebergTableManager | None = None
    _logger: Any = None

    def setup_for_execution(self, context: Any) -> None:  # noqa: ARG002
        """Initialize catalog and table manager.

        Called by Dagster before execution starts.

        Args:
            context: Dagster setup context (not used, required by interface).
        """
        self._logger = get_logger()
        self._catalog = self._create_catalog()
        self._table_manager = IcebergTableManager(self._catalog)
        self._logger.info(
            "io_manager_initialized",
            catalog_uri=self.catalog_uri,
            warehouse=self.warehouse,
            default_namespace=self.default_namespace,
        )

    def _create_catalog(self) -> Catalog:
        """Create PyIceberg catalog from configuration.

        Supports multiple authentication modes:
        1. Vended credentials (production with AWS/Azure/GCP) - catalog provides temp creds
        2. Static S3 credentials (local testing) - pass credentials directly

        For production deployments:
        - AWS S3: Use vended credentials via Polaris (no s3_* fields needed)
        - Azure: Use vended credentials or configure Azure-specific properties
        - GCP: Use vended credentials or configure GCS-specific properties

        For local testing with LocalStack:
        - Set s3_endpoint, s3_access_key_id, s3_secret_access_key
        """
        from pyiceberg.catalog import load_catalog

        properties: dict[str, Any] = {
            "uri": self.catalog_uri,
            "warehouse": self.warehouse,
        }

        if self.token:
            properties["token"] = self.token
        elif self.client_id and self.client_secret:
            properties["credential"] = f"{self.client_id}:{self.client_secret}"

        # Scope is optional - only set if explicitly configured
        # Production should use minimal scopes; tests can use PRINCIPAL_ROLE:ALL
        if self.scope:
            properties["scope"] = self.scope

        # S3 configuration for local testing (e.g., LocalStack)
        # When these are set, PyIceberg uses static credentials instead of vended credentials.
        # In production with AWS/Azure/GCP, vended credentials are used instead.
        if self.s3_endpoint:
            properties["s3.endpoint"] = self.s3_endpoint
        if self.s3_access_key_id:
            properties["s3.access-key-id"] = self.s3_access_key_id
        if self.s3_secret_access_key:
            properties["s3.secret-access-key"] = self.s3_secret_access_key
        if self.s3_region:
            properties["s3.region"] = self.s3_region

        return load_catalog("floe_iceberg", **properties)

    @property
    def catalog(self) -> Catalog:
        """Get the catalog, initializing if needed."""
        if self._catalog is None:
            self._catalog = self._create_catalog()
        return self._catalog

    @property
    def table_manager(self) -> IcebergTableManager:
        """Get the table manager, initializing if needed."""
        if self._table_manager is None:
            self._table_manager = IcebergTableManager(self.catalog)
        return self._table_manager

    def get_table_identifier(
        self,
        context: OutputContext | InputContext,
    ) -> str:
        """Map Dagster asset key to Iceberg table identifier.

        Mapping rules:
        - ["customers"] -> "{default_namespace}.customers"
        - ["bronze", "raw"] -> "bronze.raw"
        - ["gold", "metrics", "daily"] -> "gold.metrics_daily"

        Args:
            context: Dagster output or input context with asset key.

        Returns:
            Fully qualified table identifier (namespace.table).

        Example:
            >>> # Asset key ["bronze", "customers"]
            >>> identifier = io_manager.get_table_identifier(context)
            >>> identifier
            'bronze.customers'
        """
        if context.asset_key is None:
            msg = "Asset key is required for Iceberg IOManager"
            raise ValueError(msg)

        parts = list(context.asset_key.path)

        if len(parts) == 1:
            # Single part: use default namespace
            namespace = self.default_namespace
            table_name = parts[0]
        elif len(parts) == 2:
            # Two parts: namespace.table
            namespace = parts[0]
            table_name = parts[1]
        else:
            # Multiple parts: first is namespace, rest joined with underscore
            namespace = parts[0]
            table_name = "_".join(parts[1:])

        return f"{namespace}.{table_name}"

    def handle_output(
        self,
        context: OutputContext,
        obj: pa.Table | pd.DataFrame,
    ) -> None:
        """Write asset output to Iceberg table.

        Converts the output to PyArrow Table (if needed), determines the
        target table identifier from the asset key, and writes the data
        using the configured write mode.

        Args:
            context: Dagster output context with asset key and metadata.
            obj: Data to write (PyArrow Table or Pandas DataFrame).

        Raises:
            TableNotFoundError: If table doesn't exist and auto_create disabled.
            SchemaEvolutionError: If schema change is incompatible.
            WriteError: If write operation fails.

        Side Effects:
            - Attaches metadata to context: table, num_rows, snapshot_id
            - Creates table if it doesn't exist (when auto_create=True)
            - Evolves schema if new columns present (when enabled)

        Example:
            >>> @asset
            ... def customers() -> pd.DataFrame:
            ...     return pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})
            >>> # IOManager automatically writes to {namespace}.customers
        """
        table_id = self.get_table_identifier(context)
        asset_key = str(context.asset_key) if context.asset_key else "unknown"
        partition_key = context.partition_key if context.has_partition_key else None

        with dagster_asset_operation(
            "handle_output",
            asset_key=asset_key,
            partition_key=partition_key,
            table=table_id,
        ):
            # Convert to PyArrow Table
            if isinstance(obj, pd.DataFrame):
                arrow_table = pa.Table.from_pandas(obj)
            elif isinstance(obj, pa.Table):
                arrow_table = obj
            else:
                msg = (
                    f"Unsupported output type: {type(obj)}. "
                    "Expected PyArrow Table or Pandas DataFrame."
                )
                raise WriteError(msg, table=table_id)

            num_rows = arrow_table.num_rows

            # Determine write mode from context metadata or config default
            write_mode = self._get_write_mode(context)

            # Ensure table exists
            self._ensure_table_exists(table_id, arrow_table.schema, context)

            # Write data
            schema_evolved = False
            try:
                if write_mode == WriteMode.APPEND:
                    snapshot_info = self.table_manager.append(
                        table_id,
                        arrow_table,
                        evolve_schema=self.schema_evolution_enabled,
                    )
                else:
                    snapshot_info = self.table_manager.overwrite(
                        table_id,
                        arrow_table,
                        evolve_schema=self.schema_evolution_enabled,
                    )
                snapshot_id = snapshot_info.snapshot_id
            except Exception as e:
                msg = f"Failed to write to table {table_id}"
                raise WriteError(
                    msg, table=table_id, operation=write_mode.value, cause=str(e)
                ) from e

            # Parse table identifier for metadata
            tid = TableIdentifier.from_string(table_id)

            # Attach metadata to context
            # Note: In append mode, multiple handle_output calls may occur with same context
            # In that case, metadata keys already exist and we skip adding them again
            with contextlib.suppress(DagsterInvalidMetadata):
                context.add_output_metadata(
                    {
                        "table": table_id,
                        "namespace": tid.namespace,
                        "table_name": tid.name,
                        "snapshot_id": snapshot_id,
                        "num_rows": num_rows,
                        "write_mode": write_mode.value,
                        "schema_evolved": schema_evolved,
                    }
                )

            # Log materialization
            log_materialization(
                table=table_id,
                snapshot_id=snapshot_id,
                num_rows=num_rows,
                write_mode=write_mode.value,
                schema_evolved=schema_evolved,
            )

            if self._logger:
                self._logger.info(
                    "asset_output_handled",
                    asset_key=asset_key,
                    table=table_id,
                    num_rows=num_rows,
                    snapshot_id=snapshot_id,
                    write_mode=write_mode.value,
                )

    def load_input(
        self,
        context: InputContext,
    ) -> pa.Table:
        """Read asset input from Iceberg table.

        Loads data from the Iceberg table mapped to the input asset key.
        Supports column projection, row filtering, and partitioned reads.

        Args:
            context: Dagster input context with asset key.

        Returns:
            PyArrow Table with requested data.

        Raises:
            TableNotFoundError: If table doesn't exist.
            ScanError: If scan operation fails.

        Metadata Options:
            columns: List of column names to project (default: all columns).
            row_filter: Iceberg expression string for filtering rows.
            snapshot_id: Read from specific snapshot (time travel).
            limit: Maximum number of rows to return.

        Example:
            >>> @asset(
            ...     ins={"customers": AssetIn(metadata={"columns": ["id", "name"]})}
            ... )
            ... def downstream(customers: pa.Table) -> pa.Table:
            ...     # customers has only id and name columns
            ...     return customers.filter(...)
        """
        table_id = self.get_table_identifier(context)
        asset_key = str(context.asset_key) if context.asset_key else "unknown"
        partition_key = context.partition_key if context.has_partition_key else None

        with dagster_asset_operation(
            "load_input",
            asset_key=asset_key,
            partition_key=partition_key,
            table=table_id,
        ):
            # Check table exists
            if not self.table_manager.table_exists(table_id):
                raise TableNotFoundError(table_id)

            # Extract scan options from metadata
            columns = self._get_columns_from_context(context)
            row_filter = self._get_row_filter_from_context(context)
            snapshot_id = self._get_snapshot_id_from_context(context)
            limit = self._get_limit_from_context(context)

            # Add partition filter if present
            partition_filter = self._get_partition_filter(context, partition_key)
            if partition_filter:
                if row_filter:
                    row_filter = f"({row_filter}) AND ({partition_filter})"
                else:
                    row_filter = partition_filter

            # Perform scan with options
            result = self.table_manager.scan(
                table_id,
                columns=columns,
                row_filter=row_filter,
                snapshot_id=snapshot_id,
                limit=limit,
            )

            if self._logger:
                self._logger.info(
                    "asset_input_loaded",
                    asset_key=asset_key,
                    table=table_id,
                    num_rows=result.num_rows,
                    columns=columns,
                    has_filter=row_filter is not None,
                    snapshot_id=snapshot_id,
                )

            return result

    def _get_columns_from_context(self, context: InputContext) -> list[str] | None:
        """Extract column projection from input context metadata.

        Args:
            context: Dagster input context.

        Returns:
            List of column names or None for all columns.
        """
        if context.metadata:
            columns = context.metadata.get("columns")
            if columns and isinstance(columns, (list, tuple)):
                return list(columns)
        return None

    def _get_row_filter_from_context(self, context: InputContext) -> str | None:
        """Extract row filter from input context metadata.

        Args:
            context: Dagster input context.

        Returns:
            Row filter expression string or None.
        """
        if context.metadata:
            row_filter = context.metadata.get("row_filter")
            if row_filter and isinstance(row_filter, str):
                return str(row_filter)  # Explicit cast to satisfy mypy
        return None

    def _get_snapshot_id_from_context(self, context: InputContext) -> int | None:
        """Extract snapshot ID from input context metadata.

        Args:
            context: Dagster input context.

        Returns:
            Snapshot ID for time travel or None.
        """
        if context.metadata:
            snapshot_id = context.metadata.get("snapshot_id")
            if snapshot_id is not None:
                return int(snapshot_id)
        return None

    def _get_limit_from_context(self, context: InputContext) -> int | None:
        """Extract row limit from input context metadata.

        Args:
            context: Dagster input context.

        Returns:
            Maximum rows to return or None for unlimited.
        """
        if context.metadata:
            limit = context.metadata.get("limit")
            if limit is not None:
                return int(limit)
        return None

    def _get_partition_filter(
        self,
        context: InputContext,
        partition_key: str | None,
    ) -> str | None:
        """Build partition filter from Dagster partition key.

        For partitioned assets, converts Dagster partition key to
        Iceberg row filter expression.

        Args:
            context: Dagster input context.
            partition_key: Dagster partition key (e.g., "2024-01-15").

        Returns:
            Iceberg filter expression or None.
        """
        if not partition_key:
            return None

        # Get partition column from config or metadata
        partition_column = self.partition_column
        if context.metadata:
            partition_column = context.metadata.get("partition_column", partition_column)

        if not partition_column:
            return None

        # Build filter based on partition key format
        # For daily partitions: partition_key = "2024-01-15"
        # For monthly partitions: partition_key = "2024-01"
        # For hourly partitions: partition_key = "2024-01-15-12"
        return f"{partition_column} = '{partition_key}'"

    def _get_write_mode(self, context: OutputContext) -> WriteMode:
        """Get write mode from context metadata or config default.

        Checks for 'write_mode' in output metadata, falls back to
        configured default.

        Args:
            context: Dagster output context.

        Returns:
            WriteMode to use for this operation.
        """
        # Check if write_mode specified in asset metadata
        if context.metadata:
            mode = context.metadata.get("write_mode")
            if mode:
                if isinstance(mode, WriteMode):
                    return mode
                if isinstance(mode, str):
                    return WriteMode(mode)

        # Fall back to config default
        return WriteMode(self.write_mode)

    def _ensure_table_exists(
        self,
        table_id: str,
        schema: pa.Schema,
        context: OutputContext,
    ) -> None:
        """Ensure table exists, creating if necessary.

        Args:
            table_id: Table identifier.
            schema: Schema for new table.
            context: Dagster output context.

        Raises:
            TableNotFoundError: If table doesn't exist and auto_create disabled.
        """
        if self.table_manager.table_exists(table_id):
            return

        if not self.auto_create_tables:
            msg = f"Table {table_id} does not exist and auto_create_tables is disabled"
            raise TableNotFoundError(table_id, message=msg)

        # Create table
        partition_spec = self._get_partition_spec(schema, context)
        self.table_manager.create_table(table_id, schema, partition_spec=partition_spec)

        if self._logger:
            self._logger.info(
                "table_created",
                table=table_id,
                has_partition_spec=partition_spec is not None,
            )

    def _get_partition_spec(
        self,
        schema: pa.Schema,
        context: OutputContext,  # noqa: ARG002
    ) -> Any | None:
        """Get partition spec for table creation.

        Determines partitioning from asset partitions definition or
        default partition column configuration.

        Args:
            schema: Table schema.
            context: Dagster output context (reserved for future use).

        Returns:
            PyIceberg PartitionSpec or None.
        """
        from floe_iceberg.config import PartitionTransform, PartitionTransformType
        from floe_iceberg.tables import build_partition_spec

        # Check for partition column in config
        if self.partition_column:
            # Verify column exists in schema
            field_names = [field.name for field in schema]
            if self.partition_column in field_names:
                # Convert to Iceberg schema to get field ID
                iceberg_schema = IcebergTableManager._to_iceberg_schema(schema)
                transforms = [
                    PartitionTransform(
                        source_column=self.partition_column,
                        transform_type=PartitionTransformType.DAY,
                    )
                ]
                return build_partition_spec(transforms, iceberg_schema)

        return None


def create_io_manager(
    config: IcebergIOManagerConfig,
    catalog: Catalog | None = None,
) -> IcebergIOManager:
    """Create an Iceberg IOManager for Dagster assets.

    Factory function to create a configured IcebergIOManager instance.

    Args:
        config: IOManager configuration.
        catalog: Optional pre-configured catalog. If not provided,
            creates one from config.catalog_config.

    Returns:
        IcebergIOManager: Configured IOManager for Dagster Definitions.

    Example:
        >>> from floe_iceberg import create_io_manager, IcebergIOManagerConfig
        >>> config = IcebergIOManagerConfig(
        ...     catalog_uri="http://localhost:8181/api/catalog",
        ...     warehouse="my_warehouse",
        ...     default_namespace="bronze",
        ... )
        >>> io_manager = create_io_manager(config)
        >>> defs = Definitions(
        ...     assets=[my_asset],
        ...     resources={"io_manager": io_manager},
        ... )
    """
    # Extract secret values if present
    client_secret = config.client_secret.get_secret_value() if config.client_secret else None
    token = config.token.get_secret_value() if config.token else None
    s3_secret_access_key = (
        config.s3_secret_access_key.get_secret_value()
        if config.s3_secret_access_key
        else None
    )

    io_manager = IcebergIOManager(
        catalog_uri=config.catalog_uri,
        warehouse=config.warehouse,
        client_id=config.client_id,
        client_secret=client_secret,
        token=token,
        scope=config.scope,  # Pass scope - should be set explicitly per environment
        default_namespace=config.default_namespace,
        write_mode=config.write_mode.value,
        schema_evolution_enabled=config.schema_evolution_enabled,
        auto_create_tables=config.auto_create_tables,
        partition_column=config.partition_column,
        # S3 configuration for local testing (not needed for AWS with vended creds)
        s3_endpoint=config.s3_endpoint,
        s3_access_key_id=config.s3_access_key_id,
        s3_secret_access_key=s3_secret_access_key,
        s3_region=config.s3_region,
    )

    # If pre-configured catalog provided, set it
    if catalog is not None:
        io_manager._catalog = catalog
        io_manager._table_manager = IcebergTableManager(catalog)

    return io_manager
