"""Unit tests for FloeSpec model.

T017: [US1] Unit tests for FloeSpec validation
Tests FloeSpec root model with name/version validation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestFloeSpec:
    """Tests for FloeSpec root model."""

    def test_floe_spec_requires_name(self) -> None:
        """FloeSpec should require name field."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(
                version="1.0.0",
                compute=ComputeConfig(target=ComputeTarget.duckdb),
            )  # type: ignore[call-arg]

        assert "name" in str(exc_info.value)

    def test_floe_spec_requires_version(self) -> None:
        """FloeSpec should require version field."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(
                name="test-project",
                compute=ComputeConfig(target=ComputeTarget.duckdb),
            )  # type: ignore[call-arg]

        assert "version" in str(exc_info.value)

    def test_floe_spec_requires_compute(self) -> None:
        """FloeSpec should require compute field."""
        from floe_core.schemas import FloeSpec

        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(
                name="test-project",
                version="1.0.0",
            )  # type: ignore[call-arg]

        assert "compute" in str(exc_info.value)

    def test_floe_spec_minimal_valid(self) -> None:
        """FloeSpec should accept minimal valid configuration."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
        )
        assert spec.name == "test-project"
        assert spec.version == "1.0.0"
        assert spec.compute.target == ComputeTarget.duckdb

    def test_floe_spec_name_valid_alphanumeric(self) -> None:
        """FloeSpec should accept alphanumeric names."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        spec = FloeSpec(
            name="myproject123",
            version="1.0.0",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
        )
        assert spec.name == "myproject123"

    def test_floe_spec_name_valid_with_hyphens(self) -> None:
        """FloeSpec should accept names with hyphens."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        spec = FloeSpec(
            name="my-test-project",
            version="1.0.0",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
        )
        assert spec.name == "my-test-project"

    def test_floe_spec_name_valid_with_underscores(self) -> None:
        """FloeSpec should accept names with underscores."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        spec = FloeSpec(
            name="my_test_project",
            version="1.0.0",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
        )
        assert spec.name == "my_test_project"

    def test_floe_spec_name_invalid_starts_with_number(self) -> None:
        """FloeSpec should reject names starting with number."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(
                name="123project",
                version="1.0.0",
                compute=ComputeConfig(target=ComputeTarget.duckdb),
            )

        assert "name" in str(exc_info.value)

    def test_floe_spec_name_invalid_starts_with_hyphen(self) -> None:
        """FloeSpec should reject names starting with hyphen."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(
                name="-project",
                version="1.0.0",
                compute=ComputeConfig(target=ComputeTarget.duckdb),
            )

        assert "name" in str(exc_info.value)

    def test_floe_spec_name_invalid_special_chars(self) -> None:
        """FloeSpec should reject names with special characters."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(
                name="my@project!",
                version="1.0.0",
                compute=ComputeConfig(target=ComputeTarget.duckdb),
            )

        assert "name" in str(exc_info.value)

    def test_floe_spec_name_too_long(self) -> None:
        """FloeSpec should reject names exceeding 100 characters."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        long_name = "a" * 101
        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(
                name=long_name,
                version="1.0.0",
                compute=ComputeConfig(target=ComputeTarget.duckdb),
            )

        assert "name" in str(exc_info.value)

    def test_floe_spec_name_max_length(self) -> None:
        """FloeSpec should accept names at max length (100 chars)."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        max_name = "a" * 100
        spec = FloeSpec(
            name=max_name,
            version="1.0.0",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
        )
        assert len(spec.name) == 100

    def test_floe_spec_version_valid_semver(self) -> None:
        """FloeSpec should accept valid semver versions."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        spec = FloeSpec(
            name="test-project",
            version="2.1.3",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
        )
        assert spec.version == "2.1.3"

    def test_floe_spec_version_with_prerelease(self) -> None:
        """FloeSpec should accept semver with prerelease."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        spec = FloeSpec(
            name="test-project",
            version="1.0.0-beta",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
        )
        assert spec.version == "1.0.0-beta"

    def test_floe_spec_version_with_build_metadata(self) -> None:
        """FloeSpec should accept semver with build metadata."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        spec = FloeSpec(
            name="test-project",
            version="1.0.0+build.123",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
        )
        assert spec.version == "1.0.0+build.123"

    def test_floe_spec_transforms_default_empty(self) -> None:
        """FloeSpec.transforms should default to empty list."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
        )
        assert spec.transforms == []

    def test_floe_spec_with_transforms(self) -> None:
        """FloeSpec should accept transforms list."""
        from floe_core.schemas import (
            ComputeConfig,
            ComputeTarget,
            FloeSpec,
            TransformConfig,
        )

        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
            transforms=[TransformConfig(type="dbt", path="./dbt")],
        )
        assert len(spec.transforms) == 1
        assert spec.transforms[0].type == "dbt"

    def test_floe_spec_consumption_default(self) -> None:
        """FloeSpec.consumption should have default ConsumptionConfig."""
        from floe_core.schemas import (
            ComputeConfig,
            ComputeTarget,
            ConsumptionConfig,
            FloeSpec,
        )

        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
        )
        assert isinstance(spec.consumption, ConsumptionConfig)
        assert spec.consumption.enabled is False

    def test_floe_spec_governance_default(self) -> None:
        """FloeSpec.governance should have default GovernanceConfig."""
        from floe_core.schemas import (
            ComputeConfig,
            ComputeTarget,
            FloeSpec,
            GovernanceConfig,
        )

        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
        )
        assert isinstance(spec.governance, GovernanceConfig)
        assert spec.governance.classification_source == "dbt_meta"

    def test_floe_spec_observability_default(self) -> None:
        """FloeSpec.observability should have default ObservabilityConfig."""
        from floe_core.schemas import (
            ComputeConfig,
            ComputeTarget,
            FloeSpec,
            ObservabilityConfig,
        )

        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
        )
        assert isinstance(spec.observability, ObservabilityConfig)
        assert spec.observability.traces is True

    def test_floe_spec_catalog_optional(self) -> None:
        """FloeSpec.catalog should be optional (None by default)."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
        )
        assert spec.catalog is None

    def test_floe_spec_with_catalog(self) -> None:
        """FloeSpec should accept catalog configuration."""
        from floe_core.schemas import (
            CatalogConfig,
            ComputeConfig,
            ComputeTarget,
            FloeSpec,
        )

        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
            catalog=CatalogConfig(
                type="polaris",
                uri="http://polaris:8181/api/catalog",
            ),
        )
        assert spec.catalog is not None
        assert spec.catalog.type == "polaris"

    def test_floe_spec_is_frozen(self) -> None:
        """FloeSpec should be immutable."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
        )

        with pytest.raises(ValidationError):
            spec.name = "new-name"  # type: ignore[misc]

    def test_floe_spec_rejects_extra_fields(self) -> None:
        """FloeSpec should reject unknown fields."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(
                name="test-project",
                version="1.0.0",
                compute=ComputeConfig(target=ComputeTarget.duckdb),
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower()

    def test_floe_spec_default_factory_isolation(self) -> None:
        """FloeSpec defaults should be isolated (no shared state)."""
        from floe_core.schemas import ComputeConfig, ComputeTarget, FloeSpec

        spec1 = FloeSpec(
            name="project1",
            version="1.0.0",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
        )
        spec2 = FloeSpec(
            name="project2",
            version="1.0.0",
            compute=ComputeConfig(target=ComputeTarget.duckdb),
        )

        # Verify they are independent objects
        assert spec1 is not spec2
        assert spec1.transforms is not spec2.transforms
        assert spec1.consumption is not spec2.consumption
        assert spec1.governance is not spec2.governance
        assert spec1.observability is not spec2.observability
