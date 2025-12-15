"""FloeSpec root model for floe-runtime.

T030: [US1] Implement FloeSpec root model with from_yaml()

This module defines the FloeSpec root configuration model
that represents a complete floe.yaml definition.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from floe_core.schemas.catalog import CatalogConfig
from floe_core.schemas.compute import ComputeConfig
from floe_core.schemas.consumption import ConsumptionConfig
from floe_core.schemas.governance import GovernanceConfig
from floe_core.schemas.observability import ObservabilityConfig
from floe_core.schemas.transforms import TransformConfig


class FloeSpec(BaseModel):
    """Root configuration model for floe.yaml.

    Represents a complete pipeline definition including compute target,
    transformations, consumption layer, governance, and observability.

    Attributes:
        name: Pipeline name (1-100 chars, alphanumeric with hyphens/underscores).
        version: Pipeline version (semver format).
        compute: Compute target configuration.
        transforms: List of transformation steps.
        consumption: Semantic layer configuration.
        governance: Data governance configuration.
        observability: Observability configuration.
        catalog: Optional Iceberg catalog configuration.

    Example:
        >>> spec = FloeSpec(
        ...     name="my-pipeline",
        ...     version="1.0.0",
        ...     compute=ComputeConfig(target=ComputeTarget.duckdb)
        ... )

        >>> spec = FloeSpec.from_yaml("floe.yaml")
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,99}$",
        description="Pipeline name",
    )
    version: str = Field(
        ...,
        description="Pipeline version (semver)",
    )
    compute: ComputeConfig
    transforms: list[TransformConfig] = Field(
        default_factory=list,
        description="List of transformation steps",
    )
    consumption: ConsumptionConfig = Field(
        default_factory=ConsumptionConfig,
        description="Semantic layer configuration",
    )
    governance: GovernanceConfig = Field(
        default_factory=GovernanceConfig,
        description="Data governance configuration",
    )
    observability: ObservabilityConfig = Field(
        default_factory=ObservabilityConfig,
        description="Observability configuration",
    )
    catalog: CatalogConfig | None = Field(
        default=None,
        description="Iceberg catalog configuration",
    )

    @classmethod
    def from_yaml(cls, path: str | Path) -> FloeSpec:
        """Load and validate FloeSpec from a YAML file.

        Args:
            path: Path to floe.yaml file.

        Returns:
            Validated FloeSpec instance.

        Raises:
            FileNotFoundError: If file doesn't exist.
            yaml.YAMLError: If YAML syntax is invalid.
            ValidationError: If schema validation fails.

        Example:
            >>> spec = FloeSpec.from_yaml("floe.yaml")
            >>> spec.name
            'my-pipeline'
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        with path.open("r") as f:
            data: dict[str, Any] = yaml.safe_load(f)

        return cls.model_validate(data)
