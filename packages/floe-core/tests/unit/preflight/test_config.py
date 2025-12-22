"""Unit tests for preflight configuration models.

Covers: 007-FR-005 (pre-deployment validation)

Run with:
    pytest packages/floe-core/tests/unit/preflight/test_config.py -v
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from floe_core.preflight.config import (
    CatalogCheckConfig,
    ComputeCheckConfig,
    OTelCheckConfig,
    PostgresCheckConfig,
    PreflightConfig,
    StorageCheckConfig,
)


class TestComputeCheckConfig:
    """Tests for ComputeCheckConfig."""

    @pytest.mark.requirement("007-FR-005")
    def test_default_values(self) -> None:
        """Default configuration is valid."""
        config = ComputeCheckConfig()
        assert config.enabled is True
        assert config.timeout_seconds == 30
        assert config.type == "trino"

    @pytest.mark.requirement("007-FR-005")
    def test_custom_values(self) -> None:
        """Custom configuration values work."""
        config = ComputeCheckConfig(
            enabled=False,
            timeout_seconds=60,
            type="snowflake",
        )
        assert config.enabled is False
        assert config.timeout_seconds == 60
        assert config.type == "snowflake"

    @pytest.mark.requirement("007-FR-005")
    def test_timeout_validation_min(self) -> None:
        """Timeout must be at least 1 second."""
        with pytest.raises(ValidationError) as exc_info:
            ComputeCheckConfig(timeout_seconds=0)
        assert "timeout_seconds" in str(exc_info.value)

    @pytest.mark.requirement("007-FR-005")
    def test_timeout_validation_max(self) -> None:
        """Timeout must be at most 300 seconds."""
        with pytest.raises(ValidationError) as exc_info:
            ComputeCheckConfig(timeout_seconds=301)
        assert "timeout_seconds" in str(exc_info.value)

    @pytest.mark.requirement("007-FR-005")
    def test_frozen_model(self) -> None:
        """Config is immutable."""
        config = ComputeCheckConfig()
        with pytest.raises(ValidationError):
            config.enabled = False  # type: ignore[misc]


class TestStorageCheckConfig:
    """Tests for StorageCheckConfig."""

    @pytest.mark.requirement("007-FR-005")
    def test_default_values(self) -> None:
        """Default configuration is valid."""
        config = StorageCheckConfig()
        assert config.enabled is True
        assert config.timeout_seconds == 30
        assert config.bucket == ""

    @pytest.mark.requirement("007-FR-005")
    def test_with_bucket(self) -> None:
        """Configuration with bucket works."""
        config = StorageCheckConfig(bucket="my-data-bucket")
        assert config.bucket == "my-data-bucket"


class TestCatalogCheckConfig:
    """Tests for CatalogCheckConfig."""

    @pytest.mark.requirement("007-FR-005")
    def test_default_values(self) -> None:
        """Default configuration is valid."""
        config = CatalogCheckConfig()
        assert config.enabled is True
        assert config.uri == ""

    @pytest.mark.requirement("007-FR-005")
    def test_with_uri(self) -> None:
        """Configuration with URI works."""
        config = CatalogCheckConfig(uri="http://polaris:8181/api/catalog")
        assert config.uri == "http://polaris:8181/api/catalog"


class TestPostgresCheckConfig:
    """Tests for PostgresCheckConfig."""

    @pytest.mark.requirement("007-FR-005")
    def test_default_values(self) -> None:
        """Default configuration is valid."""
        config = PostgresCheckConfig()
        assert config.enabled is True
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "dagster"

    @pytest.mark.requirement("007-FR-005")
    def test_custom_values(self) -> None:
        """Custom configuration values work."""
        config = PostgresCheckConfig(
            host="postgres.example.com",
            port=5433,
            database="dagster_prod",
        )
        assert config.host == "postgres.example.com"
        assert config.port == 5433
        assert config.database == "dagster_prod"

    @pytest.mark.requirement("007-FR-005")
    def test_port_validation_range(self) -> None:
        """Port must be in valid range."""
        # Valid boundary
        config = PostgresCheckConfig(port=1)
        assert config.port == 1

        config = PostgresCheckConfig(port=65535)
        assert config.port == 65535

        # Invalid
        with pytest.raises(ValidationError):
            PostgresCheckConfig(port=0)

        with pytest.raises(ValidationError):
            PostgresCheckConfig(port=65536)


class TestOTelCheckConfig:
    """Tests for OTelCheckConfig."""

    @pytest.mark.requirement("007-FR-005")
    def test_default_disabled(self) -> None:
        """OTel check is disabled by default (optional)."""
        config = OTelCheckConfig()
        assert config.enabled is False
        assert config.timeout_seconds == 10


class TestPreflightConfig:
    """Tests for PreflightConfig."""

    @pytest.mark.requirement("007-FR-005")
    def test_default_values(self) -> None:
        """Default configuration has all checks enabled except OTel."""
        config = PreflightConfig()
        assert config.compute.enabled is True
        assert config.storage.enabled is True
        assert config.catalog.enabled is True
        assert config.postgres.enabled is True
        assert config.otel.enabled is False
        assert config.fail_fast is False
        assert config.verbose is False

    @pytest.mark.requirement("007-FR-005")
    def test_custom_checks(self) -> None:
        """Custom check configurations work."""
        config = PreflightConfig(
            compute=ComputeCheckConfig(type="snowflake"),
            storage=StorageCheckConfig(bucket="my-bucket"),
            fail_fast=True,
            verbose=True,
        )
        assert config.compute.type == "snowflake"
        assert config.storage.bucket == "my-bucket"
        assert config.fail_fast is True
        assert config.verbose is True

    @pytest.mark.requirement("007-FR-005")
    def test_frozen_model(self) -> None:
        """Config is immutable."""
        config = PreflightConfig()
        with pytest.raises(ValidationError):
            config.fail_fast = True  # type: ignore[misc]

    @pytest.mark.requirement("007-FR-005")
    def test_extra_fields_forbidden(self) -> None:
        """Extra fields are not allowed."""
        with pytest.raises(ValidationError) as exc_info:
            PreflightConfig(unknown_field="value")  # type: ignore[call-arg]
        assert "extra" in str(exc_info.value).lower()
