"""Compiler output models for floe-runtime.

T040: [US2] Implement ArtifactMetadata model
T041: [US2] Implement EnvironmentContext optional model
T042: [US2] Implement CompiledArtifacts contract model

This module defines the output contract models produced by the Compiler.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from floe_core.schemas import (
    CatalogConfig,
    ColumnClassification,
    ComputeConfig,
    ConsumptionConfig,
    GovernanceConfig,
    ObservabilityConfig,
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


class CompiledArtifacts(BaseModel):
    """Immutable output contract from compilation.

    This is the sole integration point between floe-core (compiler) and
    downstream packages (floe-dagster, floe-dbt, floe-cube, floe-polaris).

    Contract Rules:
    - Model is immutable (frozen=True)
    - Unknown fields are rejected (extra="forbid")
    - 3-version backward compatibility maintained
    - JSON Schema exported for cross-language validation

    Attributes:
        version: Contract version (semver). Default "1.0.0".
        metadata: Compilation metadata.
        compute: Compute target configuration.
        transforms: List of transform configurations.
        consumption: Cube semantic layer configuration.
        governance: Data governance configuration.
        observability: Observability configuration.
        catalog: Optional Iceberg catalog configuration.
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
        ...     transforms=[transform_config]
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Contract versioning
    version: str = Field(
        default="1.0.0",
        description="Contract version (semver)",
    )

    # Core required fields
    metadata: ArtifactMetadata = Field(
        ...,
        description="Compilation metadata",
    )
    compute: ComputeConfig = Field(
        ...,
        description="Compute target configuration",
    )
    transforms: list[TransformConfig] = Field(
        ...,
        description="List of transform configurations",
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

    # Optional configurations
    catalog: CatalogConfig | None = Field(
        default=None,
        description="Iceberg catalog configuration",
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
