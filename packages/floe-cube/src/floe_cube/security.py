"""JWT validation and claim extraction for Cube security.

T049: [US6] Implement JWT validation claim extraction functionality.

This module provides:
- JWTValidator: Validate and extract claims from JWT tokens
- extract_security_context(): Convert JWT claims to SecurityContext
- Token expiration validation
- Required claims validation

Functional Requirements:
- FR-023: Extract user claims from JWT for row-level security
- FR-024: Validate JWT signature (delegated to Cube)
- FR-025: Support custom claim mappings
- FR-026: Reject expired tokens

Architecture:
    JWTValidator decodes and validates JWT structure without verifying
    signatures (signature verification is delegated to Cube's built-in
    JWT validation). This module focuses on claim extraction and
    SecurityContext construction.

Usage:
    >>> from floe_cube.security import JWTValidator, extract_security_context
    >>>
    >>> validator = JWTValidator(
    ...     user_id_claim="sub",
    ...     roles_claim="roles",
    ...     filter_claims=["organization_id", "department"],
    ... )
    >>> context = validator.extract_context(jwt_payload)

Note:
    JWT signature verification MUST be performed by Cube's JWT middleware.
    This module only handles claim extraction after signature validation.
"""

from __future__ import annotations

import base64
import json
import time
from typing import Any

import structlog

from floe_cube.models import SecurityContext

logger = structlog.get_logger(__name__)


class JWTValidationError(Exception):
    """Error during JWT validation.

    Raised when:
    - Token is malformed
    - Required claims are missing
    - Token has expired
    - Claims have invalid types

    Note:
        This error should NOT expose internal details to users.
        Log details internally, return generic message to users.
    """

    pass


class JWTValidator:
    """JWT validator and claim extractor for Cube security.

    Validates JWT structure and extracts claims to build SecurityContext.
    Does NOT verify signatures (delegated to Cube).

    Attributes:
        user_id_claim: JWT claim name for user ID (default: "sub")
        roles_claim: JWT claim name for roles (default: "roles")
        filter_claims: List of claim names to extract for row-level filtering

    Example:
        >>> validator = JWTValidator(
        ...     user_id_claim="sub",
        ...     roles_claim="groups",
        ...     filter_claims=["org_id", "dept_id"],
        ... )
        >>> payload = {"sub": "user1", "org_id": "org1", "exp": 9999999999}
        >>> context = validator.extract_context(payload)
        >>> context.user_id
        'user1'
    """

    def __init__(
        self,
        user_id_claim: str = "sub",
        roles_claim: str = "roles",
        filter_claims: list[str] | None = None,
        *,
        validate_expiration: bool = True,
    ) -> None:
        """Initialize JWTValidator.

        Args:
            user_id_claim: Claim name for user identifier
            roles_claim: Claim name for user roles
            filter_claims: List of claim names to extract for filtering
            validate_expiration: Whether to validate exp claim
        """
        self._user_id_claim = user_id_claim
        self._roles_claim = roles_claim
        self._filter_claims = filter_claims or []
        self._validate_expiration = validate_expiration
        self._log = logger.bind(
            user_id_claim=user_id_claim,
            roles_claim=roles_claim,
        )

    @property
    def user_id_claim(self) -> str:
        """Get the user ID claim name."""
        return self._user_id_claim

    @property
    def roles_claim(self) -> str:
        """Get the roles claim name."""
        return self._roles_claim

    @property
    def filter_claims(self) -> list[str]:
        """Get the filter claim names."""
        return list(self._filter_claims)

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode JWT token without signature verification.

        Extracts payload from JWT. Does NOT verify signature.

        Args:
            token: JWT token string

        Returns:
            Decoded payload as dictionary

        Raises:
            JWTValidationError: If token is malformed
        """
        try:
            # JWT format: header.payload.signature
            parts = token.split(".")
            if len(parts) != 3:
                self._log.warning("malformed_jwt", parts_count=len(parts))
                raise JWTValidationError("Malformed JWT token")

            # Decode payload (second part)
            payload_b64 = parts[1]

            # Add padding if needed (JWT uses base64url without padding)
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding

            # Decode base64url
            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload: dict[str, Any] = json.loads(payload_bytes)

            self._log.debug("jwt_decoded", claim_count=len(payload))
            return payload

        except JWTValidationError:
            raise
        except Exception as e:
            self._log.warning("jwt_decode_error", error=str(e))
            raise JWTValidationError("Failed to decode JWT token") from e

    def validate_expiration(self, payload: dict[str, Any]) -> None:
        """Validate that token has not expired.

        Args:
            payload: Decoded JWT payload

        Raises:
            JWTValidationError: If token is expired or missing exp claim
        """
        if not self._validate_expiration:
            return

        exp = payload.get("exp")
        if exp is None:
            self._log.warning("jwt_missing_exp")
            raise JWTValidationError("JWT token missing expiration claim")

        if not isinstance(exp, (int, float)):
            self._log.warning("jwt_invalid_exp_type", exp_type=type(exp).__name__)
            raise JWTValidationError("JWT expiration must be numeric")

        current_time = time.time()
        if current_time > exp:
            self._log.warning(
                "jwt_expired",
                exp=exp,
                current_time=current_time,
            )
            raise JWTValidationError("JWT token has expired")

    def extract_context(self, payload: dict[str, Any]) -> SecurityContext:
        """Extract SecurityContext from JWT payload.

        Args:
            payload: Decoded JWT payload (already verified by Cube)

        Returns:
            SecurityContext with extracted claims

        Raises:
            JWTValidationError: If required claims are missing or invalid
        """
        # Validate expiration
        self.validate_expiration(payload)

        # Extract user_id (required)
        user_id = payload.get(self._user_id_claim)
        if user_id is None:
            self._log.warning(
                "jwt_missing_user_id",
                claim=self._user_id_claim,
            )
            raise JWTValidationError(f"JWT missing required claim: {self._user_id_claim}")

        if not isinstance(user_id, str):
            user_id = str(user_id)

        if not user_id:
            raise JWTValidationError(f"JWT claim {self._user_id_claim} cannot be empty")

        # Extract roles (optional)
        roles: list[str] = []
        raw_roles = payload.get(self._roles_claim)
        if raw_roles is not None:
            if isinstance(raw_roles, list):
                roles = [str(r) for r in raw_roles if r]
            elif isinstance(raw_roles, str):
                # Single role as string
                roles = [raw_roles] if raw_roles else []
            else:
                self._log.warning(
                    "jwt_invalid_roles_type",
                    roles_type=type(raw_roles).__name__,
                )

        # Extract filter claims (optional)
        filter_claims: dict[str, str] = {}
        for claim_name in self._filter_claims:
            value = payload.get(claim_name)
            if value is not None:
                filter_claims[claim_name] = str(value)

        # Get expiration (default to 1 hour from now if missing)
        raw_exp = payload.get("exp")
        exp = int(time.time()) + 3600 if raw_exp is None else int(raw_exp)

        self._log.debug(
            "security_context_extracted",
            user_id=user_id,
            roles_count=len(roles),
            filter_claims_count=len(filter_claims),
        )

        return SecurityContext(
            user_id=user_id,
            roles=roles,
            filter_claims=filter_claims,
            exp=exp,
        )

    def extract_context_from_token(self, token: str) -> SecurityContext:
        """Decode JWT and extract SecurityContext.

        Convenience method that combines decode and extract.

        Args:
            token: JWT token string

        Returns:
            SecurityContext with extracted claims

        Raises:
            JWTValidationError: If token is invalid or claims are missing
        """
        payload = self.decode_token(token)
        return self.extract_context(payload)


def extract_security_context(
    payload: dict[str, Any],
    *,
    user_id_claim: str = "sub",
    roles_claim: str = "roles",
    filter_claims: list[str] | None = None,
    validate_expiration: bool = True,
) -> SecurityContext:
    """Extract SecurityContext from JWT payload.

    Convenience function for one-off extraction.

    Args:
        payload: Decoded JWT payload
        user_id_claim: Claim name for user ID
        roles_claim: Claim name for roles
        filter_claims: List of claim names for filtering
        validate_expiration: Whether to check exp claim

    Returns:
        SecurityContext with extracted claims

    Raises:
        JWTValidationError: If required claims are missing or invalid

    Example:
        >>> payload = {"sub": "user1", "exp": 9999999999}
        >>> ctx = extract_security_context(payload)
        >>> ctx.user_id
        'user1'
    """
    validator = JWTValidator(
        user_id_claim=user_id_claim,
        roles_claim=roles_claim,
        filter_claims=filter_claims,
        validate_expiration=validate_expiration,
    )
    return validator.extract_context(payload)
