"""Base class for preflight checks.

Abstract base class defining the interface for all preflight checks.

Covers: 007-FR-005 (pre-deployment validation)
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

import structlog

from floe_core.preflight.models import CheckResult, CheckStatus

logger = structlog.get_logger(__name__)


class BaseCheck(ABC):
    """Base class for preflight checks.

    Provides common functionality for running checks with timing,
    error handling, and logging.

    Attributes:
        name: Check name for identification
        timeout_seconds: Maximum time for check execution

    Example:
        >>> class MyCheck(BaseCheck):
        ...     def _execute(self) -> CheckResult:
        ...         # Perform check
        ...         return CheckResult(name=self.name, status=CheckStatus.PASSED)
    """

    def __init__(self, name: str, timeout_seconds: int = 30) -> None:
        """Initialize the check.

        Args:
            name: Check name for identification and logging
            timeout_seconds: Maximum execution time in seconds
        """
        self.name = name
        self.timeout_seconds = timeout_seconds
        self._log = logger.bind(check=name)

    def run(self) -> CheckResult:
        """Run the check with timing and error handling.

        Returns:
            CheckResult with status, message, and duration.
        """
        start_time = time.monotonic()
        timestamp = datetime.now(UTC)

        self._log.info("check_started", timeout_seconds=self.timeout_seconds)

        try:
            result = self._execute()
            duration_ms = int((time.monotonic() - start_time) * 1000)

            # Update result with timing
            result_dict = result.model_dump()
            result_dict["duration_ms"] = duration_ms
            result_dict["timestamp"] = timestamp

            final_result = CheckResult(**result_dict)

            self._log.info(
                "check_completed",
                status=final_result.status.value,
                duration_ms=duration_ms,
            )

            return final_result

        except TimeoutError as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            self._log.error("check_timeout", duration_ms=duration_ms)
            return CheckResult(
                name=self.name,
                status=CheckStatus.ERROR,
                message=f"Check timed out after {self.timeout_seconds}s",
                details={"error": str(e)},
                duration_ms=duration_ms,
                timestamp=timestamp,
            )

        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            self._log.error("check_error", error=str(e))
            return CheckResult(
                name=self.name,
                status=CheckStatus.ERROR,
                message=f"Check failed with error: {type(e).__name__}",
                details={"error": str(e), "error_type": type(e).__name__},
                duration_ms=duration_ms,
                timestamp=timestamp,
            )

    @abstractmethod
    def _execute(self) -> CheckResult:
        """Execute the actual check logic.

        Subclasses must implement this method to perform their specific check.

        Returns:
            CheckResult with the check outcome.

        Raises:
            Any exception will be caught by run() and converted to ERROR status.
        """
        pass

    def _make_result(
        self,
        status: CheckStatus,
        message: str = "",
        details: dict[str, Any] | None = None,
    ) -> CheckResult:
        """Create a CheckResult with common fields.

        Helper method for subclasses to create results.

        Args:
            status: Check status
            message: Human-readable message
            details: Additional details dict

        Returns:
            CheckResult with provided fields
        """
        return CheckResult(
            name=self.name,
            status=status,
            message=message,
            details=details or {},
        )
