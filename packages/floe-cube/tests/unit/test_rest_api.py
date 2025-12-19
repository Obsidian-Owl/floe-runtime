"""Unit tests for REST API configuration.

T039: Add REST API port configuration
T040: Add API authentication configuration

These tests verify:
- REST API port configuration in CubeConfig
- API authentication configuration (jwt_audience, jwt_issuer, api_secret_ref)
- Configuration validation for REST API settings
- API port range validation
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from floe_cube.models import CubeConfig, DatabaseType


class TestRestApiPortConfiguration:
    """T039: Tests for REST API port configuration."""

    def test_default_api_port(self) -> None:
        """Default REST API port should be 4000."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES)
        assert config.api_port == 4000

    def test_custom_api_port(self) -> None:
        """REST API port should be configurable."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES, api_port=8080)
        assert config.api_port == 8080

    def test_api_port_minimum_value(self) -> None:
        """API port must be at least 1."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES, api_port=1)
        assert config.api_port == 1

    def test_api_port_maximum_value(self) -> None:
        """API port can be up to 65535."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES, api_port=65535)
        assert config.api_port == 65535

    def test_api_port_zero_rejected(self) -> None:
        """API port of 0 should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CubeConfig(database_type=DatabaseType.POSTGRES, api_port=0)
        assert "api_port" in str(exc_info.value)

    def test_api_port_negative_rejected(self) -> None:
        """Negative API port should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CubeConfig(database_type=DatabaseType.POSTGRES, api_port=-1)
        assert "api_port" in str(exc_info.value)

    def test_api_port_above_max_rejected(self) -> None:
        """API port above 65535 should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CubeConfig(database_type=DatabaseType.POSTGRES, api_port=65536)
        assert "api_port" in str(exc_info.value)

    def test_common_http_port(self) -> None:
        """Common HTTP port 80 should be valid."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES, api_port=80)
        assert config.api_port == 80

    def test_common_https_port(self) -> None:
        """Common HTTPS port 443 should be valid."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES, api_port=443)
        assert config.api_port == 443

    def test_ephemeral_port_range(self) -> None:
        """Ephemeral port range should be valid."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES, api_port=49152)
        assert config.api_port == 49152


class TestSqlApiPortConfiguration:
    """Tests for SQL API (Postgres wire protocol) port configuration."""

    def test_default_sql_port(self) -> None:
        """Default SQL API port should be 15432."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES)
        assert config.sql_port == 15432

    def test_custom_sql_port(self) -> None:
        """SQL API port should be configurable."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES, sql_port=5432)
        assert config.sql_port == 5432

    def test_sql_port_validation(self) -> None:
        """SQL port has same validation as API port."""
        with pytest.raises(ValidationError) as exc_info:
            CubeConfig(database_type=DatabaseType.POSTGRES, sql_port=0)
        assert "sql_port" in str(exc_info.value)

    def test_different_api_and_sql_ports(self) -> None:
        """API and SQL ports can be different."""
        config = CubeConfig(
            database_type=DatabaseType.POSTGRES,
            api_port=4000,
            sql_port=15432,
        )
        assert config.api_port == 4000
        assert config.sql_port == 15432


class TestApiAuthenticationConfiguration:
    """T040: Tests for API authentication configuration."""

    def test_api_secret_ref_default_none(self) -> None:
        """api_secret_ref should default to None."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES)
        assert config.api_secret_ref is None

    def test_api_secret_ref_valid_names(self) -> None:
        """api_secret_ref accepts valid K8s secret names."""
        valid_names = [
            "my-secret",
            "cube-api-secret",
            "CUBE_SECRET",
            "secret123",
            "a",
            "abc-def_ghi",
        ]
        for name in valid_names:
            config = CubeConfig(database_type=DatabaseType.POSTGRES, api_secret_ref=name)
            assert config.api_secret_ref == name

    def test_api_secret_ref_invalid_start_dash(self) -> None:
        """api_secret_ref cannot start with dash."""
        with pytest.raises(ValidationError) as exc_info:
            CubeConfig(database_type=DatabaseType.POSTGRES, api_secret_ref="-invalid")
        assert "api_secret_ref" in str(exc_info.value)

    def test_api_secret_ref_invalid_start_underscore(self) -> None:
        """api_secret_ref cannot start with underscore."""
        with pytest.raises(ValidationError) as exc_info:
            CubeConfig(database_type=DatabaseType.POSTGRES, api_secret_ref="_invalid")
        assert "api_secret_ref" in str(exc_info.value)

    def test_jwt_audience_default_none(self) -> None:
        """jwt_audience should default to None."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES)
        assert config.jwt_audience is None

    def test_jwt_audience_configurable(self) -> None:
        """jwt_audience should be configurable."""
        config = CubeConfig(
            database_type=DatabaseType.POSTGRES,
            jwt_audience="https://api.example.com",
        )
        assert config.jwt_audience == "https://api.example.com"

    def test_jwt_issuer_default_none(self) -> None:
        """jwt_issuer should default to None."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES)
        assert config.jwt_issuer is None

    def test_jwt_issuer_configurable(self) -> None:
        """jwt_issuer should be configurable."""
        config = CubeConfig(
            database_type=DatabaseType.POSTGRES,
            jwt_issuer="https://auth.example.com",
        )
        assert config.jwt_issuer == "https://auth.example.com"

    def test_full_jwt_configuration(self) -> None:
        """All JWT configuration options work together."""
        config = CubeConfig(
            database_type=DatabaseType.POSTGRES,
            api_secret_ref="cube-jwt-secret",
            jwt_audience="https://api.example.com",
            jwt_issuer="https://auth.example.com",
        )
        assert config.api_secret_ref == "cube-jwt-secret"
        assert config.jwt_audience == "https://api.example.com"
        assert config.jwt_issuer == "https://auth.example.com"

    def test_auth_config_with_dev_mode(self) -> None:
        """Auth configuration works with dev_mode enabled."""
        config = CubeConfig(
            database_type=DatabaseType.POSTGRES,
            api_secret_ref="dev-secret",
            dev_mode=True,
        )
        assert config.api_secret_ref == "dev-secret"
        assert config.dev_mode is True


class TestDevModeConfiguration:
    """Tests for development mode configuration."""

    def test_dev_mode_default_false(self) -> None:
        """dev_mode should default to False."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES)
        assert config.dev_mode is False

    def test_dev_mode_true(self) -> None:
        """dev_mode can be enabled."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES, dev_mode=True)
        assert config.dev_mode is True

    def test_dev_mode_false_explicit(self) -> None:
        """dev_mode can be explicitly set to False."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES, dev_mode=False)
        assert config.dev_mode is False


class TestCubeConfigSerialization:
    """Tests for CubeConfig serialization."""

    def test_serialize_with_all_api_fields(self) -> None:
        """CubeConfig with all API fields serializes correctly."""
        config = CubeConfig(
            database_type=DatabaseType.POSTGRES,
            api_port=4000,
            sql_port=15432,
            api_secret_ref="my-secret",
            dev_mode=True,
            jwt_audience="audience",
            jwt_issuer="issuer",
        )
        data = config.model_dump()

        assert data["api_port"] == 4000
        assert data["sql_port"] == 15432
        assert data["api_secret_ref"] == "my-secret"
        assert data["dev_mode"] is True
        assert data["jwt_audience"] == "audience"
        assert data["jwt_issuer"] == "issuer"

    def test_round_trip_serialization(self) -> None:
        """CubeConfig survives JSON round-trip."""
        original = CubeConfig(
            database_type=DatabaseType.SNOWFLAKE,
            api_port=8080,
            sql_port=5432,
            api_secret_ref="secret",
            dev_mode=True,
            jwt_audience="aud",
            jwt_issuer="iss",
        )
        json_str = original.model_dump_json()
        loaded = CubeConfig.model_validate_json(json_str)

        assert loaded == original


class TestCubeConfigImmutability:
    """Tests for CubeConfig immutability."""

    def test_api_port_immutable(self) -> None:
        """api_port should be immutable."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES)
        with pytest.raises(ValidationError):
            config.api_port = 9999  # type: ignore[misc]

    def test_sql_port_immutable(self) -> None:
        """sql_port should be immutable."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES)
        with pytest.raises(ValidationError):
            config.sql_port = 9999  # type: ignore[misc]

    def test_api_secret_ref_immutable(self) -> None:
        """api_secret_ref should be immutable."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES, api_secret_ref="secret")
        with pytest.raises(ValidationError):
            config.api_secret_ref = "new-secret"  # type: ignore[misc]

    def test_jwt_audience_immutable(self) -> None:
        """jwt_audience should be immutable."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES, jwt_audience="aud")
        with pytest.raises(ValidationError):
            config.jwt_audience = "new-aud"  # type: ignore[misc]

    def test_jwt_issuer_immutable(self) -> None:
        """jwt_issuer should be immutable."""
        config = CubeConfig(database_type=DatabaseType.POSTGRES, jwt_issuer="iss")
        with pytest.raises(ValidationError):
            config.jwt_issuer = "new-iss"  # type: ignore[misc]
