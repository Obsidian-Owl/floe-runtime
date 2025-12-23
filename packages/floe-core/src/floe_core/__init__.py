"""floe-core: Core schemas and compilation for floe-runtime.

T068: Update package __init__.py with complete public API

This package provides:
- FloeSpec: Pydantic schema for floe.yaml configuration
- CompiledArtifacts: Output contract consumed by other packages
- Compiler: Transform FloeSpec → CompiledArtifacts
- JSON Schema export utilities
"""

from __future__ import annotations

__version__ = "0.1.0"

# Compiler and output models
from floe_core.compiler import (
    ArtifactMetadata,
    CompiledArtifacts,
    Compiler,
    EnvironmentContext,
    extract_column_classifications,
)

# Error types
from floe_core.errors import (
    CompilationError,
    ConfigurationError,
    FloeError,
    ProfileNotFoundError,
    SecretResolutionError,
    ValidationError,
)

# JSON Schema export functions
from floe_core.export import (
    export_compiled_artifacts_schema,
    export_floe_spec_schema,
)

# Schema models
from floe_core.schemas import (
    CatalogConfig,
    ColumnClassification,
    ComputeConfig,
    ComputeTarget,
    ConsumptionConfig,
    CubeSecurityConfig,
    FloeSpec,
    GovernanceConfig,
    ObservabilityConfig,
    PreAggregationConfig,
    TransformConfig,
)

__all__ = [
    "__version__",
    # Compiler
    "Compiler",
    "CompiledArtifacts",
    "ArtifactMetadata",
    "EnvironmentContext",
    "extract_column_classifications",
    # Errors
    "FloeError",
    "ValidationError",
    "CompilationError",
    "ConfigurationError",
    "ProfileNotFoundError",
    "SecretResolutionError",
    # JSON Schema exports
    "export_floe_spec_schema",
    "export_compiled_artifacts_schema",
    # Schema models
    "FloeSpec",
    "ComputeTarget",
    "ComputeConfig",
    "TransformConfig",
    "ConsumptionConfig",
    "PreAggregationConfig",
    "CubeSecurityConfig",
    "GovernanceConfig",
    "ColumnClassification",
    "ObservabilityConfig",
    "CatalogConfig",
]
