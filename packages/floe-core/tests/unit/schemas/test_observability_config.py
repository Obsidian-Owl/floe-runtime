"""Unit tests for ObservabilityConfig model.

T015: [US1] Unit tests for ObservabilityConfig defaults
Tests ObservabilityConfig with traces, metrics, lineage settings.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestObservabilityConfig:
    """Tests for ObservabilityConfig model."""

    def test_observability_config_default_values(self) -> None:
        """ObservabilityConfig should have correct defaults."""
        from floe_core.schemas import ObservabilityConfig

        config = ObservabilityConfig()
        assert config.traces is True
        assert config.metrics is True
        assert config.lineage is True
        assert config.otlp_endpoint is None
        assert config.lineage_endpoint is None
        assert config.attributes == {}

    def test_observability_config_traces_disabled(self) -> None:
        """ObservabilityConfig should accept traces=False."""
        from floe_core.schemas import ObservabilityConfig

        config = ObservabilityConfig(traces=False)
        assert config.traces is False

    def test_observability_config_metrics_disabled(self) -> None:
        """ObservabilityConfig should accept metrics=False."""
        from floe_core.schemas import ObservabilityConfig

        config = ObservabilityConfig(metrics=False)
        assert config.metrics is False

    def test_observability_config_lineage_disabled(self) -> None:
        """ObservabilityConfig should accept lineage=False."""
        from floe_core.schemas import ObservabilityConfig

        config = ObservabilityConfig(lineage=False)
        assert config.lineage is False

    def test_observability_config_otlp_endpoint(self) -> None:
        """ObservabilityConfig should accept otlp_endpoint."""
        from floe_core.schemas import ObservabilityConfig

        config = ObservabilityConfig(
            otlp_endpoint="http://otel-collector:4317",
        )
        assert config.otlp_endpoint == "http://otel-collector:4317"

    def test_observability_config_lineage_endpoint(self) -> None:
        """ObservabilityConfig should accept lineage_endpoint."""
        from floe_core.schemas import ObservabilityConfig

        config = ObservabilityConfig(
            lineage_endpoint="http://marquez:5000/api/v1/lineage",
        )
        assert config.lineage_endpoint == "http://marquez:5000/api/v1/lineage"

    def test_observability_config_attributes_empty_default(self) -> None:
        """ObservabilityConfig.attributes should default to empty dict."""
        from floe_core.schemas import ObservabilityConfig

        config = ObservabilityConfig()
        assert config.attributes == {}
        assert isinstance(config.attributes, dict)

    def test_observability_config_attributes_with_values(self) -> None:
        """ObservabilityConfig should accept custom attributes."""
        from floe_core.schemas import ObservabilityConfig

        config = ObservabilityConfig(
            attributes={
                "service.name": "floe-pipeline",
                "deployment.environment": "production",
            }
        )
        assert config.attributes["service.name"] == "floe-pipeline"
        assert config.attributes["deployment.environment"] == "production"

    def test_observability_config_attributes_string_values_only(self) -> None:
        """ObservabilityConfig.attributes should accept string values."""
        from floe_core.schemas import ObservabilityConfig

        config = ObservabilityConfig(
            attributes={
                "key1": "value1",
                "key2": "value2",
            }
        )
        assert all(isinstance(v, str) for v in config.attributes.values())

    def test_observability_config_all_disabled(self) -> None:
        """ObservabilityConfig should accept all features disabled."""
        from floe_core.schemas import ObservabilityConfig

        config = ObservabilityConfig(
            traces=False,
            metrics=False,
            lineage=False,
        )
        assert config.traces is False
        assert config.metrics is False
        assert config.lineage is False

    def test_observability_config_full_configuration(self) -> None:
        """ObservabilityConfig should accept full configuration."""
        from floe_core.schemas import ObservabilityConfig

        config = ObservabilityConfig(
            traces=True,
            metrics=True,
            lineage=True,
            otlp_endpoint="http://otel-collector:4317",
            lineage_endpoint="http://marquez:5000/api/v1/lineage",
            attributes={
                "service.name": "floe-pipeline",
                "deployment.environment": "staging",
            },
        )
        assert config.traces is True
        assert config.otlp_endpoint == "http://otel-collector:4317"
        assert config.lineage_endpoint == "http://marquez:5000/api/v1/lineage"
        assert config.attributes["service.name"] == "floe-pipeline"

    def test_observability_config_is_frozen(self) -> None:
        """ObservabilityConfig should be immutable."""
        from floe_core.schemas import ObservabilityConfig

        config = ObservabilityConfig()

        with pytest.raises(ValidationError):
            config.traces = False  # type: ignore[misc]

    def test_observability_config_rejects_extra_fields(self) -> None:
        """ObservabilityConfig should reject unknown fields."""
        from floe_core.schemas import ObservabilityConfig

        with pytest.raises(ValidationError) as exc_info:
            ObservabilityConfig(unknown_field="value")  # type: ignore[call-arg]

        assert "extra" in str(exc_info.value).lower()

    def test_observability_config_default_factory_isolation(self) -> None:
        """ObservabilityConfig defaults should be isolated (no shared state)."""
        from floe_core.schemas import ObservabilityConfig

        config1 = ObservabilityConfig()
        config2 = ObservabilityConfig()

        # Verify they are independent objects
        assert config1 is not config2
        assert config1.attributes is not config2.attributes
