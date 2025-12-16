"""Unit tests for OpenLineageConfig model.

T051: [US3] Unit tests for OpenLineageConfig model
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestOpenLineageConfig:
    """Tests for OpenLineageConfig model."""

    def test_create_with_defaults(self) -> None:
        """Test creating config with default values."""
        from floe_dagster.lineage.config import OpenLineageConfig

        config = OpenLineageConfig()

        assert config.endpoint is None
        assert config.namespace == "floe"
        assert config.producer == "floe-dagster"
        assert config.async_transport is True
        assert config.timeout == 5.0

    def test_create_with_endpoint(self) -> None:
        """Test creating config with OpenLineage endpoint."""
        from floe_dagster.lineage.config import OpenLineageConfig

        config = OpenLineageConfig(
            endpoint="http://localhost:5000/api/v1/lineage",
        )

        assert config.endpoint == "http://localhost:5000/api/v1/lineage"

    def test_create_with_all_fields(self) -> None:
        """Test creating config with all fields specified."""
        from floe_dagster.lineage.config import OpenLineageConfig

        config = OpenLineageConfig(
            endpoint="https://lineage.example.com/api/v1/lineage",
            namespace="production",
            producer="my-pipeline",
            async_transport=False,
            timeout=10.0,
        )

        assert config.endpoint == "https://lineage.example.com/api/v1/lineage"
        assert config.namespace == "production"
        assert config.producer == "my-pipeline"
        assert config.async_transport is False
        assert config.timeout == 10.0

    def test_enabled_property_when_endpoint_set(self) -> None:
        """Test enabled property returns True when endpoint is set."""
        from floe_dagster.lineage.config import OpenLineageConfig

        config = OpenLineageConfig(
            endpoint="http://localhost:5000/api/v1/lineage",
        )

        assert config.enabled is True

    def test_enabled_property_when_endpoint_none(self) -> None:
        """Test enabled property returns False when endpoint is None."""
        from floe_dagster.lineage.config import OpenLineageConfig

        config = OpenLineageConfig()

        assert config.enabled is False

    def test_config_is_frozen(self) -> None:
        """Test OpenLineageConfig is immutable."""
        from floe_dagster.lineage.config import OpenLineageConfig

        config = OpenLineageConfig()

        with pytest.raises((ValidationError, TypeError, AttributeError)):
            config.namespace = "different"  # type: ignore[misc]

    def test_config_forbids_extra_fields(self) -> None:
        """Test extra fields are rejected."""
        from floe_dagster.lineage.config import OpenLineageConfig

        with pytest.raises(ValidationError) as exc_info:
            OpenLineageConfig(
                endpoint="http://localhost:5000",
                extra_field="not allowed",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower()

    def test_namespace_validation_min_length(self) -> None:
        """Test namespace must have minimum length."""
        from floe_dagster.lineage.config import OpenLineageConfig

        with pytest.raises(ValidationError) as exc_info:
            OpenLineageConfig(namespace="")

        assert "namespace" in str(exc_info.value).lower()

    def test_namespace_validation_max_length(self) -> None:
        """Test namespace must not exceed max length."""
        from floe_dagster.lineage.config import OpenLineageConfig

        with pytest.raises(ValidationError) as exc_info:
            OpenLineageConfig(namespace="a" * 256)  # Exceeds 255 char limit

        assert "namespace" in str(exc_info.value).lower()

    def test_timeout_validation_min(self) -> None:
        """Test timeout must be at least 0.1 seconds."""
        from floe_dagster.lineage.config import OpenLineageConfig

        with pytest.raises(ValidationError) as exc_info:
            OpenLineageConfig(timeout=0.05)

        assert "timeout" in str(exc_info.value).lower()

    def test_timeout_validation_max(self) -> None:
        """Test timeout must not exceed 60 seconds."""
        from floe_dagster.lineage.config import OpenLineageConfig

        with pytest.raises(ValidationError) as exc_info:
            OpenLineageConfig(timeout=120.0)

        assert "timeout" in str(exc_info.value).lower()

    def test_endpoint_accepts_http_url(self) -> None:
        """Test endpoint accepts HTTP URLs."""
        from floe_dagster.lineage.config import OpenLineageConfig

        config = OpenLineageConfig(
            endpoint="http://localhost:5000/api/v1/lineage",
        )

        assert str(config.endpoint).startswith("http://")

    def test_endpoint_accepts_https_url(self) -> None:
        """Test endpoint accepts HTTPS URLs."""
        from floe_dagster.lineage.config import OpenLineageConfig

        config = OpenLineageConfig(
            endpoint="https://lineage.example.com/api/v1/lineage",
        )

        assert str(config.endpoint).startswith("https://")

    def test_from_compiled_artifacts(self) -> None:
        """Test creating config from CompiledArtifacts dict."""
        from floe_dagster.lineage.config import OpenLineageConfig

        artifacts = {
            "observability": {
                "lineage": {
                    "endpoint": "http://localhost:5000/api/v1/lineage",
                    "namespace": "analytics",
                    "producer": "floe",
                }
            }
        }

        config = OpenLineageConfig.from_artifacts(artifacts)

        assert config.endpoint == "http://localhost:5000/api/v1/lineage"
        assert config.namespace == "analytics"
        assert config.producer == "floe"

    def test_from_compiled_artifacts_defaults(self) -> None:
        """Test creating config from artifacts with missing fields."""
        from floe_dagster.lineage.config import OpenLineageConfig

        # Empty artifacts = default config (disabled)
        artifacts: dict[str, object] = {}

        config = OpenLineageConfig.from_artifacts(artifacts)

        assert config.endpoint is None
        assert config.enabled is False

    def test_from_compiled_artifacts_partial(self) -> None:
        """Test creating config from artifacts with partial fields."""
        from floe_dagster.lineage.config import OpenLineageConfig

        artifacts = {
            "observability": {
                "lineage": {
                    "endpoint": "http://localhost:5000",
                    # Other fields should use defaults
                }
            }
        }

        config = OpenLineageConfig.from_artifacts(artifacts)

        assert config.endpoint == "http://localhost:5000"
        assert config.namespace == "floe"  # Default
        assert config.producer == "floe-dagster"  # Default
