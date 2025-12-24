"""floe-dagster: Dagster integration for floe-runtime.

This package provides Dagster asset factory and orchestration
capabilities from CompiledArtifacts, with batteries-included
observability via the ObservabilityOrchestrator.

Key Features:
    - @floe_asset: Instrumented asset decorator with auto-observability
    - CatalogResource: Catalog-agnostic resource abstraction
    - ObservabilityOrchestrator: Unified tracing + lineage management
    - FloeDefinitions: One-line Definitions factory from CompiledArtifacts
"""

from __future__ import annotations

__version__ = "0.1.0"

from floe_dagster.assets import FloeAssetFactory
from floe_dagster.decorators import floe_asset
from floe_dagster.definitions import (
    FloeDefinitions,
    load_definitions_from_artifacts,
    load_definitions_from_dict,
)
from floe_dagster.lineage import OpenLineageEmitter
from floe_dagster.models import (
    AssetMaterializationResult,
    ColumnMetadata,
    DbtModelMetadata,
)
from floe_dagster.observability import (
    AssetRunContext,
    ObservabilityOrchestrator,
    TracingManager,
)
from floe_dagster.resources import (
    CatalogResource,
    PolarisCatalogResource,
    create_dbt_cli_resource,
)
from floe_dagster.translator import FloeTranslator

__all__ = [
    "__version__",
    # Batteries-included (primary API)
    "floe_asset",
    "FloeDefinitions",
    # Legacy factory and definitions
    "FloeAssetFactory",
    "load_definitions_from_artifacts",
    "load_definitions_from_dict",
    # Translator
    "FloeTranslator",
    # Models
    "DbtModelMetadata",
    "ColumnMetadata",
    "AssetMaterializationResult",
    # Resources (catalog-agnostic)
    "CatalogResource",
    "PolarisCatalogResource",
    "create_dbt_cli_resource",
    # Observability (batteries-included)
    "ObservabilityOrchestrator",
    "AssetRunContext",
    "TracingManager",
    "OpenLineageEmitter",
]
