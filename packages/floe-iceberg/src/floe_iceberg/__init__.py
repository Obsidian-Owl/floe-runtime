"""floe-iceberg: Apache Iceberg integration for floe-runtime.

This package provides:
- Dagster IOManager for reading/writing assets to Iceberg tables
- Table management utilities (create, drop, list)
- Data operations (append, overwrite, scan)
- Time travel and snapshot management
- Automatic schema evolution

Example (Dagster integration):
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

Example (direct table management):
    >>> from floe_polaris import create_catalog, PolarisCatalogConfig
    >>> from floe_iceberg import IcebergTableManager
    >>>
    >>> catalog = create_catalog(config)
    >>> manager = IcebergTableManager(catalog)
    >>> manager.append("bronze.customers", data)
"""

from __future__ import annotations

__version__ = "0.1.0"

# Public API exports
# Note: Actual implementations are in User Stories. These are forward declarations.
__all__ = [
    # Factory function
    "create_io_manager",
    # IOManager class
    "IcebergIOManager",
    # Table manager
    "IcebergTableManager",
    # Configuration models
    "IcebergIOManagerConfig",
    "WriteMode",
    # Data models
    "TableIdentifier",
    "SnapshotInfo",
    "PartitionTransform",
    "PartitionTransformType",
    "MaterializationMetadata",
    # Exceptions
    "FloeStorageError",
    "TableNotFoundError",
    "TableExistsError",
    "SchemaEvolutionError",
    "WriteError",
    "ScanError",
]

# Lazy imports to avoid circular dependencies and allow gradual implementation
# These will be populated as User Story tasks are completed


def __getattr__(name: str) -> object:
    """Lazy import of public API members."""
    if name == "create_io_manager":
        from floe_iceberg.io_manager import create_io_manager

        return create_io_manager
    if name == "IcebergIOManager":
        from floe_iceberg.io_manager import IcebergIOManager

        return IcebergIOManager
    if name == "IcebergTableManager":
        from floe_iceberg.tables import IcebergTableManager

        return IcebergTableManager
    if name in (
        "IcebergIOManagerConfig",
        "WriteMode",
        "TableIdentifier",
        "SnapshotInfo",
        "PartitionTransform",
        "PartitionTransformType",
        "MaterializationMetadata",
    ):
        from floe_iceberg import config as config_module

        return getattr(config_module, name)
    if name in (
        "FloeStorageError",
        "TableNotFoundError",
        "TableExistsError",
        "SchemaEvolutionError",
        "WriteError",
        "ScanError",
    ):
        from floe_iceberg import errors as errors_module

        return getattr(errors_module, name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
