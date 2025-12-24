"""Credential configuration models for floe-runtime.

This module defines credential management configuration including:
- SecretReference: Reference to external secrets (K8s secrets, env vars)
- CredentialMode: Enum for credential modes (static, oauth2, iam_role, service_account)
- CredentialConfig: Credential configuration with mode validation
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from typing_extensions import Self

# Pattern for K8s secret names (RFC 1123 DNS subdomain)
K8S_SECRET_PATTERN = r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,252}$"


class SecretNotFoundError(Exception):
    """Raised when a secret reference cannot be resolved."""

    pass


class SecretReference(BaseModel):
    """Reference to external secret (K8s secret or environment variable).

    Secrets are never stored in configuration files. Instead,
    secret_ref points to a K8s secret name or environment variable.

    Resolution order:
        1. Check environment variable: {SECRET_REF_UPPER_SNAKE_CASE}
        2. Check K8s secret mount: /var/run/secrets/{secret_ref}
        3. Fail with clear error if not found

    Attributes:
        secret_ref: K8s secret name or environment variable name.

    Example:
        >>> ref = SecretReference(secret_ref="polaris-oauth-secret")
        >>> ref.resolve()  # Returns SecretStr from env or K8s mount
        SecretStr('**********')
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    secret_ref: str = Field(
        ...,
        pattern=K8S_SECRET_PATTERN,
        min_length=1,
        max_length=253,
        description="K8s secret name or environment variable name",
    )

    def resolve(self) -> SecretStr:
        """Resolve secret at runtime.

        Returns:
            SecretStr containing the secret value.

        Raises:
            SecretNotFoundError: If secret cannot be found in env or K8s mount.
        """
        # Try environment variable first (convert to UPPER_SNAKE_CASE)
        env_var_name = self.secret_ref.upper().replace("-", "_")
        value = os.environ.get(env_var_name)
        if value:
            return SecretStr(value)

        # Try K8s secret mount
        secret_path = Path(f"/var/run/secrets/{self.secret_ref}")
        if secret_path.exists():
            return SecretStr(secret_path.read_text().strip())

        raise SecretNotFoundError(
            f"Secret '{self.secret_ref}' not found. "
            f"Expected in environment variable '{env_var_name}' "
            f"or K8s secret mount at '{secret_path}'"
        )

    def __str__(self) -> str:
        """Return string representation without exposing the secret."""
        return f"SecretReference(secret_ref='{self.secret_ref}')"


class CredentialMode(str, Enum):
    """Credential management modes.

    Defines how credentials are managed and retrieved at runtime.

    Values:
        STATIC: Credentials from K8s secret or environment variable.
        OAUTH2: OAuth2 client credentials flow.
        IAM_ROLE: AWS IAM role assumption (no static credentials).
        SERVICE_ACCOUNT: GCP/Azure workload identity.
    """

    STATIC = "static"
    OAUTH2 = "oauth2"
    IAM_ROLE = "iam_role"
    SERVICE_ACCOUNT = "service_account"


class CredentialConfig(BaseModel):
    """Credential configuration with multiple modes.

    Supports different credential management strategies depending on
    the deployment environment and security requirements.

    Attributes:
        mode: Credential management mode.
        client_id: OAuth2 client ID (for oauth2 mode).
        client_secret: OAuth2 client secret reference (for oauth2 mode).
        scope: OAuth2 scope (for oauth2 mode).
        role_arn: AWS IAM role ARN (for iam_role mode).
        secret_ref: Generic secret reference name (for static mode).

    Example:
        >>> config = CredentialConfig(
        ...     mode=CredentialMode.OAUTH2,
        ...     client_id="data-platform-svc",
        ...     client_secret=SecretReference(secret_ref="polaris-oauth-secret"),
        ...     scope="PRINCIPAL_ROLE:DATA_ENGINEER",
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: CredentialMode = Field(
        default=CredentialMode.STATIC,
        description="Credential management mode",
    )
    client_id: str | SecretReference | None = Field(
        default=None,
        description="OAuth2 client ID (can be string or secret reference)",
    )
    client_secret: SecretReference | None = Field(
        default=None,
        description="OAuth2 client secret (must be secret reference)",
    )
    scope: str | None = Field(
        default=None,
        description="OAuth2 scope (e.g., 'PRINCIPAL_ROLE:DATA_ENGINEER')",
    )
    role_arn: str | None = Field(
        default=None,
        pattern=r"^arn:aws:iam::\d{12}:role/[\w+=,.@-]+$",
        description="AWS IAM role ARN (for iam_role mode)",
    )
    secret_ref: str | None = Field(
        default=None,
        pattern=K8S_SECRET_PATTERN,
        description="Generic secret reference (K8s secret name)",
    )

    @model_validator(mode="after")
    def validate_mode_requirements(self) -> Self:
        """Validate required fields per credential mode.

        Raises:
            ValueError: If required fields for the mode are missing.
        """
        if self.mode == CredentialMode.OAUTH2:
            if not self.client_id:
                raise ValueError("OAuth2 mode requires client_id")
            if not self.client_secret:
                raise ValueError("OAuth2 mode requires client_secret")
        elif self.mode == CredentialMode.IAM_ROLE:
            if not self.role_arn:
                raise ValueError("IAM role mode requires role_arn")
        elif self.mode == CredentialMode.STATIC:
            # Static mode can use secret_ref or be empty (env var fallback)
            pass
        elif self.mode == CredentialMode.SERVICE_ACCOUNT:
            # Service account uses platform-specific auth (no explicit config needed)
            pass
        return self

    def get_client_id(self) -> str | None:
        """Get client ID, resolving SecretReference if needed.

        Returns:
            Client ID string or None.
        """
        if isinstance(self.client_id, SecretReference):
            return self.client_id.resolve().get_secret_value()
        return self.client_id

    def get_client_secret(self) -> SecretStr | None:
        """Get client secret, resolving SecretReference.

        Returns:
            SecretStr containing client secret or None.
        """
        if self.client_secret:
            return self.client_secret.resolve()
        return None
