"""Catalog client factory.

This module provides the create_catalog() factory function for creating
configured PolarisCatalog instances from configuration objects.

Supports both:
- CatalogProfile: New two-tier configuration from platform.yaml (recommended)
- CatalogConfig: Legacy configuration (deprecated, will be removed)
- PolarisCatalogConfig: Native floe-polaris configuration
"""

from __future__ import annotations

from typing import Any

from pydantic import SecretStr

from floe_polaris.client import PolarisCatalog
from floe_polaris.config import PolarisCatalogConfig
from floe_polaris.observability import catalog_operation, get_logger


def create_catalog(
    config: PolarisCatalogConfig | Any,
) -> PolarisCatalog:
    """Create a Polaris catalog client from configuration.

    This is the primary entry point for creating catalog connections.
    Supports the two-tier configuration architecture.

    Args:
        config: Catalog configuration. Can be:
            - PolarisCatalogConfig: Native floe-polaris configuration
            - CatalogProfile: Two-tier platform.yaml configuration (recommended)
            - CatalogConfig: Legacy configuration (deprecated)

    Returns:
        PolarisCatalog: Configured catalog client with retry and observability.

    Raises:
        CatalogConnectionError: If connection cannot be established.
        CatalogAuthenticationError: If authentication fails.
        ValueError: If config type is not supported.

    Example with PolarisCatalogConfig (native):
        >>> from floe_polaris import create_catalog, PolarisCatalogConfig
        >>> config = PolarisCatalogConfig(
        ...     uri="http://localhost:8181/api/catalog",
        ...     warehouse="my_warehouse",
        ...     client_id="my_client",
        ...     client_secret="my_secret",
        ...     scope="PRINCIPAL_ROLE:DATA_ENGINEER",
        ... )
        >>> catalog = create_catalog(config)

    Example with CatalogProfile (two-tier architecture):
        >>> from floe_core.schemas import CatalogProfile, CredentialConfig, CredentialMode
        >>> profile = CatalogProfile(
        ...     type="polaris",
        ...     uri="http://localhost:8181/api/catalog",
        ...     warehouse="my_warehouse",
        ...     credentials=CredentialConfig(
        ...         mode=CredentialMode.OAUTH2,
        ...         scope="PRINCIPAL_ROLE:DATA_ENGINEER",
        ...     ),
        ... )
        >>> catalog = create_catalog(profile)
    """
    logger = get_logger()

    # Convert to PolarisCatalogConfig if needed
    if isinstance(config, PolarisCatalogConfig):
        polaris_config = config
    else:
        polaris_config = _convert_catalog_config(config)

    with catalog_operation(
        "create_catalog",
        uri=polaris_config.uri,
        warehouse=polaris_config.warehouse,
    ):
        logger.info(
            "creating_catalog",
            uri=polaris_config.uri,
            warehouse=polaris_config.warehouse,
        )
        return PolarisCatalog(polaris_config)


def _convert_catalog_config(config: Any) -> PolarisCatalogConfig:
    """Convert a floe-core config to PolarisCatalogConfig.

    Supports both:
    - CatalogProfile: New two-tier config with CredentialConfig
    - CatalogConfig: Legacy config with direct fields

    Args:
        config: A CatalogProfile or CatalogConfig from floe-core.

    Returns:
        PolarisCatalogConfig: Converted configuration.

    Raises:
        ValueError: If conversion fails or config is not supported.
    """
    # Check for CatalogProfile (two-tier architecture)
    if hasattr(config, "credentials") and hasattr(config, "get_uri"):
        return _convert_catalog_profile(config)

    # Check for legacy CatalogConfig
    if hasattr(config, "uri") and hasattr(config, "warehouse"):
        return _convert_legacy_catalog_config(config)

    msg = (
        f"Unsupported config type: {type(config).__name__}. "
        "Expected PolarisCatalogConfig, CatalogProfile, or CatalogConfig."
    )
    raise ValueError(msg)


def _convert_catalog_profile(profile: Any) -> PolarisCatalogConfig:
    """Convert a CatalogProfile (two-tier) to PolarisCatalogConfig.

    Args:
        profile: CatalogProfile from platform.yaml.

    Returns:
        PolarisCatalogConfig: Converted configuration.

    Raises:
        ValueError: If required fields are missing.
    """
    # Get URI (may be string or SecretReference)
    uri = profile.get_uri() if hasattr(profile, "get_uri") else str(profile.uri)

    kwargs: dict[str, Any] = {
        "uri": uri,
        "warehouse": profile.warehouse,
    }

    # Extract credentials from CredentialConfig
    _extract_credentials(profile.credentials, kwargs)

    # Access delegation mode
    _extract_access_delegation(profile, kwargs)

    # Token refresh
    if hasattr(profile, "token_refresh_enabled"):
        kwargs["token_refresh_enabled"] = profile.token_refresh_enabled

    return PolarisCatalogConfig(**kwargs)


def _extract_credentials(creds: Any, kwargs: dict[str, Any]) -> None:
    """Extract credential fields from CredentialConfig into kwargs.

    Args:
        creds: CredentialConfig instance.
        kwargs: Dictionary to populate with credential fields.

    Raises:
        ValueError: If scope is missing.
    """
    if not creds:
        return

    # Scope is required for Polaris
    if not creds.scope:
        msg = (
            "scope is required for Polaris catalog configuration. "
            "Set credentials.scope in platform.yaml."
        )
        raise ValueError(msg)
    kwargs["scope"] = creds.scope

    # Client ID (may be string or SecretReference)
    if creds.client_id:
        kwargs["client_id"] = _resolve_secret_or_string(creds.client_id)

    # Client secret (must be SecretReference for security)
    if creds.client_secret:
        secret_value = creds.client_secret.resolve().get_secret_value()
        kwargs["client_secret"] = SecretStr(secret_value)


def _resolve_secret_or_string(value: Any) -> str:
    """Resolve a value that may be a string or SecretReference.

    Args:
        value: String or SecretReference.

    Returns:
        Resolved string value.
    """
    if hasattr(value, "resolve"):
        resolved = value.resolve().get_secret_value()
        return str(resolved)
    return str(value)


def _extract_access_delegation(profile: Any, kwargs: dict[str, Any]) -> None:
    """Extract access delegation mode from profile.

    Args:
        profile: CatalogProfile instance.
        kwargs: Dictionary to populate.
    """
    if not hasattr(profile, "access_delegation") or not profile.access_delegation:
        return

    delegation = profile.access_delegation
    # AccessDelegation enum - convert to string
    kwargs["access_delegation"] = (
        delegation.value if hasattr(delegation, "value") else str(delegation)
    )


def _convert_legacy_catalog_config(config: Any) -> PolarisCatalogConfig:
    """Convert a legacy CatalogConfig to PolarisCatalogConfig.

    Args:
        config: Legacy CatalogConfig from floe-core.

    Returns:
        PolarisCatalogConfig: Converted configuration.

    Raises:
        ValueError: If required fields are missing.
    """
    kwargs: dict[str, Any] = {
        "uri": config.uri,
        "warehouse": config.warehouse,
    }

    # Optional fields
    if hasattr(config, "client_id") and config.client_id:
        kwargs["client_id"] = config.client_id

    if hasattr(config, "client_secret") and config.client_secret:
        kwargs["client_secret"] = config.client_secret

    if hasattr(config, "token") and config.token:
        kwargs["token"] = config.token

    # Scope is required - fail if not provided (security: least privilege)
    if not (hasattr(config, "scope") and config.scope):
        msg = (
            "scope is required for Polaris catalog configuration. "
            "Use a least-privilege scope like 'PRINCIPAL_ROLE:DATA_ENGINEER'. "
            "Never use 'PRINCIPAL_ROLE:ALL' in production."
        )
        raise ValueError(msg)
    kwargs["scope"] = config.scope

    return PolarisCatalogConfig(**kwargs)
