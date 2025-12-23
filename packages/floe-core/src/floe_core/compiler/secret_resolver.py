"""Secret resolver for floe-runtime.

This module provides centralized secret resolution and validation:
- SecretResolver: Resolve all secrets from a PlatformSpec
- Pre-validate secret availability before runtime
- Batch resolution with detailed error reporting
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic import SecretStr

from floe_core.schemas.credential_config import (
    CredentialConfig,
    CredentialMode,
    SecretNotFoundError,
    SecretReference,
)

if TYPE_CHECKING:
    from floe_core.schemas.platform_spec import PlatformSpec

logger = logging.getLogger(__name__)


@dataclass
class SecretValidationResult:
    """Result of secret validation.

    Attributes:
        valid: True if all secrets are resolvable.
        missing: List of missing secret references with context.
        warnings: List of warnings (e.g., empty optional secrets).
    """

    valid: bool
    missing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class SecretResolver:
    """Centralized secret resolution for platform configurations.

    SecretResolver provides a higher-level interface for resolving
    secrets from PlatformSpec credential configurations. It supports:

    - Pre-validation of all secrets before runtime
    - Batch resolution with detailed error reporting
    - Caching of resolved secrets

    Attributes:
        platform: The PlatformSpec to resolve secrets from.

    Example:
        >>> from floe_core.compiler import PlatformResolver, SecretResolver
        >>>
        >>> platform = PlatformResolver.load_default()
        >>> resolver = SecretResolver(platform)
        >>>
        >>> # Validate all secrets are available
        >>> result = resolver.validate_all()
        >>> if not result.valid:
        ...     print("Missing secrets:", result.missing)
        >>>
        >>> # Resolve a specific secret reference
        >>> secret = resolver.resolve_secret("polaris-oauth-secret")
    """

    def __init__(self, platform: PlatformSpec) -> None:
        """Initialize the SecretResolver.

        Args:
            platform: PlatformSpec containing credential configurations.
        """
        self.platform = platform
        self._cache: dict[str, SecretStr] = {}

    def resolve_secret(
        self,
        secret_ref: str,
        use_cache: bool = True,
    ) -> SecretStr:
        """Resolve a single secret reference.

        Args:
            secret_ref: Secret reference name.
            use_cache: Whether to use cached value.

        Returns:
            SecretStr containing the secret value.

        Raises:
            SecretNotFoundError: If secret cannot be resolved.

        Example:
            >>> secret = resolver.resolve_secret("polaris-oauth-secret")
            >>> value = secret.get_secret_value()
        """
        if use_cache and secret_ref in self._cache:
            logger.debug("Using cached secret: %s", secret_ref)
            return self._cache[secret_ref]

        ref = SecretReference(secret_ref=secret_ref)
        secret = ref.resolve()

        self._cache[secret_ref] = secret
        return secret

    def resolve_credential_config(
        self,
        config: CredentialConfig,
    ) -> dict[str, SecretStr]:
        """Resolve all secrets from a CredentialConfig.

        Args:
            config: CredentialConfig to resolve secrets from.

        Returns:
            Dictionary mapping field names to resolved SecretStr values.

        Raises:
            SecretNotFoundError: If any secret cannot be resolved.

        Example:
            >>> secrets = resolver.resolve_credential_config(catalog.credentials)
            >>> client_secret = secrets.get("client_secret")
        """
        resolved: dict[str, SecretStr] = {}

        # Resolve client_id if it's a SecretReference
        if isinstance(config.client_id, SecretReference):
            resolved["client_id"] = self.resolve_secret(config.client_id.secret_ref)

        # Resolve client_secret
        if config.client_secret is not None:
            resolved["client_secret"] = self.resolve_secret(config.client_secret.secret_ref)

        # Resolve generic secret_ref
        if config.secret_ref is not None:
            resolved["secret_ref"] = self.resolve_secret(config.secret_ref)

        return resolved

    def validate_all(self) -> SecretValidationResult:
        """Validate all secret references in the platform configuration.

        Checks that all secrets referenced in storage, catalog, and compute
        profiles can be resolved without actually caching the values.

        Returns:
            SecretValidationResult with validation status and details.

        Example:
            >>> result = resolver.validate_all()
            >>> if not result.valid:
            ...     for error in result.missing:
            ...         print(f"Missing: {error}")
        """
        missing: list[str] = []
        warnings: list[str] = []

        # Validate storage profile credentials
        for storage_name, storage_profile in self.platform.storage.items():
            self._validate_credential_config(
                config=storage_profile.credentials,
                context=f"storage.{storage_name}",
                missing=missing,
                warnings=warnings,
            )

        # Validate catalog profile credentials
        for catalog_name, catalog_profile in self.platform.catalogs.items():
            self._validate_credential_config(
                config=catalog_profile.credentials,
                context=f"catalogs.{catalog_name}",
                missing=missing,
                warnings=warnings,
            )

        # Validate compute profile credentials
        for compute_name, compute_profile in self.platform.compute.items():
            self._validate_credential_config(
                config=compute_profile.credentials,
                context=f"compute.{compute_name}",
                missing=missing,
                warnings=warnings,
            )

        return SecretValidationResult(
            valid=len(missing) == 0,
            missing=missing,
            warnings=warnings,
        )

    def _validate_credential_config(
        self,
        config: CredentialConfig,
        context: str,
        missing: list[str],
        warnings: list[str],
    ) -> None:
        """Validate a single credential configuration.

        Args:
            config: CredentialConfig to validate.
            context: Context string for error messages.
            missing: List to append missing secret errors to.
            warnings: List to append warnings to.
        """
        # Skip validation for modes that don't use explicit secrets
        if config.mode in (CredentialMode.IAM_ROLE, CredentialMode.SERVICE_ACCOUNT):
            logger.debug(
                "Skipping secret validation for %s (mode=%s)",
                context,
                config.mode.value,
            )
            return

        # Validate client_id if it's a SecretReference (combined for SIM102)
        if isinstance(config.client_id, SecretReference) and not self._can_resolve(
            config.client_id.secret_ref
        ):
            missing.append(
                f"{context}.credentials.client_id: Secret '{config.client_id.secret_ref}' not found"
            )

        # Validate client_secret (combined for SIM102)
        if config.client_secret is not None and not self._can_resolve(
            config.client_secret.secret_ref
        ):
            missing.append(
                f"{context}.credentials.client_secret: "
                f"Secret '{config.client_secret.secret_ref}' not found"
            )

        # Validate generic secret_ref (combined for SIM102)
        if config.secret_ref is not None and not self._can_resolve(config.secret_ref):
            missing.append(
                f"{context}.credentials.secret_ref: Secret '{config.secret_ref}' not found"
            )

        # Check for empty optional OAuth2 scope
        if config.mode == CredentialMode.OAUTH2 and config.scope is None:
            warnings.append(
                f"{context}.credentials.scope: OAuth2 scope not specified, using default"
            )

    def _can_resolve(self, secret_ref: str) -> bool:
        """Check if a secret reference can be resolved.

        Args:
            secret_ref: Secret reference name.

        Returns:
            True if the secret can be resolved.
        """
        try:
            ref = SecretReference(secret_ref=secret_ref)
            ref.resolve()
            return True
        except SecretNotFoundError:
            return False

    def clear_cache(self) -> None:
        """Clear the secret cache.

        Use when secrets may have changed (e.g., in tests).
        """
        self._cache.clear()
        logger.debug("Secret resolver cache cleared")


def validate_platform_secrets(platform: PlatformSpec) -> SecretValidationResult:
    """Convenience function to validate all platform secrets.

    Args:
        platform: PlatformSpec to validate.

    Returns:
        SecretValidationResult with validation status.

    Example:
        >>> from floe_core.compiler import PlatformResolver
        >>> platform = PlatformResolver.load_default()
        >>> result = validate_platform_secrets(platform)
        >>> if not result.valid:
        ...     raise RuntimeError(f"Missing secrets: {result.missing}")
    """
    resolver = SecretResolver(platform)
    return resolver.validate_all()
