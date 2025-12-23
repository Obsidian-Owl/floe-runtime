"""Unit tests for platform resolver.

T009: [Setup] Create test directory structure
T064-T069: [Phase 2] Will implement full test coverage for PlatformResolver

This module tests:
- Platform file discovery
- Environment variable fallback
- Platform.yaml loading and validation
- Missing platform config error handling
"""

from __future__ import annotations

import pytest

from floe_core.compiler.platform_resolver import (
    DEFAULT_PLATFORM_ENV,
    PLATFORM_ENV_VAR,
    PLATFORM_FILE_NAME,
    get_platform_env,
)


class TestPlatformResolverConstants:
    """Tests for PlatformResolver module constants."""

    def test_platform_env_var_defined(self) -> None:
        """Verify platform environment variable name is defined."""
        assert PLATFORM_ENV_VAR == "FLOE_PLATFORM_ENV"

    def test_default_platform_env(self) -> None:
        """Verify default platform environment is local."""
        assert DEFAULT_PLATFORM_ENV == "local"

    def test_platform_file_name(self) -> None:
        """Verify platform file name is defined."""
        assert PLATFORM_FILE_NAME == "platform.yaml"


class TestGetPlatformEnv:
    """Tests for get_platform_env function."""

    def test_returns_default_when_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns default environment when env var not set."""
        monkeypatch.delenv(PLATFORM_ENV_VAR, raising=False)
        assert get_platform_env() == DEFAULT_PLATFORM_ENV

    def test_returns_env_var_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Returns environment from env var when set."""
        monkeypatch.setenv(PLATFORM_ENV_VAR, "prod")
        assert get_platform_env() == "prod"


# TODO(T064): Implement test_platform_resolver_class
# TODO(T065): Implement test_platform_file_discovery
# TODO(T066): Implement test_environment_based_selection
# TODO(T067): Implement test_platform_yaml_loading
# TODO(T068): Implement test_platform_config_caching
# TODO(T069): Implement test_missing_platform_error
