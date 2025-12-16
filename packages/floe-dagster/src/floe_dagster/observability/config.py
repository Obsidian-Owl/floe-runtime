"""OpenTelemetry tracing configuration.

T071: [US4] Create TracingConfig model
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TracingConfig(BaseModel):
    """Configuration for OpenTelemetry tracing.

    When endpoint is None, tracing uses NoOpTracerProvider (graceful degradation).
    This allows pipelines to run without requiring a tracing backend.

    Attributes:
        endpoint: OTLP endpoint URL (None = disabled)
        service_name: Service name for traces
        attributes: Default span attributes (e.g., tenant, environment)
        batch_export: Use batch span processor for efficiency

    Example:
        >>> config = TracingConfig(
        ...     endpoint="http://localhost:4317",
        ...     service_name="analytics-pipeline",
        ...     attributes={"environment": "production"},
        ... )
        >>> config.enabled
        True

        >>> disabled_config = TracingConfig()
        >>> disabled_config.enabled
        False
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    endpoint: str | None = Field(
        default=None,
        description="OTLP endpoint URL (None = disabled)",
    )
    service_name: str = Field(
        default="floe-dagster",
        min_length=1,
        max_length=255,
        description="Service name for traces",
    )
    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Default span attributes (e.g., tenant, environment)",
    )
    batch_export: bool = Field(
        default=True,
        description="Use batch span processor for efficiency",
    )

    @property
    def enabled(self) -> bool:
        """Check if tracing is enabled.

        Returns:
            True if endpoint is configured, False otherwise.
        """
        return self.endpoint is not None

    @classmethod
    def from_artifacts(cls, artifacts: dict[str, Any]) -> "TracingConfig":
        """Create TracingConfig from CompiledArtifacts dictionary.

        Extracts tracing configuration from the observability section
        of CompiledArtifacts.

        Args:
            artifacts: CompiledArtifacts dictionary.

        Returns:
            TracingConfig with values from artifacts or defaults.

        Example:
            >>> artifacts = {
            ...     "observability": {
            ...         "tracing": {
            ...             "endpoint": "http://localhost:4317",
            ...             "service_name": "my-pipeline",
            ...         }
            ...     }
            ... }
            >>> config = TracingConfig.from_artifacts(artifacts)
            >>> config.service_name
            'my-pipeline'
        """
        observability = artifacts.get("observability", {})
        tracing_config = observability.get("tracing", {})

        return cls(
            endpoint=tracing_config.get("endpoint"),
            service_name=tracing_config.get("service_name", "floe-dagster"),
            attributes=tracing_config.get("attributes", {}),
            batch_export=tracing_config.get("batch_export", True),
        )
