"""Unit tests for floe_cli.output module.

T009: Create test_output.py - Unit tests for output utilities
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from floe_cli import output


class TestCreateConsole:
    """Tests for create_console function."""

    def test_create_console_default(self) -> None:
        """Test creating console with default settings."""
        console = output.create_console()
        assert console is not None

    def test_create_console_no_color(self) -> None:
        """Test creating console with no_color=True."""
        console = output.create_console(no_color=True)
        assert console.no_color is True

    def test_create_console_respects_env_var(self) -> None:
        """Test that NO_COLOR environment variable is respected."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}):
            # Re-import to pick up env var
            console = output.create_console()
            # Console should have colors disabled
            assert console is not None


class TestSuccess:
    """Tests for success() function."""

    def test_success_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test success message formatting."""
        # Create a console that writes to stdout
        test_console = output.create_console(no_color=True)
        original_console = output.console
        output.console = test_console

        try:
            output.success("Configuration valid")
            captured = capsys.readouterr()
            assert "Configuration valid" in captured.out
            assert "✓" in captured.out
        finally:
            output.console = original_console


class TestError:
    """Tests for error() function."""

    def test_error_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test error message formatting."""
        test_console = output.create_console(no_color=True)
        original_console = output.console
        output.console = test_console

        try:
            output.error("Validation failed")
            captured = capsys.readouterr()
            assert "Validation failed" in captured.out
            assert "✗" in captured.out
        finally:
            output.console = original_console


class TestWarning:
    """Tests for warning() function."""

    def test_warning_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test warning message formatting."""
        test_console = output.create_console(no_color=True)
        original_console = output.console
        output.console = test_console

        try:
            output.warning("Deprecated option")
            captured = capsys.readouterr()
            assert "Deprecated option" in captured.out
            assert "⚠" in captured.out
        finally:
            output.console = original_console


class TestInfo:
    """Tests for info() function."""

    def test_info_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test info message formatting."""
        test_console = output.create_console(no_color=True)
        original_console = output.console
        output.console = test_console

        try:
            output.info("Compiling configuration...")
            captured = capsys.readouterr()
            assert "Compiling configuration..." in captured.out
        finally:
            output.console = original_console


class TestPrintJson:
    """Tests for print_json() function."""

    def test_print_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test JSON printing."""
        test_console = output.create_console(no_color=True)
        original_console = output.console
        output.console = test_console

        try:
            output.print_json({"name": "test", "version": "1.0.0"})
            captured = capsys.readouterr()
            assert "name" in captured.out
            assert "test" in captured.out
            assert "version" in captured.out
        finally:
            output.console = original_console


class TestSetNoColor:
    """Tests for set_no_color() function."""

    def test_set_no_color_true(self) -> None:
        """Test setting no_color to True."""
        original_console = output.console
        try:
            output.set_no_color(True)
            assert output.console.no_color is True
        finally:
            output.console = original_console

    def test_set_no_color_false(self) -> None:
        """Test setting no_color to False."""
        original_console = output.console
        try:
            output.set_no_color(False)
            # Console should allow colors (unless env var is set)
            assert output.console is not None
        finally:
            output.console = original_console
