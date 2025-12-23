"""Unit tests for floe-core exception hierarchy.

Tests the FloeError, ValidationError, and CompilationError classes
per research.md exception design.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from floe_core.errors import (
    CompilationError,
    ConfigurationError,
    FloeError,
    ProfileNotFoundError,
    SecretResolutionError,
    ValidationError,
)

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
        error = FloeError(
            "User sees this",
            internal_details="Secret debug info: /path/to/file.py:42",
        )
        # Verify exception message is correct
        assert error.user_message == "User sees this"

        # structlog outputs to stdout
        captured = capsys.readouterr()
        # Internal details should be logged
        assert "Secret debug info" in captured.out
        # User message should also be in log
        assert "User sees this" in captured.out

    def test_floe_error_no_log_without_internal_details(self, caplog: LogCaptureFixture) -> None:
        """FloeError should not log if internal_details is None."""
        with caplog.at_level(logging.ERROR):
            error = FloeError("Just a user message")
            # Verify exception message is correct
            assert error.user_message == "Just a user message"

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
        error = ValidationError(
            "Config invalid",
            internal_details="Field 'name' failed regex: got 'invalid!'",
        )
        # Verify exception message is correct
        assert error.user_message == "Config invalid"

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
        error = CompilationError(
            "Compilation failed",
            internal_details="Missing dbt manifest at /project/target/manifest.json",
        )
        # Verify exception message is correct
        assert error.user_message == "Compilation failed"

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


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_configuration_error_inherits_from_floe_error(self) -> None:
        """ConfigurationError should inherit from FloeError."""
        error = ConfigurationError("Invalid YAML")
        assert isinstance(error, FloeError)
        assert isinstance(error, Exception)

    def test_configuration_error_with_no_context(self) -> None:
        """ConfigurationError without context should show plain message."""
        error = ConfigurationError("Invalid YAML syntax")
        assert error.user_message == "Invalid YAML syntax"
        assert str(error) == "Invalid YAML syntax"

    def test_configuration_error_with_file_path(self) -> None:
        """ConfigurationError with file_path should include it in message."""
        error = ConfigurationError("Invalid YAML", file_path="platform.yaml")
        assert "platform.yaml" in error.user_message
        assert "in platform.yaml" in str(error)
        assert error.file_path == "platform.yaml"

    def test_configuration_error_with_line_number(self) -> None:
        """ConfigurationError with line_number should include it in message."""
        error = ConfigurationError(
            "Invalid value",
            file_path="platform.yaml",
            line_number=42,
        )
        assert "line 42" in str(error)
        assert error.line_number == 42

    def test_configuration_error_with_field_path(self) -> None:
        """ConfigurationError with field_path should include it in message."""
        error = ConfigurationError(
            "Invalid URI",
            file_path="platform.yaml",
            field_path="catalogs.default.uri",
        )
        assert "catalogs.default.uri" in str(error)
        assert error.field_path == "catalogs.default.uri"

    def test_configuration_error_with_all_context(self) -> None:
        """ConfigurationError with all context should show complete message."""
        error = ConfigurationError(
            "Invalid URI format",
            file_path="platform.yaml",
            field_path="catalogs.default.uri",
            line_number=15,
            internal_details="Expected http:// or https://, got: ftp://",
        )

        message = str(error)
        assert "Invalid URI format" in message
        assert "platform.yaml" in message
        assert "line 15" in message
        assert "catalogs.default.uri" in message
        # Internal details not in user message
        assert "ftp://" not in error.user_message

    def test_configuration_error_attributes(self) -> None:
        """ConfigurationError should store all attributes."""
        error = ConfigurationError(
            "Test",
            file_path="test.yaml",
            field_path="foo.bar",
            line_number=10,
        )
        assert error.file_path == "test.yaml"
        assert error.field_path == "foo.bar"
        assert error.line_number == 10


class TestProfileNotFoundError:
    """Tests for ProfileNotFoundError exception."""

    def test_profile_not_found_inherits_from_floe_error(self) -> None:
        """ProfileNotFoundError should inherit from FloeError."""
        error = ProfileNotFoundError(
            profile_type="catalog",
            profile_name="production",
            available_profiles=["default"],
        )
        assert isinstance(error, FloeError)

    def test_profile_not_found_message_format(self) -> None:
        """ProfileNotFoundError should format message with available profiles."""
        error = ProfileNotFoundError(
            profile_type="catalog",
            profile_name="production",
            available_profiles=["default", "staging"],
        )

        message = str(error)
        assert "Catalog profile 'production' not found" in message
        assert "Available: default, staging" in message

    def test_profile_not_found_empty_available(self) -> None:
        """ProfileNotFoundError with no available profiles should show 'none'."""
        error = ProfileNotFoundError(
            profile_type="storage",
            profile_name="s3",
            available_profiles=[],
        )

        message = str(error)
        assert "Storage profile 's3' not found" in message
        assert "Available: none" in message

    def test_profile_not_found_attributes(self) -> None:
        """ProfileNotFoundError should store all attributes."""
        error = ProfileNotFoundError(
            profile_type="compute",
            profile_name="snowflake",
            available_profiles=["duckdb", "default"],
        )

        assert error.profile_type == "compute"
        assert error.profile_name == "snowflake"
        assert error.available_profiles == ["duckdb", "default"]

    def test_profile_not_found_capitalizes_type(self) -> None:
        """ProfileNotFoundError should capitalize the profile type."""
        error = ProfileNotFoundError(
            profile_type="storage",
            profile_name="test",
            available_profiles=[],
        )

        assert str(error).startswith("Storage")


class TestSecretResolutionError:
    """Tests for SecretResolutionError exception."""

    def test_secret_resolution_inherits_from_floe_error(self) -> None:
        """SecretResolutionError should inherit from FloeError."""
        error = SecretResolutionError(
            secret_ref="polaris-oauth-secret",
            expected_env_var="POLARIS_OAUTH_SECRET",
            expected_k8s_path="/var/run/secrets/polaris-oauth-secret",
        )
        assert isinstance(error, FloeError)

    def test_secret_resolution_message_format(self) -> None:
        """SecretResolutionError should format message with expected locations."""
        error = SecretResolutionError(
            secret_ref="polaris-oauth-secret",
            expected_env_var="POLARIS_OAUTH_SECRET",
            expected_k8s_path="/var/run/secrets/polaris-oauth-secret",
        )

        message = str(error)
        assert "Secret 'polaris-oauth-secret' not found" in message
        assert "POLARIS_OAUTH_SECRET" in message
        assert "/var/run/secrets/polaris-oauth-secret" in message

    def test_secret_resolution_attributes(self) -> None:
        """SecretResolutionError should store all attributes."""
        error = SecretResolutionError(
            secret_ref="my-secret",
            expected_env_var="MY_SECRET",
            expected_k8s_path="/var/run/secrets/my-secret",
        )

        assert error.secret_ref == "my-secret"
        assert error.expected_env_var == "MY_SECRET"
        assert error.expected_k8s_path == "/var/run/secrets/my-secret"

    def test_secret_resolution_with_internal_details(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """SecretResolutionError should log internal details."""
        error = SecretResolutionError(
            secret_ref="db-password",
            expected_env_var="DB_PASSWORD",
            expected_k8s_path="/var/run/secrets/db-password",
            internal_details="Checked env vars: PATH, HOME, USER",
        )

        # User message should not contain internal details
        assert "Checked env vars" not in error.user_message

        # Internal details should be logged
        captured = capsys.readouterr()
        assert "Checked env vars" in captured.out


class TestNewExceptionHierarchy:
    """Tests for the extended exception hierarchy."""

    def test_new_errors_are_floe_errors(self) -> None:
        """All new error types should be FloeError subclasses."""
        assert issubclass(ConfigurationError, FloeError)
        assert issubclass(ProfileNotFoundError, FloeError)
        assert issubclass(SecretResolutionError, FloeError)

    def test_new_errors_are_distinct(self) -> None:
        """New error types should not inherit from each other."""
        assert not issubclass(ConfigurationError, ProfileNotFoundError)
        assert not issubclass(ProfileNotFoundError, SecretResolutionError)
        assert not issubclass(SecretResolutionError, ConfigurationError)

    def test_catch_all_with_floe_error(self) -> None:
        """FloeError should catch all new subclasses."""
        errors_to_test = [
            ConfigurationError("Config error"),
            ProfileNotFoundError("catalog", "prod", ["default"]),
            SecretResolutionError("secret", "SECRET", "/path"),
        ]

        for error in errors_to_test:
            with pytest.raises(FloeError):
                raise error
