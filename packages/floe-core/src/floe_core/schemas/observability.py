"""Observability configuration models for floe-runtime.

T028: [US1] Implement ObservabilityConfig with attributes dict
Covers: 009-US2 (Extended Observability: Tracing, Metrics, Logging)

This module defines configuration for OpenTelemetry and OpenLineage,
extended with enterprise tracing sampling, metrics exporters, and logging backends.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class SamplingType(str, Enum):
    """Trace sampling strategy types.

    Values:
        ALWAYS_ON: Sample all traces (development).
        ALWAYS_OFF: Sample no traces (disable tracing).
        PROBABILISTIC: Sample percentage of traces.
        RATE_LIMITING: Sample up to N traces per second.
    """

    ALWAYS_ON = "always_on"
    ALWAYS_OFF = "always_off"
    PROBABILISTIC = "probabilistic"
    RATE_LIMITING = "rate_limiting"


class LogLevel(str, Enum):
    """Logging verbosity levels.

    Values:
        DEBUG: Detailed debugging information.
        INFO: General operational information.
        WARNING: Warning messages.
        ERROR: Error messages only.
        CRITICAL: Critical errors only.
    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Log output format.

    Values:
        JSON: Structured JSON logging (recommended for production).
        TEXT: Human-readable text format (development).
    """

    JSON = "json"
    TEXT = "text"


class AlertSeverity(str, Enum):
    """Alert severity levels.

    Values:
        INFO: Informational alerts.
        WARNING: Warning alerts.
        CRITICAL: Critical alerts requiring immediate action.
    """

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# =============================================================================
# Tracing Configuration
# =============================================================================


class TraceSamplingConfig(BaseModel):
    """Trace sampling configuration.

    Controls what percentage of traces are collected.

    Attributes:
        sampling_type: Sampling strategy.
        probability: Sample probability (0.0 to 1.0) for probabilistic sampling.
        rate_limit: Max traces per second for rate limiting.

    Example:
        >>> sampling = TraceSamplingConfig(
        ...     sampling_type=SamplingType.PROBABILISTIC,
        ...     probability=0.1,  # 10% of traces
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    sampling_type: SamplingType = Field(
        default=SamplingType.ALWAYS_ON,
        description="Sampling strategy",
    )
    probability: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Sample probability (0.0 to 1.0)",
    )
    rate_limit: int | None = Field(
        default=None,
        ge=1,
        description="Max traces per second for rate limiting",
    )


class TraceExportersConfig(BaseModel):
    """Trace exporters configuration.

    Attributes:
        jaeger: Enable Jaeger exporter.
        xray: Enable AWS X-Ray exporter.
        otlp: Enable generic OTLP exporter.

    Example:
        >>> exporters = TraceExportersConfig(
        ...     jaeger=True,
        ...     xray=False,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    jaeger: bool = Field(
        default=True,
        description="Enable Jaeger exporter",
    )
    xray: bool = Field(
        default=False,
        description="Enable AWS X-Ray exporter",
    )
    otlp: bool = Field(
        default=False,
        description="Enable generic OTLP exporter",
    )


class TracingConfig(BaseModel):
    """Extended tracing configuration.

    Attributes:
        sampling: Trace sampling configuration.
        exporters: Trace exporter configuration.

    Example:
        >>> tracing = TracingConfig(
        ...     sampling=TraceSamplingConfig(
        ...         sampling_type=SamplingType.PROBABILISTIC,
        ...         probability=0.1,
        ...     ),
        ...     exporters=TraceExportersConfig(jaeger=True),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    sampling: TraceSamplingConfig = Field(
        default_factory=TraceSamplingConfig,
        description="Trace sampling configuration",
    )
    exporters: TraceExportersConfig = Field(
        default_factory=TraceExportersConfig,
        description="Trace exporter configuration",
    )


# =============================================================================
# Metrics Configuration
# =============================================================================


class MetricsExportersConfig(BaseModel):
    """Metrics exporters configuration.

    Attributes:
        prometheus: Enable Prometheus exporter.
        cloudwatch: Enable AWS CloudWatch Metrics.
        statsd: Enable StatsD exporter.

    Example:
        >>> exporters = MetricsExportersConfig(
        ...     prometheus=True,
        ...     cloudwatch=False,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    prometheus: bool = Field(
        default=True,
        description="Enable Prometheus exporter",
    )
    cloudwatch: bool = Field(
        default=False,
        description="Enable AWS CloudWatch Metrics",
    )
    statsd: bool = Field(
        default=False,
        description="Enable StatsD exporter",
    )


class AlertRule(BaseModel):
    """Alerting rule definition.

    Attributes:
        severity: Alert severity level.
        notify: Notification channels.

    Example:
        >>> rule = AlertRule(
        ...     severity=AlertSeverity.CRITICAL,
        ...     notify=["slack", "pagerduty"],
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    severity: AlertSeverity = Field(
        default=AlertSeverity.WARNING,
        description="Alert severity level",
    )
    notify: list[str] = Field(
        default_factory=list,
        description="Notification channels",
    )


class MetricsAlertingConfig(BaseModel):
    """Metrics alerting configuration.

    Attributes:
        enabled: Enable alerting.
        rules: Named alert rules.

    Example:
        >>> alerting = MetricsAlertingConfig(
        ...     enabled=True,
        ...     rules={
        ...         "pipeline_failure": AlertRule(
        ...             severity=AlertSeverity.CRITICAL,
        ...             notify=["slack"],
        ...         ),
        ...     },
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable alerting",
    )
    rules: dict[str, AlertRule] = Field(
        default_factory=dict,
        description="Named alert rules",
    )


class MetricsConfig(BaseModel):
    """Extended metrics configuration.

    Attributes:
        scrape_interval: Prometheus scrape interval.
        retention_days: Metrics retention period.
        exporters: Metrics exporter configuration.
        alerting: Alerting configuration.

    Example:
        >>> metrics = MetricsConfig(
        ...     scrape_interval="15s",
        ...     retention_days=15,
        ...     exporters=MetricsExportersConfig(prometheus=True),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    scrape_interval: str = Field(
        default="15s",
        pattern=r"^\d+[smh]$",
        description="Prometheus scrape interval",
    )
    retention_days: int = Field(
        default=15,
        ge=1,
        le=365,
        description="Metrics retention period in days",
    )
    exporters: MetricsExportersConfig = Field(
        default_factory=MetricsExportersConfig,
        description="Metrics exporter configuration",
    )
    alerting: MetricsAlertingConfig = Field(
        default_factory=MetricsAlertingConfig,
        description="Alerting configuration",
    )


# =============================================================================
# Logging Configuration
# =============================================================================


class LoggingBackendsConfig(BaseModel):
    """Logging backends configuration.

    Attributes:
        loki: Enable Grafana Loki backend.
        cloudwatch: Enable AWS CloudWatch Logs.
        elasticsearch: Enable Elasticsearch backend.

    Example:
        >>> backends = LoggingBackendsConfig(
        ...     loki=True,
        ...     cloudwatch=False,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    loki: bool = Field(
        default=True,
        description="Enable Grafana Loki backend",
    )
    cloudwatch: bool = Field(
        default=False,
        description="Enable AWS CloudWatch Logs",
    )
    elasticsearch: bool = Field(
        default=False,
        description="Enable Elasticsearch backend",
    )


class LoggingConfig(BaseModel):
    """Extended logging configuration.

    Attributes:
        level: Default log level.
        log_format: Log output format.
        backends: Logging backend configuration.

    Example:
        >>> logging = LoggingConfig(
        ...     level=LogLevel.INFO,
        ...     log_format=LogFormat.JSON,
        ...     backends=LoggingBackendsConfig(loki=True),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Default log level",
    )
    log_format: LogFormat = Field(
        default=LogFormat.JSON,
        description="Log output format",
    )
    backends: LoggingBackendsConfig = Field(
        default_factory=LoggingBackendsConfig,
        description="Logging backend configuration",
    )


# =============================================================================
# Compute Logs Configuration
# =============================================================================


class ComputeLogManagerType(str, Enum):
    """Compute log manager backend types.

    Values:
        S3: Amazon S3 or S3-compatible storage (LocalStack, MinIO).
        AZURE_BLOB: Azure Blob Storage.
        GCS: Google Cloud Storage.
        LOCAL: Local filesystem storage.
        NOOP: Disable compute log storage (not recommended).
    """

    S3 = "s3"
    AZURE_BLOB = "azure_blob"
    GCS = "gcs"
    LOCAL = "local"
    NOOP = "noop"


class ComputeLogsConfig(BaseModel):
    """Dagster compute logs storage configuration.

    Platform-managed: Configured in platform.yaml observability section.
    Generates Dagster instance.yaml compute_logs configuration.

    Compute logs capture stdout/stderr from Dagster runs and store them
    in object storage for debugging and audit trails.

    Attributes:
        enabled: Enable compute log capture and storage.
        manager_type: Storage backend type.
        storage_ref: Reference to storage profile in platform.yaml.
        bucket: Override bucket name (defaults to storage profile bucket).
        prefix: S3 key prefix for log files.
        retention_days: Log retention period.
        local_dir: Local directory for log buffering.
        upload_interval: Upload interval in seconds.

    Example:
        >>> compute_logs = ComputeLogsConfig(
        ...     enabled=True,
        ...     manager_type=ComputeLogManagerType.S3,
        ...     storage_ref="default",
        ...     prefix="dagster-compute-logs/",
        ...     retention_days=30,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Enable compute log capture and storage",
    )
    manager_type: ComputeLogManagerType = Field(
        default=ComputeLogManagerType.S3,
        description="Storage backend type",
    )
    storage_ref: str | None = Field(
        default="default",
        description="Reference to storage profile in platform.yaml",
    )
    bucket: str | None = Field(
        default=None,
        description=(
            "Override bucket name (defaults to storage profile bucket with -compute-logs suffix)"
        ),
    )
    prefix: str = Field(
        default="dagster-compute-logs/",
        description="S3 key prefix for log files",
    )
    retention_days: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Log retention period in days",
    )
    local_dir: str = Field(
        default="/tmp/dagster-compute-logs",
        description="Local directory for log buffering before upload",
    )
    upload_interval: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Upload interval in seconds",
    )


# =============================================================================
# Observability Configuration (Root - Extended)
# =============================================================================


class ObservabilityConfig(BaseModel):
    """Configuration for observability.

    Enables OpenTelemetry traces and metrics, plus OpenLineage
    for data lineage tracking. Extended with enterprise tracing
    sampling, metrics exporters, logging backends, and compute log storage.

    Attributes:
        traces: Enable OpenTelemetry traces.
        metrics: Enable metrics collection.
        lineage: Enable OpenLineage emission.
        otlp_endpoint: OTLP exporter endpoint.
        lineage_endpoint: OpenLineage API endpoint.
        attributes: Custom trace attributes (service.name, etc.)
        tracing: Extended tracing configuration (sampling, exporters).
        metrics_config: Extended metrics configuration (exporters, alerting).
        logging: Extended logging configuration (backends, format).
        compute_logs: Dagster compute logs storage (platform-managed).

    Example:
        >>> config = ObservabilityConfig(
        ...     traces=True,
        ...     otlp_endpoint="http://otel-collector:4317",
        ...     attributes={"service.name": "my-pipeline"},
        ...     tracing=TracingConfig(
        ...         sampling=TraceSamplingConfig(probability=0.1),
        ...     ),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Original fields (backward compatible)
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

    # Extended fields (v1.1.0)
    tracing: TracingConfig | None = Field(
        default=None,
        description="Extended tracing configuration",
    )
    metrics_config: MetricsConfig | None = Field(
        default=None,
        description="Extended metrics configuration",
    )
    logging: LoggingConfig | None = Field(
        default=None,
        description="Extended logging configuration",
    )
    compute_logs: ComputeLogsConfig | None = Field(
        default=None,
        description="Dagster compute logs storage configuration (platform-managed)",
    )
