"""Unit tests for platform resolver.

This module tests:
- Platform file discovery
- Environment variable fallback
- Platform.yaml loading and validation
- Missing platform config error handling
- Caching behavior
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from floe_core.compiler.platform_resolver import (
    DEFAULT_PLATFORM_ENV,
    PLATFORM_ENV_VAR,
    PLATFORM_FILE_NAME,
    PlatformNotFoundError,
    PlatformResolver,
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


class TestPlatformResolverInit:
    """Tests for PlatformResolver initialization."""

    def test_default_init(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Default init uses environment variable."""
        monkeypatch.delenv(PLATFORM_ENV_VAR, raising=False)
        resolver = PlatformResolver()
        assert resolver.env == "local"

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Explicit env parameter overrides environment variable."""
        monkeypatch.setenv(PLATFORM_ENV_VAR, "production")
        resolver = PlatformResolver(env="dev")
        assert resolver.env == "dev"

    def test_custom_search_paths(self) -> None:
        """Custom search paths are accepted."""
        custom_paths = (Path("/custom/path1"), Path("/custom/path2"))
        resolver = PlatformResolver(search_paths=custom_paths)
        assert resolver.search_paths == custom_paths


class TestPlatformFileDiscovery:
    """Tests for platform file discovery logic."""

    def test_find_env_specific_file(self, tmp_path: Path) -> None:
        """Finds environment-specific platform.yaml."""
        env_dir = tmp_path / "platform" / "local"
        env_dir.mkdir(parents=True)
        platform_file = env_dir / PLATFORM_FILE_NAME
        platform_file.write_text("version: '1.0.0'\n")

        resolver = PlatformResolver(
            env="local",
            search_paths=(tmp_path / "platform",),
        )
        found = resolver._find_platform_file()
        assert found == platform_file

    def test_find_fallback_file(self, tmp_path: Path) -> None:
        """Falls back to non-env-specific platform.yaml."""
        platform_dir = tmp_path / "platform"
        platform_dir.mkdir(parents=True)
        platform_file = platform_dir / PLATFORM_FILE_NAME
        platform_file.write_text("version: '1.0.0'\n")

        resolver = PlatformResolver(
            env="local",
            search_paths=(tmp_path / "platform",),
        )
        found = resolver._find_platform_file()
        assert found == platform_file

    def test_not_found_raises_error(self, tmp_path: Path) -> None:
        """Raises PlatformNotFoundError when file not found."""
        resolver = PlatformResolver(
            env="local",
            search_paths=(tmp_path / "nonexistent",),
        )
        with pytest.raises(PlatformNotFoundError) as exc_info:
            resolver._find_platform_file()
        assert "local" in str(exc_info.value)

    def test_search_order_prefers_env_specific(self, tmp_path: Path) -> None:
        """Environment-specific file is preferred over fallback."""
        platform_dir = tmp_path / "platform"

        # Create fallback file
        platform_dir.mkdir(parents=True)
        fallback_file = platform_dir / PLATFORM_FILE_NAME
        fallback_file.write_text("version: '1.0.0'\n# fallback")

        # Create env-specific file
        env_dir = platform_dir / "local"
        env_dir.mkdir()
        env_file = env_dir / PLATFORM_FILE_NAME
        env_file.write_text("version: '1.0.0'\n# env-specific")

        resolver = PlatformResolver(
            env="local",
            search_paths=(platform_dir,),
        )
        found = resolver._find_platform_file()
        assert found == env_file
        assert "env-specific" in found.read_text()


class TestPlatformResolverLoad:
    """Tests for PlatformResolver.load method."""

    def test_load_from_explicit_path(self, tmp_path: Path) -> None:
        """Loads platform.yaml from explicit path."""
        platform_file = tmp_path / "custom" / "platform.yaml"
        platform_file.parent.mkdir(parents=True)
        platform_file.write_text("""
version: "1.0.0"
storage:
  default:
    bucket: test-bucket
""")

        resolver = PlatformResolver()
        PlatformResolver.clear_cache()

        platform = resolver.load(path=platform_file)
        assert platform.version == "1.0.0"
        assert "default" in platform.storage
        assert platform.storage["default"].bucket == "test-bucket"

    def test_load_from_discovery(self, tmp_path: Path) -> None:
        """Loads platform.yaml via discovery."""
        env_dir = tmp_path / "platform" / "local"
        env_dir.mkdir(parents=True)
        platform_file = env_dir / PLATFORM_FILE_NAME
        platform_file.write_text("""
version: "1.0.0"
catalogs:
  default:
    uri: http://localhost:8181/api/catalog
    warehouse: demo
""")

        resolver = PlatformResolver(
            env="local",
            search_paths=(tmp_path / "platform",),
        )
        PlatformResolver.clear_cache()

        platform = resolver.load()
        assert platform.version == "1.0.0"
        assert "default" in platform.catalogs


class TestPlatformResolverCaching:
    """Tests for PlatformResolver caching behavior."""

    def test_caching_returns_same_instance(self, tmp_path: Path) -> None:
        """Caches loaded platform configuration."""
        platform_file = tmp_path / "platform.yaml"
        platform_file.write_text("version: '1.0.0'\n")

        resolver = PlatformResolver()
        PlatformResolver.clear_cache()

        platform1 = resolver.load(path=platform_file)
        platform2 = resolver.load(path=platform_file)
        assert platform1 is platform2

    def test_bypass_cache(self, tmp_path: Path) -> None:
        """Can bypass cache with use_cache=False."""
        platform_file = tmp_path / "platform.yaml"
        platform_file.write_text("version: '1.0.0'\n")

        resolver = PlatformResolver()
        PlatformResolver.clear_cache()

        platform1 = resolver.load(path=platform_file)
        platform2 = resolver.load(path=platform_file, use_cache=False)

        # Different instances
        assert platform1 is not platform2
        # But equal content
        assert platform1.version == platform2.version

    def test_clear_cache(self, tmp_path: Path) -> None:
        """Cache can be cleared."""
        platform_file = tmp_path / "platform.yaml"
        platform_file.write_text("version: '1.0.0'\n")

        resolver = PlatformResolver()
        PlatformResolver.clear_cache()

        platform1 = resolver.load(path=platform_file)
        PlatformResolver.clear_cache()
        platform2 = resolver.load(path=platform_file)

        assert platform1 is not platform2


class TestPlatformResolverLoadDefault:
    """Tests for PlatformResolver.load_default class method."""

    def test_load_default_convenience(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """load_default provides convenient one-liner."""
        env_dir = tmp_path / "platform" / "local"
        env_dir.mkdir(parents=True)
        platform_file = env_dir / PLATFORM_FILE_NAME
        platform_file.write_text("version: '1.0.0'\n")

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv(PLATFORM_ENV_VAR, raising=False)
        PlatformResolver.clear_cache()

        platform = PlatformResolver.load_default()
        assert platform.version == "1.0.0"


class TestPlatformResolverErrors:
    """Tests for PlatformResolver error handling."""

    def test_invalid_yaml_raises_validation_error(self, tmp_path: Path) -> None:
        """Invalid YAML raises ValidationError."""
        platform_file = tmp_path / "platform.yaml"
        platform_file.write_text("version: 'invalid-version'\n")

        resolver = PlatformResolver()
        PlatformResolver.clear_cache()

        with pytest.raises(ValidationError):
            resolver.load(path=platform_file)

    def test_missing_explicit_path_raises_error(self, tmp_path: Path) -> None:
        """Missing explicit path raises FileNotFoundError."""
        resolver = PlatformResolver()
        missing_path = tmp_path / "nonexistent" / "platform.yaml"

        with pytest.raises(FileNotFoundError):
            resolver.load(path=missing_path)
