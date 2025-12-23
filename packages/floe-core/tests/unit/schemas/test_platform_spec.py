"""Unit tests for platform specification models.

T009: [Setup] Create test directory structure
T052-T058: [Phase 2] Will implement full test coverage for PlatformSpec

This module tests:
- PlatformSpec parsing and validation
- Environment-specific configuration
- Profile reference validation
- Schema export for IDE autocomplete
"""

from __future__ import annotations

from floe_core.schemas.platform_spec import (
    ENVIRONMENT_TYPES,
    PLATFORM_SPEC_VERSION,
)


class TestPlatformSpecConstants:
    """Tests for PlatformSpec module constants."""

    def test_environment_types_defined(self) -> None:
        """Verify environment types are defined."""
        assert ENVIRONMENT_TYPES is not None
        assert "local" in ENVIRONMENT_TYPES
        assert "prod" in ENVIRONMENT_TYPES

    def test_platform_spec_version(self) -> None:
        """Verify platform spec version is set."""
        assert PLATFORM_SPEC_VERSION == "1.0.0"


# TODO(T052): Implement test_platform_spec_parsing
# TODO(T053): Implement test_platform_spec_validation
# TODO(T054): Implement test_storage_profiles_container
# TODO(T055): Implement test_catalog_profiles_container
# TODO(T056): Implement test_compute_profiles_container
# TODO(T057): Implement test_observability_config
# TODO(T058): Implement test_environment_specific_config
