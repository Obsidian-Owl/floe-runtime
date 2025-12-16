"""Tests for floe dev command stub.

T040: Unit tests for dev command stub
"""

from __future__ import annotations

from click.testing import CliRunner
from floe_cli.commands.dev import dev


class TestDevStub:
    """Tests for dev command stub."""

    def test_dev_shows_not_installed_error(
        self, cli_runner: CliRunner
    ) -> None:
        """Test dev shows floe-dagster not installed error."""
        result = cli_runner.invoke(dev)
        assert result.exit_code == 2
        assert "floe-dagster" in result.output.lower()
        assert "not installed" in result.output.lower()

    def test_dev_shows_install_instructions(
        self, cli_runner: CliRunner
    ) -> None:
        """Test dev shows installation instructions."""
        result = cli_runner.invoke(dev)
        assert result.exit_code == 2
        assert "pip install" in result.output.lower()


class TestDevOptions:
    """Tests for dev command options."""

    def test_dev_accepts_file_option(self, cli_runner: CliRunner) -> None:
        """Test dev accepts --file option (for future compatibility)."""
        result = cli_runner.invoke(dev, ["--file", "custom.yaml"])
        # Should still show error, but accept the option
        assert result.exit_code == 2
        assert "floe-dagster" in result.output.lower()

    def test_dev_accepts_port_option(self, cli_runner: CliRunner) -> None:
        """Test dev accepts --port option (for future compatibility)."""
        result = cli_runner.invoke(dev, ["--port", "3001"])
        # Should still show error, but accept the option
        assert result.exit_code == 2
        assert "floe-dagster" in result.output.lower()

    def test_dev_accepts_all_options(self, cli_runner: CliRunner) -> None:
        """Test dev accepts all options together."""
        result = cli_runner.invoke(
            dev, ["--file", "custom.yaml", "--port", "3001"]
        )
        assert result.exit_code == 2


class TestDevHelp:
    """Tests for dev command help."""

    def test_dev_help_shows_description(self, cli_runner: CliRunner) -> None:
        """Test dev --help shows meaningful description."""
        result = cli_runner.invoke(dev, ["--help"])
        assert result.exit_code == 0
        assert "dagster" in result.output.lower()

    def test_dev_help_shows_file_option(self, cli_runner: CliRunner) -> None:
        """Test dev --help documents --file option."""
        result = cli_runner.invoke(dev, ["--help"])
        assert result.exit_code == 0
        assert "--file" in result.output

    def test_dev_help_shows_port_option(self, cli_runner: CliRunner) -> None:
        """Test dev --help documents --port option."""
        result = cli_runner.invoke(dev, ["--help"])
        assert result.exit_code == 0
        assert "--port" in result.output

    def test_dev_help_shows_default_port(self, cli_runner: CliRunner) -> None:
        """Test dev --help shows default port."""
        result = cli_runner.invoke(dev, ["--help"])
        assert result.exit_code == 0
        assert "3000" in result.output
