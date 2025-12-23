"""Unit tests for profile resolver.

T009: [Setup] Create test directory structure
T070-T075: [Phase 2] Will implement full test coverage for ProfileResolver

This module tests:
- Profile resolution from logical to concrete
- Storage, catalog, compute profile resolution
- Profile inheritance and overrides
- Missing profile error handling
"""

from __future__ import annotations

import pytest

from floe_core.compiler.profile_resolver import (
    DEFAULT_PROFILE_NAME,
    PROFILE_TYPES,
    ProfileResolutionError,
)


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


class TestProfileResolutionError:
    """Tests for ProfileResolutionError exception."""

    def test_exception_can_be_raised(self) -> None:
        """Verify exception can be raised and caught."""
        with pytest.raises(ProfileResolutionError):
            raise ProfileResolutionError("Test error")

    def test_exception_message(self) -> None:
        """Verify exception message is preserved."""
        try:
            raise ProfileResolutionError("Profile 'foo' not found")
        except ProfileResolutionError as e:
            assert "foo" in str(e)


# TODO(T070): Implement test_profile_resolver_class
# TODO(T071): Implement test_storage_profile_resolution
# TODO(T072): Implement test_catalog_profile_resolution
# TODO(T073): Implement test_compute_profile_resolution
# TODO(T074): Implement test_profile_inheritance
# TODO(T075): Implement test_missing_profile_error
