"""Catalog configuration models for floe-runtime.

T029: [US1] Implement CatalogConfig with Polaris OAuth2 fields

This module defines configuration for Iceberg catalog integration
(Polaris, Glue, Nessie).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CatalogConfig(BaseModel):
    """Configuration for Iceberg catalog integration.

    Supports Polaris, AWS Glue, and Nessie catalogs with
    appropriate authentication and connection settings.

    Attributes:
        type: Catalog type (polaris, glue, nessie).
        uri: Catalog endpoint URI.
        credential_secret_ref: K8s secret name for credentials.
        warehouse: Default warehouse name.
        scope: OAuth2 scope (Polaris: e.g., "PRINCIPAL_ROLE:ALL").
        token_refresh_enabled: Enable OAuth2 token refresh.
        access_delegation: Iceberg access delegation header.
        properties: Catalog-specific properties.

    Example:
        >>> config = CatalogConfig(
        ...     type="polaris",
        ...     uri="http://polaris:8181/api/catalog",
        ...     scope="PRINCIPAL_ROLE:DATA_ENGINEER",
        ...     token_refresh_enabled=True
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["polaris", "glue", "nessie"]
    uri: str
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
        description="OAuth2 scope (Polaris)",
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
