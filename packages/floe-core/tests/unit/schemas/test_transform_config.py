"""Unit tests for TransformConfig model.

T012: [US1] Unit tests for TransformConfig validation
Tests TransformConfig with type discriminator and path validation.
"""

from __future__ import annotations

from typing import Literal

import pytest
from pydantic import ValidationError


class TestTransformConfig:
    """Tests for TransformConfig model."""

    def test_transform_config_requires_type(self) -> None:
        """TransformConfig should require type field."""
        from floe_core.schemas import TransformConfig

        with pytest.raises(ValidationError) as exc_info:
            TransformConfig(path="./dbt")  # type: ignore[call-arg]

        assert "type" in str(exc_info.value)

    def test_transform_config_requires_path(self) -> None:
        """TransformConfig should require path field."""
        from floe_core.schemas import TransformConfig

        with pytest.raises(ValidationError) as exc_info:
            TransformConfig(type="dbt")  # type: ignore[call-arg]

        assert "path" in str(exc_info.value)

    def test_transform_config_dbt_type(self) -> None:
        """TransformConfig should accept 'dbt' type."""
        from floe_core.schemas import TransformConfig

        config = TransformConfig(type="dbt", path="./dbt")
        assert config.type == "dbt"
        assert config.path == "./dbt"

    def test_transform_config_type_is_literal_dbt(self) -> None:
        """TransformConfig.type should be Literal['dbt']."""
        from floe_core.schemas import TransformConfig

        config = TransformConfig(type="dbt", path="./dbt")

        # Type should be exactly "dbt"
        type_value: Literal["dbt"] = config.type
        assert type_value == "dbt"

    def test_transform_config_invalid_type_rejected(self) -> None:
        """TransformConfig should reject invalid type values."""
        from floe_core.schemas import TransformConfig

        with pytest.raises(ValidationError) as exc_info:
            TransformConfig(type="python", path="./script.py")  # type: ignore[arg-type]

        assert "type" in str(exc_info.value)

    def test_transform_config_target_optional(self) -> None:
        """TransformConfig.target should be optional."""
        from floe_core.schemas import TransformConfig

        config = TransformConfig(type="dbt", path="./dbt")
        assert config.target is None

    def test_transform_config_with_target(self) -> None:
        """TransformConfig should accept target override."""
        from floe_core.schemas import TransformConfig

        config = TransformConfig(type="dbt", path="./dbt", target="prod")
        assert config.target == "prod"

    def test_transform_config_is_frozen(self) -> None:
        """TransformConfig should be immutable (frozen)."""
        from floe_core.schemas import TransformConfig

        config = TransformConfig(type="dbt", path="./dbt")

        with pytest.raises(ValidationError):
            config.path = "./new-path"  # type: ignore[misc]

    def test_transform_config_rejects_extra_fields(self) -> None:
        """TransformConfig should reject unknown fields."""
        from floe_core.schemas import TransformConfig

        with pytest.raises(ValidationError) as exc_info:
            TransformConfig(
                type="dbt",
                path="./dbt",
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower()

    def test_transform_config_path_relative(self) -> None:
        """TransformConfig should accept relative paths."""
        from floe_core.schemas import TransformConfig

        config = TransformConfig(type="dbt", path="./transforms/dbt")
        assert config.path == "./transforms/dbt"

    def test_transform_config_path_absolute(self) -> None:
        """TransformConfig should accept absolute paths."""
        from floe_core.schemas import TransformConfig

        config = TransformConfig(type="dbt", path="/app/dbt")
        assert config.path == "/app/dbt"
