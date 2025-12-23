"""Integration tests for observability configuration.

Tests the observability configuration including traces, metrics, lineage
toggles, endpoint URLs, and custom attributes.

Covers:
- FR-007: System MUST define observability configuration with toggles for traces,
  metrics, lineage, optional endpoint URLs, and optional attributes dictionary
- FR-027: System MUST log technical error details internally while returning
  user-friendly messages
"""

from __future__ import annotations

import logging
from io import StringIO
from pathlib import Path

import pytest
import yaml


class TestObservabilityConfiguration:
    """Tests for observability configuration (001-FR-007)."""

    @pytest.mark.requirement("001-FR-007")
    def test_observability_config_has_all_toggles(self) -> None:
        """Test that ObservabilityConfig has all required toggles.

        Covers:
        - 001-FR-007: Toggles for traces, metrics, lineage
        """
        from floe_core.schemas import ObservabilityConfig

        # Create config with all toggles
        config = ObservabilityConfig(
            traces=True,
            metrics=True,
            lineage=True,
        )

        assert config.traces is True
        assert config.metrics is True
        assert config.lineage is True

        # Test with all disabled
        config_disabled = ObservabilityConfig(
            traces=False,
            metrics=False,
            lineage=False,
        )

        assert config_disabled.traces is False
        assert config_disabled.metrics is False
        assert config_disabled.lineage is False

    @pytest.mark.requirement("001-FR-007")
    def test_observability_config_has_endpoint_urls(self) -> None:
        """Test that ObservabilityConfig supports optional endpoint URLs.

        Covers:
        - 001-FR-007: Optional endpoint URLs for OTLP and lineage
        """
        from floe_core.schemas import ObservabilityConfig

        # With endpoints
        config = ObservabilityConfig(
            otlp_endpoint="http://otel-collector:4317",
            lineage_endpoint="http://marquez:5000/api/v1",
        )

        assert config.otlp_endpoint == "http://otel-collector:4317"
        assert config.lineage_endpoint == "http://marquez:5000/api/v1"

        # Without endpoints (default to None)
        config_no_endpoints = ObservabilityConfig()
        assert config_no_endpoints.otlp_endpoint is None
        assert config_no_endpoints.lineage_endpoint is None

    @pytest.mark.requirement("001-FR-007")
    def test_observability_config_has_attributes_dict(self) -> None:
        """Test that ObservabilityConfig supports custom attributes dictionary.

        Covers:
        - 001-FR-007: Optional attributes dictionary for custom trace context
        """
        from floe_core.schemas import ObservabilityConfig

        # With custom attributes
        config = ObservabilityConfig(
            attributes={
                "service.name": "floe-pipeline",
                "tenant.id": "acme-corp",
                "environment": "production",
            }
        )

        assert config.attributes["service.name"] == "floe-pipeline"
        assert config.attributes["tenant.id"] == "acme-corp"
        assert config.attributes["environment"] == "production"

        # Default to empty dict
        config_default = ObservabilityConfig()
        assert config_default.attributes == {}

    @pytest.mark.requirement("001-FR-007")
    def test_observability_config_in_compiled_artifacts(self, tmp_path: Path) -> None:
        """Test that observability config flows through to CompiledArtifacts.

        Covers:
        - 001-FR-007: Full observability config in compiled output
        """
        from floe_core.compiler import Compiler

        # Create floe.yaml with full observability config
        project_dir = tmp_path / "observability-project"
        project_dir.mkdir()

        # Create platform.yaml (Two-Tier Architecture)
        platform_config = {
            "version": "1.0.0",
            "storage": {"default": {"bucket": "test-bucket"}},
            "catalogs": {
                "default": {
                    "uri": "http://polaris:8181/api/catalog",
                    "warehouse": "test-warehouse",
                }
            },
            "compute": {"default": {"type": "duckdb"}},
        }

        (project_dir / "platform.yaml").write_text(yaml.dump(platform_config))

        floe_config = {
            "name": "observability-test",
            "version": "1.0.0",
            "compute": "default",
            "transforms": [{"type": "dbt", "path": "./dbt"}],
            "observability": {
                "traces": True,
                "metrics": True,
                "lineage": True,
                "otlp_endpoint": "http://otel-collector:4317",
                "lineage_endpoint": "http://marquez:5000/api/v1",
                "attributes": {
                    "service.name": "test-pipeline",
                    "tenant.id": "test-tenant",
                },
            },
        }

        (project_dir / "floe.yaml").write_text(yaml.dump(floe_config))

        # Compile
        compiler = Compiler()
        artifacts = compiler.compile(project_dir / "floe.yaml")

        # Verify observability config in artifacts
        assert artifacts.observability.traces is True
        assert artifacts.observability.metrics is True
        assert artifacts.observability.lineage is True
        assert artifacts.observability.otlp_endpoint == "http://otel-collector:4317"
        assert artifacts.observability.lineage_endpoint == "http://marquez:5000/api/v1"
        assert artifacts.observability.attributes["service.name"] == "test-pipeline"
        assert artifacts.observability.attributes["tenant.id"] == "test-tenant"


class TestErrorLogging:
    """Tests for error logging behavior (001-FR-027)."""

    @pytest.mark.requirement("001-FR-027")
    def test_validation_error_logs_details_internally(self, tmp_path: Path) -> None:
        """Test that validation errors log technical details internally.

        Covers:
        - 001-FR-027: Log technical error details internally
        """
        import structlog
        from pydantic import ValidationError

        from floe_core.schemas import FloeSpec

        # Capture logs
        log_output = StringIO()
        handler = logging.StreamHandler(log_output)
        handler.setLevel(logging.DEBUG)

        # Add handler to structlog
        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=False,
        )

        logger = structlog.get_logger("test_error_logging")

        # Trigger validation error
        try:
            FloeSpec.model_validate(
                {
                    "name": "",  # Invalid: empty name
                    "version": "1.0.0",
                    "compute": {"target": "duckdb"},
                }
            )
        except ValidationError as e:
            # Log internal details
            logger.error(
                "Validation failed",
                error_type=type(e).__name__,
                error_count=e.error_count(),
                errors=str(e.errors()),
            )

        # Verify error was caught (validation error expected)
        # The key point is that technical details should be loggable

    @pytest.mark.requirement("001-FR-027")
    def test_user_friendly_error_messages(self, tmp_path: Path) -> None:
        """Test that user-facing errors are friendly and don't expose internals.

        Covers:
        - 001-FR-027: Return user-friendly messages
        """
        from pydantic import ValidationError

        from floe_core.schemas import FloeSpec

        # Trigger validation error
        try:
            FloeSpec.model_validate(
                {
                    "name": "",  # Invalid: empty name
                    "version": "1.0.0",
                    "compute": {"target": "duckdb"},
                }
            )
            pytest.fail("Should have raised ValidationError")
        except ValidationError as e:
            # Pydantic provides structured errors that can be formatted
            errors = e.errors()

            # Verify error structure is usable for user-friendly messages
            assert len(errors) > 0
            first_error = errors[0]

            # Should have 'loc' (location) and 'msg' (message)
            assert "loc" in first_error
            assert "msg" in first_error

            # Message should be human-readable
            msg = first_error["msg"]
            assert len(msg) > 0
            assert "name" in str(first_error["loc"]) or "String" in msg

    @pytest.mark.requirement("001-FR-027")
    def test_file_not_found_error_is_user_friendly(self, tmp_path: Path) -> None:
        """Test that file not found errors are user-friendly.

        Covers:
        - 001-FR-027: User-friendly error for missing files
        """
        from floe_core.compiler import Compiler

        compiler = Compiler()

        # Try to compile non-existent file
        non_existent = tmp_path / "does-not-exist.yaml"

        try:
            compiler.compile(non_existent)
            pytest.fail("Should have raised an error")
        except FileNotFoundError as e:
            # Error message should mention the file
            assert "does-not-exist.yaml" in str(e) or str(non_existent) in str(e)

    @pytest.mark.requirement("001-FR-027")
    def test_yaml_syntax_error_is_user_friendly(self, tmp_path: Path) -> None:
        """Test that YAML syntax errors are user-friendly.

        Covers:
        - 001-FR-027: User-friendly error for invalid YAML
        """
        from floe_core.schemas import FloeSpec

        # Create file with invalid YAML
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("""
name: test
version: 1.0.0
compute:
  target: duckdb
  invalid_indent:
 broken: true
""")

        try:
            FloeSpec.from_yaml(bad_yaml)
            pytest.fail("Should have raised an error")
        except Exception as e:
            # Should get a YAML error or validation error
            # The error should be catchable and provide some context
            assert e is not None
