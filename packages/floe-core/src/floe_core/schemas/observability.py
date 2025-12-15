"""Observability configuration models for floe-runtime.

T028: [US1] Implement ObservabilityConfig with attributes dict

This module defines configuration for OpenTelemetry and OpenLineage.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ObservabilityConfig(BaseModel):
    """Configuration for observability.

    Enables OpenTelemetry traces and metrics, plus OpenLineage
    for data lineage tracking.

    Attributes:
        traces: Enable OpenTelemetry traces.
        metrics: Enable metrics collection.
        lineage: Enable OpenLineage emission.
        otlp_endpoint: OTLP exporter endpoint.
        lineage_endpoint: OpenLineage API endpoint.
        attributes: Custom trace attributes (service.name, etc.)

    Example:
        >>> config = ObservabilityConfig(
        ...     traces=True,
        ...     otlp_endpoint="http://otel-collector:4317",
        ...     attributes={"service.name": "my-pipeline"}
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    traces: bool = Field(
        default=True,
        description="Enable OpenTelemetry traces",
    )
    metrics: bool = Field(
        default=True,
        description="Enable metrics collection",
    )
    lineage: bool = Field(
        default=True,
        description="Enable OpenLineage emission",
    )
    otlp_endpoint: str | None = Field(
        default=None,
        description="OTLP exporter endpoint",
    )
    lineage_endpoint: str | None = Field(
        default=None,
        description="OpenLineage API endpoint",
    )
    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Custom trace attributes",
    )
