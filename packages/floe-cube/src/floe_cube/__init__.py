"""floe-cube: Cube semantic layer integration for floe-runtime.

This package provides:
- Configuration generation for Cube semantic layer deployment
- dbt model to Cube cube synchronization
- Row-level security via JWT claims
- OpenTelemetry tracing for query observability
- OpenLineage events for data lineage

Example (configuration generation):
    >>> from floe_cube import CubeConfigGenerator, CubeConfig
    >>>
    >>> config = CubeConfig(
    ...     database_type="postgres",
    ...     api_port=4000,
    ...     sql_port=15432,
    ... )
    >>> generator = CubeConfigGenerator(config)
    >>> generator.generate(".floe/cube/")

Example (model sync):
    >>> from floe_cube import ModelSync
    >>>
    >>> sync = ModelSync(manifest_path="target/manifest.json")
    >>> sync.sync_to_cube(".floe/cube/schema/")
"""

from __future__ import annotations

__version__ = "0.1.0"

# Public API exports
# Note: Actual implementations are in User Story tasks. These are forward declarations.
__all__ = [
    # Configuration (US1)
    "CubeConfig",
    "CubeConfigGenerator",
    # Model sync (US2)
    "ModelSync",
    "DbtManifestParser",
    "ModelSynchronizer",
    # Manifest sources (US2)
    "ManifestSource",
    "FileManifestSource",
    "ManifestLoadError",
    # File watcher (US2)
    "ManifestWatcher",
    "WatcherState",
    "WatcherError",
    # Pydantic models (Foundational)
    "CubeSchema",
    "CubeDimension",
    "CubeMeasure",
    "CubeJoin",
    "CubePreAggregation",
    # Security (US6)
    "SecurityContext",
    # Tracing (US7)
    "QueryTracer",
    # Lineage (US8)
    "QueryLineageEmitter",
    "QueryLineageEvent",
]


def __getattr__(name: str) -> object:
    """Lazy import of public API members.

    This enables forward declarations for modules that will be
    implemented in later User Story tasks.

    Args:
        name: The attribute name to look up.

    Returns:
        The requested module or class.

    Raises:
        AttributeError: If the attribute is not found.
    """
    # Configuration (US1)
    if name == "CubeConfig":
        from floe_cube.models import CubeConfig

        return CubeConfig
    if name == "CubeConfigGenerator":
        from floe_cube.config import CubeConfigGenerator

        return CubeConfigGenerator

    # Model sync (US2)
    if name == "ModelSync":
        from floe_cube.model_sync import ModelSync

        return ModelSync
    if name in ("DbtManifestParser", "ModelSynchronizer"):
        from floe_cube import model_sync as model_sync_module

        return getattr(model_sync_module, name)

    # Manifest sources (US2)
    if name in ("ManifestSource", "FileManifestSource", "ManifestLoadError"):
        from floe_cube import sources as sources_module

        return getattr(sources_module, name)

    # File watcher (US2)
    if name in ("ManifestWatcher", "WatcherState", "WatcherError"):
        from floe_cube import watcher as watcher_module

        return getattr(watcher_module, name)

    # Pydantic models (Foundational)
    if name in (
        "CubeSchema",
        "CubeDimension",
        "CubeMeasure",
        "CubeJoin",
        "CubePreAggregation",
        "SecurityContext",
    ):
        from floe_cube import models as models_module

        return getattr(models_module, name)

    # Tracing (US7)
    if name == "QueryTracer":
        from floe_cube.tracing import QueryTracer

        return QueryTracer

    # Lineage (US8)
    if name in ("QueryLineageEmitter", "QueryLineageEvent"):
        from floe_cube import lineage as lineage_module

        return getattr(lineage_module, name)

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
