"""Unit tests for credential configuration models.

This module tests:
- SecretReference validation and resolution
- CredentialMode enum behavior
- CredentialConfig mode-specific validation
- K8s secret name pattern validation
"""

from __future__ import annotations

import re

import pytest
from pydantic import ValidationError

from floe_core.schemas.credential_config import (
    K8S_SECRET_PATTERN,
    CredentialConfig,
    CredentialMode,
    SecretNotFoundError,
    SecretReference,
)


class TestK8sSecretPattern:
    """Tests for K8S_SECRET_PATTERN constant."""

    def test_pattern_defined(self) -> None:
        """Verify K8s secret name pattern is defined."""
        assert K8S_SECRET_PATTERN is not None

    def test_valid_secret_names(self) -> None:
        """Valid K8s secret names should match pattern."""
        valid_names = [
            "my-secret",
            "secret123",
            "polaris-oauth-secret",
            "a",
            "a1",
            "my_secret_name",
            "Secret-With-Mixed-Case123",
        ]
        for name in valid_names:
            assert re.match(K8S_SECRET_PATTERN, name), f"Should match: {name}"

    def test_invalid_secret_names(self) -> None:
        """Invalid K8s secret names should not match pattern."""
        invalid_names = [
            "-invalid",  # Cannot start with hyphen
            "_invalid",  # Cannot start with underscore
            "",  # Cannot be empty
        ]
        for name in invalid_names:
            assert not re.match(K8S_SECRET_PATTERN, name), f"Should not match: {name}"


class TestSecretReference:
    """Tests for SecretReference model."""

    def test_valid_secret_reference(self) -> None:
        """SecretReference accepts valid secret names."""
        ref = SecretReference(secret_ref="my-secret")
        assert ref.secret_ref == "my-secret"

    def test_invalid_secret_reference_pattern(self) -> None:
        """SecretReference rejects invalid secret names."""
        with pytest.raises(ValidationError) as exc_info:
            SecretReference(secret_ref="-invalid")
        assert "secret_ref" in str(exc_info.value)

    def test_secret_reference_empty(self) -> None:
        """SecretReference rejects empty secret names."""
        with pytest.raises(ValidationError) as exc_info:
            SecretReference(secret_ref="")
        assert "secret_ref" in str(exc_info.value)

    def test_secret_reference_is_frozen(self) -> None:
        """SecretReference is immutable."""
        ref = SecretReference(secret_ref="my-secret")
        with pytest.raises(ValidationError):
            ref.secret_ref = "other-secret"  # type: ignore[misc]

    def test_resolve_from_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SecretReference resolves from environment variable."""
        monkeypatch.setenv("MY_SECRET", "secret-value-123")
        ref = SecretReference(secret_ref="my-secret")
        secret = ref.resolve()
        assert secret.get_secret_value() == "secret-value-123"

    def test_resolve_converts_hyphen_to_underscore(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SecretReference converts hyphens to underscores for env var lookup."""
        monkeypatch.setenv("POLARIS_OAUTH_SECRET", "oauth-secret-value")
        ref = SecretReference(secret_ref="polaris-oauth-secret")
        secret = ref.resolve()
        assert secret.get_secret_value() == "oauth-secret-value"

    def test_resolve_not_found_raises_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """SecretReference raises error when secret not found."""
        # Ensure env var doesn't exist
        monkeypatch.delenv("NONEXISTENT_SECRET", raising=False)
        ref = SecretReference(secret_ref="nonexistent-secret")
        with pytest.raises(SecretNotFoundError) as exc_info:
            ref.resolve()
        assert "nonexistent-secret" in str(exc_info.value)
        assert "NONEXISTENT_SECRET" in str(exc_info.value)

    def test_str_representation(self) -> None:
        """SecretReference str doesn't expose the secret."""
        ref = SecretReference(secret_ref="my-secret")
        assert "my-secret" in str(ref)
        assert "SecretReference" in str(ref)


class TestCredentialMode:
    """Tests for CredentialMode enum."""

    def test_all_modes_defined(self) -> None:
        """All credential modes are defined."""
        assert CredentialMode.STATIC == "static"
        assert CredentialMode.OAUTH2 == "oauth2"
        assert CredentialMode.IAM_ROLE == "iam_role"
        assert CredentialMode.SERVICE_ACCOUNT == "service_account"

    def test_mode_count(self) -> None:
        """Four credential modes exist."""
        assert len(CredentialMode) == 4


class TestCredentialConfigStaticMode:
    """Tests for CredentialConfig with static mode."""

    def test_default_is_static_mode(self) -> None:
        """CredentialConfig defaults to static mode."""
        config = CredentialConfig()
        assert config.mode == CredentialMode.STATIC

    def test_static_mode_with_secret_ref(self) -> None:
        """Static mode accepts secret_ref."""
        config = CredentialConfig(
            mode=CredentialMode.STATIC,
            secret_ref="my-credentials",
        )
        assert config.secret_ref == "my-credentials"

    def test_static_mode_without_secret_ref(self) -> None:
        """Static mode works without secret_ref (env var fallback)."""
        config = CredentialConfig(mode=CredentialMode.STATIC)
        assert config.secret_ref is None


class TestCredentialConfigOAuth2Mode:
    """Tests for CredentialConfig with OAuth2 mode."""

    def test_oauth2_mode_requires_client_id(self) -> None:
        """OAuth2 mode requires client_id."""
        with pytest.raises(ValidationError) as exc_info:
            CredentialConfig(
                mode=CredentialMode.OAUTH2,
                client_secret=SecretReference(secret_ref="my-secret"),
            )
        assert "client_id" in str(exc_info.value)

    def test_oauth2_mode_requires_client_secret(self) -> None:
        """OAuth2 mode requires client_secret."""
        with pytest.raises(ValidationError) as exc_info:
            CredentialConfig(
                mode=CredentialMode.OAUTH2,
                client_id="my-client-id",
            )
        assert "client_secret" in str(exc_info.value)

    def test_oauth2_mode_valid_config(self) -> None:
        """OAuth2 mode accepts valid configuration."""
        config = CredentialConfig(
            mode=CredentialMode.OAUTH2,
            client_id="data-platform-svc",
            client_secret=SecretReference(secret_ref="polaris-oauth-secret"),
            scope="PRINCIPAL_ROLE:DATA_ENGINEER",
        )
        assert config.mode == CredentialMode.OAUTH2
        assert config.client_id == "data-platform-svc"
        assert config.scope == "PRINCIPAL_ROLE:DATA_ENGINEER"

    def test_oauth2_mode_with_secret_ref_client_id(self) -> None:
        """OAuth2 mode accepts SecretReference for client_id."""
        config = CredentialConfig(
            mode=CredentialMode.OAUTH2,
            client_id=SecretReference(secret_ref="client-id-secret"),
            client_secret=SecretReference(secret_ref="client-secret"),
        )
        assert isinstance(config.client_id, SecretReference)


class TestCredentialConfigIamRoleMode:
    """Tests for CredentialConfig with IAM role mode."""

    def test_iam_role_mode_requires_role_arn(self) -> None:
        """IAM role mode requires role_arn."""
        with pytest.raises(ValidationError) as exc_info:
            CredentialConfig(mode=CredentialMode.IAM_ROLE)
        assert "role_arn" in str(exc_info.value)

    def test_iam_role_mode_valid_config(self) -> None:
        """IAM role mode accepts valid configuration."""
        config = CredentialConfig(
            mode=CredentialMode.IAM_ROLE,
            role_arn="arn:aws:iam::123456789012:role/FloeStorageRole",
        )
        assert config.mode == CredentialMode.IAM_ROLE
        assert "FloeStorageRole" in str(config.role_arn)

    def test_iam_role_mode_invalid_arn_pattern(self) -> None:
        """IAM role mode rejects invalid ARN patterns."""
        with pytest.raises(ValidationError) as exc_info:
            CredentialConfig(
                mode=CredentialMode.IAM_ROLE,
                role_arn="invalid-arn-format",
            )
        assert "role_arn" in str(exc_info.value)


class TestCredentialConfigServiceAccountMode:
    """Tests for CredentialConfig with service account mode."""

    def test_service_account_mode_no_requirements(self) -> None:
        """Service account mode has no additional requirements."""
        config = CredentialConfig(mode=CredentialMode.SERVICE_ACCOUNT)
        assert config.mode == CredentialMode.SERVICE_ACCOUNT


class TestCredentialConfigHelperMethods:
    """Tests for CredentialConfig helper methods."""

    def test_get_client_id_string(self) -> None:
        """get_client_id returns string directly."""
        config = CredentialConfig(
            mode=CredentialMode.OAUTH2,
            client_id="my-client-id",
            client_secret=SecretReference(secret_ref="my-secret"),
        )
        assert config.get_client_id() == "my-client-id"

    def test_get_client_id_from_secret_ref(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_client_id resolves SecretReference."""
        monkeypatch.setenv("CLIENT_ID_SECRET", "resolved-client-id")
        config = CredentialConfig(
            mode=CredentialMode.OAUTH2,
            client_id=SecretReference(secret_ref="client-id-secret"),
            client_secret=SecretReference(secret_ref="my-secret"),
        )
        assert config.get_client_id() == "resolved-client-id"

    def test_get_client_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_client_secret resolves SecretReference."""
        monkeypatch.setenv("MY_SECRET", "resolved-secret")
        config = CredentialConfig(
            mode=CredentialMode.OAUTH2,
            client_id="my-client-id",
            client_secret=SecretReference(secret_ref="my-secret"),
        )
        secret = config.get_client_secret()
        assert secret is not None
        assert secret.get_secret_value() == "resolved-secret"

    def test_get_client_secret_none(self) -> None:
        """get_client_secret returns None when not set."""
        config = CredentialConfig()
        assert config.get_client_secret() is None
