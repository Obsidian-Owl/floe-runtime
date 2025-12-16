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
