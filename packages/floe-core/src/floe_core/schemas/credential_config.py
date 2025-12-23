"""Credential configuration models for floe-runtime.

T003: [Setup] Create schema module credential_config.py
T011-T013: [Phase 2] Will implement SecretReference, CredentialMode, CredentialConfig

This module defines credential management configuration including:
- SecretReference: Reference to external secrets (K8s secrets, env vars)
- CredentialMode: Enum for credential modes (static, oauth2, iam_role, service_account)
- CredentialConfig: Credential configuration with mode validation
"""

from __future__ import annotations

# Pattern for K8s secret names (RFC 1123)
K8S_SECRET_PATTERN = r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,252}$"

# TODO(T011): Implement SecretReference model
# TODO(T012): Implement CredentialMode enum
# TODO(T013): Implement CredentialConfig model
