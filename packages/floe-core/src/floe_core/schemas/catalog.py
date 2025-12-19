"""Catalog configuration models for floe-runtime.

T029: [US1] Implement CatalogConfig with Polaris OAuth2 fields

This module defines configuration for Iceberg catalog integration
(Polaris, Glue, Nessie).
"""

from __future__ import annotations

import warnings
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CatalogConfig(BaseModel):
    """Configuration for Iceberg catalog integration.

    T067: [US6] Document catalog-specific properties

    Supports Polaris, AWS Glue, and Nessie catalogs with
    appropriate authentication and connection settings.

    Security:
        For Polaris catalogs, the scope field MUST follow the principle of least
        privilege. Use a narrowly-scoped role like 'PRINCIPAL_ROLE:DATA_ENGINEER'.
        NEVER use 'PRINCIPAL_ROLE:ALL' in production - it grants unrestricted access.

    Attributes:
        type: Catalog type (polaris, glue, nessie).
        uri: Catalog endpoint URI.
        credential_secret_ref: K8s secret name for credentials.
        warehouse: Default warehouse name.
        scope: OAuth2 scope (Polaris: e.g., "PRINCIPAL_ROLE:DATA_ENGINEER").
        token_refresh_enabled: Enable OAuth2 token refresh.
        access_delegation: Iceberg access delegation header.
        properties: Catalog-specific properties. Common properties per type:

            Polaris:
                Uses top-level fields: scope, token_refresh_enabled, access_delegation
                - scope: OAuth2 scope (e.g., "PRINCIPAL_ROLE:DATA_ENGINEER")
                - token_refresh_enabled: Enable token refresh for long sessions
                - access_delegation: "vended-credentials" for delegated access

            AWS Glue:
                - region: AWS region (e.g., "us-east-1")
                - catalog_id: AWS account ID for cross-account access
                - database: Default Glue database name

            Nessie:
                - branch: Git-like branch reference (default: "main")
                - hash: Specific commit hash for time-travel
                - ref: Reference name (branch or tag)

    Example:
        >>> # Polaris with OAuth2
        >>> config = CatalogConfig(
        ...     type="polaris",
        ...     uri="http://polaris:8181/api/catalog",
        ...     scope="PRINCIPAL_ROLE:DATA_ENGINEER",
        ...     token_refresh_enabled=True,
        ...     access_delegation="vended-credentials"
        ... )

        >>> # AWS Glue with region
        >>> config = CatalogConfig(
        ...     type="glue",
        ...     uri="arn:aws:glue:us-east-1:123456789:catalog",
        ...     properties={"region": "us-east-1", "catalog_id": "123456789"}
        ... )

        >>> # Nessie with branch
        >>> config = CatalogConfig(
        ...     type="nessie",
        ...     uri="http://nessie:19120/api/v2",
        ...     properties={"branch": "main"}
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["polaris", "glue", "nessie"] = Field(
        ...,
        description="Catalog type (polaris, glue, nessie)",
    )
    uri: str = Field(
        ...,
        description="Catalog endpoint URI",
    )
    credential_secret_ref: str | None = Field(
        default=None,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,252}$",
        description="K8s secret name for credentials",
    )
    warehouse: str | None = Field(
        default=None,
        description="Default warehouse name",
    )
    scope: str | None = Field(
        default=None,
        pattern=r"^PRINCIPAL_ROLE:[A-Za-z0-9_]+$",
        description=(
            "OAuth2 scope for Polaris catalogs. Required for Polaris type. "
            "Format: 'PRINCIPAL_ROLE:<role_name>'. "
            "Use least-privilege roles (e.g., 'PRINCIPAL_ROLE:DATA_ENGINEER')."
        ),
    )
    token_refresh_enabled: bool | None = Field(
        default=None,
        description="Enable OAuth2 token refresh",
    )
    access_delegation: str | None = Field(
        default=None,
        description="Iceberg access delegation header",
    )
    properties: dict[str, Any] = Field(
        default_factory=dict,
        description="Catalog-specific properties",
    )

    @field_validator("scope")
    @classmethod
    def warn_overly_permissive_scope(cls, v: str | None) -> str | None:
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
