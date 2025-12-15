"""Unit tests for ComputeConfig model.

T011: [US1] Unit tests for ComputeConfig validation
Tests ComputeConfig with target validation and secret ref patterns.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestComputeConfig:
    """Tests for ComputeConfig model."""

    def test_compute_config_requires_target(self) -> None:
        """ComputeConfig should require target field."""
        from floe_core.schemas import ComputeConfig

        with pytest.raises(ValidationError) as exc_info:
            ComputeConfig()  # type: ignore[call-arg]

        assert "target" in str(exc_info.value)

    def test_compute_config_with_valid_target(self) -> None:
        """ComputeConfig should accept valid target."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(target=ComputeTarget.duckdb)
        assert config.target == ComputeTarget.duckdb

    def test_compute_config_with_string_target(self) -> None:
        """ComputeConfig should accept target as string."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(target="snowflake")  # type: ignore[arg-type]
        assert config.target == ComputeTarget.snowflake

    def test_compute_config_connection_secret_ref_optional(self) -> None:
        """ComputeConfig.connection_secret_ref should be optional."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(target=ComputeTarget.duckdb)
        assert config.connection_secret_ref is None

    def test_compute_config_valid_secret_ref(self) -> None:
        """ComputeConfig should accept valid K8s secret ref."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.snowflake,
            connection_secret_ref="my-snowflake-secret",
        )
        assert config.connection_secret_ref == "my-snowflake-secret"

    def test_compute_config_secret_ref_with_underscores(self) -> None:
        """ComputeConfig should accept secret ref with underscores."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.snowflake,
            connection_secret_ref="my_snowflake_secret",
        )
        assert config.connection_secret_ref == "my_snowflake_secret"

    def test_compute_config_secret_ref_invalid_start_char(self) -> None:
        """ComputeConfig should reject secret ref starting with invalid char."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        with pytest.raises(ValidationError) as exc_info:
            ComputeConfig(
                target=ComputeTarget.snowflake,
                connection_secret_ref="-invalid-start",
            )

        assert "connection_secret_ref" in str(exc_info.value)

    def test_compute_config_secret_ref_too_long(self) -> None:
        """ComputeConfig should reject secret ref exceeding 253 chars."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        long_name = "a" * 254
        with pytest.raises(ValidationError) as exc_info:
            ComputeConfig(
                target=ComputeTarget.snowflake,
                connection_secret_ref=long_name,
            )

        assert "connection_secret_ref" in str(exc_info.value)

    def test_compute_config_properties_default_empty_dict(self) -> None:
        """ComputeConfig.properties should default to empty dict."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(target=ComputeTarget.duckdb)
        assert config.properties == {}

    def test_compute_config_properties_with_values(self) -> None:
        """ComputeConfig should accept properties dict."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(
            target=ComputeTarget.snowflake,
            properties={
                "account": "xy12345.us-east-1",
                "warehouse": "COMPUTE_WH",
            },
        )
        assert config.properties["account"] == "xy12345.us-east-1"
        assert config.properties["warehouse"] == "COMPUTE_WH"

    def test_compute_config_is_frozen(self) -> None:
        """ComputeConfig should be immutable (frozen)."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        config = ComputeConfig(target=ComputeTarget.duckdb)

        with pytest.raises(ValidationError):
            config.target = ComputeTarget.snowflake  # type: ignore[misc]

    def test_compute_config_rejects_extra_fields(self) -> None:
        """ComputeConfig should reject unknown fields."""
        from floe_core.schemas import ComputeConfig, ComputeTarget

        with pytest.raises(ValidationError) as exc_info:
            ComputeConfig(
                target=ComputeTarget.duckdb,
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower()
