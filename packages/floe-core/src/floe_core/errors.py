"""Custom exception hierarchy for floe-core.

This module defines the exception classes used throughout floe-runtime:
- FloeError: Base exception for all floe-related errors
- ValidationError: Raised when configuration validation fails
- CompilationError: Raised when compilation fails

Design per research.md:
- User-facing messages are safe to display (no internal details)
- Technical details logged internally via structlog
- Separation of concerns: user sees generic, logs have full context

Constitution Principle V (Security First):
- Error messages to users MUST NOT expose internal details
- Technical details logged internally only
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


class FloeError(Exception):
    """Base exception for floe-runtime.

    All floe exceptions inherit from this class. User-facing messages
    are safe to display; technical details are logged internally.

    Args:
        user_message: Safe message to display to the user. Should NOT contain
            file paths, stack traces, or other internal details.
        internal_details: Optional technical details for logging. This is
            logged internally but NEVER exposed to the user.

    Example:
        >>> raise FloeError(
        ...     "Configuration invalid",
        ...     internal_details="Field 'name' failed regex at /path/file.yaml:42"
        ... )

    The user sees: "Configuration invalid"
    The logs contain: full technical details for debugging
    """

    def __init__(
        self,
        user_message: str,
        *,
        internal_details: str | None = None,
    ) -> None:
        """Initialize FloeError with user message and optional internal details.

        Args:
            user_message: Safe message to display to the user.
            internal_details: Technical details for internal logging only.
        """
        super().__init__(user_message)
        self.user_message = user_message

        if internal_details:
            logger.error(
                "floe_error",
                error_type=self.__class__.__name__,
                user_message=user_message,
                internal_details=internal_details,
            )


class ValidationError(FloeError):
    """Raised when configuration validation fails.

    Use this exception when:
    - floe.yaml schema validation fails
    - Field values don't meet constraints
    - Required fields are missing
    - Type mismatches occur

    Example:
        >>> raise ValidationError(
        ...     "Invalid configuration",
        ...     internal_details="compute.target: expected ['duckdb', 'snowflake'], got 'invalid'"
        ... )
    """

    pass


class CompilationError(FloeError):
    """Raised when compilation fails.

    Use this exception when:
    - FloeSpec -> CompiledArtifacts transformation fails
    - dbt manifest.json is missing or invalid
    - Classification extraction fails
    - Output generation fails

    Example:
        >>> raise CompilationError(
        ...     "Compilation failed - check logs for details",
        ...     internal_details="Missing dbt manifest at /project/target/manifest.json"
        ... )
    """

    pass


class ConfigurationError(FloeError):
    """Raised when configuration file parsing or validation fails.

    Use this exception when:
    - YAML file cannot be parsed
    - Required fields are missing
    - Field values are invalid
    - Configuration file not found

    Provides file path and field context for actionable error messages.

    Attributes:
        file_path: Path to the configuration file (if known).
        field_path: Dot-separated path to the invalid field (e.g., "catalogs.default.uri").
        line_number: Line number in the file where error occurred (if available).

    Example:
        >>> raise ConfigurationError(
        ...     "Invalid catalog URI",
        ...     file_path="platform.yaml",
        ...     field_path="catalogs.default.uri",
        ...     line_number=42,
        ...     internal_details="URI must start with http:// or https://"
        ... )
    """

    def __init__(
        self,
        user_message: str,
        *,
        file_path: str | None = None,
        field_path: str | None = None,
        line_number: int | None = None,
        internal_details: str | None = None,
    ) -> None:
        """Initialize ConfigurationError with context.

        Args:
            user_message: Safe message to display to the user.
            file_path: Path to the configuration file (optional).
            field_path: Dot-separated path to the field (optional).
            line_number: Line number in the file (optional).
            internal_details: Technical details for internal logging only.
        """
        # Build contextual message for user
        context_parts: list[str] = []
        if file_path:
            context_parts.append(f"in {file_path}")
        if line_number:
            context_parts.append(f"line {line_number}")
        if field_path:
            context_parts.append(f"field '{field_path}'")

        if context_parts:
            full_message = f"{user_message} ({', '.join(context_parts)})"
        else:
            full_message = user_message

        super().__init__(full_message, internal_details=internal_details)

        self.file_path = file_path
        self.field_path = field_path
        self.line_number = line_number


class ProfileNotFoundError(FloeError):
    """Raised when a requested profile does not exist.

    Use this exception when:
    - A profile reference in floe.yaml doesn't exist in platform.yaml
    - Storage/catalog/compute profile lookup fails

    Always includes the list of available profiles for actionable feedback.

    Attributes:
        profile_type: Type of profile (storage, catalog, compute).
        profile_name: Name of the requested profile.
        available_profiles: List of available profile names.

    Example:
        >>> raise ProfileNotFoundError(
        ...     profile_type="catalog",
        ...     profile_name="production",
        ...     available_profiles=["default", "staging"],
        ... )
        # User sees: "Catalog profile 'production' not found. Available: default, staging"
    """

    def __init__(
        self,
        profile_type: str,
        profile_name: str,
        available_profiles: list[str],
        *,
        internal_details: str | None = None,
    ) -> None:
        """Initialize ProfileNotFoundError with available profiles.

        Args:
            profile_type: Type of profile (storage, catalog, compute).
            profile_name: Name of the requested profile.
            available_profiles: List of available profile names.
            internal_details: Technical details for internal logging only.
        """
        available_str = ", ".join(available_profiles) if available_profiles else "none"
        user_message = (
            f"{profile_type.capitalize()} profile '{profile_name}' not found. "
            f"Available: {available_str}"
        )

        super().__init__(user_message, internal_details=internal_details)

        self.profile_type = profile_type
        self.profile_name = profile_name
        self.available_profiles = available_profiles


class SecretResolutionError(FloeError):
    """Raised when a secret reference cannot be resolved.

    Use this exception when:
    - Environment variable for secret not found
    - K8s secret mount not found
    - Secret reference syntax is invalid

    Provides the expected location (env var name, K8s path) for debugging.

    Attributes:
        secret_ref: The secret reference that failed to resolve.
        expected_env_var: The expected environment variable name.
        expected_k8s_path: The expected K8s secret mount path.

    Example:
        >>> raise SecretResolutionError(
        ...     secret_ref="polaris-oauth-secret",
        ...     expected_env_var="POLARIS_OAUTH_SECRET",
        ...     expected_k8s_path="/var/run/secrets/polaris-oauth-secret",
        ... )
        # User sees: "Secret 'polaris-oauth-secret' not found.
        #            Expected in: POLARIS_OAUTH_SECRET or /var/run/secrets/polaris-oauth-secret"
    """

    def __init__(
        self,
        secret_ref: str,
        expected_env_var: str,
        expected_k8s_path: str,
        *,
        internal_details: str | None = None,
    ) -> None:
        """Initialize SecretResolutionError with expected locations.

        Args:
            secret_ref: The secret reference name.
            expected_env_var: Expected environment variable name.
            expected_k8s_path: Expected K8s secret mount path.
            internal_details: Technical details for internal logging only.
        """
        user_message = (
            f"Secret '{secret_ref}' not found. "
            f"Expected in: {expected_env_var} or {expected_k8s_path}"
        )

        super().__init__(user_message, internal_details=internal_details)

        self.secret_ref = secret_ref
        self.expected_env_var = expected_env_var
        self.expected_k8s_path = expected_k8s_path
