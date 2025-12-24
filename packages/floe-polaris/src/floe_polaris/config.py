"""Pydantic configuration models for floe-polaris.

This module provides:
- RetryConfig: Retry policy configuration with exponential backoff
- PolarisCatalogConfig: Polaris catalog connection configuration
- NamespaceInfo: Namespace information data model
"""

from __future__ import annotations

import warnings

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class RetryConfig(BaseModel):
    """Retry policy configuration for catalog operations.

    Implements exponential backoff with jitter for transient failures.
    Circuit breaker pattern available to prevent cascading failures.

    Attributes:
        max_attempts: Maximum retry attempts (1-10, default 3).
        initial_wait_seconds: Initial backoff wait (0.1-30s, default 1.0).
        max_wait_seconds: Maximum backoff cap (1-300s, default 30.0).
        jitter_seconds: Random jitter range (0-10s, default 1.0).
        circuit_breaker_threshold: Failures before circuit opens (default 5, 0=disabled).

    Example:
        >>> config = RetryConfig(max_attempts=5, initial_wait_seconds=0.5)
        >>> config.max_attempts
        5
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of retry attempts",
    )
    initial_wait_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=30.0,
        description="Initial backoff wait time in seconds",
    )
    max_wait_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="Maximum backoff wait time in seconds",
    )
    jitter_seconds: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Random jitter range in seconds",
    )
    circuit_breaker_threshold: int = Field(
        default=5,
        ge=0,
        le=100,
        description="Consecutive failures before circuit opens (0=disabled)",
    )

    @field_validator("max_wait_seconds")
    @classmethod
    def max_wait_must_exceed_initial(cls, v: float, info: object) -> float:
        """Validate that max_wait_seconds >= initial_wait_seconds."""
        # Access data through info.data for Pydantic v2
        data = getattr(info, "data", {})
        initial = data.get("initial_wait_seconds", 1.0)
        if v < initial:
            msg = f"max_wait_seconds ({v}) must be >= initial_wait_seconds ({initial})"
            raise ValueError(msg)
        return v


class PolarisCatalogConfig(BaseModel):
    """Polaris catalog connection configuration.

    Supports OAuth2 client credentials flow or pre-fetched bearer tokens.
    At least one of (client_id + client_secret) or token must be provided.

    Security:
        The scope field is REQUIRED and must follow the principle of least privilege.
        Use a narrowly-scoped role like 'PRINCIPAL_ROLE:DATA_ENGINEER' instead of
        'PRINCIPAL_ROLE:ALL' which grants unrestricted access.

    Attributes:
        uri: Polaris REST API endpoint (required).
        warehouse: Warehouse name (required).
        client_id: OAuth2 client ID (optional if using token).
        client_secret: OAuth2 client secret (optional if using token).
        token: Pre-fetched bearer token (alternative to client credentials).
        scope: OAuth2 scope (REQUIRED - use least-privilege role).
        token_refresh_enabled: Enable automatic token refresh (default True).
        access_delegation: Iceberg access delegation mode (default "vended-credentials").
        retry: Retry policy configuration.

    Example:
        >>> config = PolarisCatalogConfig(
        ...     uri="http://localhost:8181/api/catalog",
        ...     warehouse="my_warehouse",
        ...     client_id="my_client",
        ...     client_secret="my_secret",
        ...     scope="PRINCIPAL_ROLE:DATA_ENGINEER",
        ... )
        >>> config.uri
        'http://localhost:8181/api/catalog'
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    uri: str = Field(
        ...,
        min_length=1,
        description="Polaris REST API endpoint URL",
    )
    warehouse: str = Field(
        ...,
        min_length=1,
        description="Warehouse name in Polaris",
    )
    client_id: str | None = Field(
        default=None,
        description="OAuth2 client ID",
    )
    client_secret: SecretStr | None = Field(
        default=None,
        description="OAuth2 client secret",
    )
    token: SecretStr | None = Field(
        default=None,
        description="Pre-fetched bearer token",
    )
    scope: str = Field(
        ...,
        description=(
            "OAuth2 scope for token requests. MUST follow least privilege principle. "
            "Use 'PRINCIPAL_ROLE:<role_name>' with a narrowly-scoped role. "
            "NEVER use 'PRINCIPAL_ROLE:ALL' in production."
        ),
    )
    token_refresh_enabled: bool = Field(
        default=True,
        description="Enable automatic token refresh before expiry",
    )
    access_delegation: str = Field(
        default="",
        description=(
            "Iceberg access delegation mode. Empty string (default) auto-detects: "
            "disables vending when s3_endpoint is set (LocalStack/MinIO), "
            "otherwise uses PyIceberg defaults. Explicit values: "
            "'vended-credentials' for AWS STS, 'remote-signing' for remote signing."
        ),
    )
    retry: RetryConfig = Field(
        default_factory=RetryConfig,
        description="Retry policy configuration",
    )
    # S3 FileIO properties (optional, for non-AWS S3-compatible storage)
    s3_endpoint: str | None = Field(
        default=None,
        description="S3-compatible endpoint URL (e.g., http://localhost:4566 for LocalStack)",
    )
    s3_access_key_id: str | None = Field(
        default=None,
        description="S3 access key ID (if not using vended credentials)",
    )
    s3_secret_access_key: SecretStr | None = Field(
        default=None,
        description="S3 secret access key (if not using vended credentials)",
    )
    s3_region: str = Field(
        default="us-east-1",
        description="S3 region",
    )
    s3_path_style_access: bool = Field(
        default=False,
        description="Use path-style S3 access (required for LocalStack/MinIO)",
    )

    @field_validator("uri")
    @classmethod
    def validate_uri_format(cls, v: str) -> str:
        """Validate URI format (must be http:// or https://)."""
        if not v.startswith(("http://", "https://")):
            msg = f"URI must start with http:// or https://, got: {v}"
            raise ValueError(msg)
        return v.rstrip("/")  # Normalize by removing trailing slash

    @field_validator("scope")
    @classmethod
    def warn_overly_permissive_scope(cls, v: str) -> str:
        """Warn if scope violates least privilege principle.

        Security:
            PRINCIPAL_ROLE:ALL grants unrestricted access to all roles in Polaris.
            This violates the principle of least privilege and should only be used
            in development/testing environments, never in production.
        """
        if v == "PRINCIPAL_ROLE:ALL":
            warnings.warn(
                "scope='PRINCIPAL_ROLE:ALL' grants unrestricted access to all roles. "
                "Use a narrowly-scoped principal role in production environments.",
                UserWarning,
                stacklevel=2,
            )
        return v


class NamespaceInfo(BaseModel):
    """Information about a catalog namespace.

    Attributes:
        name: Fully qualified namespace name (e.g., "bronze" or "bronze.raw").
        properties: Namespace properties/metadata.

    Example:
        >>> ns = NamespaceInfo(name="bronze.raw", properties={"owner": "data_team"})
        >>> ns.name
        'bronze.raw'
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(
        ...,
        min_length=1,
        description="Fully qualified namespace name",
    )
    properties: dict[str, str] = Field(
        default_factory=dict,
        description="Namespace properties",
    )

    @property
    def parts(self) -> tuple[str, ...]:
        """Return namespace as tuple of parts.

        Example:
            >>> NamespaceInfo(name="bronze.raw").parts
            ('bronze', 'raw')
        """
        return tuple(self.name.split("."))
