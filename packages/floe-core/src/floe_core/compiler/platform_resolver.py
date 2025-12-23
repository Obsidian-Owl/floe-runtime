"""Platform configuration resolver for floe-runtime.

This module handles loading and resolving platform.yaml configuration:
- PlatformResolver: Load platform.yaml from file or environment
- Environment variable fallback (FLOE_PLATFORM_ENV)
- Platform file discovery in standard locations
- Validation of loaded platform configuration
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import ClassVar

from floe_core.schemas.platform_spec import PlatformSpec

logger = logging.getLogger(__name__)

# Environment variable for platform environment selection
PLATFORM_ENV_VAR = "FLOE_PLATFORM_ENV"

# Default platform environment
DEFAULT_PLATFORM_ENV = "local"

# Standard platform file name
PLATFORM_FILE_NAME = "platform.yaml"

# Standard locations to search for platform.yaml
PLATFORM_SEARCH_PATHS = (
    Path("platform"),
    Path(".floe"),
    Path.home() / ".floe",
)


class PlatformNotFoundError(Exception):
    """Raised when platform.yaml cannot be found in any search path."""

    pass


def get_platform_env() -> str:
    """Get the current platform environment from environment variable.

    Returns:
        Platform environment name (local, dev, staging, prod)
    """
    return os.environ.get(PLATFORM_ENV_VAR, DEFAULT_PLATFORM_ENV)


class PlatformResolver:
    """Resolves platform configuration from environment and files.

    PlatformResolver handles loading platform.yaml configuration with:
    - Environment-based file selection (FLOE_PLATFORM_ENV)
    - Standard search path discovery
    - Caching for repeated access
    - Explicit file path override

    Attributes:
        env: The current platform environment (local, dev, staging, prod).
        search_paths: Ordered list of directories to search for platform.yaml.

    Example:
        >>> resolver = PlatformResolver()
        >>> platform = resolver.load()
        >>> storage = platform.get_storage_profile("default")
        >>> catalog = platform.get_catalog_profile("default")

        >>> # Override environment
        >>> resolver = PlatformResolver(env="production")
        >>> platform = resolver.load()

        >>> # Load from explicit path
        >>> platform = resolver.load(path=Path("custom/platform.yaml"))
    """

    _cache: ClassVar[dict[str, PlatformSpec]] = {}

    def __init__(
        self,
        env: str | None = None,
        search_paths: tuple[Path, ...] | None = None,
    ) -> None:
        """Initialize the PlatformResolver.

        Args:
            env: Platform environment override. If None, reads from
                FLOE_PLATFORM_ENV or defaults to "local".
            search_paths: Custom search paths for platform.yaml discovery.
                If None, uses PLATFORM_SEARCH_PATHS.
        """
        self.env = env or get_platform_env()
        self.search_paths = search_paths or PLATFORM_SEARCH_PATHS

    def _find_platform_file(self) -> Path:
        """Find platform.yaml in search paths for the current environment.

        Searches for platform.yaml in the following order:
        1. platform/{env}/platform.yaml
        2. .floe/{env}/platform.yaml
        3. ~/.floe/{env}/platform.yaml
        4. platform/platform.yaml (fallback)
        5. .floe/platform.yaml (fallback)
        6. ~/.floe/platform.yaml (fallback)

        Returns:
            Path to the platform.yaml file.

        Raises:
            PlatformNotFoundError: If no platform.yaml is found.
        """
        # First, try environment-specific paths
        for base_path in self.search_paths:
            env_path = base_path / self.env / PLATFORM_FILE_NAME
            if env_path.exists():
                logger.debug("Found platform.yaml at %s", env_path)
                return env_path

        # Fallback to non-environment-specific paths
        for base_path in self.search_paths:
            fallback_path = base_path / PLATFORM_FILE_NAME
            if fallback_path.exists():
                logger.debug(
                    "No env-specific platform.yaml found, using fallback at %s",
                    fallback_path,
                )
                return fallback_path

        # No platform.yaml found
        searched = [str(p / self.env / PLATFORM_FILE_NAME) for p in self.search_paths] + [
            str(p / PLATFORM_FILE_NAME) for p in self.search_paths
        ]

        raise PlatformNotFoundError(
            f"Platform configuration not found for environment '{self.env}'. "
            f"Searched: {', '.join(searched)}"
        )

    def load(
        self,
        path: Path | None = None,
        use_cache: bool = True,
    ) -> PlatformSpec:
        """Load platform configuration from file or discovery.

        Args:
            path: Explicit path to platform.yaml. If None, discovers via
                search paths and FLOE_PLATFORM_ENV.
            use_cache: Whether to use cached configuration. Set to False
                to force reload.

        Returns:
            Validated PlatformSpec instance.

        Raises:
            PlatformNotFoundError: If platform.yaml cannot be found.
            pydantic.ValidationError: If platform.yaml is invalid.
            FileNotFoundError: If explicit path doesn't exist.

        Example:
            >>> resolver = PlatformResolver()
            >>> # Auto-discover based on FLOE_PLATFORM_ENV
            >>> platform = resolver.load()

            >>> # Load from explicit path
            >>> platform = resolver.load(path=Path("platform/prod/platform.yaml"))

            >>> # Force reload (bypass cache)
            >>> platform = resolver.load(use_cache=False)
        """
        # Resolve the path (ternary for SIM108)
        resolved_path = path.resolve() if path is not None else self._find_platform_file().resolve()

        cache_key = str(resolved_path)

        # Check cache
        if use_cache and cache_key in self._cache:
            logger.debug("Using cached platform config from %s", resolved_path)
            return self._cache[cache_key]

        # Load and validate
        logger.info(
            "Loading platform configuration from %s (env=%s)",
            resolved_path,
            self.env,
        )
        platform = PlatformSpec.from_yaml(resolved_path)

        # Cache the result
        self._cache[cache_key] = platform

        return platform

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the platform configuration cache.

        Use when platform.yaml changes during runtime (e.g., in tests).
        """
        cls._cache.clear()
        logger.debug("Platform resolver cache cleared")

    @classmethod
    def load_default(cls) -> PlatformSpec:
        """Load platform configuration using default settings.

        Convenience method for simple use cases.

        Returns:
            Validated PlatformSpec instance.

        Raises:
            PlatformNotFoundError: If platform.yaml cannot be found.

        Example:
            >>> platform = PlatformResolver.load_default()
            >>> catalog = platform.get_catalog_profile()
        """
        return cls().load()
