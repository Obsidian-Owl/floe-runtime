"""Compiler output models for floe-runtime.

T040: [US2] Implement ArtifactMetadata model
T041: [US2] Implement EnvironmentContext optional model
T042: [US2] Implement CompiledArtifacts contract model
T024: [US2] Update CompiledArtifacts v2.0 with resolved platform profiles

This module defines the output contract models produced by the Compiler.

Version History:
- v1.0.0: Initial release with resolved_profiles (two-tier configuration)
- v1.1.0: Added resolved_layers for declarative layer configuration (v1.2.0 platform.yaml)
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from floe_core.compiler.layer_resolver import ResolvedLayerConfig
from floe_core.schemas import (
    CatalogConfig,
    CatalogProfile,
    ColumnClassification,
    ComputeConfig,
    ComputeProfile,
    ConsumptionConfig,
    GovernanceConfig,
    ObservabilityConfig,
    OrchestrationConfig,
    StorageProfile,
    TransformConfig,
)


class ArtifactMetadata(BaseModel):
    """Compilation metadata for tracking artifact provenance.

    Records when artifacts were compiled and from which source file.

    Attributes:
        compiled_at: Timestamp when compilation occurred (UTC).
        floe_core_version: Version of floe-core that produced artifacts.
        source_hash: SHA-256 hash of source floe.yaml content.

    Example:
        >>> metadata = ArtifactMetadata(
        ...     compiled_at=datetime.now(timezone.utc),
        ...     floe_core_version="0.1.0",
        ...     source_hash="e3b0c44..."
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    compiled_at: datetime = Field(
        ...,
        description="Timestamp when compilation occurred (UTC)",
    )
    floe_core_version: str = Field(
        ...,
        min_length=1,
        description="Version of floe-core that produced artifacts",
    )
    source_hash: str = Field(
        ...,
        min_length=1,
        description="SHA-256 hash of source floe.yaml content",
    )


class EnvironmentContext(BaseModel):
    """Optional runtime context from Control Plane (SaaS enrichment).

    This model is only populated when running with the Floe Control Plane.
    Standalone deployments should set this to None (standalone-first principle).

    Attributes:
        tenant_id: Tenant identifier (UUID).
        tenant_slug: Human-readable tenant slug.
        project_id: Project identifier (UUID).
        project_slug: Human-readable project slug.
        environment_id: Environment identifier (UUID).
        environment_type: Type of environment (development, preview, staging, production).
        governance_category: Governance category for the environment.

    Example:
        >>> context = EnvironmentContext(
        ...     tenant_id=uuid4(),
        ...     tenant_slug="acme-corp",
        ...     project_id=uuid4(),
        ...     project_slug="data-warehouse",
        ...     environment_id=uuid4(),
        ...     environment_type="production",
        ...     governance_category="production"
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_id: UUID = Field(
        ...,
        description="Tenant identifier",
    )
    tenant_slug: str = Field(
        ...,
        min_length=1,
        description="Human-readable tenant slug",
    )
    project_id: UUID = Field(
        ...,
        description="Project identifier",
    )
    project_slug: str = Field(
        ...,
        min_length=1,
        description="Human-readable project slug",
    )
    environment_id: UUID = Field(
        ...,
        description="Environment identifier",
    )
    environment_type: Literal["development", "preview", "staging", "production"] = Field(
        ...,
        description="Type of environment",
    )
    governance_category: Literal["production", "non_production"] = Field(
        ...,
        description="Governance category for the environment",
    )


class ResolvedPlatformProfiles(BaseModel):
    """Resolved platform profiles from platform.yaml.

    Contains concrete profile configurations resolved from logical names
    in floe.yaml. This is part of the Two-Tier Configuration architecture
    where platform engineers configure infrastructure and data engineers
    reference profiles by logical name.

    Attributes:
        storage: Resolved storage profile (S3-compatible backend).
        catalog: Resolved catalog profile (Iceberg REST catalog).
        compute: Resolved compute profile (engine configuration).
        platform_env: Platform environment used for resolution.

    Example:
        >>> profiles = ResolvedPlatformProfiles(
        ...     storage=storage_profile,
        ...     catalog=catalog_profile,
        ...     compute=compute_profile,
        ...     platform_env="local"
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    storage: StorageProfile = Field(
        ...,
        description="Resolved storage profile (S3-compatible backend)",
    )
    catalog: CatalogProfile = Field(
        ...,
        description="Resolved catalog profile (Iceberg REST catalog)",
    )
    compute: ComputeProfile = Field(
        ...,
        description="Resolved compute profile (engine configuration)",
    )
    platform_env: str = Field(
        default="local",
        description="Platform environment used for resolution",
    )


class CompiledArtifacts(BaseModel):
    """Immutable output contract from compilation.

    This is the sole integration point between floe-core (compiler) and
    downstream packages (floe-dagster, floe-dbt, floe-cube, floe-polaris).

    Contract Rules:
    - Model is immutable (frozen=True)
    - Unknown fields are rejected (extra="forbid")
    - 3-version backward compatibility maintained
    - JSON Schema exported for cross-language validation

    Two-Tier Configuration (v2.0):
    - resolved_profiles contains concrete platform profiles resolved from
      logical names in floe.yaml (e.g., catalog: "default" → CatalogProfile)
    - Platform engineers configure platform.yaml with infrastructure details
    - Data engineers reference profiles by logical name in floe.yaml
    - Same floe.yaml works across dev/staging/prod environments

    Declarative Layer Configuration (v1.1.0):
    - resolved_layers contains per-layer (bronze/silver/gold) resolved configurations
    - Each layer has its own storage profile, catalog namespace, and retention policy
    - Enables medallion architecture with separate buckets per layer

    Attributes:
        version: Contract version (semver). Default "1.1.0".
        metadata: Compilation metadata.
        compute: Compute target configuration.
        transforms: List of transform configurations.
        consumption: Cube semantic layer configuration.
        governance: Data governance configuration.
        observability: Observability configuration.
        orchestration: Orchestration configuration for auto-discovery.
        catalog: Optional Iceberg catalog configuration (legacy).
        resolved_profiles: Resolved platform profiles from platform.yaml.
        resolved_layers: Per-layer resolved configurations (v1.1.0).
        dbt_manifest_path: Path to dbt manifest.json (if available).
        dbt_project_path: Path to dbt project directory (if detected).
        dbt_profiles_path: Path to profiles directory. Default ".floe/profiles".
        lineage_namespace: OpenLineage namespace (SaaS enrichment).
        environment_context: Optional SaaS environment context.
        column_classifications: Extracted column classifications from dbt.

    Example:
        >>> artifacts = CompiledArtifacts(
        ...     metadata=metadata,
        ...     compute=compute_config,
        ...     transforms=[transform_config],
        ...     resolved_profiles=resolved_profiles
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Contract versioning
    version: str = Field(
        default="1.1.0",
        description="Contract version (semver)",
    )

    # Core required fields
    metadata: ArtifactMetadata = Field(
        ...,
        description="Compilation metadata",
    )
    transforms: list[TransformConfig] = Field(
        ...,
        description="List of transform configurations",
    )

    # Legacy compute field (deprecated: use resolved_profiles.compute)
    # Kept for backward compatibility - will be populated from resolved_profiles
    compute: ComputeConfig | None = Field(
        default=None,
        description="Compute target configuration (deprecated - use resolved_profiles.compute)",
    )

    # Configuration sections (with defaults)
    consumption: ConsumptionConfig = Field(
        default_factory=ConsumptionConfig,
        description="Cube semantic layer configuration",
    )
    governance: GovernanceConfig = Field(
        default_factory=GovernanceConfig,
        description="Data governance configuration",
    )
    observability: ObservabilityConfig = Field(
        default_factory=ObservabilityConfig,
        description="Observability configuration",
    )
    orchestration: OrchestrationConfig | None = Field(
        default=None,
        description="Orchestration configuration for auto-discovery",
    )

    # Optional configurations (legacy)
    catalog: CatalogConfig | None = Field(
        default=None,
        description="Iceberg catalog configuration (legacy - use resolved_profiles)",
    )

    # Two-Tier Configuration: Resolved platform profiles
    resolved_profiles: ResolvedPlatformProfiles | None = Field(
        default=None,
        description="Resolved platform profiles from platform.yaml",
    )

    # Declarative Layer Configuration (v1.1.0)
    resolved_layers: dict[str, ResolvedLayerConfig] | None = Field(
        default=None,
        description="Per-layer resolved configurations (bronze/silver/gold) - v1.1.0",
    )

    # dbt integration paths
    dbt_manifest_path: str | None = Field(
        default=None,
        description="Path to dbt manifest.json",
    )
    dbt_project_path: str | None = Field(
        default=None,
        description="Path to dbt project directory",
    )
    dbt_profiles_path: str = Field(
        default=".floe/profiles",
        description="Path to profiles directory (required by dagster-dbt)",
    )

    # SaaS enrichment (optional - standalone-first)
    lineage_namespace: str | None = Field(
        default=None,
        description="OpenLineage namespace (SaaS enrichment)",
    )
    environment_context: EnvironmentContext | None = Field(
        default=None,
        description="Optional SaaS environment context",
    )

    # Extracted classifications
    column_classifications: dict[str, dict[str, ColumnClassification]] | None = Field(
        default=None,
        description="Extracted column classifications from dbt manifest",
    )
