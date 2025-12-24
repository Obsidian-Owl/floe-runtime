"""Security configuration models for floe-runtime.

This module defines security configuration including:
- Authentication: OIDC, OAuth2, SAML, static methods
- Authorization: RBAC roles and permissions
- Secret backends: Kubernetes, Vault, AWS Secrets Manager
- Encryption: In-transit and at-rest configuration
- Audit: Security event logging

Covers: 009-US2 (Enterprise Security Layer)
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

from floe_core.schemas.credential_config import SecretReference

# Pattern for valid role/permission names
ROLE_NAME_PATTERN = r"^[a-zA-Z][a-zA-Z0-9_-]*$"

# Pattern for valid email addresses (simplified)
EMAIL_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"


class AuthMethod(str, Enum):
    """Authentication method types.

    Values:
        OIDC: OpenID Connect (Okta, Auth0, Keycloak, etc.).
        OAUTH2: OAuth2 client credentials.
        SAML: SAML 2.0 federation.
        STATIC: Static credentials (local development only).
    """

    OIDC = "oidc"
    OAUTH2 = "oauth2"
    SAML = "saml"
    STATIC = "static"


class AuthorizationMode(str, Enum):
    """Authorization mode types.

    Values:
        RBAC: Role-Based Access Control.
        ABAC: Attribute-Based Access Control.
    """

    RBAC = "rbac"
    ABAC = "abac"


class SecretBackendType(str, Enum):
    """Secret management backend types.

    Values:
        KUBERNETES: Kubernetes secrets.
        VAULT: HashiCorp Vault.
        AWS_SECRETS_MANAGER: AWS Secrets Manager.
    """

    KUBERNETES = "kubernetes"
    VAULT = "vault"
    AWS_SECRETS_MANAGER = "aws_secrets_manager"


class VaultAuthMethod(str, Enum):
    """HashiCorp Vault authentication methods.

    Values:
        KUBERNETES: Kubernetes service account auth.
        JWT: JWT/OIDC authentication.
        APPROLE: AppRole authentication.
    """

    KUBERNETES = "kubernetes"
    JWT = "jwt"
    APPROLE = "approle"


class EncryptionProvider(str, Enum):
    """At-rest encryption provider types.

    Values:
        AWS_KMS: AWS Key Management Service.
        GCP_KMS: Google Cloud KMS.
        LOCAL: Local encryption (development only).
    """

    AWS_KMS = "aws_kms"
    GCP_KMS = "gcp_kms"
    LOCAL = "local"


class AuditBackend(str, Enum):
    """Audit log backend types.

    Values:
        CLOUDWATCH: AWS CloudWatch Logs.
        LOKI: Grafana Loki.
        ELASTICSEARCH: Elasticsearch.
    """

    CLOUDWATCH = "cloudwatch"
    LOKI = "loki"
    ELASTICSEARCH = "elasticsearch"


class SameSitePolicy(str, Enum):
    """Cookie SameSite policy.

    Values:
        STRICT: Only same-site requests.
        LAX: Same-site + top-level navigations.
        NONE: All requests (requires Secure).
    """

    STRICT = "Strict"
    LAX = "Lax"
    NONE = "None"


# =============================================================================
# OIDC Configuration
# =============================================================================


class OidcClaimsMapping(BaseModel):
    """OIDC claims to user attribute mapping.

    Attributes:
        email: Claim name for email.
        groups: Claim name for groups.
        username: Claim name for username.

    Example:
        >>> claims = OidcClaimsMapping(
        ...     email="email",
        ...     groups="groups",
        ...     username="preferred_username",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    email: str = Field(
        default="email",
        description="Claim name for email",
    )
    groups: str = Field(
        default="groups",
        description="Claim name for groups",
    )
    username: str = Field(
        default="preferred_username",
        description="Claim name for username",
    )


class OidcConfig(BaseModel):
    """OpenID Connect configuration.

    Attributes:
        provider_url: OIDC provider URL (issuer).
        client_id: OAuth2 client ID.
        client_secret: OAuth2 client secret reference.
        scopes: OIDC scopes to request.
        claims_mapping: Claims to user attribute mapping.

    Example:
        >>> oidc = OidcConfig(
        ...     provider_url="https://auth.company.com",
        ...     client_id="floe-platform",
        ...     client_secret=SecretReference(secret_ref="oidc-client-secret"),
        ...     scopes=["openid", "profile", "email", "groups"],
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider_url: str = Field(
        ...,
        description="OIDC provider URL (issuer)",
    )
    client_id: str = Field(
        ...,
        min_length=1,
        description="OAuth2 client ID",
    )
    client_secret: SecretReference | None = Field(
        default=None,
        description="OAuth2 client secret reference",
    )
    scopes: list[str] = Field(
        default_factory=lambda: ["openid", "profile", "email"],
        description="OIDC scopes to request",
    )
    claims_mapping: OidcClaimsMapping = Field(
        default_factory=OidcClaimsMapping,
        description="Claims to user attribute mapping",
    )


# =============================================================================
# Session Configuration
# =============================================================================


class SessionConfig(BaseModel):
    """Session management configuration.

    Attributes:
        timeout_minutes: Session timeout in minutes.
        max_sessions_per_user: Maximum concurrent sessions per user.
        secure_cookies: Require secure (HTTPS) cookies.
        same_site: Cookie SameSite policy.

    Example:
        >>> session = SessionConfig(
        ...     timeout_minutes=480,
        ...     max_sessions_per_user=5,
        ...     secure_cookies=True,
        ...     same_site=SameSitePolicy.LAX,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    timeout_minutes: int = Field(
        default=480,
        ge=1,
        le=10080,
        description="Session timeout in minutes (1 min to 7 days)",
    )
    max_sessions_per_user: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum concurrent sessions per user",
    )
    secure_cookies: bool = Field(
        default=True,
        description="Require secure (HTTPS) cookies",
    )
    same_site: SameSitePolicy = Field(
        default=SameSitePolicy.LAX,
        description="Cookie SameSite policy",
    )


# =============================================================================
# Authentication Configuration
# =============================================================================


class AuthenticationConfig(BaseModel):
    """Authentication configuration.

    Attributes:
        enabled: Enable authentication.
        method: Authentication method.
        oidc: OIDC configuration (for oidc method).
        session: Session management configuration.

    Example:
        >>> auth = AuthenticationConfig(
        ...     enabled=True,
        ...     method=AuthMethod.OIDC,
        ...     oidc=OidcConfig(
        ...         provider_url="https://auth.company.com",
        ...         client_id="floe-platform",
        ...     ),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable authentication",
    )
    method: AuthMethod = Field(
        default=AuthMethod.STATIC,
        description="Authentication method",
    )
    oidc: OidcConfig | None = Field(
        default=None,
        description="OIDC configuration",
    )
    session: SessionConfig = Field(
        default_factory=SessionConfig,
        description="Session management configuration",
    )

    @model_validator(mode="after")
    def validate_method_config(self) -> Self:
        """Validate method-specific configuration.

        Raises:
            ValueError: If OIDC method without OIDC config.
        """
        if self.enabled and self.method == AuthMethod.OIDC and not self.oidc:
            raise ValueError("OIDC authentication requires oidc configuration")
        return self


# =============================================================================
# RBAC Configuration
# =============================================================================


class RoleDefinition(BaseModel):
    """RBAC role definition.

    Attributes:
        description: Human-readable role description.
        permissions: List of permissions (resource:action format).

    Example:
        >>> role = RoleDefinition(
        ...     description="Data engineering operations",
        ...     permissions=[
        ...         "pipelines:read,write,execute",
        ...         "catalogs:read,write",
        ...         "storage:read,write",
        ...     ],
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    description: str = Field(
        default="",
        max_length=500,
        description="Human-readable role description",
    )
    permissions: list[str] = Field(
        default_factory=list,
        description="List of permissions (resource:action format)",
    )


class AuthorizationConfig(BaseModel):
    """Authorization configuration.

    Attributes:
        enabled: Enable authorization.
        mode: Authorization mode (RBAC or ABAC).
        roles: Named role definitions.
        group_mappings: OIDC/SAML group to role mappings.

    Example:
        >>> authz = AuthorizationConfig(
        ...     enabled=True,
        ...     mode=AuthorizationMode.RBAC,
        ...     roles={
        ...         "platform_admin": RoleDefinition(
        ...             description="Full platform access",
        ...             permissions=["platform:*", "security:*"],
        ...         ),
        ...         "data_engineer": RoleDefinition(
        ...             description="Data engineering operations",
        ...             permissions=["pipelines:read,write,execute"],
        ...         ),
        ...     },
        ...     group_mappings={
        ...         "platform-admins@company.com": "platform_admin",
        ...         "data-engineering@company.com": "data_engineer",
        ...     },
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable authorization",
    )
    mode: AuthorizationMode = Field(
        default=AuthorizationMode.RBAC,
        description="Authorization mode",
    )
    roles: dict[str, RoleDefinition] = Field(
        default_factory=dict,
        description="Named role definitions",
    )
    group_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="OIDC/SAML group to role mappings",
    )


# =============================================================================
# Secret Backends
# =============================================================================


class KubernetesSecretBackend(BaseModel):
    """Kubernetes secrets backend configuration.

    Attributes:
        enabled: Enable Kubernetes secrets backend.
        namespace: Kubernetes namespace for secrets.
        mount_path: Secret mount path in containers.

    Example:
        >>> k8s = KubernetesSecretBackend(
        ...     enabled=True,
        ...     namespace="floe",
        ...     mount_path="/var/run/secrets",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Enable Kubernetes secrets backend",
    )
    namespace: str = Field(
        default="default",
        description="Kubernetes namespace for secrets",
    )
    mount_path: str = Field(
        default="/var/run/secrets",
        description="Secret mount path in containers",
    )


class VaultSecretBackend(BaseModel):
    """HashiCorp Vault secrets backend configuration.

    Attributes:
        enabled: Enable Vault backend.
        server_url: Vault server URL.
        auth_method: Vault authentication method.
        kubernetes_role: Kubernetes auth role name.
        secret_path: Base path for secrets in Vault.

    Example:
        >>> vault = VaultSecretBackend(
        ...     enabled=True,
        ...     server_url="https://vault.internal:8200",
        ...     auth_method=VaultAuthMethod.KUBERNETES,
        ...     kubernetes_role="floe-runtime",
        ...     secret_path="secret/data/floe",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable Vault backend",
    )
    server_url: str | None = Field(
        default=None,
        description="Vault server URL",
    )
    auth_method: VaultAuthMethod = Field(
        default=VaultAuthMethod.KUBERNETES,
        description="Vault authentication method",
    )
    kubernetes_role: str | None = Field(
        default=None,
        description="Kubernetes auth role name",
    )
    secret_path: str = Field(
        default="secret/data/floe",
        description="Base path for secrets in Vault",
    )

    @model_validator(mode="after")
    def validate_vault_config(self) -> Self:
        """Validate Vault configuration.

        Raises:
            ValueError: If enabled without server_url.
        """
        if self.enabled:
            if not self.server_url:
                raise ValueError("Vault backend requires server_url")
            if self.auth_method == VaultAuthMethod.KUBERNETES and not self.kubernetes_role:
                raise ValueError("Kubernetes auth method requires kubernetes_role")
        return self


class AwsSecretsManagerBackend(BaseModel):
    """AWS Secrets Manager backend configuration.

    Attributes:
        enabled: Enable AWS Secrets Manager backend.
        region: AWS region for Secrets Manager.
        prefix: Prefix for secret names.

    Example:
        >>> asm = AwsSecretsManagerBackend(
        ...     enabled=True,
        ...     region="us-east-1",
        ...     prefix="floe/",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable AWS Secrets Manager backend",
    )
    region: str | None = Field(
        default=None,
        description="AWS region for Secrets Manager",
    )
    prefix: str = Field(
        default="floe/",
        description="Prefix for secret names",
    )


class SecretBackendsConfig(BaseModel):
    """Secret management backends configuration.

    Attributes:
        primary: Primary secret backend.
        backends: Backend-specific configurations.

    Example:
        >>> secrets = SecretBackendsConfig(
        ...     primary=SecretBackendType.KUBERNETES,
        ...     kubernetes=KubernetesSecretBackend(enabled=True),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    primary: SecretBackendType = Field(
        default=SecretBackendType.KUBERNETES,
        description="Primary secret backend",
    )
    kubernetes: KubernetesSecretBackend = Field(
        default_factory=KubernetesSecretBackend,
        description="Kubernetes secrets configuration",
    )
    vault: VaultSecretBackend = Field(
        default_factory=VaultSecretBackend,
        description="Vault secrets configuration",
    )
    aws_secrets_manager: AwsSecretsManagerBackend = Field(
        default_factory=AwsSecretsManagerBackend,
        description="AWS Secrets Manager configuration",
    )


# =============================================================================
# Encryption Configuration
# =============================================================================


class InTransitEncryption(BaseModel):
    """In-transit encryption configuration.

    Attributes:
        enabled: Enable in-transit encryption (TLS).
        min_tls_version: Minimum TLS version.

    Example:
        >>> transit = InTransitEncryption(
        ...     enabled=True,
        ...     min_tls_version="1.3",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Enable in-transit encryption",
    )
    min_tls_version: str = Field(
        default="1.2",
        pattern=r"^1\.[0-3]$",
        description="Minimum TLS version",
    )


class AtRestEncryption(BaseModel):
    """At-rest encryption configuration.

    Attributes:
        enabled: Enable at-rest encryption.
        provider: Encryption key provider.
        key_ref: Reference to encryption key.

    Example:
        >>> rest = AtRestEncryption(
        ...     enabled=True,
        ...     provider=EncryptionProvider.AWS_KMS,
        ...     key_ref=SecretReference(secret_ref="encryption-key-arn"),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable at-rest encryption",
    )
    provider: EncryptionProvider = Field(
        default=EncryptionProvider.LOCAL,
        description="Encryption key provider",
    )
    key_ref: SecretReference | None = Field(
        default=None,
        description="Reference to encryption key",
    )


class EncryptionConfig(BaseModel):
    """Encryption configuration.

    Attributes:
        in_transit: In-transit (TLS) encryption.
        at_rest: At-rest encryption.

    Example:
        >>> encryption = EncryptionConfig(
        ...     in_transit=InTransitEncryption(enabled=True),
        ...     at_rest=AtRestEncryption(enabled=True),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    in_transit: InTransitEncryption = Field(
        default_factory=InTransitEncryption,
        description="In-transit encryption configuration",
    )
    at_rest: AtRestEncryption = Field(
        default_factory=AtRestEncryption,
        description="At-rest encryption configuration",
    )


# =============================================================================
# Audit Configuration
# =============================================================================


class AuditEventsConfig(BaseModel):
    """Audit event types configuration.

    Attributes:
        authentication: Audit authentication events.
        authorization: Audit authorization events.
        data_access: Audit data access events.
        configuration_changes: Audit configuration changes.

    Example:
        >>> events = AuditEventsConfig(
        ...     authentication=True,
        ...     authorization=True,
        ...     data_access=True,
        ...     configuration_changes=True,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    authentication: bool = Field(
        default=True,
        description="Audit authentication events",
    )
    authorization: bool = Field(
        default=True,
        description="Audit authorization events",
    )
    data_access: bool = Field(
        default=True,
        description="Audit data access events",
    )
    configuration_changes: bool = Field(
        default=True,
        description="Audit configuration changes",
    )


class AuditConfig(BaseModel):
    """Security audit logging configuration.

    Attributes:
        enabled: Enable audit logging.
        events: Event types to audit.
        backend: Audit log backend.
        retention_days: Audit log retention period.

    Example:
        >>> audit = AuditConfig(
        ...     enabled=True,
        ...     events=AuditEventsConfig(authentication=True),
        ...     backend=AuditBackend.CLOUDWATCH,
        ...     retention_days=90,
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool = Field(
        default=False,
        description="Enable audit logging",
    )
    events: AuditEventsConfig = Field(
        default_factory=AuditEventsConfig,
        description="Event types to audit",
    )
    backend: AuditBackend = Field(
        default=AuditBackend.LOKI,
        description="Audit log backend",
    )
    retention_days: int = Field(
        default=90,
        ge=1,
        le=3650,
        description="Audit log retention period in days",
    )


# =============================================================================
# Security Configuration (Root)
# =============================================================================


class SecurityConfig(BaseModel):
    """Security configuration for the platform.

    Combines authentication, authorization, secret backends, encryption,
    and audit logging for enterprise security.

    Attributes:
        authentication: Authentication configuration.
        authorization: Authorization configuration.
        secret_backends: Secret management backends.
        encryption: Encryption configuration.
        audit: Audit logging configuration.

    Example:
        >>> security = SecurityConfig(
        ...     authentication=AuthenticationConfig(
        ...         enabled=True,
        ...         method=AuthMethod.OIDC,
        ...         oidc=OidcConfig(
        ...             provider_url="https://auth.company.com",
        ...             client_id="floe-platform",
        ...         ),
        ...     ),
        ...     authorization=AuthorizationConfig(
        ...         enabled=True,
        ...         mode=AuthorizationMode.RBAC,
        ...     ),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    authentication: AuthenticationConfig = Field(
        default_factory=AuthenticationConfig,
        description="Authentication configuration",
    )
    authorization: AuthorizationConfig = Field(
        default_factory=AuthorizationConfig,
        description="Authorization configuration",
    )
    secret_backends: SecretBackendsConfig = Field(
        default_factory=SecretBackendsConfig,
        description="Secret management backends",
    )
    encryption: EncryptionConfig = Field(
        default_factory=EncryptionConfig,
        description="Encryption configuration",
    )
    audit: AuditConfig = Field(
        default_factory=AuditConfig,
        description="Audit logging configuration",
    )
