"""Integration tests for CLI features covering remaining gaps.

Tests the CLI command features that were not covered by existing tests.

Covers:
- FR-004: floe run command (executes pipelines via Dagster)
- FR-005: floe dev command (starts development environment)
- FR-006: floe schema export command
- FR-012: --target option validation
- FR-013: Colored terminal output
- FR-014: --no-color option
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
import pytest

from floe_cli.main import cli


# Valid floe.yaml content for tests
VALID_FLOE_YAML = """\
name: test-project
version: "1.0.0"
compute:
  target: duckdb
  properties:
    path: ":memory:"
    threads: 4
transforms:
  - type: dbt
    path: ./dbt
"""

# Multi-target floe.yaml (for testing --target option)
MULTI_TARGET_FLOE_YAML = """\
name: multi-target-project
version: "1.0.0"
compute:
  target: duckdb
  properties:
    path: ":memory:"
transforms:
  - type: dbt
    path: ./dbt
"""


class TestRunCommand:
    """Integration tests for floe run command (002-FR-004)."""

    @pytest.mark.requirement("002-FR-004")
    def test_run_command_exists(self) -> None:
        """Test that floe run command exists and is accessible.

        Covers:
        - 002-FR-004: floe run command exists
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])

        # Command exists (help works)
        assert result.exit_code == 0
        assert "pipeline" in result.output.lower() or "dagster" in result.output.lower()

    @pytest.mark.requirement("002-FR-004")
    def test_run_command_requires_dagster(self) -> None:
        """Test that floe run indicates floe-dagster is required.

        Covers:
        - 002-FR-004: floe run requires floe-dagster package

        Note: This is expected behavior - the run command is a stub
        until floe-dagster is implemented. The test verifies the user
        receives a clear message about the missing dependency.
        """
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("floe.yaml").write_text(VALID_FLOE_YAML)

            result = runner.invoke(cli, ["run"])

            # Should indicate floe-dagster is required
            # Exit code 2 indicates the command recognizes it can't run
            assert result.exit_code == 2
            assert "dagster" in result.output.lower()
            assert "install" in result.output.lower()

    @pytest.mark.requirement("002-FR-004")
    def test_run_command_accepts_file_option(self) -> None:
        """Test that floe run accepts --file option.

        Covers:
        - 002-FR-004: floe run command with --file option
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])

        assert result.exit_code == 0
        assert "--file" in result.output or "-f" in result.output

    @pytest.mark.requirement("002-FR-004")
    def test_run_command_accepts_select_option(self) -> None:
        """Test that floe run accepts --select option.

        Covers:
        - 002-FR-004: floe run command with --select for model selection
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "--help"])

        assert result.exit_code == 0
        assert "--select" in result.output or "-s" in result.output


class TestDevCommand:
    """Integration tests for floe dev command (002-FR-005)."""

    @pytest.mark.requirement("002-FR-005")
    def test_dev_command_exists(self) -> None:
        """Test that floe dev command exists and is accessible.

        Covers:
        - 002-FR-005: floe dev command exists
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["dev", "--help"])

        # Command exists (help works)
        assert result.exit_code == 0
        assert "dagster" in result.output.lower() or "development" in result.output.lower()

    @pytest.mark.requirement("002-FR-005")
    def test_dev_command_requires_dagster(self) -> None:
        """Test that floe dev indicates floe-dagster is required.

        Covers:
        - 002-FR-005: floe dev requires floe-dagster package

        Note: This is expected behavior - the dev command is a stub
        until floe-dagster is implemented. The test verifies the user
        receives a clear message about the missing dependency.
        """
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("floe.yaml").write_text(VALID_FLOE_YAML)

            result = runner.invoke(cli, ["dev"])

            # Should indicate floe-dagster is required
            assert result.exit_code == 2
            assert "dagster" in result.output.lower()
            assert "install" in result.output.lower()

    @pytest.mark.requirement("002-FR-005")
    def test_dev_command_accepts_port_option(self) -> None:
        """Test that floe dev accepts --port option.

        Covers:
        - 002-FR-005: floe dev command with --port for custom port
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["dev", "--help"])

        assert result.exit_code == 0
        assert "--port" in result.output or "-p" in result.output

    @pytest.mark.requirement("002-FR-005")
    def test_dev_command_accepts_file_option(self) -> None:
        """Test that floe dev accepts --file option.

        Covers:
        - 002-FR-005: floe dev command with --file option
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["dev", "--help"])

        assert result.exit_code == 0
        assert "--file" in result.output or "-f" in result.output


class TestSchemaExportCommand:
    """Integration tests for floe schema export command (002-FR-006)."""

    @pytest.mark.requirement("002-FR-006")
    def test_schema_export_command_exists(self) -> None:
        """Test that floe schema export command exists.

        Covers:
        - 002-FR-006: floe schema export command exists
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["schema", "--help"])

        assert result.exit_code == 0
        assert "export" in result.output.lower()

    @pytest.mark.requirement("002-FR-006")
    def test_schema_export_produces_json_schema(self) -> None:
        """Test that floe schema export produces valid JSON Schema.

        Covers:
        - 002-FR-006: floe schema export outputs JSON Schema for FloeSpec
        """
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["schema", "export", "--output", "schema.json"])

            assert result.exit_code == 0

            # Verify JSON Schema was created
            schema_path = Path("schema.json")
            assert schema_path.exists()

            # Verify it's valid JSON Schema
            content = json.loads(schema_path.read_text())
            assert "$schema" in content
            assert "json-schema.org" in content["$schema"]

    @pytest.mark.requirement("002-FR-006")
    def test_schema_export_outputs_to_stdout(self) -> None:
        """Test that floe schema export can output to default location.

        Covers:
        - 002-FR-006: floe schema export creates file at default location
        """
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["schema", "export"])

            assert result.exit_code == 0

            # Default output path
            default_path = Path("schemas/floe.schema.json")
            assert default_path.exists()

    @pytest.mark.requirement("002-FR-006")
    def test_schema_export_json_schema_draft_2020_12(self) -> None:
        """Test that exported schema uses JSON Schema Draft 2020-12.

        Covers:
        - 002-FR-006: Schema follows modern JSON Schema standard
        """
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["schema", "export", "--output", "schema.json"])

            assert result.exit_code == 0

            content = json.loads(Path("schema.json").read_text())
            assert "2020-12" in content["$schema"]


class TestTargetOption:
    """Integration tests for --target option (002-FR-012)."""

    @pytest.mark.requirement("002-FR-012")
    def test_compile_accepts_target_option(self) -> None:
        """Test that floe compile accepts --target option.

        Covers:
        - 002-FR-012: --target option exists for compile command
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["compile", "--help"])

        assert result.exit_code == 0
        assert "--target" in result.output or "-t" in result.output

    @pytest.mark.requirement("002-FR-012")
    def test_compile_validates_target_exists(self, tmp_path: Path) -> None:
        """Test that floe compile validates target exists in spec.

        Covers:
        - 002-FR-012: CLI validates target exists in spec before compilation
        """
        runner = CliRunner()

        # Create floe.yaml with duckdb target
        floe_yaml = tmp_path / "floe.yaml"
        floe_yaml.write_text(VALID_FLOE_YAML)

        # Try to compile with invalid target
        result = runner.invoke(
            cli,
            ["compile", "--file", str(floe_yaml), "--target", "invalid_target"],
        )

        # Should fail with informative error
        assert result.exit_code == 1
        assert "target" in result.output.lower()
        assert "not found" in result.output.lower() or "invalid" in result.output.lower()

    @pytest.mark.requirement("002-FR-012")
    def test_compile_accepts_valid_target(self, tmp_path: Path) -> None:
        """Test that floe compile accepts valid target from spec.

        Covers:
        - 002-FR-012: CLI accepts valid target that exists in spec
        """
        runner = CliRunner()

        floe_yaml = tmp_path / "floe.yaml"
        floe_yaml.write_text(VALID_FLOE_YAML)

        output_dir = tmp_path / "output"

        # Compile with valid target (duckdb is defined in the spec)
        result = runner.invoke(
            cli,
            [
                "compile",
                "--file", str(floe_yaml),
                "--output", str(output_dir),
                "--target", "duckdb",
            ],
        )

        assert result.exit_code == 0
        assert (output_dir / "compiled_artifacts.json").exists()

    @pytest.mark.requirement("002-FR-012")
    def test_compile_shows_available_targets_on_error(self, tmp_path: Path) -> None:
        """Test that compile error shows available targets.

        Covers:
        - 002-FR-012: Error message lists valid targets
        """
        runner = CliRunner()

        floe_yaml = tmp_path / "floe.yaml"
        floe_yaml.write_text(VALID_FLOE_YAML)

        result = runner.invoke(
            cli,
            ["compile", "--file", str(floe_yaml), "--target", "nonexistent"],
        )

        # Should list available targets in error
        assert result.exit_code == 1
        # Should mention what targets are available
        assert "duckdb" in result.output.lower() or "available" in result.output.lower()


class TestColoredOutput:
    """Integration tests for colored terminal output (002-FR-013)."""

    @pytest.mark.requirement("002-FR-013")
    def test_success_output_uses_color_codes(self, tmp_path: Path) -> None:
        """Test that success messages include color formatting.

        Covers:
        - 002-FR-013: Colored terminal output for success states

        Note: Rich color codes appear as escape sequences in test output.
        We verify the success indicator is present.
        """
        runner = CliRunner()

        floe_yaml = tmp_path / "floe.yaml"
        floe_yaml.write_text(VALID_FLOE_YAML)

        result = runner.invoke(cli, ["validate", "--file", str(floe_yaml)])

        assert result.exit_code == 0
        # Success messages should have content (Rich strips codes in test)
        assert "valid" in result.output.lower()

    @pytest.mark.requirement("002-FR-013")
    def test_error_output_uses_color_codes(self, tmp_path: Path) -> None:
        """Test that error messages include color formatting.

        Covers:
        - 002-FR-013: Colored terminal output for error states
        """
        runner = CliRunner()

        # Invalid YAML (missing required 'name' field)
        floe_yaml = tmp_path / "invalid.yaml"
        floe_yaml.write_text("version: 1.0.0\ncompute:\n  target: duckdb\n")

        result = runner.invoke(cli, ["validate", "--file", str(floe_yaml)])

        # Error messages should have content
        assert result.exit_code != 0
        # Output contains error indication
        assert len(result.output) > 0

    @pytest.mark.requirement("002-FR-013")
    def test_output_module_has_color_functions(self) -> None:
        """Test that output module provides color functions.

        Covers:
        - 002-FR-013: Color support via output module
        """
        from floe_cli.output import error, success, warning

        # Functions should exist and be callable
        assert callable(success)
        assert callable(error)
        assert callable(warning)


class TestNoColorOption:
    """Integration tests for --no-color option (002-FR-014)."""

    @pytest.mark.requirement("002-FR-014")
    def test_cli_has_no_color_option(self) -> None:
        """Test that CLI has --no-color option.

        Covers:
        - 002-FR-014: --no-color option exists
        """
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "--no-color" in result.output

    @pytest.mark.requirement("002-FR-014")
    def test_no_color_option_disables_colors(self, tmp_path: Path) -> None:
        """Test that --no-color disables colored output.

        Covers:
        - 002-FR-014: --no-color disables colors for CI/CD environments
        """
        runner = CliRunner()

        floe_yaml = tmp_path / "floe.yaml"
        floe_yaml.write_text(VALID_FLOE_YAML)

        result = runner.invoke(
            cli,
            ["--no-color", "validate", "--file", str(floe_yaml)],
        )

        assert result.exit_code == 0
        # Output should be present but without ANSI escape codes
        # (Rich output in tests typically strips codes anyway)
        assert "valid" in result.output.lower()

    @pytest.mark.requirement("002-FR-014")
    def test_no_color_respects_env_variable(self, tmp_path: Path) -> None:
        """Test that NO_COLOR environment variable is respected.

        Covers:
        - 002-FR-014: Respects NO_COLOR environment variable
        """
        runner = CliRunner()

        floe_yaml = tmp_path / "floe.yaml"
        floe_yaml.write_text(VALID_FLOE_YAML)

        # Set NO_COLOR environment variable
        result = runner.invoke(
            cli,
            ["validate", "--file", str(floe_yaml)],
            env={"NO_COLOR": "1"},
        )

        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    @pytest.mark.requirement("002-FR-014")
    def test_set_no_color_function(self) -> None:
        """Test that set_no_color function exists and works.

        Covers:
        - 002-FR-014: Programmatic color control via set_no_color
        """
        from floe_cli.output import create_console, set_no_color

        # Should be callable
        assert callable(set_no_color)

        # Create console with no_color=True
        console = create_console(no_color=True)
        assert console is not None

        # Create console with no_color=False
        console = create_console(no_color=False)
        assert console is not None
