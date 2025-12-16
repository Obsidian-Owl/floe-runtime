"""OpenLineage configuration.

T055: [US3] Create OpenLineageConfig model
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OpenLineageConfig(BaseModel):
    """Configuration for OpenLineage lineage tracking.

    When endpoint is None, OpenLineage is disabled (graceful degradation).
    This allows pipelines to run without requiring a lineage backend.

    Attributes:
        endpoint: OpenLineage backend URL (None = disabled)
        namespace: Job namespace for lineage events
        producer: Producer identifier in lineage events
        async_transport: Use async HTTP transport (non-blocking)
        timeout: HTTP timeout in seconds

    Example:
        >>> config = OpenLineageConfig(
        ...     endpoint="http://localhost:5000/api/v1/lineage",
        ...     namespace="analytics",
        ... )
        >>> config.enabled
        True

        >>> disabled_config = OpenLineageConfig()
        >>> disabled_config.enabled
        False
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    endpoint: str | None = Field(
        default=None,
        description="OpenLineage backend URL (None = disabled)",
    )
    namespace: str = Field(
        default="floe",
        min_length=1,
        max_length=255,
        description="Job namespace for lineage events",
    )
    producer: str = Field(
        default="floe-dagster",
        description="Producer identifier in lineage events",
    )
    async_transport: bool = Field(
        default=True,
        description="Use async HTTP transport (non-blocking)",
    )
    timeout: float = Field(
        default=5.0,
        ge=0.1,
        le=60.0,
        description="HTTP timeout in seconds",
    )

    @property
    def enabled(self) -> bool:
        """Check if OpenLineage is enabled.

        Returns:
            True if endpoint is configured, False otherwise.
        """
        return self.endpoint is not None

    @classmethod
    def from_artifacts(cls, artifacts: dict[str, Any]) -> "OpenLineageConfig":
        """Create OpenLineageConfig from CompiledArtifacts dictionary.

        Extracts lineage configuration from the observability section
        of CompiledArtifacts.

        Args:
            artifacts: CompiledArtifacts dictionary.

        Returns:
            OpenLineageConfig with values from artifacts or defaults.

        Example:
            >>> artifacts = {
            ...     "observability": {
            ...         "lineage": {
            ...             "endpoint": "http://localhost:5000",
            ...             "namespace": "production",
            ...         }
            ...     }
            ... }
            >>> config = OpenLineageConfig.from_artifacts(artifacts)
            >>> config.namespace
            'production'
        """
        observability = artifacts.get("observability", {})
        lineage_config = observability.get("lineage", {})

        return cls(
            endpoint=lineage_config.get("endpoint"),
            namespace=lineage_config.get("namespace", "floe"),
            producer=lineage_config.get("producer", "floe-dagster"),
            async_transport=lineage_config.get("async_transport", True),
            timeout=lineage_config.get("timeout", 5.0),
        )
