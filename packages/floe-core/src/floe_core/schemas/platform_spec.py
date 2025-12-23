"""Platform specification models for floe-runtime.

This module defines the platform.yaml schema including:
- PlatformSpec: Root platform specification model
- Environment-specific configuration
- Profile references (storage, catalog, compute)
- Observability configuration
- Infrastructure configuration (network, cloud) - v1.1.0
- Security configuration (auth, authz, secrets) - v1.1.0
- Governance configuration (classification, compliance) - v1.1.0

Covers: 009-US2 (Enterprise Platform Configuration)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from floe_core.schemas.catalog_profile import CatalogProfile
from floe_core.schemas.compute_profile import ComputeProfile
from floe_core.schemas.governance_config import EnterpriseGovernanceConfig
from floe_core.schemas.infrastructure_config import InfrastructureConfig
from floe_core.schemas.observability import ObservabilityConfig
from floe_core.schemas.security_config import SecurityConfig
from floe_core.schemas.storage_profile import StorageProfile

# Supported environment types
ENVIRONMENT_TYPES = frozenset({"local", "dev", "staging", "prod"})

# Platform spec version for schema compatibility
# v1.0.0: Initial release (storage, catalogs, compute, observability)
# v1.1.0: Enterprise features (infrastructure, security, governance)
PLATFORM_SPEC_VERSION = "1.1.0"

# Pattern for valid profile names
PROFILE_NAME_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_-]*$"


class PlatformSpec(BaseModel):
    """Platform infrastructure configuration.

    This is the root model for platform.yaml files. It contains
    named profiles for storage, catalogs, and compute resources,
    plus enterprise configuration for infrastructure, security,
    and governance.

    Platform engineers define this configuration, which is then
    referenced by FloeSpec (floe.yaml) using logical profile names.

    Schema Version History:
        v1.0.0: Initial release (storage, catalogs, compute, observability)
        v1.1.0: Enterprise features (infrastructure, security, governance)

    Attributes:
        version: Schema version for forward compatibility.
        infrastructure: Network, DNS, and cloud configuration (v1.1.0).
        security: Authentication, authorization, secrets (v1.1.0).
        governance: Classification, retention, compliance (v1.1.0).
        storage: Named storage profiles (S3, MinIO, etc.).
        catalogs: Named catalog profiles (Polaris, Glue, etc.).
        compute: Named compute profiles (DuckDB, Snowflake, etc.).
        observability: Observability configuration (traces, lineage).

    Example:
        >>> spec = PlatformSpec.from_yaml(Path("platform/local/platform.yaml"))
        >>> spec.catalogs["default"].uri
        'http://polaris:8181/api/catalog'

        >>> spec = PlatformSpec(
        ...     storage={"default": StorageProfile(bucket="iceberg-data")},
        ...     catalogs={"default": CatalogProfile(
        ...         uri="http://polaris:8181/api/catalog",
        ...         warehouse="demo",
        ...     )},
        ... )

        >>> # v1.1.0 with enterprise features
        >>> spec = PlatformSpec(
        ...     version="1.1.0",
        ...     infrastructure=InfrastructureConfig(),
        ...     security=SecurityConfig(),
        ...     governance=EnterpriseGovernanceConfig(),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(
        default=PLATFORM_SPEC_VERSION,
        pattern=r"^\d+\.\d+\.\d+$",
        description="Schema version (semver)",
    )

    # v1.1.0: Enterprise configuration sections (optional for backward compatibility)
    infrastructure: InfrastructureConfig | None = Field(
        default=None,
        description="Infrastructure configuration (network, cloud) - v1.1.0",
    )
    security: SecurityConfig | None = Field(
        default=None,
        description="Security configuration (auth, authz, secrets) - v1.1.0",
    )
    governance: EnterpriseGovernanceConfig | None = Field(
        default=None,
        description="Governance configuration (classification, compliance) - v1.1.0",
    )

    # v1.0.0: Core profile configuration
    storage: dict[str, StorageProfile] = Field(
        default_factory=dict,
        description="Named storage profiles",
    )
    catalogs: dict[str, CatalogProfile] = Field(
        default_factory=dict,
        description="Named catalog profiles",
    )
    compute: dict[str, ComputeProfile] = Field(
        default_factory=dict,
        description="Named compute profiles",
    )
    observability: ObservabilityConfig | None = Field(
        default=None,
        description="Observability configuration",
    )

    @field_validator("storage", "catalogs", "compute", mode="before")
    @classmethod
    def validate_profile_names(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate that profile names match the required pattern."""
        import re

        for name in v:
            if not re.match(PROFILE_NAME_PATTERN, name):
                raise ValueError(
                    f"Invalid profile name '{name}'. "
                    f"Names must match pattern: {PROFILE_NAME_PATTERN}"
                )
        return v

    @classmethod
    def from_yaml(cls, path: Path) -> PlatformSpec:
        """Load PlatformSpec from YAML file.

        Args:
            path: Path to the platform.yaml file.

        Returns:
            Parsed and validated PlatformSpec.

        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If YAML is invalid or validation fails.

        Example:
            >>> spec = PlatformSpec.from_yaml(Path("platform/local/platform.yaml"))
        """
        if not path.exists():
            raise FileNotFoundError(f"Platform spec not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        if data is None:
            data = {}

        return cls.model_validate(data)

    def get_storage_profile(self, name: str = "default") -> StorageProfile:
        """Get a storage profile by name.

        Args:
            name: Profile name (default: "default").

        Returns:
            StorageProfile for the given name.

        Raises:
            KeyError: If profile not found.
        """
        if name not in self.storage:
            raise KeyError(
                f"Storage profile '{name}' not found. "
                f"Available profiles: {list(self.storage.keys())}"
            )
        return self.storage[name]

    def get_catalog_profile(self, name: str = "default") -> CatalogProfile:
        """Get a catalog profile by name.

        Args:
            name: Profile name (default: "default").

        Returns:
            CatalogProfile for the given name.

        Raises:
            KeyError: If profile not found.
        """
        if name not in self.catalogs:
            raise KeyError(
                f"Catalog profile '{name}' not found. "
                f"Available profiles: {list(self.catalogs.keys())}"
            )
        return self.catalogs[name]

    def get_compute_profile(self, name: str = "default") -> ComputeProfile:
        """Get a compute profile by name.

        Args:
            name: Profile name (default: "default").

        Returns:
            ComputeProfile for the given name.

        Raises:
            KeyError: If profile not found.
        """
        if name not in self.compute:
            raise KeyError(
                f"Compute profile '{name}' not found. "
                f"Available profiles: {list(self.compute.keys())}"
            )
        return self.compute[name]
