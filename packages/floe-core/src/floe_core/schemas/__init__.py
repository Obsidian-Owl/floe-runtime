"""Schema definitions for floe-runtime.

This module exports the core Pydantic models:

Root Models:
- FloeSpec: Root schema for floe.yaml (Data Engineer configuration)
- PlatformSpec: Root schema for platform.yaml (Platform Engineer configuration)

Profile Models (Two-Tier Configuration):
- StorageProfile: S3-compatible storage configuration
- CatalogProfile: Iceberg catalog configuration
- ComputeProfile: Compute engine configuration
- CredentialConfig: Credential management (OAuth2, IAM, static)
- SecretReference: Reference to external secrets

Legacy Models:
- ComputeTarget: Enum for compute targets
- ComputeConfig: Compute target configuration
- TransformConfig: Transformation step configuration
- ConsumptionConfig: Cube semantic layer configuration
- GovernanceConfig: Data governance configuration
- ObservabilityConfig: Observability configuration
- CatalogConfig: Iceberg catalog configuration
"""

from __future__ import annotations

from floe_core.schemas.catalog import CatalogConfig
from floe_core.schemas.catalog_profile import (
    AccessDelegation,
    CatalogProfile,
    CatalogType,
)
from floe_core.schemas.compute import ComputeConfig, ComputeTarget
from floe_core.schemas.compute_profile import ComputeProfile
from floe_core.schemas.consumption import (
    ConsumptionConfig,
    CubeSecurityConfig,
    CubeStoreConfig,
    ExportBucketConfig,
    PreAggregationConfig,
)
from floe_core.schemas.credential_config import (
    CredentialConfig,
    CredentialMode,
    SecretNotFoundError,
    SecretReference,
)
from floe_core.schemas.floe_spec import (
    DEFAULT_PROFILE_NAME,
    FloeSpec,
)
from floe_core.schemas.floe_spec import (
    PROFILE_NAME_PATTERN as FLOE_PROFILE_NAME_PATTERN,
)
from floe_core.schemas.governance import ColumnClassification, GovernanceConfig
from floe_core.schemas.observability import ObservabilityConfig
from floe_core.schemas.platform_spec import (
    ENVIRONMENT_TYPES,
    PLATFORM_SPEC_VERSION,
    PROFILE_NAME_PATTERN,
    PlatformSpec,
)
from floe_core.schemas.storage_profile import StorageProfile, StorageType
from floe_core.schemas.transforms import TransformConfig

__all__: list[str] = [
    # Root models
    "FloeSpec",
    "PlatformSpec",
    # Platform configuration constants
    "ENVIRONMENT_TYPES",
    "PLATFORM_SPEC_VERSION",
    "PROFILE_NAME_PATTERN",
    # FloeSpec configuration constants
    "DEFAULT_PROFILE_NAME",
    "FLOE_PROFILE_NAME_PATTERN",
    # Credential management
    "CredentialConfig",
    "CredentialMode",
    "SecretReference",
    "SecretNotFoundError",
    # Storage profiles
    "StorageProfile",
    "StorageType",
    # Catalog profiles
    "CatalogProfile",
    "CatalogType",
    "AccessDelegation",
    # Compute profiles
    "ComputeProfile",
    # Compute (legacy)
    "ComputeTarget",
    "ComputeConfig",
    # Transforms
    "TransformConfig",
    # Consumption
    "CubeStoreConfig",
    "ExportBucketConfig",
    "PreAggregationConfig",
    "CubeSecurityConfig",
    "ConsumptionConfig",
    # Governance
    "ColumnClassification",
    "GovernanceConfig",
    # Observability
    "ObservabilityConfig",
    # Catalog (legacy)
    "CatalogConfig",
]
