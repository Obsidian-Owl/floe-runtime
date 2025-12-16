"""floe-dagster: Dagster integration for floe-runtime.

This package provides Dagster asset factory and orchestration
capabilities from CompiledArtifacts.
"""

from __future__ import annotations

__version__ = "0.1.0"

from floe_dagster.assets import FloeAssetFactory
from floe_dagster.definitions import (
    load_definitions_from_artifacts,
    load_definitions_from_dict,
)
from floe_dagster.models import (
    AssetMaterializationResult,
    ColumnMetadata,
    DbtModelMetadata,
)
from floe_dagster.resources import create_dbt_cli_resource
from floe_dagster.translator import FloeTranslator

# Lineage and observability exports will be added when implemented
# from floe_dagster.lineage import OpenLineageEmitter
# from floe_dagster.observability import TracingManager

__all__ = [
    "__version__",
    # Factory and definitions
    "FloeAssetFactory",
    "load_definitions_from_artifacts",
    "load_definitions_from_dict",
    # Translator
    "FloeTranslator",
    # Models
    "DbtModelMetadata",
    "ColumnMetadata",
    "AssetMaterializationResult",
    # Resources
    "create_dbt_cli_resource",
]
