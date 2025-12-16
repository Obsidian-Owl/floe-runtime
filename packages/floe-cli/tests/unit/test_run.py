"""Tests for floe run command stub.

T037: Unit tests for run command stub
"""

from __future__ import annotations

from click.testing import CliRunner
from floe_cli.commands.run import run


class TestRunStub:
    """Tests for run command stub."""

    def test_run_shows_not_installed_error(
        self, cli_runner: CliRunner
    ) -> None:
        """Test run shows floe-dagster not installed error."""
        result = cli_runner.invoke(run)
        assert result.exit_code == 2
        assert "floe-dagster" in result.output.lower()
        assert "not installed" in result.output.lower()

    def test_run_shows_install_instructions(
        self, cli_runner: CliRunner
    ) -> None:
        """Test run shows installation instructions."""
        result = cli_runner.invoke(run)
        assert result.exit_code == 2
        assert "pip install" in result.output.lower()


class TestRunOptions:
    """Tests for run command options."""

    def test_run_accepts_file_option(self, cli_runner: CliRunner) -> None:
        """Test run accepts --file option (for future compatibility)."""
        result = cli_runner.invoke(run, ["--file", "custom.yaml"])
        # Should still show error, but accept the option
        assert result.exit_code == 2
        assert "floe-dagster" in result.output.lower()

    def test_run_accepts_select_option(self, cli_runner: CliRunner) -> None:
        """Test run accepts --select option (for future compatibility)."""
        result = cli_runner.invoke(run, ["--select", "my_model"])
        # Should still show error, but accept the option
        assert result.exit_code == 2
        assert "floe-dagster" in result.output.lower()

    def test_run_accepts_all_options(self, cli_runner: CliRunner) -> None:
        """Test run accepts all options together."""
        result = cli_runner.invoke(
            run, ["--file", "custom.yaml", "--select", "my_model"]
        )
        assert result.exit_code == 2


class TestRunHelp:
    """Tests for run command help."""

    def test_run_help_shows_description(self, cli_runner: CliRunner) -> None:
        """Test run --help shows meaningful description."""
        result = cli_runner.invoke(run, ["--help"])
        assert result.exit_code == 0
        assert "dagster" in result.output.lower()

    def test_run_help_shows_file_option(self, cli_runner: CliRunner) -> None:
        """Test run --help documents --file option."""
        result = cli_runner.invoke(run, ["--help"])
        assert result.exit_code == 0
        assert "--file" in result.output

    def test_run_help_shows_select_option(self, cli_runner: CliRunner) -> None:
        """Test run --help documents --select option."""
        result = cli_runner.invoke(run, ["--help"])
        assert result.exit_code == 0
        assert "--select" in result.output
