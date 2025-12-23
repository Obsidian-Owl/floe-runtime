"""Catalog profile models for floe-runtime.

T005: [Setup] Create schema module catalog_profile.py
T027-T032: [Phase 2] Will implement CatalogProfile and related models

This module defines Iceberg catalog configuration including:
- CatalogProfile: REST catalog configuration (Polaris, Glue, Unity)
- CatalogType: Enum for supported catalog types
- Access delegation modes (vended-credentials, remote-signing)
- OAuth2 scope configuration for least-privilege access
"""

from __future__ import annotations

# Supported catalog types
CATALOG_TYPES = frozenset({"polaris", "glue", "unity", "rest"})

# Access delegation modes
ACCESS_DELEGATION_MODES = frozenset({"vended-credentials", "remote-signing", "none"})

# OAuth2 scope patterns
DEFAULT_OAUTH2_SCOPE = "PRINCIPAL_ROLE:DATA_ENGINEER"
LOCAL_DEV_OAUTH2_SCOPE = "PRINCIPAL_ROLE:ALL"

# TODO(T027): Implement CatalogType enum
# TODO(T028): Implement AccessDelegation enum
# TODO(T029): Implement CatalogProfile model
# TODO(T030): Implement OAuth2 scope validation
# TODO(T031): Implement token_refresh_enabled logic
# TODO(T032): Implement catalog URI validation
