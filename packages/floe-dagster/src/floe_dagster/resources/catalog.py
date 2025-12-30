"""Catalog resource abstractions for polyglot catalog support.

T095: [US6] Create resources/catalog.py with catalog abstraction

This module provides a catalog-agnostic abstraction layer that allows
data engineers to write assets that work with any Iceberg catalog:
Polaris, AWS Glue, Unity Catalog, Hive Metastore, etc.

Design Principles:
    - Data engineers use `CatalogResource` (abstract type)
    - Platform engineers configure the concrete implementation
    - Same asset code works across Polaris, Glue, Unity, etc.
    - Secrets resolved at runtime, not compile time

Architecture:
    ```
    CatalogProtocol (Protocol)
        ↑ implements
    CatalogResource (ConfigurableResource - abstract base)
        ↑ extends
    PolarisCatalogResource | GlueCatalogResource | ...
    ```

Example (Data Engineer - catalog-agnostic):
    >>> @floe_asset(outputs=["demo.bronze_customers"])
    ... def bronze_customers(context, catalog: CatalogResource):
    ...     # Works with ANY catalog implementation
    ...     table = catalog.load_table("demo.bronze_customers")
    ...     ...

Example (Platform Engineer - configures concrete implementation):
    >>> # In platform.yaml
    >>> catalogs:
    >>>   default:
    >>>     type: polaris  # or "glue", "unity", etc.
    >>>     uri: http://polaris:8181/api/catalog
    >>>     warehouse: demo_catalog
"""

from __future__ import annotations

from abc import abstractmethod
import os
from typing import TYPE_CHECKING, Any, Literal, Protocol, TypeAlias, cast, runtime_checkable

from dagster import ConfigurableResource
import pandas as pd
import pyarrow as pa
from pydantic import Field, PrivateAttr
from pydantic import SecretStr as PydanticSecretStr

from floe_core.schemas.credential_config import SecretReference
from floe_iceberg.config import SnapshotInfo
from floe_iceberg.tables import IcebergTableManager

if TYPE_CHECKING:
    from pyiceberg.catalog import Catalog as PyIcebergCatalog
    from pyiceberg.table import Table


@runtime_checkable
class CatalogProtocol(Protocol):
    """Protocol defining the catalog interface.

    Any catalog implementation (Polaris, Glue, Unity, etc.) that implements
    these methods can be used with @floe_asset and the floe-dagster ecosystem.

    This uses structural subtyping - implementations don't need to explicitly
    inherit from this protocol, they just need to have these methods.
    """

    def load_table(self, identifier: str) -> Table:
        """Load an Iceberg table by identifier.

        Args:
            identifier: Fully qualified table name (e.g., "namespace.table")

        Returns:
            PyIceberg Table object

        Raises:
            TableNotFoundError: If table doesn't exist
        """
        ...

    def table_exists(self, identifier: str) -> bool:
        """Check if a table exists.

        Args:
            identifier: Fully qualified table name

        Returns:
            True if table exists, False otherwise
        """
        ...

    def list_tables(self, namespace: str) -> list[str]:
        """List tables in a namespace.

        Args:
            namespace: Namespace name

        Returns:
            List of fully qualified table identifiers
        """
        ...

    @property
    def inner_catalog(self) -> PyIcebergCatalog:
        """Access the underlying PyIceberg Catalog object.

        Returns:
            The wrapped PyIceberg Catalog for advanced operations
        """
        ...


class CatalogResource(ConfigurableResource):  # type: ignore[type-arg]
    """Abstract base class for catalog Dagster resources.

    Subclasses must implement `get_catalog()` to return a concrete
    catalog implementation that satisfies `CatalogProtocol`.

    This abstraction allows data engineers to write catalog-agnostic
    assets while platform engineers configure the concrete implementation.

    Supported Implementations:
        - PolarisCatalogResource: Apache Polaris REST catalog
        - GlueCatalogResource: AWS Glue Data Catalog (planned)
        - UnityCatalogResource: Databricks Unity Catalog (planned)

    Example:
        >>> # Data engineer code (catalog-agnostic)
        >>> @floe_asset(outputs=["demo.bronze_customers"])
        ... def bronze_customers(context, catalog: CatalogResource):
        ...     table = catalog.load_table("demo.bronze_customers")
        ...     # ... business logic ...
    """

    # Layer bindings from CompiledArtifacts (v1.2.0)
    layer_bindings: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Layer configuration from platform.yaml (resolved_layers)",
    )

    @abstractmethod
    def get_catalog(self) -> CatalogProtocol:
        """Get the configured catalog instance.

        Returns:
            Catalog implementation satisfying CatalogProtocol
        """
        ...

    # Delegate common operations to the underlying catalog

    def load_table(self, identifier: str) -> Table:
        """Load an Iceberg table by identifier.

        Args:
            identifier: Fully qualified table name (e.g., "namespace.table")

        Returns:
            PyIceberg Table object
        """
        return self.get_catalog().load_table(identifier)

    def table_exists(self, identifier: str) -> bool:
        """Check if a table exists.

        Args:
            identifier: Fully qualified table name

        Returns:
            True if table exists
        """
        return self.get_catalog().table_exists(identifier)

    def list_tables(self, namespace: str) -> list[str]:
        """List tables in a namespace.

        Args:
            namespace: Namespace name

        Returns:
            List of fully qualified table identifiers
        """
        return self.get_catalog().list_tables(namespace)

    @property
    def inner_catalog(self) -> PyIcebergCatalog:
        """Access the underlying PyIceberg Catalog.

        Returns:
            The wrapped PyIceberg Catalog for advanced operations
        """
        return self.get_catalog().inner_catalog

    # -------------------------------------------------------------------------
    # High-Level Table Operations (Batteries-Included DX)
    # -------------------------------------------------------------------------

    def write_table(
        self,
        identifier: str,
        data: pa.Table | pd.DataFrame,
        *,
        mode: Literal["overwrite", "append"] = "overwrite",
        create_if_not_exists: bool = True,
    ) -> SnapshotInfo:
        """Write data to an Iceberg table with auto-creation.

        This is the PRIMARY API for data engineers writing bronze/silver/gold
        assets. It handles all the boilerplate: catalog resolution, table
        manager creation, schema evolution, and table creation.

        Args:
            identifier: Table name (e.g., "demo.bronze_customers")
            data: PyArrow Table or Pandas DataFrame to write
            mode: Write mode - "overwrite" (replace all) or "append"
            create_if_not_exists: Auto-create table if missing (default: True)

        Returns:
            SnapshotInfo with snapshot_id and write metadata

        Raises:
            WriteError: If write operation fails
            TableNotFoundError: If table doesn't exist and create_if_not_exists=False

        Example:
            >>> @floe_asset(outputs=["demo.bronze_customers"])
            ... def bronze_customers(context, catalog: CatalogResource):
            ...     customers = generate_customers(1000)
            ...     snapshot = catalog.write_table("demo.bronze_customers", customers)
            ...     return {"rows": customers.num_rows, "snapshot_id": snapshot.snapshot_id}
        """
        # Convert DataFrame to PyArrow if needed
        arrow_data = pa.Table.from_pandas(data) if isinstance(data, pd.DataFrame) else data

        # Get the underlying catalog and create table manager
        catalog = self.get_catalog()
        manager = IcebergTableManager(catalog.inner_catalog)

        # Create table if it doesn't exist
        if create_if_not_exists:
            manager.create_table_if_not_exists(identifier, arrow_data.schema)

        # Write data based on mode
        if mode == "overwrite":
            return manager.overwrite(identifier, arrow_data)
        return manager.append(identifier, arrow_data)

    def read_table(
        self,
        identifier: str,
        columns: list[str] | None = None,
        row_filter: str | None = None,
        limit: int | None = None,
    ) -> pa.Table:
        """Read data from an Iceberg table.

        Convenience method for reading table data with optional projection
        and filtering. For advanced operations (time travel, snapshot reads),
        use `load_table()` to get the PyIceberg Table object directly.

        Args:
            identifier: Table name (e.g., "demo.bronze_customers")
            columns: Optional list of columns to project (None = all columns)
            row_filter: Optional Iceberg filter expression (e.g., "status = 'active'")
            limit: Optional maximum rows to return

        Returns:
            PyArrow Table with query results

        Raises:
            TableNotFoundError: If table doesn't exist
            ScanError: If scan operation fails

        Example:
            >>> @floe_asset(inputs=["demo.bronze_customers"])
            ... def silver_customers(context, catalog: CatalogResource):
            ...     customers = catalog.read_table(
            ...         "demo.bronze_customers",
            ...         columns=["customer_id", "email", "created_at"],
            ...         row_filter="status = 'active'",
            ...     )
            ...     # Transform data...
            ...     return transformed
        """
        catalog = self.get_catalog()
        manager = IcebergTableManager(catalog.inner_catalog)
        return manager.scan(
            identifier,
            columns=columns,
            row_filter=row_filter,
            limit=limit,
        )

    # -------------------------------------------------------------------------
    # Layer-Aware Operations (v1.2.0) - Declarative Medallion Architecture
    # -------------------------------------------------------------------------

    def write_to_layer(
        self,
        layer: str,
        table_name: str,
        data: pa.Table | pd.DataFrame,
        *,
        mode: Literal["overwrite", "append"] = "overwrite",
        create_if_not_exists: bool = True,
    ) -> SnapshotInfo:
        """Write data to a layer-specific namespace (declarative API).

        This is the RECOMMENDED API for writing to medallion layers (bronze/silver/gold)
        as it eliminates hardcoded namespaces and centralizes layer configuration
        in platform.yaml.

        The layer name is resolved against `layer_bindings` (populated from
        CompiledArtifacts.resolved_layers) to determine the target namespace.

        Args:
            layer: Layer name from platform.yaml (e.g., "bronze", "silver", "gold")
            table_name: Table name WITHOUT namespace (e.g., "customers")
            data: PyArrow Table or Pandas DataFrame to write
            mode: Write mode - "overwrite" or "append"
            create_if_not_exists: Auto-create table if missing

        Returns:
            SnapshotInfo with snapshot_id and write metadata

        Raises:
            ValueError: If layer not configured in layer_bindings
            WriteError: If write operation fails

        Example:
            >>> @floe_asset
            ... def bronze_customers(context, catalog: CatalogResource):
            ...     customers = generate_customers(1000)
            ...     snapshot = catalog.write_to_layer("bronze", "customers", customers)
            ...     return {"rows": customers.num_rows, "snapshot_id": snapshot.snapshot_id}
        """
        if layer not in self.layer_bindings:
            raise ValueError(
                f"Layer '{layer}' not configured. "
                f"Available layers: {list(self.layer_bindings.keys())}"
            )

        layer_config = self.layer_bindings[layer]
        namespace = layer_config["namespace"]
        full_identifier = f"{namespace}.{table_name}"

        return self.write_table(
            full_identifier,
            data,
            mode=mode,
            create_if_not_exists=create_if_not_exists,
        )

    def read_from_layer(
        self,
        layer: str,
        table_name: str,
        columns: list[str] | None = None,
        row_filter: str | None = None,
        limit: int | None = None,
    ) -> pa.Table:
        """Read data from a layer-specific namespace (declarative API).

        Companion to `write_to_layer()` for reading from medallion layers
        without hardcoded namespaces.

        Args:
            layer: Layer name from platform.yaml (e.g., "bronze", "silver")
            table_name: Table name WITHOUT namespace (e.g., "customers")
            columns: Optional list of columns to project
            row_filter: Optional Iceberg filter expression
            limit: Optional maximum rows to return

        Returns:
            PyArrow Table with query results

        Raises:
            ValueError: If layer not configured
            TableNotFoundError: If table doesn't exist

        Example:
            >>> @floe_asset
            ... def silver_customers(context, catalog: CatalogResource):
            ...     bronze_customers = catalog.read_from_layer(
            ...         "bronze",
            ...         "customers",
            ...         columns=["id", "email", "created_at"]
            ...     )
            ...     # Transform data...
            ...     catalog.write_to_layer("silver", "customers", transformed)
        """
        if layer not in self.layer_bindings:
            raise ValueError(
                f"Layer '{layer}' not configured. "
                f"Available layers: {list(self.layer_bindings.keys())}"
            )

        layer_config = self.layer_bindings[layer]
        namespace = layer_config["namespace"]
        full_identifier = f"{namespace}.{table_name}"

        return self.read_table(
            full_identifier,
            columns=columns,
            row_filter=row_filter,
            limit=limit,
        )


class PolarisCatalogResource(CatalogResource):
    """Dagster resource for Apache Polaris REST catalog.

    Loads configuration from CompiledArtifacts and resolves secrets
    at runtime (not compile time) for security.

    Configuration Sources (in priority order):
        1. Explicit parameters
        2. Environment variables (for secrets)
        3. CompiledArtifacts.resolved_catalog

    Attributes:
        uri: Polaris REST API endpoint
        warehouse: Warehouse name in Polaris
        client_id: OAuth2 client ID (can be secret_ref)
        client_secret: OAuth2 client secret (resolved at runtime)
        scope: OAuth2 scope (default: PRINCIPAL_ROLE:ALL)
        s3_endpoint: Optional S3-compatible endpoint for LocalStack/MinIO

    Note:
        Secrets are stored as plain strings for Dagster ConfigurableResource
        compatibility. Use environment variable references (e.g., "$MY_SECRET")
        or secret_ref patterns to keep actual secrets out of configuration.

    Example:
        >>> resource = PolarisCatalogResource(
        ...     uri="http://polaris:8181/api/catalog",
        ...     warehouse="demo_catalog",
        ...     client_id="demo_engineer",
        ...     client_secret="$POLARIS_CLIENT_SECRET",  # Env var reference
        ...     scope="PRINCIPAL_ROLE:ALL",
        ... )
        >>> catalog = resource.get_catalog()
        >>> table = catalog.load_table("demo.bronze_customers")
    """

    # Required fields
    uri: str = Field(
        description="Polaris REST API endpoint URL",
    )
    warehouse: str = Field(
        description="Warehouse name in Polaris",
    )

    # Authentication (resolved at runtime)
    # Note: Using str instead of SecretStr for Dagster ConfigurableResource compatibility
    # Secrets should be stored as env var references (e.g., "$MY_SECRET")
    client_id: str | None = Field(
        default=None,
        description="OAuth2 client ID (or env var name if prefixed with $)",
    )
    client_secret: str | None = Field(
        default=None,
        description="OAuth2 client secret (use $VAR_NAME for env var reference)",
    )
    scope: str = Field(
        default="PRINCIPAL_ROLE:ALL",
        description="OAuth2 scope for token requests",
    )

    # S3 configuration (for LocalStack/MinIO)
    s3_endpoint: str | None = Field(
        default=None,
        description="S3-compatible endpoint (e.g., http://localhost:4566)",
    )
    s3_region: str = Field(
        default="us-east-1",
        description="S3 region",
    )
    s3_path_style_access: bool = Field(
        default=False,
        description="Use path-style S3 access (required for LocalStack/MinIO)",
    )
    s3_access_key_id: str | None = Field(
        default=None,
        description="S3 access key ID (if not using vended credentials)",
    )
    s3_secret_access_key: str | None = Field(
        default=None,
        description="S3 secret access key (use $VAR_NAME for env var reference)",
    )

    # Cached catalog instance (PrivateAttr for Pydantic v2)
    _catalog: Any = PrivateAttr(default=None)

    def get_catalog(self) -> CatalogProtocol:
        """Get or create the Polaris catalog instance.

        Secrets are resolved at runtime from environment variables
        or the values provided. This ensures secrets are never stored
        in CompiledArtifacts or logged.

        Returns:
            PolarisCatalog instance satisfying CatalogProtocol
        """
        if self._catalog is not None:
            return cast(CatalogProtocol, self._catalog)

        # Import directly from submodules for proper type checking
        from floe_polaris.client import PolarisCatalog as PolarisCatalogImpl
        from floe_polaris.config import PolarisCatalogConfig as ConfigClass

        # Resolve client_id (may be env var reference)
        resolved_client_id = self._resolve_value(self.client_id)

        # Resolve client_secret (may be env var reference)
        # Convert to SecretStr for the underlying PolarisCatalogConfig
        resolved_secret: PydanticSecretStr | None = None
        if self.client_secret:
            resolved_value = self._resolve_value(self.client_secret)
            if resolved_value:
                resolved_secret = PydanticSecretStr(resolved_value)

        # Resolve S3 credentials
        resolved_s3_key = self._resolve_value(self.s3_access_key_id)
        resolved_s3_secret: PydanticSecretStr | None = None
        if self.s3_secret_access_key:
            resolved_s3_value = self._resolve_value(self.s3_secret_access_key)
            if resolved_s3_value:
                resolved_s3_secret = PydanticSecretStr(resolved_s3_value)

        config = ConfigClass(
            uri=self.uri,
            warehouse=self.warehouse,
            client_id=resolved_client_id,
            client_secret=resolved_secret,
            scope=self.scope,
            s3_endpoint=self.s3_endpoint,
            s3_region=self.s3_region,
            s3_path_style_access=self.s3_path_style_access,
            s3_access_key_id=resolved_s3_key,
            s3_secret_access_key=resolved_s3_secret,
        )

        self._catalog = PolarisCatalogImpl(config)
        return cast(CatalogProtocol, self._catalog)

    @staticmethod
    def _resolve_value(value: str | None) -> str | None:
        """Resolve a value that may be an environment variable reference.

        Supports:
            - Direct values: "my_value" -> "my_value"
            - Env var references: "$MY_VAR" -> os.environ["MY_VAR"]
            - Secret refs: "secret_ref:MY_SECRET" -> os.environ["MY_SECRET"]

        Args:
            value: Value to resolve

        Returns:
            Resolved value or None
        """
        if value is None:
            return None

        # Check for env var reference ($VAR_NAME)
        if value.startswith("$"):
            env_name = value[1:]
            return os.environ.get(env_name, "")

        # Check for secret_ref pattern
        if value.startswith("secret_ref:"):
            env_name = value[11:]  # len("secret_ref:") = 11
            return os.environ.get(env_name, "")

        return value

    @classmethod
    def from_compiled_artifacts(
        cls,
        artifacts: dict[str, Any],
        profile_name: str = "default",
    ) -> PolarisCatalogResource:
        """Create PolarisCatalogResource from CompiledArtifacts.

        Extracts the resolved catalog profile from CompiledArtifacts
        and creates a resource with runtime secret resolution.

        Args:
            artifacts: CompiledArtifacts dict (or model_dump() result)
            profile_name: Name of the catalog profile to use

        Returns:
            Configured PolarisCatalogResource

        Example:
            >>> artifacts = load_compiled_artifacts()
            >>> resource = PolarisCatalogResource.from_compiled_artifacts(
            ...     artifacts.model_dump()
            ... )
        """
        # Try v2 format (resolved_catalog)
        resolved_catalog = artifacts.get("resolved_catalog", {})
        if not resolved_catalog:
            # Try v1 format (catalogs dict)
            catalogs = artifacts.get("catalogs", {})
            resolved_catalog = catalogs.get(profile_name, {})

        # Extract credentials section
        credentials = resolved_catalog.get("credentials", {})

        # Handle secret_ref pattern in credentials with runtime resolution
        client_id_raw = credentials.get("client_id")
        client_id: str | None = None
        if isinstance(client_id_raw, SecretReference):
            # SecretReference Pydantic model - resolve to actual value
            client_id = client_id_raw.resolve().get_secret_value()
        elif isinstance(client_id_raw, dict) and "secret_ref" in client_id_raw:
            # Dict format from YAML - create SecretReference and resolve
            secret_ref = SecretReference(secret_ref=client_id_raw["secret_ref"])
            client_id = secret_ref.resolve().get_secret_value()
        elif client_id_raw:
            client_id = str(client_id_raw)

        client_secret_raw = credentials.get("client_secret")
        client_secret: str | None = None
        if isinstance(client_secret_raw, SecretReference):
            # SecretReference Pydantic model - resolve to actual SecretStr
            client_secret = client_secret_raw.resolve().get_secret_value()
        elif isinstance(client_secret_raw, dict) and "secret_ref" in client_secret_raw:
            # Dict format from YAML - create SecretReference and resolve
            secret_ref = SecretReference(secret_ref=client_secret_raw["secret_ref"])
            client_secret = secret_ref.resolve().get_secret_value()
        elif client_secret_raw:
            client_secret = str(client_secret_raw)

        return cls(
            uri=resolved_catalog.get("uri", ""),
            warehouse=resolved_catalog.get("warehouse", ""),
            client_id=client_id,
            client_secret=client_secret,
            scope=credentials.get("scope", "PRINCIPAL_ROLE:ALL"),
            s3_endpoint=resolved_catalog.get("s3_endpoint"),
            s3_region=resolved_catalog.get("s3_region", "us-east-1"),
            s3_path_style_access=resolved_catalog.get("s3_path_style_access", False),
            layer_bindings=artifacts.get("resolved_layers", {}),
        )


# Type alias for data engineers to use in type hints
# This allows writing `catalog: Catalog` which works with any implementation
Catalog: TypeAlias = CatalogResource
