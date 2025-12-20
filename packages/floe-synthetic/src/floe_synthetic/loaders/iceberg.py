"""Iceberg data loader for synthetic data.

This module provides the IcebergLoader for persisting generated data
to Apache Iceberg tables via PyIceberg.

Features:
- Append and overwrite modes
- Automatic schema evolution
- Snapshot management
- Catalog configuration via environment or explicit parameters
"""

from __future__ import annotations

import os
from typing import Any

import pyarrow as pa
import structlog
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pyiceberg.catalog import Catalog, load_catalog
from pyiceberg.table import Table

logger = structlog.get_logger(__name__)


class IcebergLoaderConfig(BaseSettings):
    """Configuration for IcebergLoader.

    Can be loaded from environment variables with FLOE_ICEBERG_ prefix.

    Example:
        >>> # From environment
        >>> config = IcebergLoaderConfig()
        >>>
        >>> # Explicit
        >>> config = IcebergLoaderConfig(
        ...     catalog_uri="http://polaris:8181/api/catalog",
        ...     warehouse="warehouse",
        ... )
    """

    model_config = SettingsConfigDict(
        env_prefix="FLOE_ICEBERG_",
        env_file=".env",
        extra="ignore",
    )

    catalog_name: str = Field(
        default="polaris",
        description="Name of the catalog",
    )
    catalog_uri: str = Field(
        default="http://localhost:8181/api/catalog",
        description="URI of the Polaris REST catalog",
    )
    warehouse: str = Field(
        default="warehouse",
        description="Warehouse name",
    )
    credential: str | None = Field(
        default=None,
        description="OAuth credential (client_id:client_secret)",
    )
    s3_endpoint: str | None = Field(
        default=None,
        description="S3 endpoint override for LocalStack",
    )
    s3_region: str = Field(
        default="us-east-1",
        description="S3 region",
    )


class LoadResult(BaseModel):
    """Result of a data load operation.

    Attributes:
        table_name: Full table identifier
        rows_loaded: Number of rows loaded
        snapshot_id: New snapshot ID after load
        operation: Operation type (append or overwrite)
    """

    model_config = ConfigDict(frozen=True)

    table_name: str
    rows_loaded: int
    snapshot_id: int | None
    operation: str


class IcebergLoader:
    """Load synthetic data into Iceberg tables via PyIceberg.

    Supports both append and overwrite operations with automatic
    schema evolution and snapshot management.

    Example:
        >>> loader = IcebergLoader(
        ...     catalog_uri="http://polaris:8181/api/catalog",
        ...     warehouse="warehouse",
        ... )
        >>> orders = generator.generate_orders(1000)
        >>> result = loader.append("default.orders", orders)
        >>> print(f"Loaded {result.rows_loaded} rows")
    """

    def __init__(
        self,
        catalog_uri: str | None = None,
        catalog_name: str = "polaris",
        warehouse: str = "warehouse",
        credential: str | None = None,
        s3_endpoint: str | None = None,
        s3_region: str = "us-east-1",
        config: IcebergLoaderConfig | None = None,
    ) -> None:
        """Initialize the Iceberg loader.

        Args:
            catalog_uri: URI of the Polaris REST catalog
            catalog_name: Name for the catalog
            warehouse: Warehouse name
            credential: OAuth credential (client_id:client_secret)
            s3_endpoint: S3 endpoint override (for LocalStack)
            s3_region: S3 region
            config: Full configuration object (overrides other args)
        """
        if config:
            self._config = config
        else:
            self._config = IcebergLoaderConfig(
                catalog_name=catalog_name,
                catalog_uri=catalog_uri or "http://localhost:8181/api/catalog",
                warehouse=warehouse,
                credential=credential,
                s3_endpoint=s3_endpoint,
                s3_region=s3_region,
            )

        self._catalog: Catalog | None = None
        self._log = logger.bind(
            catalog=self._config.catalog_name,
            warehouse=self._config.warehouse,
        )

    @property
    def catalog(self) -> Catalog:
        """Lazily load and cache the catalog connection."""
        if self._catalog is None:
            self._catalog = self._create_catalog()
        return self._catalog

    def _create_catalog(self) -> Catalog:
        """Create and configure the PyIceberg catalog.

        Returns:
            Configured PyIceberg Catalog
        """
        catalog_props: dict[str, Any] = {
            "uri": self._config.catalog_uri,
            "warehouse": self._config.warehouse,
        }

        # Add OAuth credential if provided
        if self._config.credential:
            catalog_props["credential"] = self._config.credential
        else:
            # Try environment variables
            client_id = os.environ.get("POLARIS_CLIENT_ID")
            client_secret = os.environ.get("POLARIS_CLIENT_SECRET")
            if client_id and client_secret:
                catalog_props["credential"] = f"{client_id}:{client_secret}"

        # Add S3 configuration
        if self._config.s3_endpoint:
            catalog_props["s3.endpoint"] = self._config.s3_endpoint
            catalog_props["s3.path-style-access"] = "true"

        catalog_props["s3.region"] = self._config.s3_region

        self._log.info("catalog_connecting", uri=self._config.catalog_uri)
        return load_catalog(self._config.catalog_name, **catalog_props)

    def load_table(self, table_name: str) -> Table:
        """Load an Iceberg table by name.

        Args:
            table_name: Full table identifier (namespace.table)

        Returns:
            PyIceberg Table object
        """
        return self.catalog.load_table(table_name)

    def append(
        self,
        table_name: str,
        data: pa.Table,
        *,
        evolve_schema: bool = True,
    ) -> LoadResult:
        """Append data to an existing Iceberg table.

        Args:
            table_name: Full table identifier (namespace.table)
            data: PyArrow Table with data to append
            evolve_schema: Allow automatic schema evolution

        Returns:
            LoadResult with operation details
        """
        table = self.load_table(table_name)

        # Handle schema evolution if needed
        if evolve_schema:
            self._maybe_evolve_schema(table, data.schema)

        # Append data
        table.append(data)

        # Get new snapshot
        snapshot = table.current_snapshot()
        snapshot_id = snapshot.snapshot_id if snapshot else None

        self._log.info(
            "data_appended",
            table=table_name,
            rows=len(data),
            snapshot_id=snapshot_id,
        )

        return LoadResult(
            table_name=table_name,
            rows_loaded=len(data),
            snapshot_id=snapshot_id,
            operation="append",
        )

    def overwrite(
        self,
        table_name: str,
        data: pa.Table,
        *,
        evolve_schema: bool = True,
    ) -> LoadResult:
        """Overwrite an Iceberg table with new data.

        Args:
            table_name: Full table identifier (namespace.table)
            data: PyArrow Table with data to write
            evolve_schema: Allow automatic schema evolution

        Returns:
            LoadResult with operation details
        """
        table = self.load_table(table_name)

        # Handle schema evolution if needed
        if evolve_schema:
            self._maybe_evolve_schema(table, data.schema)

        # Overwrite data
        table.overwrite(data)

        # Get new snapshot
        snapshot = table.current_snapshot()
        snapshot_id = snapshot.snapshot_id if snapshot else None

        self._log.info(
            "data_overwritten",
            table=table_name,
            rows=len(data),
            snapshot_id=snapshot_id,
        )

        return LoadResult(
            table_name=table_name,
            rows_loaded=len(data),
            snapshot_id=snapshot_id,
            operation="overwrite",
        )

    def append_stream(
        self,
        table_name: str,
        batches: list[pa.Table],
        *,
        evolve_schema: bool = True,
    ) -> LoadResult:
        """Append multiple batches to an Iceberg table.

        Useful for memory-efficient loading of large datasets.

        Args:
            table_name: Full table identifier
            batches: List of PyArrow Tables to append
            evolve_schema: Allow automatic schema evolution

        Returns:
            LoadResult with total rows loaded
        """
        total_rows = 0

        for i, batch in enumerate(batches):
            result = self.append(table_name, batch, evolve_schema=evolve_schema)
            total_rows += result.rows_loaded
            self._log.debug(
                "batch_appended",
                batch_num=i + 1,
                batch_rows=len(batch),
                total_rows=total_rows,
            )

        # Get final snapshot
        table = self.load_table(table_name)
        snapshot = table.current_snapshot()
        snapshot_id = snapshot.snapshot_id if snapshot else None

        return LoadResult(
            table_name=table_name,
            rows_loaded=total_rows,
            snapshot_id=snapshot_id,
            operation="append_stream",
        )

    def _maybe_evolve_schema(
        self,
        table: Table,
        arrow_schema: pa.Schema,
    ) -> None:
        """Evolve table schema if new columns are present.

        Args:
            table: PyIceberg Table
            arrow_schema: Schema of data being written
        """
        table_schema = table.schema()
        table_field_names = {field.name for field in table_schema.fields}

        new_fields = []
        for field in arrow_schema:
            if field.name not in table_field_names:
                new_fields.append(field)

        if new_fields:
            self._log.info(
                "schema_evolution",
                new_fields=[f.name for f in new_fields],
            )
            # PyIceberg handles this automatically during append/overwrite
            # when schema evolution is enabled in table properties

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists.

        Args:
            table_name: Full table identifier

        Returns:
            True if table exists
        """
        try:
            self.catalog.load_table(table_name)
            return True
        except Exception:
            return False
