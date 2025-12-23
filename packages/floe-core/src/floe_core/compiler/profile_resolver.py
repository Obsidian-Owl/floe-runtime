"""Profile resolver for floe-runtime.

This module handles resolving logical profile references to concrete configurations:
- ProfileResolver: Resolve 'default' → actual StorageProfile, CatalogProfile, etc.
- Merge FloeSpec logical refs with PlatformSpec concrete profiles
- Profile inheritance and override logic
- Validation of profile references
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from floe_core.errors import ProfileNotFoundError

if TYPE_CHECKING:
    from floe_core.schemas.catalog_profile import CatalogProfile
    from floe_core.schemas.compute_profile import ComputeProfile
    from floe_core.schemas.platform_spec import PlatformSpec
    from floe_core.schemas.storage_profile import StorageProfile

logger = logging.getLogger(__name__)

# Default profile name used when not specified
DEFAULT_PROFILE_NAME = "default"

# Profile type identifiers
PROFILE_TYPES = frozenset({"storage", "catalog", "compute"})


@dataclass(frozen=True)
class ResolvedProfiles:
    """Container for resolved profile configurations.

    This is the output of ProfileResolver.resolve_all(), containing
    the concrete profile configurations for a FloeSpec.

    Attributes:
        storage: Resolved storage profile (S3, GCS, etc.)
        catalog: Resolved catalog profile (Polaris, Glue, etc.)
        compute: Resolved compute profile (DuckDB, Snowflake, etc.)
    """

    storage: StorageProfile
    catalog: CatalogProfile
    compute: ComputeProfile


class ProfileResolver:
    """Resolves logical profile references to concrete configurations.

    ProfileResolver takes a PlatformSpec and resolves logical profile
    references (like "default" or "production") to actual profile
    configurations.

    Attributes:
        platform: The PlatformSpec to resolve profiles from.

    Example:
        >>> from floe_core.compiler import PlatformResolver, ProfileResolver
        >>> from floe_core.schemas import FloeSpec
        >>>
        >>> # Load platform configuration
        >>> platform = PlatformResolver.load_default()
        >>>
        >>> # Create resolver
        >>> resolver = ProfileResolver(platform)
        >>>
        >>> # Resolve individual profiles
        >>> storage = resolver.resolve_storage("default")
        >>> catalog = resolver.resolve_catalog("production")
        >>>
        >>> # Resolve all profiles at once
        >>> profiles = resolver.resolve_all(
        ...     storage="default",
        ...     catalog="default",
        ...     compute="default",
        ... )
    """

    def __init__(self, platform: PlatformSpec) -> None:
        """Initialize the ProfileResolver.

        Args:
            platform: PlatformSpec containing profile definitions.
        """
        self.platform = platform

    def resolve_storage(self, name: str | None = None) -> StorageProfile:
        """Resolve a storage profile by name.

        Args:
            name: Profile name. Defaults to "default" if None.

        Returns:
            Resolved StorageProfile.

        Raises:
            ProfileNotFoundError: If profile not found.

        Example:
            >>> storage = resolver.resolve_storage("production")
            >>> print(storage.bucket)
        """
        profile_name = name or DEFAULT_PROFILE_NAME
        try:
            profile = self.platform.get_storage_profile(profile_name)
            logger.debug("Resolved storage profile: %s", profile_name)
            return profile
        except KeyError as e:
            available = list(self.platform.storage.keys())
            raise ProfileNotFoundError(
                profile_type="storage",
                profile_name=profile_name,
                available_profiles=available,
            ) from e

    def resolve_catalog(self, name: str | None = None) -> CatalogProfile:
        """Resolve a catalog profile by name.

        Args:
            name: Profile name. Defaults to "default" if None.

        Returns:
            Resolved CatalogProfile.

        Raises:
            ProfileNotFoundError: If profile not found.

        Example:
            >>> catalog = resolver.resolve_catalog("production")
            >>> print(catalog.uri)
        """
        profile_name = name or DEFAULT_PROFILE_NAME
        try:
            profile = self.platform.get_catalog_profile(profile_name)
            logger.debug("Resolved catalog profile: %s", profile_name)
            return profile
        except KeyError as e:
            available = list(self.platform.catalogs.keys())
            raise ProfileNotFoundError(
                profile_type="catalog",
                profile_name=profile_name,
                available_profiles=available,
            ) from e

    def resolve_compute(self, name: str | None = None) -> ComputeProfile:
        """Resolve a compute profile by name.

        Args:
            name: Profile name. Defaults to "default" if None.

        Returns:
            Resolved ComputeProfile.

        Raises:
            ProfileNotFoundError: If profile not found.

        Example:
            >>> compute = resolver.resolve_compute("snowflake")
            >>> print(compute.type)
        """
        profile_name = name or DEFAULT_PROFILE_NAME
        try:
            profile = self.platform.get_compute_profile(profile_name)
            logger.debug("Resolved compute profile: %s", profile_name)
            return profile
        except KeyError as e:
            available = list(self.platform.compute.keys())
            raise ProfileNotFoundError(
                profile_type="compute",
                profile_name=profile_name,
                available_profiles=available,
            ) from e

    def resolve_all(
        self,
        storage: str | None = None,
        catalog: str | None = None,
        compute: str | None = None,
    ) -> ResolvedProfiles:
        """Resolve all profile references at once.

        Args:
            storage: Storage profile name. Defaults to "default".
            catalog: Catalog profile name. Defaults to "default".
            compute: Compute profile name. Defaults to "default".

        Returns:
            ResolvedProfiles containing all resolved configurations.

        Raises:
            ProfileNotFoundError: If any profile not found.

        Example:
            >>> profiles = resolver.resolve_all(
            ...     storage="default",
            ...     catalog="production",
            ...     compute="snowflake",
            ... )
            >>> print(profiles.catalog.uri)
        """
        logger.info(
            "Resolving profiles: storage=%s, catalog=%s, compute=%s",
            storage or DEFAULT_PROFILE_NAME,
            catalog or DEFAULT_PROFILE_NAME,
            compute or DEFAULT_PROFILE_NAME,
        )

        return ResolvedProfiles(
            storage=self.resolve_storage(storage),
            catalog=self.resolve_catalog(catalog),
            compute=self.resolve_compute(compute),
        )

    def validate_references(
        self,
        storage: str | None = None,
        catalog: str | None = None,
        compute: str | None = None,
    ) -> list[str]:
        """Validate profile references without resolving.

        Returns a list of error messages for invalid references.
        Empty list means all references are valid.

        Args:
            storage: Storage profile name to validate.
            catalog: Catalog profile name to validate.
            compute: Compute profile name to validate.

        Returns:
            List of error messages. Empty if all valid.

        Example:
            >>> errors = resolver.validate_references(
            ...     storage="default",
            ...     catalog="nonexistent",
            ... )
            >>> if errors:
            ...     print("Invalid references:", errors)
        """
        errors: list[str] = []

        storage_name = storage or DEFAULT_PROFILE_NAME
        if storage_name not in self.platform.storage:
            available = list(self.platform.storage.keys())
            errors.append(
                f"Storage profile '{storage_name}' not found. "
                f"Available: {', '.join(available) or 'none'}"
            )

        catalog_name = catalog or DEFAULT_PROFILE_NAME
        if catalog_name not in self.platform.catalogs:
            available = list(self.platform.catalogs.keys())
            errors.append(
                f"Catalog profile '{catalog_name}' not found. "
                f"Available: {', '.join(available) or 'none'}"
            )

        compute_name = compute or DEFAULT_PROFILE_NAME
        if compute_name not in self.platform.compute:
            available = list(self.platform.compute.keys())
            errors.append(
                f"Compute profile '{compute_name}' not found. "
                f"Available: {', '.join(available) or 'none'}"
            )

        return errors
