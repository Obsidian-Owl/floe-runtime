"""Unit tests for configuration models.

Tests for:
- T025: RetryConfig validation
- T026: PolarisCatalogConfig validation
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from floe_polaris.config import NamespaceInfo, PolarisCatalogConfig, RetryConfig


class TestRetryConfig:
    """Tests for RetryConfig Pydantic model."""

    def test_default_values(self) -> None:
        """Test RetryConfig uses correct defaults."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.initial_wait_seconds == pytest.approx(1.0)
        assert config.max_wait_seconds == pytest.approx(30.0)
        assert config.jitter_seconds == pytest.approx(1.0)
        assert config.circuit_breaker_threshold == 5

    def test_custom_values(self) -> None:
        """Test RetryConfig accepts custom values within bounds."""
        config = RetryConfig(
            max_attempts=5,
            initial_wait_seconds=0.5,
            max_wait_seconds=60.0,
            jitter_seconds=2.0,
            circuit_breaker_threshold=10,
        )

        assert config.max_attempts == 5
        assert config.initial_wait_seconds == pytest.approx(0.5)
        assert config.max_wait_seconds == pytest.approx(60.0)
        assert config.jitter_seconds == pytest.approx(2.0)
        assert config.circuit_breaker_threshold == 10

    def test_max_attempts_min_boundary(self) -> None:
        """Test max_attempts minimum is 1."""
        with pytest.raises(ValidationError) as exc_info:
            RetryConfig(max_attempts=0)

        assert "max_attempts" in str(exc_info.value)

    def test_max_attempts_max_boundary(self) -> None:
        """Test max_attempts maximum is 10."""
        with pytest.raises(ValidationError) as exc_info:
            RetryConfig(max_attempts=11)

        assert "max_attempts" in str(exc_info.value)

    def test_initial_wait_min_boundary(self) -> None:
        """Test initial_wait_seconds minimum is 0.1."""
        with pytest.raises(ValidationError) as exc_info:
            RetryConfig(initial_wait_seconds=0.05)

        assert "initial_wait_seconds" in str(exc_info.value)

    def test_initial_wait_max_boundary(self) -> None:
        """Test initial_wait_seconds maximum is 30.0."""
        with pytest.raises(ValidationError) as exc_info:
            RetryConfig(initial_wait_seconds=31.0)

        assert "initial_wait_seconds" in str(exc_info.value)

    def test_max_wait_must_exceed_initial(self) -> None:
        """Test max_wait_seconds must be >= initial_wait_seconds."""
        with pytest.raises(ValidationError) as exc_info:
            RetryConfig(initial_wait_seconds=10.0, max_wait_seconds=5.0)

        assert "max_wait_seconds" in str(exc_info.value)

    def test_jitter_can_be_zero(self) -> None:
        """Test jitter_seconds can be 0 (disabled)."""
        config = RetryConfig(jitter_seconds=0.0)

        assert config.jitter_seconds == pytest.approx(0.0)

    def test_circuit_breaker_disabled(self) -> None:
        """Test circuit_breaker_threshold 0 disables circuit breaker."""
        config = RetryConfig(circuit_breaker_threshold=0)

        assert config.circuit_breaker_threshold == 0

    def test_frozen_model(self) -> None:
        """Test RetryConfig is immutable."""
        config = RetryConfig()

        with pytest.raises(ValidationError):
            config.max_attempts = 5  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            RetryConfig(unknown_field="value")  # type: ignore[call-arg]

        assert "extra" in str(exc_info.value).lower()


class TestPolarisCatalogConfig:
    """Tests for PolarisCatalogConfig Pydantic model."""

    def test_minimal_config(self) -> None:
        """Test minimal valid config with just uri and warehouse."""
        config = PolarisCatalogConfig(
            uri="http://localhost:8181/api/catalog",
            warehouse="my_warehouse",
        )

        assert config.uri == "http://localhost:8181/api/catalog"
        assert config.warehouse == "my_warehouse"
        assert config.client_id is None
        assert config.client_secret is None

    def test_full_config(self) -> None:
        """Test full config with all fields."""
        config = PolarisCatalogConfig(
            uri="https://polaris.example.com/api/catalog",
            warehouse="production",
            client_id="my_client",
            client_secret="my_secret",
            scope="PRINCIPAL_ROLE:ADMIN",
            token_refresh_enabled=False,
            access_delegation="remote-signing",
        )

        assert config.uri == "https://polaris.example.com/api/catalog"
        assert config.warehouse == "production"
        assert config.client_id == "my_client"
        assert config.client_secret.get_secret_value() == "my_secret"
        assert config.scope == "PRINCIPAL_ROLE:ADMIN"
        assert config.token_refresh_enabled is False

    def test_uri_http_valid(self) -> None:
        """Test http:// URI is valid."""
        config = PolarisCatalogConfig(
            uri="http://localhost:8181/api/catalog",
            warehouse="test",
        )

        assert config.uri.startswith("http://")

    def test_uri_https_valid(self) -> None:
        """Test https:// URI is valid."""
        config = PolarisCatalogConfig(
            uri="https://secure.example.com/api/catalog",
            warehouse="test",
        )

        assert config.uri.startswith("https://")

    def test_uri_invalid_scheme(self) -> None:
        """Test invalid URI scheme is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PolarisCatalogConfig(
                uri="ftp://invalid.example.com/catalog",
                warehouse="test",
            )

        assert "uri" in str(exc_info.value).lower()

    def test_uri_trailing_slash_removed(self) -> None:
        """Test trailing slash is normalized."""
        config = PolarisCatalogConfig(
            uri="http://localhost:8181/api/catalog/",
            warehouse="test",
        )

        assert not config.uri.endswith("/")

    def test_warehouse_required(self) -> None:
        """Test warehouse is required."""
        with pytest.raises(ValidationError) as exc_info:
            PolarisCatalogConfig(uri="http://localhost:8181/api/catalog")  # type: ignore[call-arg]

        assert "warehouse" in str(exc_info.value).lower()

    def test_warehouse_not_empty(self) -> None:
        """Test warehouse cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            PolarisCatalogConfig(
                uri="http://localhost:8181/api/catalog",
                warehouse="",
            )

        assert "warehouse" in str(exc_info.value).lower()

    def test_default_retry_config(self) -> None:
        """Test default retry config is applied."""
        config = PolarisCatalogConfig(
            uri="http://localhost:8181/api/catalog",
            warehouse="test",
        )

        assert isinstance(config.retry, RetryConfig)
        assert config.retry.max_attempts == 3

    def test_custom_retry_config(self) -> None:
        """Test custom retry config is accepted."""
        config = PolarisCatalogConfig(
            uri="http://localhost:8181/api/catalog",
            warehouse="test",
            retry=RetryConfig(max_attempts=5),
        )

        assert config.retry.max_attempts == 5

    def test_secret_not_exposed(self) -> None:
        """Test client_secret is not exposed in repr/str."""
        config = PolarisCatalogConfig(
            uri="http://localhost:8181/api/catalog",
            warehouse="test",
            client_secret="super_secret_password",
        )

        repr_str = repr(config)
        assert "super_secret_password" not in repr_str
        assert "**" in repr_str or "SecretStr" in repr_str

    def test_default_scope(self) -> None:
        """Test default OAuth2 scope."""
        config = PolarisCatalogConfig(
            uri="http://localhost:8181/api/catalog",
            warehouse="test",
        )

        assert config.scope == "PRINCIPAL_ROLE:ALL"

    def test_token_alternative_to_credentials(self) -> None:
        """Test token can be used instead of client credentials."""
        config = PolarisCatalogConfig(
            uri="http://localhost:8181/api/catalog",
            warehouse="test",
            token="bearer_token_value",
        )

        assert config.token.get_secret_value() == "bearer_token_value"
        assert config.client_id is None


class TestNamespaceInfo:
    """Tests for NamespaceInfo model."""

    def test_simple_namespace(self) -> None:
        """Test simple namespace without nesting."""
        ns = NamespaceInfo(name="bronze")

        assert ns.name == "bronze"
        assert ns.parts == ("bronze",)

    def test_nested_namespace(self) -> None:
        """Test nested namespace with dots."""
        ns = NamespaceInfo(name="bronze.raw.events")

        assert ns.name == "bronze.raw.events"
        assert ns.parts == ("bronze", "raw", "events")

    def test_with_properties(self) -> None:
        """Test namespace with properties."""
        ns = NamespaceInfo(
            name="bronze",
            properties={"owner": "data_team", "description": "Raw data"},
        )

        assert ns.properties == {"owner": "data_team", "description": "Raw data"}

    def test_empty_properties_default(self) -> None:
        """Test empty properties is default."""
        ns = NamespaceInfo(name="bronze")

        assert ns.properties == {}

    def test_frozen(self) -> None:
        """Test NamespaceInfo is immutable."""
        ns = NamespaceInfo(name="bronze")

        with pytest.raises(ValidationError):
            ns.name = "silver"  # type: ignore[misc]
