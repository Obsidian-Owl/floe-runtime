"""Base profile generator infrastructure for floe-dbt.

T008: Create ProfileGenerator Protocol
T009: Create ProfileGeneratorConfig model
T080: [US5] Add environment-aware target name generation

This module defines the abstract contract for profile generators
and shared configuration used by all target-specific implementations.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Protocol, Self, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProfileGeneratorConfig(BaseModel):
    """Configuration for dbt profile generation.

    Controls the profile and target names used in generated profiles.yml,
    plus threading configuration for dbt execution. Supports multi-environment
    deployments with environment-specific secret references.

    Attributes:
        profile_name: Name of the dbt profile. Must be alphanumeric with underscores.
        target_name: Name of the target within the profile. Defaults to environment.
        environment: Deployment environment (dev, staging, prod, etc.).
        threads: Number of dbt threads for parallel model execution.

    Example:
        >>> config = ProfileGeneratorConfig(
        ...     profile_name="floe",
        ...     environment="production",
        ...     threads=4
        ... )
        >>> config.target_name
        'production'
        >>> config.get_secret_env_var("SNOWFLAKE", "PASSWORD")
        "{{ env_var('SNOWFLAKE_PRODUCTION_PASSWORD') }}"
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_name: str = Field(
        default="floe",
        min_length=1,
        max_length=100,
        description="Name of the dbt profile",
    )
    target_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Name of the target within profile (defaults to environment)",
    )
    environment: str = Field(
        default="dev",
        min_length=1,
        max_length=100,
        description="Deployment environment (dev, staging, prod, etc.)",
    )
    threads: int = Field(
        default=4,
        ge=1,
        le=64,
        description="Number of dbt threads",
    )

    @field_validator("profile_name", "environment")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Validate identifier is alphanumeric with underscores only.

        Args:
            v: The identifier value to validate.

        Returns:
            The validated identifier.

        Raises:
            ValueError: If identifier contains invalid characters.
        """
        if not v.replace("_", "").isalnum():
            raise ValueError("Must be alphanumeric with underscores only")
        return v

    @field_validator("target_name")
    @classmethod
    def validate_target_name(cls, v: str | None) -> str | None:
        """Validate target_name if provided.

        Args:
            v: The target_name value to validate.

        Returns:
            The validated target_name or None.

        Raises:
            ValueError: If target_name contains invalid characters.
        """
        if v is not None and not v.replace("_", "").isalnum():
            raise ValueError("Must be alphanumeric with underscores only")
        return v

    @model_validator(mode="after")
    def set_target_name_from_environment(self) -> Self:
        """Set target_name to environment if not explicitly specified.

        Returns:
            Self with target_name set.
        """
        if self.target_name is None:
            # Use object.__setattr__ since model is frozen
            object.__setattr__(self, "target_name", self.environment)
        return self

    def get_secret_env_var(self, service: str, secret_name: str) -> str:
        """Generate environment-prefixed secret env_var reference.

        Creates a dbt env_var() template string with environment prefix
        for multi-environment secret management.

        Args:
            service: Service name (e.g., "SNOWFLAKE", "REDSHIFT").
            secret_name: Secret name (e.g., "USER", "PASSWORD").

        Returns:
            dbt env_var template string.

        Example:
            >>> config = ProfileGeneratorConfig(environment="prod")
            >>> config.get_secret_env_var("SNOWFLAKE", "PASSWORD")
            "{{ env_var('SNOWFLAKE_PROD_PASSWORD') }}"
        """
        env_upper = self.environment.upper()
        return f"{{{{ env_var('{service}_{env_upper}_{secret_name}') }}}}"

    @classmethod
    def from_artifacts(cls, artifacts: dict[str, Any]) -> "ProfileGeneratorConfig":
        """Create ProfileGeneratorConfig from CompiledArtifacts.

        Extracts environment from environment_context if present,
        and allows custom target name override.

        Args:
            artifacts: CompiledArtifacts dictionary.

        Returns:
            ProfileGeneratorConfig instance.

        Example:
            >>> artifacts = {
            ...     "environment_context": {"environment": "production"},
            ... }
            >>> config = ProfileGeneratorConfig.from_artifacts(artifacts)
            >>> config.environment
            'production'
        """
        env_context = artifacts.get("environment_context") or {}
        environment = env_context.get("environment", "dev")

        # Allow custom target name override
        target_name = artifacts.get("dbt_target_name")

        return cls(
            environment=environment,
            target_name=target_name,
        )


@runtime_checkable
class ProfileGenerator(Protocol):
    """Protocol defining the interface for target-specific profile generators.

    Each compute target (DuckDB, Snowflake, BigQuery, etc.) implements this
    protocol to generate target-appropriate dbt profile configurations.

    The generate method receives CompiledArtifacts and returns a dictionary
    that forms the 'outputs' section of profiles.yml.

    Example implementation:
        >>> class DuckDBProfileGenerator:
        ...     def generate(
        ...         self,
        ...         artifacts: CompiledArtifacts,
        ...         config: ProfileGeneratorConfig,
        ...     ) -> dict[str, Any]:
        ...         return {
        ...             config.target_name: {
        ...                 "type": "duckdb",
        ...                 "path": artifacts.compute.properties.get("path", ":memory:"),
        ...                 "threads": config.threads,
        ...             }
        ...         }
    """

    @abstractmethod
    def generate(
        self,
        artifacts: "CompiledArtifacts",
        config: ProfileGeneratorConfig,
    ) -> dict[str, Any]:
        """Generate dbt profile configuration for this target.

        Args:
            artifacts: Compiled artifacts containing compute configuration.
            config: Profile generator configuration (names, threads).

        Returns:
            Dictionary containing the target configuration for profiles.yml.
            The returned dict should be the 'outputs' section content:
            {
                "<target_name>": {
                    "type": "<adapter>",
                    # target-specific fields...
                }
            }

        Raises:
            ProfileGenerationError: If generation fails due to missing
                required configuration or invalid values.
        """
        ...


# Type alias for forward reference to avoid circular import
# Actual type is floe_core.compiler.models.CompiledArtifacts
CompiledArtifacts = Any  # noqa: N816
