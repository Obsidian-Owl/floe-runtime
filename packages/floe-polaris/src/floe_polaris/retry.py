"""Configurable retry policies with tenacity.

This module provides:
- Retry decorator factory using tenacity
- Exponential backoff with jitter
- Circuit breaker support for cascading failure prevention
"""

from __future__ import annotations

import random
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from tenacity import (
    RetryError,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from floe_polaris.config import RetryConfig
from floe_polaris.errors import CatalogConnectionError
from floe_polaris.observability import log_retry_attempt

P = ParamSpec("P")
R = TypeVar("R")

# Default exceptions that trigger retry
DEFAULT_RETRY_EXCEPTIONS: tuple[type[Exception], ...] = (
    CatalogConnectionError,
    ConnectionError,
    TimeoutError,
    OSError,
)


class CircuitBreaker:
    """Simple circuit breaker implementation.

    Tracks consecutive failures and opens the circuit when threshold is reached.
    Once open, the circuit will fail fast without attempting the operation.

    Attributes:
        threshold: Number of consecutive failures before opening.
        failure_count: Current consecutive failure count.
        is_open: Whether the circuit is currently open.

    Example:
        >>> breaker = CircuitBreaker(threshold=5)
        >>> breaker.record_failure()
        >>> breaker.is_open
        False
        >>> for _ in range(4):
        ...     breaker.record_failure()
        >>> breaker.is_open
        True
    """

    def __init__(self, threshold: int) -> None:
        """Initialize circuit breaker.

        Args:
            threshold: Consecutive failures before circuit opens (0=disabled).
        """
        self.threshold = threshold
        self.failure_count = 0
        self._is_open = False

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing fast)."""
        return self._is_open

    def record_failure(self) -> None:
        """Record a failure, potentially opening the circuit."""
        if self.threshold == 0:
            return  # Disabled
        self.failure_count += 1
        if self.failure_count >= self.threshold:
            self._is_open = True

    def record_success(self) -> None:
        """Record a success, resetting failure count and closing circuit."""
        self.failure_count = 0
        self._is_open = False

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self.failure_count = 0
        self._is_open = False


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open and operation is not attempted."""

    def __init__(self, message: str = "Circuit breaker is open") -> None:
        super().__init__(message)


def create_retry_decorator(
    config: RetryConfig,
    *,
    retry_exceptions: tuple[type[Exception], ...] | None = None,
    operation_name: str | None = None,
    circuit_breaker: CircuitBreaker | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Create a retry decorator with the specified configuration.

    Creates a decorator that wraps functions with exponential backoff retry
    logic, optional circuit breaker, and observability logging.

    Args:
        config: RetryConfig with retry policy settings.
        retry_exceptions: Exception types that trigger retry.
            Defaults to connection-related exceptions.
        operation_name: Name for logging purposes.
        circuit_breaker: Optional CircuitBreaker instance for fail-fast.

    Returns:
        Decorator function that adds retry behavior.

    Example:
        >>> config = RetryConfig(max_attempts=3)
        >>> @create_retry_decorator(config, operation_name="load_table")
        ... def load_table(name: str) -> Table:
        ...     return catalog.load_table(name)
    """
    exceptions = retry_exceptions or DEFAULT_RETRY_EXCEPTIONS

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        op_name = operation_name or func.__name__

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Check circuit breaker first
            if circuit_breaker is not None and circuit_breaker.is_open:
                raise CircuitOpenError(f"Circuit open for {op_name}")

            attempt = 0
            last_exception: Exception | None = None

            try:
                for attempt_state in Retrying(
                    retry=retry_if_exception_type(exceptions),
                    stop=stop_after_attempt(config.max_attempts),
                    wait=wait_exponential_jitter(
                        initial=config.initial_wait_seconds,
                        max=config.max_wait_seconds,
                        jitter=config.jitter_seconds,
                    ),
                    reraise=False,
                ):
                    with attempt_state:
                        attempt = attempt_state.retry_state.attempt_number
                        try:
                            result = func(*args, **kwargs)
                            # Success - reset circuit breaker
                            if circuit_breaker is not None:
                                circuit_breaker.record_success()
                            return result
                        except exceptions as exc:
                            last_exception = exc
                            # Log retry attempt
                            if attempt < config.max_attempts:
                                wait_time = _calculate_wait_time(config, attempt)
                                log_retry_attempt(
                                    operation=op_name,
                                    attempt=attempt,
                                    max_attempts=config.max_attempts,
                                    wait_seconds=wait_time,
                                    error=str(exc),
                                )
                            raise
            except RetryError:
                # All retries exhausted - record failure
                if circuit_breaker is not None:
                    circuit_breaker.record_failure()
                if last_exception is not None:
                    raise last_exception
                raise

            # Should not reach here, but satisfy type checker
            raise RuntimeError("Unexpected retry state")  # pragma: no cover

        return wrapper

    return decorator


def _calculate_wait_time(config: RetryConfig, attempt: int) -> float:
    """Calculate wait time for a given attempt.

    Uses exponential backoff: initial * 2^(attempt-1) + jitter

    Args:
        config: Retry configuration.
        attempt: Current attempt number (1-based).

    Returns:
        Wait time in seconds.
    """
    base_wait = config.initial_wait_seconds * (2 ** (attempt - 1))
    jitter = random.uniform(0, config.jitter_seconds)  # noqa: S311
    return min(base_wait + jitter, config.max_wait_seconds)


def with_retry(
    config: RetryConfig | None = None,
    *,
    retry_exceptions: tuple[type[Exception], ...] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Convenience decorator for adding retry behavior.

    Simplified version of create_retry_decorator for common use cases.

    Args:
        config: Optional RetryConfig. Uses defaults if not provided.
        retry_exceptions: Exception types that trigger retry.

    Returns:
        Decorator function.

    Example:
        >>> @with_retry()
        ... def connect_to_catalog():
        ...     return create_connection()

        >>> @with_retry(RetryConfig(max_attempts=5))
        ... def important_operation():
        ...     return do_work()
    """
    cfg = config or RetryConfig()
    return create_retry_decorator(cfg, retry_exceptions=retry_exceptions)
