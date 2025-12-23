"""Unit tests for secret resolver.

This module tests:
- SecretResolver initialization
- Single secret resolution
- Credential config resolution
- Platform-wide secret validation
- Caching behavior
"""

from __future__ import annotations

import pytest

from floe_core.compiler.secret_resolver import (
    SecretResolver,
    SecretValidationResult,
    validate_platform_secrets,
)
from floe_core.schemas.catalog_profile import CatalogProfile
from floe_core.schemas.compute_profile import ComputeProfile
from floe_core.schemas.credential_config import (
    CredentialConfig,
    CredentialMode,
    SecretNotFoundError,
    SecretReference,
)
from floe_core.schemas.platform_spec import PlatformSpec
from floe_core.schemas.storage_profile import StorageProfile


@pytest.fixture
def platform_with_secrets() -> PlatformSpec:
    """Create PlatformSpec with credential configurations."""
    return PlatformSpec(
        storage={
            "default": StorageProfile(
                bucket="default-bucket",
                credentials=CredentialConfig(
                    mode=CredentialMode.STATIC,
                    secret_ref="storage-credentials",
                ),
            ),
        },
        catalogs={
            "default": CatalogProfile(
                uri="http://polaris:8181/api/catalog",
                warehouse="demo",
                credentials=CredentialConfig(
                    mode=CredentialMode.OAUTH2,
                    client_id="test-client",
                    client_secret=SecretReference(secret_ref="polaris-oauth-secret"),
                    scope="PRINCIPAL_ROLE:DATA_ENGINEER",
                ),
            ),
        },
        compute={
            "default": ComputeProfile(
                credentials=CredentialConfig(
                    mode=CredentialMode.SERVICE_ACCOUNT,
                ),
            ),
        },
    )


@pytest.fixture
def platform_with_iam() -> PlatformSpec:
    """Create PlatformSpec with IAM role mode (no secrets needed)."""
    return PlatformSpec(
        storage={
            "default": StorageProfile(
                bucket="default-bucket",
                credentials=CredentialConfig(
                    mode=CredentialMode.IAM_ROLE,
                    role_arn="arn:aws:iam::123456789012:role/FloeRole",
                ),
            ),
        },
        catalogs={
            "default": CatalogProfile(
                uri="http://polaris:8181/api/catalog",
                warehouse="demo",
                credentials=CredentialConfig(
                    mode=CredentialMode.SERVICE_ACCOUNT,
                ),
            ),
        },
        compute={
            "default": ComputeProfile(),
        },
    )


class TestSecretResolverInit:
    """Tests for SecretResolver initialization."""

    def test_init_with_platform(self, platform_with_secrets: PlatformSpec) -> None:
        """SecretResolver accepts PlatformSpec."""
        resolver = SecretResolver(platform_with_secrets)
        assert resolver.platform is platform_with_secrets

    def test_init_empty_cache(self, platform_with_secrets: PlatformSpec) -> None:
        """SecretResolver starts with empty cache."""
        resolver = SecretResolver(platform_with_secrets)
        assert len(resolver._cache) == 0


class TestResolveSingleSecret:
    """Tests for resolving single secrets."""

    def test_resolve_from_env_var(
        self, platform_with_secrets: PlatformSpec, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Resolves secret from environment variable."""
        monkeypatch.setenv("TEST_SECRET", "secret-value-123")

        resolver = SecretResolver(platform_with_secrets)
        secret = resolver.resolve_secret("test-secret")

        assert secret.get_secret_value() == "secret-value-123"

    def test_resolve_caches_result(
        self, platform_with_secrets: PlatformSpec, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Resolved secrets are cached."""
        monkeypatch.setenv("TEST_SECRET", "cached-value")

        resolver = SecretResolver(platform_with_secrets)
        resolver.resolve_secret("test-secret")

        assert "test-secret" in resolver._cache

    def test_resolve_uses_cache(
        self, platform_with_secrets: PlatformSpec, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Second resolution uses cached value."""
        monkeypatch.setenv("TEST_SECRET", "original-value")

        resolver = SecretResolver(platform_with_secrets)
        secret1 = resolver.resolve_secret("test-secret")

        # Change the env var
        monkeypatch.setenv("TEST_SECRET", "new-value")

        # Should still return cached value
        secret2 = resolver.resolve_secret("test-secret")
        assert secret1.get_secret_value() == secret2.get_secret_value()

    def test_resolve_bypasses_cache(
        self, platform_with_secrets: PlatformSpec, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Can bypass cache with use_cache=False."""
        monkeypatch.setenv("TEST_SECRET", "original-value")

        resolver = SecretResolver(platform_with_secrets)
        resolver.resolve_secret("test-secret")

        # Change the env var
        monkeypatch.setenv("TEST_SECRET", "new-value")

        # Should get new value
        secret = resolver.resolve_secret("test-secret", use_cache=False)
        assert secret.get_secret_value() == "new-value"

    def test_resolve_not_found_raises_error(
        self, platform_with_secrets: PlatformSpec, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing secret raises SecretNotFoundError."""
        monkeypatch.delenv("NONEXISTENT_SECRET", raising=False)

        resolver = SecretResolver(platform_with_secrets)
        with pytest.raises(SecretNotFoundError):
            resolver.resolve_secret("nonexistent-secret")


class TestResolveCredentialConfig:
    """Tests for resolving credential configs."""

    def test_resolve_oauth2_config(
        self, platform_with_secrets: PlatformSpec, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Resolves OAuth2 credential config."""
        monkeypatch.setenv("POLARIS_OAUTH_SECRET", "oauth-secret-value")

        catalog = platform_with_secrets.catalogs["default"]
        resolver = SecretResolver(platform_with_secrets)

        secrets = resolver.resolve_credential_config(catalog.credentials)
        assert "client_secret" in secrets
        assert secrets["client_secret"].get_secret_value() == "oauth-secret-value"

    def test_resolve_static_config(
        self, platform_with_secrets: PlatformSpec, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Resolves static credential config."""
        monkeypatch.setenv("STORAGE_CREDENTIALS", "storage-secret-value")

        storage = platform_with_secrets.storage["default"]
        resolver = SecretResolver(platform_with_secrets)

        secrets = resolver.resolve_credential_config(storage.credentials)
        assert "secret_ref" in secrets
        assert secrets["secret_ref"].get_secret_value() == "storage-secret-value"


class TestValidateAll:
    """Tests for platform-wide validation."""

    def test_validate_all_secrets_present(
        self, platform_with_secrets: PlatformSpec, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Validation passes when all secrets are present."""
        monkeypatch.setenv("STORAGE_CREDENTIALS", "storage-value")
        monkeypatch.setenv("POLARIS_OAUTH_SECRET", "oauth-value")

        resolver = SecretResolver(platform_with_secrets)
        result = resolver.validate_all()

        assert result.valid is True
        assert len(result.missing) == 0

    def test_validate_missing_secrets(
        self, platform_with_secrets: PlatformSpec, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Validation fails when secrets are missing."""
        # Don't set any secrets
        monkeypatch.delenv("STORAGE_CREDENTIALS", raising=False)
        monkeypatch.delenv("POLARIS_OAUTH_SECRET", raising=False)

        resolver = SecretResolver(platform_with_secrets)
        result = resolver.validate_all()

        assert result.valid is False
        assert len(result.missing) >= 1

    def test_validate_partial_secrets(
        self, platform_with_secrets: PlatformSpec, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Validation reports specific missing secrets."""
        # Set only one secret
        monkeypatch.setenv("STORAGE_CREDENTIALS", "storage-value")
        monkeypatch.delenv("POLARIS_OAUTH_SECRET", raising=False)

        resolver = SecretResolver(platform_with_secrets)
        result = resolver.validate_all()

        assert result.valid is False
        assert any("polaris-oauth-secret" in msg for msg in result.missing)

    def test_validate_iam_mode_skipped(
        self, platform_with_iam: PlatformSpec, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """IAM role mode doesn't require secrets."""
        resolver = SecretResolver(platform_with_iam)
        result = resolver.validate_all()

        # IAM/service account modes don't need secrets
        assert result.valid is True

    def test_validate_oauth2_scope_warning(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OAuth2 without scope generates warning."""
        platform = PlatformSpec(
            catalogs={
                "default": CatalogProfile(
                    uri="http://polaris:8181/api/catalog",
                    warehouse="demo",
                    credentials=CredentialConfig(
                        mode=CredentialMode.OAUTH2,
                        client_id="test-client",
                        client_secret=SecretReference(secret_ref="polaris-secret"),
                        scope=None,  # No scope
                    ),
                ),
            },
        )

        monkeypatch.setenv("POLARIS_SECRET", "secret-value")

        resolver = SecretResolver(platform)
        result = resolver.validate_all()

        # Valid but has warning about scope
        assert result.valid is True
        assert any("scope" in warning for warning in result.warnings)


class TestSecretValidationResult:
    """Tests for SecretValidationResult dataclass."""

    def test_valid_result(self) -> None:
        """Valid result has expected attributes."""
        result = SecretValidationResult(valid=True)
        assert result.valid is True
        assert result.missing == []
        assert result.warnings == []

    def test_invalid_result(self) -> None:
        """Invalid result with missing secrets."""
        result = SecretValidationResult(
            valid=False,
            missing=["secret1 not found", "secret2 not found"],
        )
        assert result.valid is False
        assert len(result.missing) == 2


class TestClearCache:
    """Tests for cache clearing."""

    def test_clear_cache(
        self, platform_with_secrets: PlatformSpec, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Clear cache removes all cached secrets."""
        monkeypatch.setenv("TEST_SECRET", "value")

        resolver = SecretResolver(platform_with_secrets)
        resolver.resolve_secret("test-secret")

        assert len(resolver._cache) > 0
        resolver.clear_cache()
        assert len(resolver._cache) == 0


class TestValidatePlatformSecretsFunction:
    """Tests for validate_platform_secrets convenience function."""

    def test_validates_platform(
        self, platform_with_secrets: PlatformSpec, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Convenience function validates platform."""
        monkeypatch.setenv("STORAGE_CREDENTIALS", "storage-value")
        monkeypatch.setenv("POLARIS_OAUTH_SECRET", "oauth-value")

        result = validate_platform_secrets(platform_with_secrets)
        assert result.valid is True


class TestEmptyPlatform:
    """Tests with empty platform spec."""

    def test_validate_empty_platform(self) -> None:
        """Empty platform validates successfully."""
        platform = PlatformSpec()
        resolver = SecretResolver(platform)
        result = resolver.validate_all()

        assert result.valid is True
        assert len(result.missing) == 0
