"""Performance tests for CLI help.

T012: Create test_help_performance.py - Test --help completes in <500ms
"""

from __future__ import annotations

import time

from click.testing import CliRunner
from floe_cli.main import cli


class TestHelpPerformance:
    """Performance tests for CLI help command."""

    def test_help_completes_under_500ms(self) -> None:
        """Test that --help completes in under 500ms.

        This test validates the LazyGroup pattern is working correctly
        and commands are not being imported at help time.
        """
        runner = CliRunner()

        start_time = time.perf_counter()
        result = runner.invoke(cli, ["--help"])
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        assert result.exit_code == 0
        assert elapsed_ms < 500, f"Help took {elapsed_ms:.1f}ms, expected < 500ms"

    def test_version_completes_under_500ms(self) -> None:
        """Test that --version completes in under 500ms."""
        runner = CliRunner()

        start_time = time.perf_counter()
        result = runner.invoke(cli, ["--version"])
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        assert result.exit_code == 0
        assert elapsed_ms < 500, f"Version took {elapsed_ms:.1f}ms, expected < 500ms"

    def test_subcommand_help_completes_under_500ms(self) -> None:
        """Test that subcommand --help completes in under 500ms."""
        runner = CliRunner()

        start_time = time.perf_counter()
        result = runner.invoke(cli, ["validate", "--help"])
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        assert result.exit_code == 0
        assert elapsed_ms < 500, f"Subcommand help took {elapsed_ms:.1f}ms, expected < 500ms"
