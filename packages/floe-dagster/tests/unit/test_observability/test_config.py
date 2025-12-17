"""Unit tests for TracingConfig model.

T068: [US4] Unit tests for TracingConfig model
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestTracingConfig:
    """Tests for TracingConfig model."""

    def test_create_with_defaults(self) -> None:
        """Test creating config with default values."""
        from floe_dagster.observability.config import TracingConfig

        config = TracingConfig()

        assert config.endpoint is None
        assert config.service_name == "floe-dagster"
        assert config.attributes == {}
        assert config.batch_export is True

    def test_create_with_endpoint(self) -> None:
        """Test creating config with OTLP endpoint."""
        from floe_dagster.observability.config import TracingConfig

        config = TracingConfig(
            endpoint="http://localhost:4317",
        )

        assert config.endpoint == "http://localhost:4317"

    def test_create_with_all_fields(self) -> None:
        """Test creating config with all fields specified."""
        from floe_dagster.observability.config import TracingConfig

        config = TracingConfig(
            endpoint="http://otel-collector:4317",
            service_name="my-pipeline",
            attributes={"environment": "production", "tenant": "acme"},
            batch_export=False,
        )

        assert config.endpoint == "http://otel-collector:4317"
        assert config.service_name == "my-pipeline"
        assert config.attributes == {"environment": "production", "tenant": "acme"}
        assert config.batch_export is False

    def test_enabled_property_when_endpoint_set(self) -> None:
        """Test enabled property returns True when endpoint is set."""
        from floe_dagster.observability.config import TracingConfig

        config = TracingConfig(
            endpoint="http://localhost:4317",
        )

        assert config.enabled is True

    def test_enabled_property_when_endpoint_none(self) -> None:
        """Test enabled property returns False when endpoint is None."""
        from floe_dagster.observability.config import TracingConfig

        config = TracingConfig()

        assert config.enabled is False

    def test_config_is_frozen(self) -> None:
        """Test TracingConfig is immutable."""
        from floe_dagster.observability.config import TracingConfig

        config = TracingConfig()

        with pytest.raises((ValidationError, TypeError, AttributeError)):
            config.service_name = "different"  # type: ignore[misc]

    def test_config_forbids_extra_fields(self) -> None:
        """Test extra fields are rejected."""
        from floe_dagster.observability.config import TracingConfig

        with pytest.raises(ValidationError) as exc_info:
            TracingConfig(
                endpoint="http://localhost:4317",
                extra_field="not allowed",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower()

    def test_service_name_validation_min_length(self) -> None:
        """Test service_name must have minimum length."""
        from floe_dagster.observability.config import TracingConfig

        with pytest.raises(ValidationError) as exc_info:
            TracingConfig(service_name="")

        assert "service_name" in str(exc_info.value).lower()

    def test_service_name_validation_max_length(self) -> None:
        """Test service_name must not exceed max length."""
        from floe_dagster.observability.config import TracingConfig

        with pytest.raises(ValidationError) as exc_info:
            TracingConfig(service_name="a" * 256)  # Exceeds 255 char limit

        assert "service_name" in str(exc_info.value).lower()

    def test_attributes_default_factory(self) -> None:
        """Test attributes uses default_factory for mutable default."""
        from floe_dagster.observability.config import TracingConfig

        config1 = TracingConfig()
        config2 = TracingConfig()

        # Should be different dict instances
        assert config1.attributes is not config2.attributes
        # Both should be empty dicts
        assert config1.attributes == {}
        assert config2.attributes == {}

    def test_from_compiled_artifacts(self) -> None:
        """Test creating config from CompiledArtifacts dict."""
        from floe_dagster.observability.config import TracingConfig

        artifacts = {
            "observability": {
                "tracing": {
                    "endpoint": "http://localhost:4317",
                    "service_name": "analytics-pipeline",
                    "attributes": {"env": "prod"},
                    "batch_export": False,
                }
            }
        }

        config = TracingConfig.from_artifacts(artifacts)

        assert config.endpoint == "http://localhost:4317"
        assert config.service_name == "analytics-pipeline"
        assert config.attributes == {"env": "prod"}
        assert config.batch_export is False

    def test_from_compiled_artifacts_defaults(self) -> None:
        """Test creating config from artifacts with missing fields."""
        from floe_dagster.observability.config import TracingConfig

        # Empty artifacts = default config (disabled)
        artifacts: dict[str, object] = {}

        config = TracingConfig.from_artifacts(artifacts)

        assert config.endpoint is None
        assert config.enabled is False

    def test_from_compiled_artifacts_partial(self) -> None:
        """Test creating config from artifacts with partial fields."""
        from floe_dagster.observability.config import TracingConfig

        artifacts = {
            "observability": {
                "tracing": {
                    "endpoint": "http://localhost:4317",
                    # Other fields should use defaults
                }
            }
        }

        config = TracingConfig.from_artifacts(artifacts)

        assert config.endpoint == "http://localhost:4317"
        assert config.service_name == "floe-dagster"  # Default
        assert config.batch_export is True  # Default
