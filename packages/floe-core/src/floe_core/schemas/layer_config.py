"""Data layer configuration models for platform.yaml.

This module defines the LayerConfig schema for declarative medallion/layer architecture
configuration in platform.yaml. Supports any layer naming pattern (bronze/silver/gold,
raw/curated/analytics, landing/staging/production, etc.).

Covers: Declarative Layer Configuration (v1.2.0)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LayerConfig(BaseModel):
    """Data layer configuration for platform.yaml.

    Supports arbitrary layer names for any data architecture pattern:
    - Medallion: bronze, silver, gold
    - Alternative: raw, curated, analytics
    - Staging: landing, staging, production
    - Custom: Any alphanumeric pattern

    Platform engineers define layers with storage bindings, catalog namespaces,
    and retention policies. Data engineers reference layer names in assets.

    Attributes:
        name: Layer name (flexible naming, e.g., "bronze", "raw", "landing").
        description: Human-readable layer description.
        storage_ref: Storage profile reference (must exist in storage dict).
        catalog_ref: Catalog profile reference (must exist in catalogs dict).
        namespace: Catalog namespace for this layer (e.g., "demo_catalog.bronze").
        retention_days: Data retention policy in days (metadata only, not enforced).
        properties: Additional layer-specific properties (tags, owner, etc.).

    Example:
        >>> layer = LayerConfig(
        ...     name="bronze",
        ...     description="Raw and lightly cleaned data",
        ...     storage_ref="bronze",
        ...     catalog_ref="default",
        ...     namespace="demo_catalog.bronze",
        ...     retention_days=2555,  # 7 years for audit compliance
        ...     properties={"owner": "data-engineering", "sensitivity": "internal"}
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(
        ...,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        min_length=1,
        max_length=100,
        description="Layer name (flexible: bronze, raw, landing, etc.)",
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Human-readable layer description",
    )
    storage_ref: str = Field(
        ...,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        description="Storage profile reference (must exist in storage dict)",
    )
    catalog_ref: str = Field(
        default="default",
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        description="Catalog profile reference (must exist in catalogs dict)",
    )
    namespace: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Catalog namespace for this layer (e.g., 'demo_catalog.bronze')",
    )
    retention_days: int | None = Field(
        default=None,
        ge=1,
        le=36500,  # 100 years max
        description="Data retention policy in days (metadata only, not enforced in v1.2.0)",
    )
    properties: dict[str, str] = Field(
        default_factory=dict,
        description="Additional layer-specific properties (tags, owner, sensitivity, etc.)",
    )

    @field_validator("namespace")
    @classmethod
    def validate_namespace_format(cls, v: str) -> str:
        """Validate namespace format (must include warehouse prefix).

        Args:
            v: Namespace string to validate.

        Returns:
            Validated namespace string.

        Raises:
            ValueError: If namespace doesn't contain '.' separator.

        Examples:
            >>> LayerConfig.validate_namespace_format("demo_catalog.bronze")
            'demo_catalog.bronze'
            >>> LayerConfig.validate_namespace_format("bronze")
            Traceback (most recent call last):
            ...
            ValueError: Catalog namespace must include warehouse prefix...
        """
        if "." not in v:
            raise ValueError(
                f"Catalog namespace must include warehouse prefix "
                f"(e.g., 'demo_catalog.bronze'), got '{v}'"
            )
        return v
