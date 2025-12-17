"""Unit tests for floe-core exception hierarchy.

Tests the FloeError, ValidationError, and CompilationError classes
per research.md exception design.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from floe_core.errors import CompilationError, FloeError, ValidationError

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


class TestFloeError:
    """Tests for the base FloeError exception."""

    def test_floe_error_stores_user_message(self) -> None:
        """FloeError should store and expose user_message."""
        error = FloeError("Something went wrong")
        assert error.user_message == "Something went wrong"

    def test_floe_error_str_returns_user_message(self) -> None:
        """str(FloeError) should return user_message."""
        error = FloeError("Something went wrong")
        assert str(error) == "Something went wrong"

    def test_floe_error_is_exception(self) -> None:
        """FloeError should be a proper Exception subclass."""
        error = FloeError("Test error")
        assert isinstance(error, Exception)

    def test_floe_error_can_be_raised_and_caught(self) -> None:
        """FloeError should be raisable and catchable."""
        with pytest.raises(FloeError) as exc_info:
            raise FloeError("Test raise")
        assert exc_info.value.user_message == "Test raise"

    def test_floe_error_logs_internal_details(self, capsys: pytest.CaptureFixture[str]) -> None:
        """FloeError should log internal_details when provided."""
        _error = FloeError(
            "User sees this",
            internal_details="Secret debug info: /path/to/file.py:42",
        )
        assert _error is not None  # Verify exception was created

        # structlog outputs to stdout
        captured = capsys.readouterr()
        # Internal details should be logged
        assert "Secret debug info" in captured.out
        # User message should also be in log
        assert "User sees this" in captured.out

    def test_floe_error_no_log_without_internal_details(self, caplog: LogCaptureFixture) -> None:
        """FloeError should not log if internal_details is None."""
        with caplog.at_level(logging.ERROR):
            _error = FloeError("Just a user message")
            assert _error is not None  # Verify exception was created

        # No error logging when internal_details not provided
        assert caplog.text == "" or "floe_error" not in caplog.text


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_validation_error_inherits_from_floe_error(self) -> None:
        """ValidationError should inherit from FloeError."""
        error = ValidationError("Invalid config")
        assert isinstance(error, FloeError)
        assert isinstance(error, Exception)

    def test_validation_error_stores_user_message(self) -> None:
        """ValidationError should store user_message."""
        error = ValidationError("Invalid config")
        assert error.user_message == "Invalid config"

    def test_validation_error_can_be_caught_as_floe_error(self) -> None:
        """ValidationError should be catchable as FloeError."""
        with pytest.raises(FloeError):
            raise ValidationError("Invalid config")

    def test_validation_error_logs_internal_details(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """ValidationError should log internal_details."""
        _error = ValidationError(
            "Config invalid",
            internal_details="Field 'name' failed regex: got 'invalid!'",
        )
        assert _error is not None  # Verify exception was created

        captured = capsys.readouterr()
        assert "Field 'name' failed regex" in captured.out


class TestCompilationError:
    """Tests for CompilationError exception."""

    def test_compilation_error_inherits_from_floe_error(self) -> None:
        """CompilationError should inherit from FloeError."""
        error = CompilationError("Compilation failed")
        assert isinstance(error, FloeError)
        assert isinstance(error, Exception)

    def test_compilation_error_stores_user_message(self) -> None:
        """CompilationError should store user_message."""
        error = CompilationError("Compilation failed")
        assert error.user_message == "Compilation failed"

    def test_compilation_error_can_be_caught_as_floe_error(self) -> None:
        """CompilationError should be catchable as FloeError."""
        with pytest.raises(FloeError):
            raise CompilationError("Compilation failed")

    def test_compilation_error_logs_internal_details(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """CompilationError should log internal_details."""
        _error = CompilationError(
            "Compilation failed",
            internal_details="Missing dbt manifest at /project/target/manifest.json",
        )
        assert _error is not None  # Verify exception was created

        captured = capsys.readouterr()
        assert "Missing dbt manifest" in captured.out


class TestExceptionHierarchy:
    """Tests for the complete exception hierarchy."""

    def test_hierarchy_structure(self) -> None:
        """Verify the exception hierarchy: FloeError -> ValidationError, CompilationError."""
        # Check inheritance
        assert issubclass(ValidationError, FloeError)
        assert issubclass(CompilationError, FloeError)

        # Check they're distinct
        assert not issubclass(ValidationError, CompilationError)
        assert not issubclass(CompilationError, ValidationError)

    def test_selective_catching(self) -> None:
        """Different exception types should be catchable selectively."""
        # Catch only ValidationError
        with pytest.raises(ValidationError):
            raise ValidationError("Validation failed")

        # Catch only CompilationError
        with pytest.raises(CompilationError):
            raise CompilationError("Compilation failed")

    def test_catch_all_with_floe_error(self) -> None:
        """FloeError should catch all subclasses."""
        errors_to_test = [
            FloeError("Base error"),
            ValidationError("Validation error"),
            CompilationError("Compilation error"),
        ]

        for error in errors_to_test:
            with pytest.raises(FloeError):
                raise error


class TestSecurityCompliance:
    """Tests ensuring exception hierarchy meets security requirements.

    Per Constitution Principle V (Security First):
    - Error messages to users MUST NOT expose internal details
    - Technical details logged internally only
    """

    def test_user_message_does_not_expose_file_paths(self) -> None:
        """User message should not contain file paths."""
        error = FloeError(
            "Configuration invalid",  # Safe user message
            internal_details="/Users/dev/project/floe.yaml:42",  # Internal only
        )

        # User message should not have path
        assert "/Users" not in error.user_message
        assert ".yaml" not in error.user_message
        assert str(error) == "Configuration invalid"

    def test_user_message_does_not_expose_stack_traces(self) -> None:
        """User message should not contain stack traces."""
        error = ValidationError(
            "Validation failed",
            internal_details="Traceback: File 'schema.py', line 42, in validate...",
        )

        assert "Traceback" not in error.user_message
        assert "line 42" not in error.user_message

    def test_internal_details_logged_separately(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Internal details should be logged but not exposed in user message."""
        error = CompilationError(
            "Compilation failed - check logs for details",
            internal_details="KeyError: 'transforms' at /path/to/config.yaml:15",
        )

        # User sees generic message
        assert error.user_message == "Compilation failed - check logs for details"

        # Internal details in logs (structlog outputs to stdout)
        captured = capsys.readouterr()
        assert "KeyError" in captured.out
        assert "/path/to/config.yaml" in captured.out
