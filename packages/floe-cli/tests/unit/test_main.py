"""Unit tests for floe_cli.main module.

T011: Create test_main.py - Test --help output format
"""

from __future__ import annotations

from click.testing import CliRunner
from floe_cli.main import cli


class TestCLIHelp:
    """Tests for CLI help output."""

    def test_help_shows_version_option(self) -> None:
        """Test that --help shows version option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "--version" in result.output
        assert "--help" in result.output

    def test_help_shows_no_color_option(self) -> None:
        """Test that --help shows no-color option."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "--no-color" in result.output

    def test_help_shows_all_commands(self) -> None:
        """Test that --help shows all available commands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        # Check for all commands in lazy loading config
        assert "validate" in result.output
        assert "compile" in result.output
        assert "init" in result.output
        assert "run" in result.output
        assert "dev" in result.output
        assert "schema" in result.output

    def test_help_shows_description(self) -> None:
        """Test that --help shows CLI description."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Floe Runtime" in result.output


class TestCLIVersion:
    """Tests for CLI version output."""

    def test_version_output(self) -> None:
        """Test that --version outputs version number."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output
        assert "floe" in result.output.lower()


class TestCLINoColor:
    """Tests for CLI no-color option."""

    def test_no_color_option_accepted(self) -> None:
        """Test that --no-color option is accepted."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--no-color", "--help"])

        # Should not fail due to --no-color
        assert result.exit_code == 0


class TestLazyGroup:
    """Tests for LazyGroup command loading."""

    def test_list_commands_returns_all(self) -> None:
        """Test that list_commands returns all lazy commands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        # All commands should be listed
        expected_commands = ["compile", "dev", "init", "run", "schema", "validate"]
        for cmd in expected_commands:
            assert cmd in result.output
