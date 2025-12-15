"""Unit tests for ConsumptionConfig and related models.

T013: [US1] Unit tests for ConsumptionConfig defaults
Tests ConsumptionConfig, PreAggregationConfig, and CubeSecurityConfig defaults.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestPreAggregationConfig:
    """Tests for PreAggregationConfig model."""

    def test_pre_aggregation_config_default_values(self) -> None:
        """PreAggregationConfig should have correct defaults."""
        from floe_core.schemas import PreAggregationConfig

        config = PreAggregationConfig()
        assert config.refresh_schedule == "*/30 * * * *"
        assert config.timezone == "UTC"

    def test_pre_aggregation_config_custom_values(self) -> None:
        """PreAggregationConfig should accept custom values."""
        from floe_core.schemas import PreAggregationConfig

        config = PreAggregationConfig(
            refresh_schedule="0 * * * *",
            timezone="America/New_York",
        )
        assert config.refresh_schedule == "0 * * * *"
        assert config.timezone == "America/New_York"

    def test_pre_aggregation_config_is_frozen(self) -> None:
        """PreAggregationConfig should be immutable."""
        from floe_core.schemas import PreAggregationConfig

        config = PreAggregationConfig()

        with pytest.raises(ValidationError):
            config.timezone = "Europe/London"  # type: ignore[misc]


class TestCubeSecurityConfig:
    """Tests for CubeSecurityConfig model."""

    def test_cube_security_config_default_values(self) -> None:
        """CubeSecurityConfig should have correct defaults."""
        from floe_core.schemas import CubeSecurityConfig

        config = CubeSecurityConfig()
        assert config.row_level is True
        assert config.tenant_column == "tenant_id"

    def test_cube_security_config_custom_values(self) -> None:
        """CubeSecurityConfig should accept custom values."""
        from floe_core.schemas import CubeSecurityConfig

        config = CubeSecurityConfig(
            row_level=False,
            tenant_column="org_id",
        )
        assert config.row_level is False
        assert config.tenant_column == "org_id"

    def test_cube_security_config_is_frozen(self) -> None:
        """CubeSecurityConfig should be immutable."""
        from floe_core.schemas import CubeSecurityConfig

        config = CubeSecurityConfig()

        with pytest.raises(ValidationError):
            config.row_level = False  # type: ignore[misc]


class TestConsumptionConfig:
    """Tests for ConsumptionConfig model."""

    def test_consumption_config_default_values(self) -> None:
        """ConsumptionConfig should have correct defaults."""
        from floe_core.schemas import ConsumptionConfig

        config = ConsumptionConfig()
        assert config.enabled is False
        assert config.port == 4000
        assert config.api_secret_ref is None
        assert config.database_type is None
        assert config.dev_mode is False

    def test_consumption_config_pre_aggregations_default(self) -> None:
        """ConsumptionConfig should have default PreAggregationConfig."""
        from floe_core.schemas import ConsumptionConfig, PreAggregationConfig

        config = ConsumptionConfig()
        assert isinstance(config.pre_aggregations, PreAggregationConfig)
        assert config.pre_aggregations.refresh_schedule == "*/30 * * * *"

    def test_consumption_config_security_default(self) -> None:
        """ConsumptionConfig should have default CubeSecurityConfig."""
        from floe_core.schemas import ConsumptionConfig, CubeSecurityConfig

        config = ConsumptionConfig()
        assert isinstance(config.security, CubeSecurityConfig)
        assert config.security.row_level is True

    def test_consumption_config_enabled(self) -> None:
        """ConsumptionConfig should accept enabled=True."""
        from floe_core.schemas import ConsumptionConfig

        config = ConsumptionConfig(enabled=True)
        assert config.enabled is True

    def test_consumption_config_custom_port(self) -> None:
        """ConsumptionConfig should accept custom port."""
        from floe_core.schemas import ConsumptionConfig

        config = ConsumptionConfig(port=8080)
        assert config.port == 8080

    def test_consumption_config_database_type(self) -> None:
        """ConsumptionConfig should accept database_type."""
        from floe_core.schemas import ConsumptionConfig

        config = ConsumptionConfig(
            enabled=True,
            database_type="snowflake",
        )
        assert config.database_type == "snowflake"

    def test_consumption_config_api_secret_ref(self) -> None:
        """ConsumptionConfig should accept api_secret_ref."""
        from floe_core.schemas import ConsumptionConfig

        config = ConsumptionConfig(
            enabled=True,
            api_secret_ref="cube-api-secret",
        )
        assert config.api_secret_ref == "cube-api-secret"

    def test_consumption_config_invalid_api_secret_ref(self) -> None:
        """ConsumptionConfig should reject invalid api_secret_ref."""
        from floe_core.schemas import ConsumptionConfig

        with pytest.raises(ValidationError) as exc_info:
            ConsumptionConfig(
                enabled=True,
                api_secret_ref="-invalid-start",
            )

        assert "api_secret_ref" in str(exc_info.value)

    def test_consumption_config_dev_mode(self) -> None:
        """ConsumptionConfig should accept dev_mode."""
        from floe_core.schemas import ConsumptionConfig

        config = ConsumptionConfig(
            enabled=True,
            dev_mode=True,
        )
        assert config.dev_mode is True

    def test_consumption_config_custom_pre_aggregations(self) -> None:
        """ConsumptionConfig should accept custom pre_aggregations."""
        from floe_core.schemas import ConsumptionConfig, PreAggregationConfig

        config = ConsumptionConfig(
            enabled=True,
            pre_aggregations=PreAggregationConfig(
                refresh_schedule="0 */2 * * *",
                timezone="Europe/London",
            ),
        )
        assert config.pre_aggregations.refresh_schedule == "0 */2 * * *"
        assert config.pre_aggregations.timezone == "Europe/London"

    def test_consumption_config_custom_security(self) -> None:
        """ConsumptionConfig should accept custom security."""
        from floe_core.schemas import ConsumptionConfig, CubeSecurityConfig

        config = ConsumptionConfig(
            enabled=True,
            security=CubeSecurityConfig(
                row_level=False,
                tenant_column="organization_id",
            ),
        )
        assert config.security.row_level is False
        assert config.security.tenant_column == "organization_id"

    def test_consumption_config_is_frozen(self) -> None:
        """ConsumptionConfig should be immutable."""
        from floe_core.schemas import ConsumptionConfig

        config = ConsumptionConfig()

        with pytest.raises(ValidationError):
            config.enabled = True  # type: ignore[misc]

    def test_consumption_config_rejects_extra_fields(self) -> None:
        """ConsumptionConfig should reject unknown fields."""
        from floe_core.schemas import ConsumptionConfig

        with pytest.raises(ValidationError) as exc_info:
            ConsumptionConfig(unknown_field="value")  # type: ignore[call-arg]

        assert "extra" in str(exc_info.value).lower()

    def test_consumption_config_default_factory_isolation(self) -> None:
        """ConsumptionConfig defaults should be isolated (no shared state)."""
        from floe_core.schemas import ConsumptionConfig

        config1 = ConsumptionConfig()
        config2 = ConsumptionConfig()

        # Verify they are independent objects
        assert config1 is not config2
        assert config1.pre_aggregations is not config2.pre_aggregations
        assert config1.security is not config2.security
