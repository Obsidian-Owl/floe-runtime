"""Unit tests for profile resolver.

This module tests:
- Profile resolution from logical to concrete
- Storage, catalog, compute profile resolution
- ResolvedProfiles container
- Missing profile error handling
- Profile reference validation
"""

from __future__ import annotations

import pytest

from floe_core.compiler.profile_resolver import (
    DEFAULT_PROFILE_NAME,
    PROFILE_TYPES,
    ProfileResolver,
    ResolvedProfiles,
)
from floe_core.errors import ProfileNotFoundError
from floe_core.schemas.catalog_profile import CatalogProfile
from floe_core.schemas.compute_profile import ComputeProfile
from floe_core.schemas.platform_spec import PlatformSpec
from floe_core.schemas.storage_profile import StorageProfile


class TestProfileResolverConstants:
    """Tests for ProfileResolver module constants."""

    def test_default_profile_name(self) -> None:
        """Verify default profile name is 'default'."""
        assert DEFAULT_PROFILE_NAME == "default"

    def test_profile_types_defined(self) -> None:
        """Verify profile types are defined."""
        assert PROFILE_TYPES is not None
        assert "storage" in PROFILE_TYPES
        assert "catalog" in PROFILE_TYPES
        assert "compute" in PROFILE_TYPES


class TestProfileNotFoundError:
    """Tests for ProfileNotFoundError exception."""

    def test_exception_can_be_raised(self) -> None:
        """Verify exception can be raised and caught."""
        with pytest.raises(ProfileNotFoundError):
            raise ProfileNotFoundError(
                profile_type="storage",
                profile_name="test",
                available_profiles=["default"],
            )

    def test_exception_message(self) -> None:
        """Verify exception message contains profile info."""
        error = ProfileNotFoundError(
            profile_type="storage",
            profile_name="foo",
            available_profiles=["default"],
        )
        assert "foo" in str(error)
        assert "Storage" in str(error)

    def test_exception_attributes(self) -> None:
        """Verify exception preserves metadata."""
        error = ProfileNotFoundError(
            profile_type="storage",
            profile_name="prod",
            available_profiles=["default", "dev"],
        )
        assert error.profile_type == "storage"
        assert error.profile_name == "prod"
        assert "default" in error.available_profiles
        assert "dev" in error.available_profiles


@pytest.fixture
def platform_with_profiles() -> PlatformSpec:
    """Create PlatformSpec with all profile types."""
    return PlatformSpec(
        storage={
            "default": StorageProfile(bucket="default-bucket"),
            "production": StorageProfile(bucket="prod-bucket", region="us-east-1"),
        },
        catalogs={
            "default": CatalogProfile(
                uri="http://polaris:8181/api/catalog",
                warehouse="demo",
            ),
            "production": CatalogProfile(
                uri="http://polaris-prod:8181/api/catalog",
                warehouse="production",
            ),
        },
        compute={
            "default": ComputeProfile(),
            "snowflake": ComputeProfile(
                properties={"account": "acme.us-east-1"},
            ),
        },
    )


class TestProfileResolverInit:
    """Tests for ProfileResolver initialization."""

    def test_init_with_platform(self, platform_with_profiles: PlatformSpec) -> None:
        """ProfileResolver accepts PlatformSpec."""
        resolver = ProfileResolver(platform_with_profiles)
        assert resolver.platform is platform_with_profiles


class TestStorageProfileResolution:
    """Tests for storage profile resolution."""

    def test_resolve_default_storage(self, platform_with_profiles: PlatformSpec) -> None:
        """Resolves default storage profile."""
        resolver = ProfileResolver(platform_with_profiles)
        profile = resolver.resolve_storage()
        assert profile.bucket == "default-bucket"

    def test_resolve_named_storage(self, platform_with_profiles: PlatformSpec) -> None:
        """Resolves named storage profile."""
        resolver = ProfileResolver(platform_with_profiles)
        profile = resolver.resolve_storage("production")
        assert profile.bucket == "prod-bucket"

    def test_resolve_storage_none_uses_default(self, platform_with_profiles: PlatformSpec) -> None:
        """None profile name resolves to default."""
        resolver = ProfileResolver(platform_with_profiles)
        profile = resolver.resolve_storage(None)
        assert profile.bucket == "default-bucket"

    def test_resolve_storage_not_found(self, platform_with_profiles: PlatformSpec) -> None:
        """Missing storage profile raises error."""
        resolver = ProfileResolver(platform_with_profiles)
        with pytest.raises(ProfileNotFoundError) as exc_info:
            resolver.resolve_storage("nonexistent")
        assert "nonexistent" in str(exc_info.value)
        assert exc_info.value.profile_type == "storage"
        assert "default" in exc_info.value.available_profiles


class TestCatalogProfileResolution:
    """Tests for catalog profile resolution."""

    def test_resolve_default_catalog(self, platform_with_profiles: PlatformSpec) -> None:
        """Resolves default catalog profile."""
        resolver = ProfileResolver(platform_with_profiles)
        profile = resolver.resolve_catalog()
        assert profile.warehouse == "demo"

    def test_resolve_named_catalog(self, platform_with_profiles: PlatformSpec) -> None:
        """Resolves named catalog profile."""
        resolver = ProfileResolver(platform_with_profiles)
        profile = resolver.resolve_catalog("production")
        assert profile.warehouse == "production"

    def test_resolve_catalog_not_found(self, platform_with_profiles: PlatformSpec) -> None:
        """Missing catalog profile raises error."""
        resolver = ProfileResolver(platform_with_profiles)
        with pytest.raises(ProfileNotFoundError) as exc_info:
            resolver.resolve_catalog("nonexistent")
        assert exc_info.value.profile_type == "catalog"


class TestComputeProfileResolution:
    """Tests for compute profile resolution."""

    def test_resolve_default_compute(self, platform_with_profiles: PlatformSpec) -> None:
        """Resolves default compute profile."""
        resolver = ProfileResolver(platform_with_profiles)
        profile = resolver.resolve_compute()
        assert profile is not None

    def test_resolve_named_compute(self, platform_with_profiles: PlatformSpec) -> None:
        """Resolves named compute profile."""
        resolver = ProfileResolver(platform_with_profiles)
        profile = resolver.resolve_compute("snowflake")
        assert "account" in profile.properties

    def test_resolve_compute_not_found(self, platform_with_profiles: PlatformSpec) -> None:
        """Missing compute profile raises error."""
        resolver = ProfileResolver(platform_with_profiles)
        with pytest.raises(ProfileNotFoundError) as exc_info:
            resolver.resolve_compute("nonexistent")
        assert exc_info.value.profile_type == "compute"


class TestResolveAll:
    """Tests for resolve_all method."""

    def test_resolve_all_defaults(self, platform_with_profiles: PlatformSpec) -> None:
        """Resolves all profiles with defaults."""
        resolver = ProfileResolver(platform_with_profiles)
        profiles = resolver.resolve_all()

        assert isinstance(profiles, ResolvedProfiles)
        assert profiles.storage.bucket == "default-bucket"
        assert profiles.catalog.warehouse == "demo"
        assert profiles.compute is not None

    def test_resolve_all_named(self, platform_with_profiles: PlatformSpec) -> None:
        """Resolves all profiles with named references."""
        resolver = ProfileResolver(platform_with_profiles)
        profiles = resolver.resolve_all(
            storage="production",
            catalog="production",
            compute="snowflake",
        )

        assert profiles.storage.bucket == "prod-bucket"
        assert profiles.catalog.warehouse == "production"
        assert "account" in profiles.compute.properties

    def test_resolve_all_mixed(self, platform_with_profiles: PlatformSpec) -> None:
        """Resolves mix of default and named profiles."""
        resolver = ProfileResolver(platform_with_profiles)
        profiles = resolver.resolve_all(
            storage="production",
            catalog=None,  # Use default
            compute="default",
        )

        assert profiles.storage.bucket == "prod-bucket"
        assert profiles.catalog.warehouse == "demo"


class TestResolvedProfiles:
    """Tests for ResolvedProfiles container."""

    def test_resolved_profiles_immutable(self, platform_with_profiles: PlatformSpec) -> None:
        """ResolvedProfiles is frozen dataclass."""
        resolver = ProfileResolver(platform_with_profiles)
        profiles = resolver.resolve_all()

        # Should be immutable
        with pytest.raises(AttributeError):
            profiles.storage = StorageProfile(bucket="hacked")  # type: ignore[misc]


class TestValidateReferences:
    """Tests for validate_references method."""

    def test_validate_all_valid(self, platform_with_profiles: PlatformSpec) -> None:
        """Valid references return empty error list."""
        resolver = ProfileResolver(platform_with_profiles)
        errors = resolver.validate_references(
            storage="default",
            catalog="default",
            compute="default",
        )
        assert errors == []

    def test_validate_invalid_storage(self, platform_with_profiles: PlatformSpec) -> None:
        """Invalid storage reference returns error."""
        resolver = ProfileResolver(platform_with_profiles)
        errors = resolver.validate_references(
            storage="nonexistent",
            catalog="default",
            compute="default",
        )
        assert len(errors) == 1
        assert "storage" in errors[0].lower()

    def test_validate_multiple_invalid(self, platform_with_profiles: PlatformSpec) -> None:
        """Multiple invalid references return multiple errors."""
        resolver = ProfileResolver(platform_with_profiles)
        errors = resolver.validate_references(
            storage="bad-storage",
            catalog="bad-catalog",
            compute="bad-compute",
        )
        assert len(errors) == 3


class TestEmptyPlatform:
    """Tests with empty platform spec."""

    def test_resolve_from_empty_platform(self) -> None:
        """Resolving from empty platform raises errors."""
        platform = PlatformSpec()
        resolver = ProfileResolver(platform)

        with pytest.raises(ProfileNotFoundError) as exc_info:
            resolver.resolve_storage()
        assert "none" in str(exc_info.value).lower()

    def test_validate_empty_platform(self) -> None:
        """Validating against empty platform reports all missing."""
        platform = PlatformSpec()
        resolver = ProfileResolver(platform)

        errors = resolver.validate_references()
        assert len(errors) == 3
