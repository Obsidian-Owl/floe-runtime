"""Profile resolver for floe-runtime.

T008: [Setup] Create compiler module profile_resolver.py
T045-T051: [Phase 2] Will implement full profile resolution logic

This module handles resolving logical profile references to concrete configurations:
- ProfileResolver: Resolve 'default' → actual StorageProfile, CatalogProfile, etc.
- Merge FloeSpec logical refs with PlatformSpec concrete profiles
- Profile inheritance and override logic
- Validation of profile references
"""

from __future__ import annotations

# Default profile name used when not specified
DEFAULT_PROFILE_NAME = "default"

# Profile type identifiers
PROFILE_TYPES = frozenset({"storage", "catalog", "compute"})


class ProfileResolutionError(Exception):
    """Raised when profile resolution fails."""

    pass


# TODO(T045): Implement ProfileResolver class
# TODO(T046): Implement storage profile resolution
# TODO(T047): Implement catalog profile resolution
# TODO(T048): Implement compute profile resolution
# TODO(T049): Implement profile inheritance logic
# TODO(T050): Implement profile override validation
# TODO(T051): Implement missing profile error handling
