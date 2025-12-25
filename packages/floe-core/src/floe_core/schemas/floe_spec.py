"""FloeSpec root model for floe-runtime.

T030: [US1] Implement FloeSpec root model with from_yaml()
T035: [US2] Add profile reference fields for Two-Tier Architecture
T046: [US3] Add validation to reject any credentials in floe.yaml

This module defines the FloeSpec root configuration model
that represents a complete floe.yaml definition.

In the Two-Tier Architecture:
- FloeSpec uses logical profile references (e.g., catalog: "default")
- PlatformSpec defines the actual infrastructure configuration
- Profile references are resolved at compile/deploy time

Security: Uses Yelp's detect-secrets library to prevent accidental
credential exposure in floe.yaml files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from floe_core.schemas.consumption import ConsumptionConfig
from floe_core.schemas.governance import GovernanceConfig
from floe_core.schemas.observability import ObservabilityConfig
from floe_core.schemas.orchestration_config import OrchestrationConfig
from floe_core.schemas.transforms import TransformConfig
from floe_core.security import CredentialDetectedError, detect_credentials_in_string

# Default profile name for profile references
DEFAULT_PROFILE_NAME = "default"

# Valid profile name pattern (alphanumeric with hyphens/underscores)
PROFILE_NAME_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_-]*$"


class FloeSpec(BaseModel):
    """Root configuration model for floe.yaml (Data Engineer domain).

    Represents a complete pipeline definition with logical profile references.
    This is the Data Engineer's view - no infrastructure details, credentials,
    or endpoints. All infrastructure is referenced via profile names that
    resolve to PlatformSpec configurations at compile/deploy time.

    Attributes:
        name: Pipeline name (1-100 chars, alphanumeric with hyphens/underscores).
        version: Pipeline version (semver format).
        storage: Logical storage profile reference (e.g., "default", "archive").
        catalog: Logical catalog profile reference (e.g., "default", "analytics").
        compute: Logical compute profile reference (e.g., "default", "snowflake").
        transforms: List of transformation steps.
        consumption: Semantic layer configuration.
        governance: Data governance configuration.
        observability: Observability configuration.
        orchestration: Declarative orchestration configuration (Feature 010).

    Example:
        >>> # Data engineer creates floe.yaml with logical references
        >>> spec = FloeSpec(
        ...     name="customer-analytics",
        ...     version="1.0.0",
        ...     storage="default",
        ...     catalog="default",
        ...     compute="default",
        ... )

        >>> # Same floe.yaml works across environments
        >>> spec = FloeSpec.from_yaml("floe.yaml")
        >>> spec.catalog  # Returns "default" - resolved by PlatformSpec
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
    storage: str = Field(
        default=DEFAULT_PROFILE_NAME,
        pattern=PROFILE_NAME_PATTERN,
        description="Logical storage profile reference",
    )
    catalog: str = Field(
        default=DEFAULT_PROFILE_NAME,
        pattern=PROFILE_NAME_PATTERN,
        description="Logical catalog profile reference",
    )
    compute: str = Field(
        default=DEFAULT_PROFILE_NAME,
        pattern=PROFILE_NAME_PATTERN,
        description="Logical compute profile reference",
    )
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
    orchestration: OrchestrationConfig | None = Field(
        default=None,
        description="Declarative orchestration configuration (Feature 010)",
    )

    @classmethod
    def from_yaml(cls, path: str | Path) -> FloeSpec:
        """Load and validate FloeSpec from a YAML file.

        Performs credential scanning using detect-secrets before parsing
        to prevent accidental exposure of secrets in floe.yaml files.

        Args:
            path: Path to floe.yaml file.

        Returns:
            Validated FloeSpec instance.

        Raises:
            FileNotFoundError: If file doesn't exist.
            yaml.YAMLError: If YAML syntax is invalid.
            ValidationError: If schema validation fails.
            CredentialDetectedError: If credentials are detected in the file.

        Example:
            >>> spec = FloeSpec.from_yaml("floe.yaml")
            >>> spec.name
            'my-pipeline'
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        # T046: Scan file for credentials before parsing
        _scan_file_for_credentials(path)

        with path.open("r") as f:
            data: dict[str, Any] = yaml.safe_load(f)

        return cls.model_validate(data)


def _scan_file_for_credentials(path: Path) -> None:
    """Scan a YAML file for credentials using detect-secrets.

    This function scans the entire file content to catch any secrets
    that might be embedded in any field, not just profile references.

    Args:
        path: Path to the file to scan.

    Raises:
        CredentialDetectedError: If credentials are detected.
    """
    content = path.read_text()
    detected = detect_credentials_in_string(content)

    if detected:
        raise CredentialDetectedError(
            field_name=f"file '{path.name}'",
            secret_type=detected[0].secret_type,
        )
