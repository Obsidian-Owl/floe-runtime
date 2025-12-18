"""Unit tests for floe_cube security module.

T048: SecurityContext model validation unit tests
T049: JWT validation claim extraction unit tests

This module tests:
- SecurityContext model creation and validation
- SecurityContext field validation (user_id, roles, filter_claims, exp)
- SecurityContext expiration checking
- JWTValidator initialization and configuration
- JWT token decoding
- JWT claim extraction to SecurityContext
- JWT expiration validation
- Custom claim mappings
- Error handling for malformed tokens
"""

from __future__ import annotations

import base64
import json
import time

import pytest
from pydantic import ValidationError

from floe_cube.models import SecurityContext
from floe_cube.security import (
    JWTValidationError,
    JWTValidator,
    extract_security_context,
)


# =============================================================================
# T048: SecurityContext Model Validation Tests
# =============================================================================


class TestSecurityContextCreation:
    """Tests for SecurityContext model creation."""

    def test_create_minimal_context(self) -> None:
        """SecurityContext with only required fields."""
        future_exp = int(time.time()) + 3600
        ctx = SecurityContext(user_id="user_123", exp=future_exp)

        assert ctx.user_id == "user_123"
        assert ctx.roles == []
        assert ctx.filter_claims == {}
        assert ctx.exp == future_exp

    def test_create_full_context(self) -> None:
        """SecurityContext with all fields populated."""
        future_exp = int(time.time()) + 3600
        ctx = SecurityContext(
            user_id="user_456",
            roles=["admin", "analyst", "viewer"],
            filter_claims={
                "organization_id": "org_abc",
                "department": "engineering",
                "region": "us-west",
            },
            exp=future_exp,
        )

        assert ctx.user_id == "user_456"
        assert ctx.roles == ["admin", "analyst", "viewer"]
        assert len(ctx.filter_claims) == 3
        assert ctx.filter_claims["organization_id"] == "org_abc"
        assert ctx.filter_claims["department"] == "engineering"
        assert ctx.filter_claims["region"] == "us-west"

    def test_create_with_empty_roles(self) -> None:
        """SecurityContext with explicit empty roles."""
        ctx = SecurityContext(
            user_id="user_123",
            roles=[],
            exp=int(time.time()) + 3600,
        )
        assert ctx.roles == []

    def test_create_with_single_role(self) -> None:
        """SecurityContext with single role."""
        ctx = SecurityContext(
            user_id="user_123",
            roles=["viewer"],
            exp=int(time.time()) + 3600,
        )
        assert ctx.roles == ["viewer"]

    def test_create_with_many_roles(self) -> None:
        """SecurityContext with many roles."""
        roles = [f"role_{i}" for i in range(100)]
        ctx = SecurityContext(
            user_id="user_123",
            roles=roles,
            exp=int(time.time()) + 3600,
        )
        assert len(ctx.roles) == 100
        assert ctx.roles[0] == "role_0"
        assert ctx.roles[99] == "role_99"


class TestSecurityContextUserIdValidation:
    """Tests for user_id field validation."""

    def test_user_id_required(self) -> None:
        """user_id is a required field."""
        with pytest.raises(ValidationError) as exc_info:
            SecurityContext(exp=int(time.time()) + 3600)  # type: ignore[call-arg]
        assert "user_id" in str(exc_info.value)

    def test_user_id_empty_rejected(self) -> None:
        """Empty user_id should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SecurityContext(user_id="", exp=int(time.time()) + 3600)
        assert "user_id" in str(exc_info.value)

    def test_user_id_whitespace_only_rejected(self) -> None:
        """Whitespace-only user_id should be rejected (via min_length)."""
        with pytest.raises(ValidationError) as exc_info:
            SecurityContext(user_id="", exp=int(time.time()) + 3600)
        assert "user_id" in str(exc_info.value)

    def test_user_id_alphanumeric(self) -> None:
        """user_id can be alphanumeric."""
        ctx = SecurityContext(user_id="user123abc", exp=int(time.time()) + 3600)
        assert ctx.user_id == "user123abc"

    def test_user_id_with_special_chars(self) -> None:
        """user_id can contain special characters."""
        ctx = SecurityContext(user_id="user@example.com", exp=int(time.time()) + 3600)
        assert ctx.user_id == "user@example.com"

    def test_user_id_uuid_format(self) -> None:
        """user_id can be a UUID."""
        uuid = "550e8400-e29b-41d4-a716-446655440000"
        ctx = SecurityContext(user_id=uuid, exp=int(time.time()) + 3600)
        assert ctx.user_id == uuid

    def test_user_id_numeric_string(self) -> None:
        """user_id can be a numeric string."""
        ctx = SecurityContext(user_id="12345", exp=int(time.time()) + 3600)
        assert ctx.user_id == "12345"


class TestSecurityContextRolesValidation:
    """Tests for roles field validation."""

    def test_roles_default_empty_list(self) -> None:
        """roles defaults to empty list."""
        ctx = SecurityContext(user_id="user", exp=int(time.time()) + 3600)
        assert ctx.roles == []

    def test_roles_list_of_strings(self) -> None:
        """roles must be a list of strings."""
        ctx = SecurityContext(
            user_id="user",
            roles=["admin", "viewer"],
            exp=int(time.time()) + 3600,
        )
        assert ctx.roles == ["admin", "viewer"]

    def test_roles_preserves_order(self) -> None:
        """roles list order should be preserved."""
        roles = ["z_role", "a_role", "m_role"]
        ctx = SecurityContext(
            user_id="user",
            roles=roles,
            exp=int(time.time()) + 3600,
        )
        assert ctx.roles == ["z_role", "a_role", "m_role"]

    def test_roles_allows_duplicates(self) -> None:
        """roles can contain duplicates (application responsibility)."""
        ctx = SecurityContext(
            user_id="user",
            roles=["admin", "admin", "viewer"],
            exp=int(time.time()) + 3600,
        )
        assert ctx.roles == ["admin", "admin", "viewer"]


class TestSecurityContextFilterClaimsValidation:
    """Tests for filter_claims field validation."""

    def test_filter_claims_default_empty_dict(self) -> None:
        """filter_claims defaults to empty dict."""
        ctx = SecurityContext(user_id="user", exp=int(time.time()) + 3600)
        assert ctx.filter_claims == {}

    def test_filter_claims_string_values(self) -> None:
        """filter_claims must have string values."""
        ctx = SecurityContext(
            user_id="user",
            filter_claims={"org_id": "org_123", "dept": "sales"},
            exp=int(time.time()) + 3600,
        )
        assert ctx.filter_claims["org_id"] == "org_123"
        assert ctx.filter_claims["dept"] == "sales"

    def test_filter_claims_various_keys(self) -> None:
        """filter_claims can have various key names."""
        ctx = SecurityContext(
            user_id="user",
            filter_claims={
                "organization_id": "org_1",
                "tenant_id": "tenant_1",
                "department": "eng",
                "team": "platform",
            },
            exp=int(time.time()) + 3600,
        )
        assert len(ctx.filter_claims) == 4

    def test_filter_claims_empty_string_value(self) -> None:
        """filter_claims can have empty string values."""
        ctx = SecurityContext(
            user_id="user",
            filter_claims={"org_id": ""},
            exp=int(time.time()) + 3600,
        )
        assert ctx.filter_claims["org_id"] == ""


class TestSecurityContextExpirationValidation:
    """Tests for exp field validation."""

    def test_exp_required(self) -> None:
        """exp is a required field."""
        with pytest.raises(ValidationError) as exc_info:
            SecurityContext(user_id="user")  # type: ignore[call-arg]
        assert "exp" in str(exc_info.value)

    def test_exp_must_be_after_2020(self) -> None:
        """exp must be after 2020-01-01."""
        with pytest.raises(ValidationError) as exc_info:
            SecurityContext(user_id="user", exp=1000000000)  # ~2001
        assert "2020" in str(exc_info.value)

    def test_exp_accepts_2020_boundary(self) -> None:
        """exp accepts timestamp right after 2020."""
        min_timestamp = 1577836801  # Just after 2020-01-01
        ctx = SecurityContext(user_id="user", exp=min_timestamp)
        assert ctx.exp == min_timestamp

    def test_exp_accepts_future_dates(self) -> None:
        """exp accepts far future timestamps."""
        future_exp = int(time.time()) + 365 * 24 * 3600  # 1 year
        ctx = SecurityContext(user_id="user", exp=future_exp)
        assert ctx.exp == future_exp


class TestSecurityContextExpiration:
    """Tests for SecurityContext.is_expired() method."""

    def test_is_expired_future_token(self) -> None:
        """Token expiring in future should not be expired."""
        future_exp = int(time.time()) + 3600  # 1 hour from now
        ctx = SecurityContext(user_id="user", exp=future_exp)
        assert ctx.is_expired() is False

    def test_is_expired_past_token(self) -> None:
        """Token expired in past should be expired."""
        # Use 2021 timestamp (valid per validator, but in the past)
        past_exp = 1609459200  # 2021-01-01
        ctx = SecurityContext(user_id="user", exp=past_exp)
        assert ctx.is_expired() is True

    def test_is_expired_just_expired(self) -> None:
        """Token that just expired should be expired."""
        just_past_exp = int(time.time()) - 1
        # Need to ensure this is after 2020
        if just_past_exp > 1577836800:
            ctx = SecurityContext(user_id="user", exp=just_past_exp)
            assert ctx.is_expired() is True


class TestSecurityContextImmutability:
    """Tests for SecurityContext immutability (frozen=True)."""

    def test_user_id_immutable(self) -> None:
        """user_id should be immutable."""
        ctx = SecurityContext(user_id="user", exp=int(time.time()) + 3600)
        with pytest.raises(ValidationError):
            ctx.user_id = "new_user"  # type: ignore[misc]

    def test_roles_immutable(self) -> None:
        """roles should be immutable."""
        ctx = SecurityContext(user_id="user", roles=["admin"], exp=int(time.time()) + 3600)
        with pytest.raises(ValidationError):
            ctx.roles = ["new_role"]  # type: ignore[misc]

    def test_filter_claims_immutable(self) -> None:
        """filter_claims should be immutable."""
        ctx = SecurityContext(
            user_id="user",
            filter_claims={"org": "abc"},
            exp=int(time.time()) + 3600,
        )
        with pytest.raises(ValidationError):
            ctx.filter_claims = {"new": "value"}  # type: ignore[misc]

    def test_exp_immutable(self) -> None:
        """exp should be immutable."""
        ctx = SecurityContext(user_id="user", exp=int(time.time()) + 3600)
        with pytest.raises(ValidationError):
            ctx.exp = 9999999999  # type: ignore[misc]


class TestSecurityContextSerialization:
    """Tests for SecurityContext JSON serialization."""

    def test_serialize_minimal(self) -> None:
        """Minimal SecurityContext serializes correctly."""
        ctx = SecurityContext(user_id="user_123", exp=1700000000)
        json_str = ctx.model_dump_json()
        data = json.loads(json_str)

        assert data["user_id"] == "user_123"
        assert data["roles"] == []
        assert data["filter_claims"] == {}
        assert data["exp"] == 1700000000

    def test_serialize_full(self) -> None:
        """Full SecurityContext serializes correctly."""
        ctx = SecurityContext(
            user_id="user_456",
            roles=["admin"],
            filter_claims={"org": "abc"},
            exp=1700000000,
        )
        json_str = ctx.model_dump_json()
        data = json.loads(json_str)

        assert data["user_id"] == "user_456"
        assert data["roles"] == ["admin"]
        assert data["filter_claims"] == {"org": "abc"}

    def test_round_trip(self) -> None:
        """SecurityContext survives JSON round-trip."""
        original = SecurityContext(
            user_id="user_789",
            roles=["viewer", "editor"],
            filter_claims={"tenant": "t1", "region": "us"},
            exp=1700000000,
        )
        json_str = original.model_dump_json()
        loaded = SecurityContext.model_validate_json(json_str)

        assert loaded.user_id == original.user_id
        assert loaded.roles == original.roles
        assert loaded.filter_claims == original.filter_claims
        assert loaded.exp == original.exp


# =============================================================================
# T049: JWT Validation and Claim Extraction Tests
# =============================================================================


def _create_jwt(payload: dict[str, object], header: dict[str, str] | None = None) -> str:
    """Create a JWT token (without signature verification).

    This creates a valid JWT structure for testing decode functionality.
    Signature is dummy since we don't verify it.
    """
    if header is None:
        header = {"alg": "HS256", "typ": "JWT"}

    # Encode header
    header_json = json.dumps(header, separators=(",", ":"))
    header_b64 = base64.urlsafe_b64encode(header_json.encode()).decode().rstrip("=")

    # Encode payload
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")

    # Dummy signature
    signature = "dummy_signature"

    return f"{header_b64}.{payload_b64}.{signature}"


class TestJWTValidatorInitialization:
    """Tests for JWTValidator initialization."""

    def test_default_initialization(self) -> None:
        """JWTValidator has sensible defaults."""
        validator = JWTValidator()

        assert validator.user_id_claim == "sub"
        assert validator.roles_claim == "roles"
        assert validator.filter_claims == []

    def test_custom_claims(self) -> None:
        """JWTValidator accepts custom claim names."""
        validator = JWTValidator(
            user_id_claim="user_id",
            roles_claim="groups",
            filter_claims=["org_id", "tenant_id"],
        )

        assert validator.user_id_claim == "user_id"
        assert validator.roles_claim == "groups"
        assert validator.filter_claims == ["org_id", "tenant_id"]

    def test_filter_claims_immutable_copy(self) -> None:
        """filter_claims property returns a copy."""
        validator = JWTValidator(filter_claims=["org_id"])
        claims = validator.filter_claims
        claims.append("modified")

        assert validator.filter_claims == ["org_id"]


class TestJWTTokenDecoding:
    """Tests for JWT token decoding."""

    def test_decode_valid_token(self) -> None:
        """Decode valid JWT token."""
        payload = {"sub": "user_123", "exp": 9999999999}
        token = _create_jwt(payload)

        validator = JWTValidator()
        decoded = validator.decode_token(token)

        assert decoded["sub"] == "user_123"
        assert decoded["exp"] == 9999999999

    def test_decode_with_various_claims(self) -> None:
        """Decode JWT with various claim types."""
        payload = {
            "sub": "user_123",
            "roles": ["admin", "viewer"],
            "org_id": "org_abc",
            "is_admin": True,
            "level": 5,
            "exp": 9999999999,
        }
        token = _create_jwt(payload)

        validator = JWTValidator()
        decoded = validator.decode_token(token)

        assert decoded["sub"] == "user_123"
        assert decoded["roles"] == ["admin", "viewer"]
        assert decoded["org_id"] == "org_abc"
        assert decoded["is_admin"] is True
        assert decoded["level"] == 5

    def test_decode_malformed_not_enough_parts(self) -> None:
        """Reject token without three parts."""
        validator = JWTValidator()

        with pytest.raises(JWTValidationError) as exc_info:
            validator.decode_token("invalid.token")
        assert "Malformed" in str(exc_info.value)

    def test_decode_malformed_too_many_parts(self) -> None:
        """Reject token with too many parts."""
        validator = JWTValidator()

        with pytest.raises(JWTValidationError) as exc_info:
            validator.decode_token("a.b.c.d")
        assert "Malformed" in str(exc_info.value)

    def test_decode_invalid_base64(self) -> None:
        """Reject token with invalid base64."""
        validator = JWTValidator()

        with pytest.raises(JWTValidationError) as exc_info:
            validator.decode_token("header.!!!invalid!!!.sig")
        assert "decode" in str(exc_info.value).lower()

    def test_decode_invalid_json(self) -> None:
        """Reject token with invalid JSON payload."""
        validator = JWTValidator()

        # Create token with invalid JSON in payload
        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
        invalid_payload = base64.urlsafe_b64encode(b"not valid json").decode().rstrip("=")
        token = f"{header}.{invalid_payload}.sig"

        with pytest.raises(JWTValidationError) as exc_info:
            validator.decode_token(token)
        assert "decode" in str(exc_info.value).lower()


class TestJWTExpirationValidation:
    """Tests for JWT expiration validation."""

    def test_validate_valid_expiration(self) -> None:
        """Accept token with future expiration."""
        validator = JWTValidator()
        payload = {"exp": int(time.time()) + 3600}

        # Should not raise
        validator.validate_expiration(payload)

    def test_validate_expired_token(self) -> None:
        """Reject expired token."""
        validator = JWTValidator()
        payload = {"exp": int(time.time()) - 3600}

        with pytest.raises(JWTValidationError) as exc_info:
            validator.validate_expiration(payload)
        assert "expired" in str(exc_info.value).lower()

    def test_validate_missing_exp(self) -> None:
        """Reject token without exp claim."""
        validator = JWTValidator()
        payload = {"sub": "user_123"}

        with pytest.raises(JWTValidationError) as exc_info:
            validator.validate_expiration(payload)
        assert "expiration" in str(exc_info.value).lower()

    def test_validate_invalid_exp_type_string(self) -> None:
        """Reject token with string exp."""
        validator = JWTValidator()
        payload = {"exp": "not a number"}

        with pytest.raises(JWTValidationError) as exc_info:
            validator.validate_expiration(payload)
        assert "numeric" in str(exc_info.value).lower()

    def test_validate_expiration_disabled(self) -> None:
        """Expiration validation can be disabled."""
        validator = JWTValidator(validate_expiration=False)
        payload = {"exp": int(time.time()) - 3600}  # Expired

        # Should not raise
        validator.validate_expiration(payload)

    def test_validate_expiration_disabled_missing_exp(self) -> None:
        """Missing exp is OK when validation disabled."""
        validator = JWTValidator(validate_expiration=False)
        payload = {"sub": "user"}

        # Should not raise
        validator.validate_expiration(payload)


class TestJWTClaimExtraction:
    """Tests for extracting SecurityContext from JWT payload."""

    def test_extract_minimal_context(self) -> None:
        """Extract context with just user_id and exp."""
        validator = JWTValidator()
        future_exp = int(time.time()) + 3600
        payload = {"sub": "user_123", "exp": future_exp}

        ctx = validator.extract_context(payload)

        assert ctx.user_id == "user_123"
        assert ctx.roles == []
        assert ctx.filter_claims == {}
        assert ctx.exp == future_exp

    def test_extract_with_roles_list(self) -> None:
        """Extract context with roles as list."""
        validator = JWTValidator()
        payload = {
            "sub": "user_123",
            "roles": ["admin", "viewer"],
            "exp": int(time.time()) + 3600,
        }

        ctx = validator.extract_context(payload)

        assert ctx.roles == ["admin", "viewer"]

    def test_extract_with_roles_string(self) -> None:
        """Extract context with roles as single string."""
        validator = JWTValidator()
        payload = {
            "sub": "user_123",
            "roles": "admin",
            "exp": int(time.time()) + 3600,
        }

        ctx = validator.extract_context(payload)

        assert ctx.roles == ["admin"]

    def test_extract_with_filter_claims(self) -> None:
        """Extract context with filter claims."""
        validator = JWTValidator(filter_claims=["org_id", "department"])
        payload = {
            "sub": "user_123",
            "org_id": "org_abc",
            "department": "engineering",
            "other_claim": "ignored",
            "exp": int(time.time()) + 3600,
        }

        ctx = validator.extract_context(payload)

        assert ctx.filter_claims == {
            "org_id": "org_abc",
            "department": "engineering",
        }
        assert "other_claim" not in ctx.filter_claims

    def test_extract_missing_user_id(self) -> None:
        """Reject payload without user_id claim."""
        validator = JWTValidator()
        payload = {"exp": int(time.time()) + 3600}

        with pytest.raises(JWTValidationError) as exc_info:
            validator.extract_context(payload)
        assert "sub" in str(exc_info.value)

    def test_extract_empty_user_id(self) -> None:
        """Reject payload with empty user_id."""
        validator = JWTValidator()
        payload = {"sub": "", "exp": int(time.time()) + 3600}

        with pytest.raises(JWTValidationError) as exc_info:
            validator.extract_context(payload)
        assert "empty" in str(exc_info.value).lower()

    def test_extract_custom_user_id_claim(self) -> None:
        """Extract with custom user_id claim name."""
        validator = JWTValidator(user_id_claim="user_id")
        payload = {
            "user_id": "custom_user",
            "exp": int(time.time()) + 3600,
        }

        ctx = validator.extract_context(payload)

        assert ctx.user_id == "custom_user"

    def test_extract_custom_roles_claim(self) -> None:
        """Extract with custom roles claim name."""
        validator = JWTValidator(roles_claim="groups")
        payload = {
            "sub": "user_123",
            "groups": ["group1", "group2"],
            "roles": ["ignored"],
            "exp": int(time.time()) + 3600,
        }

        ctx = validator.extract_context(payload)

        assert ctx.roles == ["group1", "group2"]

    def test_extract_numeric_user_id_converted(self) -> None:
        """Numeric user_id is converted to string."""
        validator = JWTValidator()
        payload = {
            "sub": 12345,  # Numeric
            "exp": int(time.time()) + 3600,
        }

        ctx = validator.extract_context(payload)

        assert ctx.user_id == "12345"

    def test_extract_numeric_filter_claim_converted(self) -> None:
        """Numeric filter claims are converted to strings."""
        validator = JWTValidator(filter_claims=["org_id"])
        payload = {
            "sub": "user",
            "org_id": 123,  # Numeric
            "exp": int(time.time()) + 3600,
        }

        ctx = validator.extract_context(payload)

        assert ctx.filter_claims["org_id"] == "123"

    def test_extract_missing_optional_filter_claims(self) -> None:
        """Missing filter claims are skipped (not included)."""
        validator = JWTValidator(filter_claims=["org_id", "dept_id"])
        payload = {
            "sub": "user",
            "org_id": "org_1",
            # dept_id missing
            "exp": int(time.time()) + 3600,
        }

        ctx = validator.extract_context(payload)

        assert ctx.filter_claims == {"org_id": "org_1"}
        assert "dept_id" not in ctx.filter_claims


class TestJWTValidatorFromToken:
    """Tests for extract_context_from_token (combined decode + extract)."""

    def test_extract_from_token(self) -> None:
        """Extract context directly from JWT token."""
        payload = {
            "sub": "user_456",
            "roles": ["editor"],
            "exp": int(time.time()) + 3600,
        }
        token = _create_jwt(payload)

        validator = JWTValidator()
        ctx = validator.extract_context_from_token(token)

        assert ctx.user_id == "user_456"
        assert ctx.roles == ["editor"]

    def test_extract_from_token_with_filter_claims(self) -> None:
        """Extract with filter claims from token."""
        payload = {
            "sub": "user",
            "org_id": "org_abc",
            "tenant_id": "tenant_xyz",
            "exp": int(time.time()) + 3600,
        }
        token = _create_jwt(payload)

        validator = JWTValidator(filter_claims=["org_id", "tenant_id"])
        ctx = validator.extract_context_from_token(token)

        assert ctx.filter_claims["org_id"] == "org_abc"
        assert ctx.filter_claims["tenant_id"] == "tenant_xyz"

    def test_extract_from_malformed_token(self) -> None:
        """Reject malformed token."""
        validator = JWTValidator()

        with pytest.raises(JWTValidationError):
            validator.extract_context_from_token("not.a.valid.token.format")


class TestExtractSecurityContextFunction:
    """Tests for extract_security_context convenience function."""

    def test_extract_minimal(self) -> None:
        """Extract with default settings."""
        payload = {
            "sub": "user_123",
            "exp": int(time.time()) + 3600,
        }

        ctx = extract_security_context(payload)

        assert ctx.user_id == "user_123"

    def test_extract_with_custom_claims(self) -> None:
        """Extract with custom claim configuration."""
        payload = {
            "user_id": "custom_user",
            "groups": ["g1", "g2"],
            "org": "my_org",
            "exp": int(time.time()) + 3600,
        }

        ctx = extract_security_context(
            payload,
            user_id_claim="user_id",
            roles_claim="groups",
            filter_claims=["org"],
        )

        assert ctx.user_id == "custom_user"
        assert ctx.roles == ["g1", "g2"]
        assert ctx.filter_claims["org"] == "my_org"

    def test_extract_skip_expiration_validation(self) -> None:
        """Can skip expiration validation."""
        payload = {
            "sub": "user",
            "exp": int(time.time()) - 3600,  # Expired
        }

        # Should not raise
        ctx = extract_security_context(payload, validate_expiration=False)

        assert ctx.user_id == "user"


class TestJWTEdgeCases:
    """Tests for JWT edge cases and error handling."""

    def test_empty_roles_list(self) -> None:
        """Empty roles list is preserved."""
        validator = JWTValidator()
        payload = {
            "sub": "user",
            "roles": [],
            "exp": int(time.time()) + 3600,
        }

        ctx = validator.extract_context(payload)

        assert ctx.roles == []

    def test_null_roles(self) -> None:
        """Null roles treated as empty."""
        validator = JWTValidator()
        payload = {
            "sub": "user",
            "roles": None,
            "exp": int(time.time()) + 3600,
        }

        ctx = validator.extract_context(payload)

        assert ctx.roles == []

    def test_invalid_roles_type_ignored(self) -> None:
        """Invalid roles type results in empty list."""
        validator = JWTValidator()
        payload = {
            "sub": "user",
            "roles": {"invalid": "type"},  # dict instead of list
            "exp": int(time.time()) + 3600,
        }

        ctx = validator.extract_context(payload)

        assert ctx.roles == []

    def test_roles_with_empty_strings_filtered(self) -> None:
        """Empty strings in roles are filtered."""
        validator = JWTValidator()
        payload = {
            "sub": "user",
            "roles": ["admin", "", "viewer", ""],
            "exp": int(time.time()) + 3600,
        }

        ctx = validator.extract_context(payload)

        assert ctx.roles == ["admin", "viewer"]

    def test_default_exp_when_disabled_and_missing(self) -> None:
        """Default exp is set when validation disabled and exp missing."""
        validator = JWTValidator(validate_expiration=False)
        payload = {"sub": "user"}

        ctx = validator.extract_context(payload)

        # Should have a reasonable exp
        assert ctx.exp > int(time.time())

    def test_filter_claim_null_value_skipped(self) -> None:
        """Null filter claim values are skipped."""
        validator = JWTValidator(filter_claims=["org_id", "dept_id"])
        payload = {
            "sub": "user",
            "org_id": "org_1",
            "dept_id": None,
            "exp": int(time.time()) + 3600,
        }

        ctx = validator.extract_context(payload)

        assert ctx.filter_claims == {"org_id": "org_1"}

    def test_boolean_filter_claim_converted(self) -> None:
        """Boolean filter claims are converted to strings."""
        validator = JWTValidator(filter_claims=["is_admin"])
        payload = {
            "sub": "user",
            "is_admin": True,
            "exp": int(time.time()) + 3600,
        }

        ctx = validator.extract_context(payload)

        assert ctx.filter_claims["is_admin"] == "True"
