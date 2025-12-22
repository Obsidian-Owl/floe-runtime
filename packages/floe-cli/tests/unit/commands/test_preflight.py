"""Unit tests for floe preflight command.

Covers: 007-FR-005 (pre-deployment validation)

Run with:
    pytest packages/floe-cli/tests/unit/commands/test_preflight.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner
import pytest

from floe_cli.commands.preflight import preflight


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


class TestPreflightCommand:
    """Tests for preflight command."""

    @pytest.mark.requirement("007-FR-005")
    def test_help_shows_description(self, runner: CliRunner) -> None:
        """Help shows command description."""
        result = runner.invoke(preflight, ["--help"])

        assert result.exit_code == 0
        assert "pre-deployment validation" in result.output.lower()

    @pytest.mark.requirement("007-FR-005")
    def test_help_shows_options(self, runner: CliRunner) -> None:
        """Help shows all options."""
        result = runner.invoke(preflight, ["--help"])

        assert "--compute" in result.output
        assert "--storage" in result.output
        assert "--catalog" in result.output
        assert "--postgres" in result.output
        assert "--compute-type" in result.output
        assert "--bucket" in result.output
        assert "--fail-fast" in result.output
        assert "--format" in result.output

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.run_preflight")
    @patch("floe_core.preflight.print_result")
    def test_all_checks_pass(
        self,
        mock_print: MagicMock,
        mock_run: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Command exits 0 when all checks pass."""
        from floe_core.preflight.models import CheckStatus, PreflightResult

        mock_result = MagicMock(spec=PreflightResult)
        mock_result.passed = True
        mock_result.overall_status = CheckStatus.PASSED
        mock_run.return_value = mock_result

        result = runner.invoke(preflight)

        assert result.exit_code == 0
        mock_run.assert_called_once()
        mock_print.assert_called_once()

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.run_preflight")
    @patch("floe_core.preflight.print_result")
    def test_checks_fail(
        self,
        mock_print: MagicMock,
        mock_run: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Command exits 1 when checks fail."""
        from floe_core.preflight.models import CheckStatus, PreflightResult

        mock_result = MagicMock(spec=PreflightResult)
        mock_result.passed = False
        mock_result.overall_status = CheckStatus.FAILED
        mock_run.return_value = mock_result

        result = runner.invoke(preflight)

        assert result.exit_code == 1

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.run_preflight")
    @patch("floe_core.preflight.print_result")
    def test_disable_compute_check(
        self,
        mock_print: MagicMock,
        mock_run: MagicMock,
        runner: CliRunner,
    ) -> None:
        """--no-compute disables compute check."""
        from floe_core.preflight.models import PreflightResult

        mock_result = MagicMock(spec=PreflightResult)
        mock_result.passed = True
        mock_run.return_value = mock_result

        runner.invoke(preflight, ["--no-compute"])

        # Verify config was created with compute disabled
        call_args = mock_run.call_args
        config = call_args[0][0]
        assert config.compute.enabled is False

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.run_preflight")
    @patch("floe_core.preflight.print_result")
    def test_set_compute_type(
        self,
        mock_print: MagicMock,
        mock_run: MagicMock,
        runner: CliRunner,
    ) -> None:
        """--compute-type sets compute engine type."""
        from floe_core.preflight.models import PreflightResult

        mock_result = MagicMock(spec=PreflightResult)
        mock_result.passed = True
        mock_run.return_value = mock_result

        runner.invoke(preflight, ["--compute-type", "snowflake"])

        config = mock_run.call_args[0][0]
        assert config.compute.type == "snowflake"

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.run_preflight")
    @patch("floe_core.preflight.print_result")
    def test_set_bucket(
        self,
        mock_print: MagicMock,
        mock_run: MagicMock,
        runner: CliRunner,
    ) -> None:
        """--bucket sets storage bucket."""
        from floe_core.preflight.models import PreflightResult

        mock_result = MagicMock(spec=PreflightResult)
        mock_result.passed = True
        mock_run.return_value = mock_result

        runner.invoke(preflight, ["--bucket", "s3://my-bucket"])

        config = mock_run.call_args[0][0]
        assert config.storage.bucket == "s3://my-bucket"

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.run_preflight")
    @patch("floe_core.preflight.print_result")
    def test_set_catalog_uri(
        self,
        mock_print: MagicMock,
        mock_run: MagicMock,
        runner: CliRunner,
    ) -> None:
        """--catalog-uri sets catalog URI."""
        from floe_core.preflight.models import PreflightResult

        mock_result = MagicMock(spec=PreflightResult)
        mock_result.passed = True
        mock_run.return_value = mock_result

        runner.invoke(preflight, ["--catalog-uri", "http://polaris:8181"])

        config = mock_run.call_args[0][0]
        assert config.catalog.uri == "http://polaris:8181"

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.run_preflight")
    @patch("floe_core.preflight.print_result")
    def test_set_postgres_options(
        self,
        mock_print: MagicMock,
        mock_run: MagicMock,
        runner: CliRunner,
    ) -> None:
        """PostgreSQL options are passed to config."""
        from floe_core.preflight.models import PreflightResult

        mock_result = MagicMock(spec=PreflightResult)
        mock_result.passed = True
        mock_run.return_value = mock_result

        runner.invoke(
            preflight,
            [
                "--postgres-host",
                "db.example.com",
                "--postgres-port",
                "5433",
                "--postgres-database",
                "mydb",
            ],
        )

        config = mock_run.call_args[0][0]
        assert config.postgres.host == "db.example.com"
        assert config.postgres.port == 5433
        assert config.postgres.database == "mydb"

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.run_preflight")
    @patch("floe_core.preflight.print_result")
    def test_fail_fast_option(
        self,
        mock_print: MagicMock,
        mock_run: MagicMock,
        runner: CliRunner,
    ) -> None:
        """--fail-fast sets fail_fast in config."""
        from floe_core.preflight.models import PreflightResult

        mock_result = MagicMock(spec=PreflightResult)
        mock_result.passed = True
        mock_run.return_value = mock_result

        runner.invoke(preflight, ["--fail-fast"])

        config = mock_run.call_args[0][0]
        assert config.fail_fast is True

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.run_preflight")
    @patch("floe_core.preflight.print_result")
    def test_json_format(
        self,
        mock_print: MagicMock,
        mock_run: MagicMock,
        runner: CliRunner,
    ) -> None:
        """--format json passes format to print_result."""
        from floe_core.preflight.models import PreflightResult

        mock_result = MagicMock(spec=PreflightResult)
        mock_result.passed = True
        mock_run.return_value = mock_result

        runner.invoke(preflight, ["--format", "json"])

        mock_print.assert_called_once()
        call_kwargs = mock_print.call_args[1]
        assert call_kwargs["output_format"] == "json"

    @pytest.mark.requirement("007-FR-005")
    @patch("floe_core.preflight.run_preflight")
    @patch("floe_core.preflight.print_result")
    def test_timeout_option(
        self,
        mock_print: MagicMock,
        mock_run: MagicMock,
        runner: CliRunner,
    ) -> None:
        """--timeout sets timeout for all checks."""
        from floe_core.preflight.models import PreflightResult

        mock_result = MagicMock(spec=PreflightResult)
        mock_result.passed = True
        mock_run.return_value = mock_result

        runner.invoke(preflight, ["--timeout", "60"])

        config = mock_run.call_args[0][0]
        assert config.compute.timeout_seconds == 60
        assert config.storage.timeout_seconds == 60
        assert config.catalog.timeout_seconds == 60
        assert config.postgres.timeout_seconds == 60


class TestPreflightCommandIntegration:
    """Integration-style tests for preflight command."""

    @pytest.mark.requirement("007-FR-005")
    def test_command_registered_in_main(self) -> None:
        """Preflight command is registered in main CLI."""
        from floe_cli.main import LAZY_COMMANDS

        assert "preflight" in LAZY_COMMANDS
        assert LAZY_COMMANDS["preflight"] == "floe_cli.commands.preflight.preflight"

    @pytest.mark.requirement("007-FR-005")
    def test_compute_type_choices(self, runner: CliRunner) -> None:
        """Invalid compute type shows error."""
        result = runner.invoke(preflight, ["--compute-type", "invalid"])

        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "choice" in result.output.lower()

    @pytest.mark.requirement("007-FR-005")
    def test_format_choices(self, runner: CliRunner) -> None:
        """Invalid format shows error."""
        result = runner.invoke(preflight, ["--format", "invalid"])

        assert result.exit_code != 0
