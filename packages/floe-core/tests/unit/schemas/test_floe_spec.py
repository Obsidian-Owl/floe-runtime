"""Unit tests for FloeSpec model.

T017: [US1] Unit tests for FloeSpec validation
T035: [US2] Unit tests for FloeSpec profile references

Tests FloeSpec root model with name/version validation and profile references.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from floe_core.schemas.floe_spec import (
    DEFAULT_PROFILE_NAME,
    PROFILE_NAME_PATTERN,
    FloeSpec,
)


class TestFloeSpecConstants:
    """Tests for FloeSpec module constants."""

    def test_default_profile_name(self) -> None:
        """Verify default profile name is 'default'."""
        assert DEFAULT_PROFILE_NAME == "default"

    def test_profile_name_pattern_defined(self) -> None:
        """Verify profile name pattern is defined."""
        assert PROFILE_NAME_PATTERN is not None
        assert "a-zA-Z" in PROFILE_NAME_PATTERN


class TestFloeSpecRequired:
    """Tests for FloeSpec required fields."""

    def test_floe_spec_requires_name(self) -> None:
        """FloeSpec should require name field."""
        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(
                version="1.0.0",
            )  # type: ignore[call-arg]

        assert "name" in str(exc_info.value)

    def test_floe_spec_requires_version(self) -> None:
        """FloeSpec should require version field."""
        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(
                name="test-project",
            )  # type: ignore[call-arg]

        assert "version" in str(exc_info.value)


class TestFloeSpecMinimal:
    """Tests for minimal FloeSpec configuration."""

    def test_floe_spec_minimal_valid(self) -> None:
        """FloeSpec should accept minimal valid configuration."""
        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
        )
        assert spec.name == "test-project"
        assert spec.version == "1.0.0"
        # Profile references default to "default"
        assert spec.storage == "default"
        assert spec.catalog == "default"
        assert spec.compute == "default"

    def test_floe_spec_with_profile_references(self) -> None:
        """FloeSpec should accept profile references."""
        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
            storage="production",
            catalog="analytics",
            compute="snowflake",
        )
        assert spec.storage == "production"
        assert spec.catalog == "analytics"
        assert spec.compute == "snowflake"


class TestFloeSpecNameValidation:
    """Tests for FloeSpec name validation."""

    def test_floe_spec_name_valid_alphanumeric(self) -> None:
        """FloeSpec should accept alphanumeric names."""
        spec = FloeSpec(
            name="myproject123",
            version="1.0.0",
        )
        assert spec.name == "myproject123"

    def test_floe_spec_name_valid_with_hyphens(self) -> None:
        """FloeSpec should accept names with hyphens."""
        spec = FloeSpec(
            name="my-test-project",
            version="1.0.0",
        )
        assert spec.name == "my-test-project"

    def test_floe_spec_name_valid_with_underscores(self) -> None:
        """FloeSpec should accept names with underscores."""
        spec = FloeSpec(
            name="my_test_project",
            version="1.0.0",
        )
        assert spec.name == "my_test_project"

    def test_floe_spec_name_invalid_starts_with_number(self) -> None:
        """FloeSpec should reject names starting with number."""
        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(
                name="123project",
                version="1.0.0",
            )

        assert "name" in str(exc_info.value)

    def test_floe_spec_name_invalid_starts_with_hyphen(self) -> None:
        """FloeSpec should reject names starting with hyphen."""
        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(
                name="-project",
                version="1.0.0",
            )

        assert "name" in str(exc_info.value)

    def test_floe_spec_name_invalid_special_chars(self) -> None:
        """FloeSpec should reject names with special characters."""
        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(
                name="my@project!",
                version="1.0.0",
            )

        assert "name" in str(exc_info.value)

    def test_floe_spec_name_too_long(self) -> None:
        """FloeSpec should reject names exceeding 100 characters."""
        long_name = "a" * 101
        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(
                name=long_name,
                version="1.0.0",
            )

        assert "name" in str(exc_info.value)

    def test_floe_spec_name_max_length(self) -> None:
        """FloeSpec should accept names at max length (100 chars)."""
        max_name = "a" * 100
        spec = FloeSpec(
            name=max_name,
            version="1.0.0",
        )
        assert len(spec.name) == 100


class TestFloeSpecVersionValidation:
    """Tests for FloeSpec version validation."""

    def test_floe_spec_version_valid_semver(self) -> None:
        """FloeSpec should accept valid semver versions."""
        spec = FloeSpec(
            name="test-project",
            version="2.1.3",
        )
        assert spec.version == "2.1.3"

    def test_floe_spec_version_with_prerelease(self) -> None:
        """FloeSpec should accept semver with prerelease."""
        spec = FloeSpec(
            name="test-project",
            version="1.0.0-beta",
        )
        assert spec.version == "1.0.0-beta"

    def test_floe_spec_version_with_build_metadata(self) -> None:
        """FloeSpec should accept semver with build metadata."""
        spec = FloeSpec(
            name="test-project",
            version="1.0.0+build.123",
        )
        assert spec.version == "1.0.0+build.123"


class TestFloeSpecProfileReferences:
    """Tests for FloeSpec profile reference validation (Two-Tier Architecture)."""

    def test_storage_profile_default(self) -> None:
        """Storage profile defaults to 'default'."""
        spec = FloeSpec(name="test", version="1.0.0")
        assert spec.storage == "default"

    def test_catalog_profile_default(self) -> None:
        """Catalog profile defaults to 'default'."""
        spec = FloeSpec(name="test", version="1.0.0")
        assert spec.catalog == "default"

    def test_compute_profile_default(self) -> None:
        """Compute profile defaults to 'default'."""
        spec = FloeSpec(name="test", version="1.0.0")
        assert spec.compute == "default"

    def test_storage_profile_valid_name(self) -> None:
        """Storage profile accepts valid profile names."""
        spec = FloeSpec(name="test", version="1.0.0", storage="production")
        assert spec.storage == "production"

    def test_catalog_profile_valid_name(self) -> None:
        """Catalog profile accepts valid profile names."""
        spec = FloeSpec(name="test", version="1.0.0", catalog="analytics")
        assert spec.catalog == "analytics"

    def test_compute_profile_valid_name(self) -> None:
        """Compute profile accepts valid profile names."""
        spec = FloeSpec(name="test", version="1.0.0", compute="snowflake-prod")
        assert spec.compute == "snowflake-prod"

    def test_profile_name_with_underscore(self) -> None:
        """Profile names can contain underscores."""
        spec = FloeSpec(name="test", version="1.0.0", storage="prod_archive")
        assert spec.storage == "prod_archive"

    def test_profile_name_with_hyphen(self) -> None:
        """Profile names can contain hyphens."""
        spec = FloeSpec(name="test", version="1.0.0", catalog="prod-analytics")
        assert spec.catalog == "prod-analytics"

    def test_profile_name_invalid_starts_with_number(self) -> None:
        """Profile names cannot start with a number."""
        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(name="test", version="1.0.0", storage="123bucket")
        assert "storage" in str(exc_info.value)

    def test_profile_name_invalid_starts_with_hyphen(self) -> None:
        """Profile names cannot start with a hyphen."""
        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(name="test", version="1.0.0", catalog="-analytics")
        assert "catalog" in str(exc_info.value)

    def test_profile_name_invalid_special_chars(self) -> None:
        """Profile names cannot contain special characters."""
        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(name="test", version="1.0.0", compute="prod@cluster")
        assert "compute" in str(exc_info.value)


class TestFloeSpecDefaults:
    """Tests for FloeSpec default values."""

    def test_floe_spec_transforms_default_empty(self) -> None:
        """FloeSpec.transforms should default to empty list."""
        from floe_core.schemas import FloeSpec

        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
        )
        assert spec.transforms == []

    def test_floe_spec_with_transforms(self) -> None:
        """FloeSpec should accept transforms list."""
        from floe_core.schemas import FloeSpec, TransformConfig

        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
            transforms=[TransformConfig(type="dbt", path="./dbt")],
        )
        assert len(spec.transforms) == 1
        assert spec.transforms[0].type == "dbt"

    def test_floe_spec_consumption_default(self) -> None:
        """FloeSpec.consumption should have default ConsumptionConfig."""
        from floe_core.schemas import ConsumptionConfig, FloeSpec

        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
        )
        assert isinstance(spec.consumption, ConsumptionConfig)
        assert spec.consumption.enabled is False

    def test_floe_spec_governance_default(self) -> None:
        """FloeSpec.governance should have default GovernanceConfig."""
        from floe_core.schemas import FloeSpec, GovernanceConfig

        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
        )
        assert isinstance(spec.governance, GovernanceConfig)
        assert spec.governance.classification_source == "dbt_meta"

    def test_floe_spec_observability_default(self) -> None:
        """FloeSpec.observability should have default ObservabilityConfig."""
        from floe_core.schemas import FloeSpec, ObservabilityConfig

        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
        )
        assert isinstance(spec.observability, ObservabilityConfig)
        assert spec.observability.traces is True


class TestFloeSpecImmutability:
    """Tests for FloeSpec immutability and validation."""

    def test_floe_spec_is_frozen(self) -> None:
        """FloeSpec should be immutable."""
        spec = FloeSpec(
            name="test-project",
            version="1.0.0",
        )

        with pytest.raises(ValidationError):
            spec.name = "new-name"

    def test_floe_spec_rejects_extra_fields(self) -> None:
        """FloeSpec should reject unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            FloeSpec(
                name="test-project",
                version="1.0.0",
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower()

    def test_floe_spec_default_factory_isolation(self) -> None:
        """FloeSpec defaults should be isolated (no shared state)."""
        spec1 = FloeSpec(
            name="project1",
            version="1.0.0",
        )
        spec2 = FloeSpec(
            name="project2",
            version="1.0.0",
        )

        # Verify they are independent objects
        assert spec1 is not spec2
        assert spec1.transforms is not spec2.transforms
        assert spec1.consumption is not spec2.consumption
        assert spec1.governance is not spec2.governance
        assert spec1.observability is not spec2.observability


class TestFloeSpecZeroSecrets:
    """Tests verifying FloeSpec contains no infrastructure details (FR-012)."""

    def test_no_credentials_field(self) -> None:
        """FloeSpec should not have credentials field."""
        spec = FloeSpec(name="test", version="1.0.0")
        assert not hasattr(spec, "credentials")

    def test_no_endpoint_fields(self) -> None:
        """FloeSpec should not have endpoint/uri fields."""
        spec = FloeSpec(name="test", version="1.0.0")
        assert not hasattr(spec, "endpoint")
        assert not hasattr(spec, "uri")

    def test_no_secret_fields(self) -> None:
        """FloeSpec should not have secret_ref fields."""
        spec = FloeSpec(name="test", version="1.0.0")
        assert not hasattr(spec, "secret_ref")

    def test_profile_references_are_strings(self) -> None:
        """All profile references should be simple strings, not objects."""
        spec = FloeSpec(
            name="test",
            version="1.0.0",
            storage="prod",
            catalog="analytics",
            compute="snowflake",
        )
        assert isinstance(spec.storage, str)
        assert isinstance(spec.catalog, str)
        assert isinstance(spec.compute, str)
