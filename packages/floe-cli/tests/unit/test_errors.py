"""Unit tests for floe_cli.errors module.

T010: Create test_errors.py - Unit tests for error handling
"""

from __future__ import annotations

import pytest
from floe_cli.errors import (
    EXIT_SYSTEM_ERROR,
    EXIT_USER_ERROR,
    CLIError,
    format_pydantic_error,
    handle_file_not_found,
    handle_permission_error,
    handle_validation_error,
)
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError


class TestCLIError:
    """Tests for CLIError exception."""

    def test_cli_error_message(self) -> None:
        """Test CLIError stores message correctly."""
        error = CLIError("Test error message")
        assert error.message == "Test error message"
        assert str(error) == "Test error message"

    def test_cli_error_default_exit_code(self) -> None:
        """Test CLIError has default exit code of 1."""
        error = CLIError("Test error")
        assert error.exit_code == EXIT_USER_ERROR

    def test_cli_error_custom_exit_code(self) -> None:
        """Test CLIError accepts custom exit code."""
        error = CLIError("Test error", exit_code=EXIT_SYSTEM_ERROR)
        assert error.exit_code == EXIT_SYSTEM_ERROR


class TestFormatPydanticError:
    """Tests for format_pydantic_error function."""

    def test_format_single_error(self) -> None:
        """Test formatting a single validation error."""

        class TestModel(BaseModel):
            name: str

        try:
            TestModel()  # Missing required field
        except PydanticValidationError as e:
            formatted = format_pydantic_error(e)
            assert "Validation failed:" in formatted
            assert "name" in formatted
            assert "Field required" in formatted

    def test_format_multiple_errors(self) -> None:
        """Test formatting multiple validation errors."""

        class TestModel(BaseModel):
            name: str
            version: str

        try:
            TestModel()  # Missing both fields
        except PydanticValidationError as e:
            formatted = format_pydantic_error(e)
            assert "Validation failed:" in formatted
            assert "name" in formatted
            assert "version" in formatted

    def test_format_nested_error(self) -> None:
        """Test formatting errors in nested models."""

        class NestedModel(BaseModel):
            value: int

        class ParentModel(BaseModel):
            nested: NestedModel

        try:
            ParentModel(nested={"value": "not_an_int"})
        except PydanticValidationError as e:
            formatted = format_pydantic_error(e)
            assert "Validation failed:" in formatted
            assert "nested.value" in formatted or "nested" in formatted


class TestHandleFileNotFound:
    """Tests for handle_file_not_found function."""

    def test_raises_cli_error(self) -> None:
        """Test that handle_file_not_found raises CLIError."""
        with pytest.raises(CLIError) as exc_info:
            handle_file_not_found("floe.yaml")

        assert "File not found: floe.yaml" in str(exc_info.value)
        assert exc_info.value.exit_code == EXIT_SYSTEM_ERROR

    def test_includes_suggestion(self) -> None:
        """Test that error message includes helpful suggestions."""
        with pytest.raises(CLIError) as exc_info:
            handle_file_not_found("floe.yaml")

        assert "floe init" in str(exc_info.value)
        assert "--file" in str(exc_info.value)


class TestHandlePermissionError:
    """Tests for handle_permission_error function."""

    def test_raises_cli_error(self) -> None:
        """Test that handle_permission_error raises CLIError."""
        with pytest.raises(CLIError) as exc_info:
            handle_permission_error("/path/to/file", "write")

        assert "Permission denied" in str(exc_info.value)
        assert "write" in str(exc_info.value)
        assert exc_info.value.exit_code == EXIT_SYSTEM_ERROR

    def test_default_operation(self) -> None:
        """Test default operation is 'access'."""
        with pytest.raises(CLIError) as exc_info:
            handle_permission_error("/path/to/file")

        assert "access" in str(exc_info.value)


class TestHandleValidationError:
    """Tests for handle_validation_error function."""

    def test_raises_cli_error_with_formatted_message(self) -> None:
        """Test that handle_validation_error raises CLIError with formatted message."""

        class TestModel(BaseModel):
            name: str

        try:
            TestModel()  # Missing required field
        except PydanticValidationError as e:
            with pytest.raises(CLIError) as exc_info:
                handle_validation_error(e, "floe.yaml")

            assert "Invalid configuration in floe.yaml" in str(exc_info.value)
            assert "name" in str(exc_info.value)
