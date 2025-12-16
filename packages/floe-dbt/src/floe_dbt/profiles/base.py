"""Base profile generator infrastructure for floe-dbt.

T008: Create ProfileGenerator Protocol
T009: Create ProfileGeneratorConfig model

This module defines the abstract contract for profile generators
and shared configuration used by all target-specific implementations.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProfileGeneratorConfig(BaseModel):
    """Configuration for dbt profile generation.

    Controls the profile and target names used in generated profiles.yml,
    plus threading configuration for dbt execution.

    Attributes:
        profile_name: Name of the dbt profile. Must be alphanumeric with underscores.
        target_name: Name of the target within the profile. Must be alphanumeric with underscores.
        threads: Number of dbt threads for parallel model execution.

    Example:
        >>> config = ProfileGeneratorConfig(
        ...     profile_name="floe",
        ...     target_name="dev",
        ...     threads=4
        ... )
        >>> config.profile_name
        'floe'
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    profile_name: str = Field(
        default="floe",
        min_length=1,
        max_length=100,
        description="Name of the dbt profile",
    )
    target_name: str = Field(
        default="dev",
        min_length=1,
        max_length=100,
        description="Name of the target within profile",
    )
    threads: int = Field(
        default=4,
        ge=1,
        le=64,
        description="Number of dbt threads",
    )

    @field_validator("profile_name", "target_name")
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
