"""Catalog profile models for floe-runtime.

This module defines Iceberg catalog configuration including:
- CatalogType: Enum for supported catalog types
- AccessDelegation: Enum for STS credential delegation modes
- CatalogProfile: REST catalog configuration (Polaris, Glue, Unity)
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from floe_core.schemas.credential_config import CredentialConfig, SecretReference

# OAuth2 scope patterns
DEFAULT_OAUTH2_SCOPE = "PRINCIPAL_ROLE:DATA_ENGINEER"
LOCAL_DEV_OAUTH2_SCOPE = "PRINCIPAL_ROLE:ALL"


class CatalogType(str, Enum):
    """Supported Iceberg catalog types.

    Values:
        POLARIS: Apache Polaris REST catalog.
        GLUE: AWS Glue Data Catalog.
        NESSIE: Project Nessie catalog.
        REST: Generic Iceberg REST catalog.
        HIVE: Hive Metastore catalog.
    """

    POLARIS = "polaris"
    GLUE = "glue"
    NESSIE = "nessie"
    REST = "rest"
    HIVE = "hive"


class AccessDelegation(str, Enum):
    """STS credential delegation modes for storage access.

    Values:
        VENDED_CREDENTIALS: Catalog vends temporary STS credentials.
        REMOTE_SIGNING: Catalog signs requests remotely.
        NONE: No delegation (use storage credentials directly).
    """

    VENDED_CREDENTIALS = "vended-credentials"
    REMOTE_SIGNING = "remote-signing"
    NONE = "none"


class CatalogProfile(BaseModel):
    """Iceberg catalog configuration.

    Defines connection parameters for Iceberg REST catalogs.
    Supports Polaris, Glue, Nessie, and other Iceberg catalog implementations.

    Attributes:
        type: Catalog type (polaris, glue, nessie, rest).
        uri: Catalog URI endpoint.
        warehouse: Warehouse/catalog name.
        namespace: Default namespace.
        credentials: Credential configuration (OAuth2, IAM, etc.).
        access_delegation: Access delegation mode for STS.
        token_refresh_enabled: Enable automatic OAuth2 token refresh.
        properties: Additional catalog properties.

    Example:
        >>> profile = CatalogProfile(
        ...     type=CatalogType.POLARIS,
        ...     uri="http://polaris:8181/api/catalog",
        ...     warehouse="production",
        ...     credentials=CredentialConfig(
        ...         mode=CredentialMode.OAUTH2,
        ...         client_id="data-platform-svc",
        ...         client_secret=SecretReference(secret_ref="polaris-oauth-secret"),
        ...         scope="PRINCIPAL_ROLE:DATA_ENGINEER",
        ...     ),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: CatalogType = Field(
        default=CatalogType.POLARIS,
        description="Catalog type",
    )
    uri: str | SecretReference = Field(
        ...,
        description="Catalog URI endpoint",
    )
    warehouse: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Warehouse/catalog name",
    )
    namespace: str = Field(
        default="default",
        min_length=1,
        max_length=255,
        description="Default namespace",
    )
    credentials: CredentialConfig = Field(
        default_factory=CredentialConfig,
        description="Credential configuration",
    )
    access_delegation: AccessDelegation = Field(
        default=AccessDelegation.NONE,
        description="Access delegation mode (vended-credentials, remote-signing, none)",
    )
    token_refresh_enabled: bool = Field(
        default=True,
        description="Enable automatic OAuth2 token refresh",
    )
    properties: dict[str, str] = Field(
        default_factory=dict,
        description="Additional catalog properties",
    )

    def get_uri(self) -> str:
        """Get URI, resolving SecretReference if needed.

        Returns:
            Catalog URI string.
        """
        if isinstance(self.uri, SecretReference):
            return self.uri.resolve().get_secret_value()
        return self.uri
