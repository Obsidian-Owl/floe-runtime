"""Unit tests for retry decorator.

Tests for:
- T029: Retry decorator and circuit breaker
"""

from __future__ import annotations

import pytest

from floe_polaris.config import RetryConfig
from floe_polaris.errors import CatalogConnectionError
from floe_polaris.retry import (
    CircuitBreaker,
    CircuitOpenError,
    create_retry_decorator,
    with_retry,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_initial_state_closed(self) -> None:
        """Test circuit starts in closed state."""
        breaker = CircuitBreaker(threshold=3)

        assert breaker.is_open is False
        assert breaker.failure_count == 0

    def test_opens_after_threshold_failures(self) -> None:
        """Test circuit opens after threshold consecutive failures."""
        breaker = CircuitBreaker(threshold=3)

        breaker.record_failure()
        assert breaker.is_open is False
        breaker.record_failure()
        assert breaker.is_open is False
        breaker.record_failure()
        assert breaker.is_open is True

    def test_success_resets_failure_count(self) -> None:
        """Test success resets failure count and closes circuit."""
        breaker = CircuitBreaker(threshold=3)

        breaker.record_failure()
        breaker.record_failure()
        assert breaker.failure_count == 2

        breaker.record_success()
        assert breaker.failure_count == 0
        assert breaker.is_open is False

    def test_success_closes_open_circuit(self) -> None:
        """Test success closes an open circuit."""
        breaker = CircuitBreaker(threshold=2)

        breaker.record_failure()
        breaker.record_failure()
        assert breaker.is_open is True

        breaker.record_success()
        assert breaker.is_open is False

    def test_manual_reset(self) -> None:
        """Test manual reset of circuit breaker."""
        breaker = CircuitBreaker(threshold=2)

        breaker.record_failure()
        breaker.record_failure()
        assert breaker.is_open is True

        breaker.reset()
        assert breaker.is_open is False
        assert breaker.failure_count == 0

    def test_disabled_when_threshold_zero(self) -> None:
        """Test circuit breaker is disabled when threshold is 0."""
        breaker = CircuitBreaker(threshold=0)

        # Many failures should not open the circuit
        for _ in range(100):
            breaker.record_failure()

        assert breaker.is_open is False


class TestCreateRetryDecorator:
    """Tests for create_retry_decorator factory."""

    def test_successful_function_not_retried(self) -> None:
        """Test successful function is not retried."""
        config = RetryConfig(max_attempts=3)
        call_count = 0

        @create_retry_decorator(config)
        def successful_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()

        assert result == "success"
        assert call_count == 1

    def test_retries_on_connection_error(self) -> None:
        """Test function is retried on CatalogConnectionError."""
        config = RetryConfig(max_attempts=3, initial_wait_seconds=0.1, jitter_seconds=0)
        call_count = 0

        @create_retry_decorator(config)
        def flaky_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise CatalogConnectionError("Connection failed")
            return "success"

        result = flaky_func()

        assert result == "success"
        assert call_count == 3

    def test_raises_after_max_attempts(self) -> None:
        """Test exception is raised after max attempts exhausted."""
        config = RetryConfig(max_attempts=2, initial_wait_seconds=0.1, jitter_seconds=0)
        call_count = 0

        @create_retry_decorator(config)
        def always_fails() -> str:
            nonlocal call_count
            call_count += 1
            raise CatalogConnectionError("Always fails")

        with pytest.raises(CatalogConnectionError):
            always_fails()

        assert call_count == 2

    def test_non_retryable_exception_not_retried(self) -> None:
        """Test non-retryable exceptions are not retried."""
        config = RetryConfig(max_attempts=3)
        call_count = 0

        @create_retry_decorator(config)
        def value_error_func() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            value_error_func()

        assert call_count == 1  # Not retried

    def test_custom_retry_exceptions(self) -> None:
        """Test custom exception types can be specified."""
        config = RetryConfig(max_attempts=3, initial_wait_seconds=0.1, jitter_seconds=0)
        call_count = 0

        @create_retry_decorator(config, retry_exceptions=(ValueError,))
        def custom_retry_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Custom retry")
            return "success"

        result = custom_retry_func()

        assert result == "success"
        assert call_count == 2

    def test_circuit_breaker_integration(self) -> None:
        """Test circuit breaker prevents calls when open."""
        config = RetryConfig(max_attempts=1, initial_wait_seconds=0.1)
        breaker = CircuitBreaker(threshold=1)
        call_count = 0

        @create_retry_decorator(config, circuit_breaker=breaker)
        def func() -> str:
            nonlocal call_count
            call_count += 1
            raise CatalogConnectionError("Fail")

        # First call fails - circuit opens after failure
        with pytest.raises(CatalogConnectionError):
            func()

        assert call_count == 1
        assert breaker.is_open is True

        # Second call should fail fast with CircuitOpenError (not even called)
        with pytest.raises(CircuitOpenError):
            func()

        assert call_count == 1  # Function was not called again

    def test_preserves_function_metadata(self) -> None:
        """Test decorator preserves function name and docstring."""
        config = RetryConfig()

        @create_retry_decorator(config)
        def my_function() -> str:
            """My docstring."""
            return "result"

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."


class TestWithRetry:
    """Tests for with_retry convenience decorator."""

    def test_default_config(self) -> None:
        """Test with_retry uses default config."""
        call_count = 0

        @with_retry()
        def func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = func()

        assert result == "success"
        assert call_count == 1

    def test_custom_config(self) -> None:
        """Test with_retry accepts custom config."""
        config = RetryConfig(max_attempts=2, initial_wait_seconds=0.1, jitter_seconds=0)
        call_count = 0

        @with_retry(config)
        def func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise CatalogConnectionError("Fail")
            return "success"

        result = func()

        assert result == "success"
        assert call_count == 2

    def test_custom_exceptions(self) -> None:
        """Test with_retry accepts custom exception types."""
        call_count = 0

        @with_retry(
            RetryConfig(max_attempts=2, initial_wait_seconds=0.1, jitter_seconds=0),
            retry_exceptions=(KeyError,),
        )
        def func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise KeyError("Custom")
            return "success"

        result = func()

        assert result == "success"
        assert call_count == 2
