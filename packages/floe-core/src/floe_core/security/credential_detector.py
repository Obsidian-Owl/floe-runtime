"""Credential detection using detect-secrets library.

T046: [US3] Add validation to reject any credentials in floe.yaml

This module uses Yelp's detect-secrets library to identify potential
credentials in configuration values. This is a security-by-design
feature that prevents data engineers from accidentally putting
infrastructure secrets in floe.yaml (which should only contain
logical profile references).

The detect-secrets library is enterprise-grade with low false positive
rates and is maintained by Yelp with regular updates for new secret patterns.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import NamedTuple

from detect_secrets import SecretsCollection
from detect_secrets.settings import default_settings


class DetectedSecret(NamedTuple):
    """Information about a detected secret."""

    secret_type: str
    line_number: int
    is_verified: bool


class CredentialDetectedError(Exception):
    """Raised when credentials are detected in a value that should not contain them.

    Attributes:
        field_name: The field that contains the credential.
        value: The value that was detected as a credential (masked).
        secret_type: The type of secret detected (e.g., 'AWS Access Key').
    """

    def __init__(self, field_name: str, secret_type: str) -> None:
        self.field_name = field_name
        self.secret_type = secret_type
        super().__init__(
            f"Field '{field_name}' contains a potential credential ({secret_type}). "
            f"floe.yaml should only contain logical profile references (e.g., 'default'), "
            f"not infrastructure secrets. Move credentials to platform.yaml or K8s secrets."
        )


def detect_credentials_in_string(value: str) -> list[DetectedSecret]:
    """Detect potential credentials in a string value.

    Uses Yelp's detect-secrets library with default settings to scan
    the provided value for potential secrets like API keys, passwords,
    AWS credentials, etc.

    Args:
        value: The string value to scan for credentials.

    Returns:
        List of DetectedSecret objects if credentials are found.
        Empty list if no credentials are detected.

    Example:
        >>> secrets = detect_credentials_in_string("AKIAIOSFODNN7EXAMPLE")
        >>> len(secrets) > 0
        True
        >>> secrets[0].secret_type
        'AWS Access Key'
    """
    if not value or len(value) < 8:
        # Skip very short values - they're unlikely to be real secrets
        # and detect-secrets works better with context
        return []

    # Create a temporary file with the value to scan
    # detect-secrets is designed to scan files, so we use a temp file
    secrets_found: list[DetectedSecret] = []

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as temp_file:
        temp_file.write(value)
        temp_file.flush()
        temp_path = Path(temp_file.name)

    try:
        secrets = SecretsCollection()
        with default_settings():
            secrets.scan_file(str(temp_path))

        # Extract detected secrets
        for _file_path, secret_list in secrets.data.items():
            for secret in secret_list:
                secrets_found.append(
                    DetectedSecret(
                        secret_type=secret.type,
                        line_number=secret.line_number,
                        is_verified=getattr(secret, "is_verified", False),
                    )
                )
    finally:
        # Clean up temp file
        temp_path.unlink(missing_ok=True)

    return secrets_found


def validate_no_credentials(field_name: str, value: str) -> None:
    """Validate that a field value does not contain credentials.

    This is the primary validation function used by FloeSpec to ensure
    data engineers don't accidentally put secrets in floe.yaml.

    Args:
        field_name: Name of the field being validated (for error messages).
        value: The value to check for credentials.

    Raises:
        CredentialDetectedError: If credentials are detected in the value.

    Example:
        >>> validate_no_credentials("catalog", "default")  # OK
        >>> validate_no_credentials("catalog", "AKIAIOSFODNN7EXAMPLE")
        Traceback (most recent call last):
            ...
        CredentialDetectedError: Field 'catalog' contains a potential credential...
    """
    detected = detect_credentials_in_string(value)
    if detected:
        # Report the first detected secret type
        raise CredentialDetectedError(
            field_name=field_name,
            secret_type=detected[0].secret_type,
        )
