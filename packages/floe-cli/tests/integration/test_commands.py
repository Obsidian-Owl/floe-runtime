"""Integration tests for CLI commands.

These tests verify end-to-end behavior of CLI commands with
real file I/O and command execution.

T026: test_validate_command
T027: test_compile_command
T028: test_init_command
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from click.testing import CliRunner
import pytest

from floe_cli.main import cli

if TYPE_CHECKING:
    pass


# Valid floe.yaml content for integration tests
VALID_FLOE_YAML = """\
name: integration-test
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

# Invalid floe.yaml content (missing required field)
INVALID_FLOE_YAML = """\
version: "1.0.0"
compute:
  target: duckdb
"""


class TestValidateCommandIntegration:
    """Integration tests for floe validate command."""

    @pytest.mark.requirement("FR-006")
    def test_validate_with_valid_config(self, tmp_path: Path) -> None:
        """Verify validate command succeeds with valid configuration."""
        runner = CliRunner()

        # Create valid floe.yaml
        floe_yaml = tmp_path / "floe.yaml"
        floe_yaml.write_text(VALID_FLOE_YAML)

        # Run validate
        result = runner.invoke(cli, ["validate", "--file", str(floe_yaml)])

        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    @pytest.mark.requirement("FR-006")
    def test_validate_with_invalid_config(self, tmp_path: Path) -> None:
        """Verify validate command fails with invalid configuration."""
        runner = CliRunner()

        # Create invalid floe.yaml (missing name)
        floe_yaml = tmp_path / "floe.yaml"
        floe_yaml.write_text(INVALID_FLOE_YAML)

        # Run validate
        result = runner.invoke(cli, ["validate", "--file", str(floe_yaml)])

        assert result.exit_code == 1
        # Should mention missing field
        assert "name" in result.output.lower() or "error" in result.output.lower()

    @pytest.mark.requirement("FR-006")
    def test_validate_with_missing_file(self, tmp_path: Path) -> None:
        """Verify validate command fails gracefully when file is missing."""
        runner = CliRunner()

        nonexistent = tmp_path / "nonexistent.yaml"

        result = runner.invoke(cli, ["validate", "--file", str(nonexistent)])

        assert result.exit_code == 2
        assert "not found" in result.output.lower()

    @pytest.mark.requirement("FR-006")
    def test_validate_default_path_without_file(self) -> None:
        """Verify validate command fails when default floe.yaml doesn't exist."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["validate"])

            assert result.exit_code == 2
            assert "not found" in result.output.lower()

    @pytest.mark.requirement("FR-006")
    def test_validate_default_path_with_file(self) -> None:
        """Verify validate command uses default ./floe.yaml path."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create floe.yaml in current directory
            Path("floe.yaml").write_text(VALID_FLOE_YAML)

            result = runner.invoke(cli, ["validate"])

            assert result.exit_code == 0
            assert "valid" in result.output.lower()


class TestCompileCommandIntegration:
    """Integration tests for floe compile command."""

    @pytest.mark.requirement("FR-006")
    def test_compile_produces_artifacts(self, tmp_path: Path) -> None:
        """Verify compile command generates CompiledArtifacts JSON."""
        runner = CliRunner()

        # Create valid floe.yaml
        floe_yaml = tmp_path / "floe.yaml"
        floe_yaml.write_text(VALID_FLOE_YAML)

        output_dir = tmp_path / "output"

        # Run compile
        result = runner.invoke(
            cli, ["compile", "--file", str(floe_yaml), "--output", str(output_dir)]
        )

        assert result.exit_code == 0
        assert "compiled" in result.output.lower()

        # Verify artifacts file was created
        artifacts_path = output_dir / "compiled_artifacts.json"
        assert artifacts_path.exists()

        # Verify artifacts content
        artifacts = json.loads(artifacts_path.read_text())
        assert artifacts["version"] == "1.0.0"
        assert "metadata" in artifacts
        assert "compute" in artifacts
        assert "transforms" in artifacts

    @pytest.mark.requirement("FR-006")
    def test_compile_creates_output_directory(self, tmp_path: Path) -> None:
        """Verify compile command creates output directory if it doesn't exist."""
        runner = CliRunner()

        floe_yaml = tmp_path / "floe.yaml"
        floe_yaml.write_text(VALID_FLOE_YAML)

        # Nested output directory that doesn't exist
        output_dir = tmp_path / "nested" / "output" / "dir"

        result = runner.invoke(
            cli, ["compile", "--file", str(floe_yaml), "--output", str(output_dir)]
        )

        assert result.exit_code == 0
        assert output_dir.exists()
        assert (output_dir / "compiled_artifacts.json").exists()

    @pytest.mark.requirement("FR-006")
    def test_compile_with_invalid_config(self, tmp_path: Path) -> None:
        """Verify compile command fails with invalid configuration."""
        runner = CliRunner()

        floe_yaml = tmp_path / "floe.yaml"
        floe_yaml.write_text(INVALID_FLOE_YAML)

        output_dir = tmp_path / "output"

        result = runner.invoke(
            cli, ["compile", "--file", str(floe_yaml), "--output", str(output_dir)]
        )

        assert result.exit_code == 1

    @pytest.mark.requirement("FR-006")
    def test_compile_with_missing_file(self, tmp_path: Path) -> None:
        """Verify compile command fails when source file is missing."""
        runner = CliRunner()

        nonexistent = tmp_path / "nonexistent.yaml"
        output_dir = tmp_path / "output"

        result = runner.invoke(
            cli, ["compile", "--file", str(nonexistent), "--output", str(output_dir)]
        )

        assert result.exit_code == 2
        assert "not found" in result.output.lower()

    @pytest.mark.requirement("FR-006")
    def test_compile_default_output_directory(self) -> None:
        """Verify compile command uses default .floe/ output directory."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("floe.yaml").write_text(VALID_FLOE_YAML)

            result = runner.invoke(cli, ["compile"])

            assert result.exit_code == 0
            assert Path(".floe/compiled_artifacts.json").exists()


class TestInitCommandIntegration:
    """Integration tests for floe init command."""

    @pytest.mark.requirement("FR-006")
    def test_init_creates_floe_yaml(self) -> None:
        """Verify init command creates floe.yaml file."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init", "--name", "test-project"])

            assert result.exit_code == 0
            assert "created" in result.output.lower()

            # Verify floe.yaml was created
            floe_yaml = Path("floe.yaml")
            assert floe_yaml.exists()

            content = floe_yaml.read_text()
            assert "test-project" in content
            assert "name:" in content

    @pytest.mark.requirement("FR-006")
    def test_init_creates_readme(self) -> None:
        """Verify init command creates README.md file."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init", "--name", "test-project"])

            assert result.exit_code == 0

            # Verify README was created
            readme = Path("README.md")
            assert readme.exists()
            assert "test-project" in readme.read_text()

    @pytest.mark.requirement("FR-006")
    def test_init_with_custom_target(self) -> None:
        """Verify init command accepts custom compute target."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(
                cli, ["init", "--name", "snowflake-project", "--target", "snowflake"]
            )

            assert result.exit_code == 0

            content = Path("floe.yaml").read_text()
            assert "target: snowflake" in content

    @pytest.mark.requirement("FR-006")
    def test_init_refuses_overwrite_without_force(self) -> None:
        """Verify init command refuses to overwrite existing floe.yaml."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create existing floe.yaml
            Path("floe.yaml").write_text("existing: content\n")

            result = runner.invoke(cli, ["init", "--name", "test-project"])

            assert result.exit_code == 1
            assert "already exists" in result.output.lower() or "force" in result.output.lower()

    @pytest.mark.requirement("FR-006")
    def test_init_overwrites_with_force(self) -> None:
        """Verify init command overwrites with --force flag."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create existing floe.yaml
            Path("floe.yaml").write_text("existing: content\n")

            result = runner.invoke(cli, ["init", "--name", "new-project", "--force"])

            assert result.exit_code == 0

            content = Path("floe.yaml").read_text()
            assert "new-project" in content
            assert "existing" not in content

    @pytest.mark.requirement("FR-006")
    def test_init_uses_directory_name_as_default(self) -> None:
        """Verify init command uses current directory name when no name specified."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=None) as temp_dir:
            result = runner.invoke(cli, ["init"])

            assert result.exit_code == 0

            # Project name should be the directory name
            content = Path("floe.yaml").read_text()
            dir_name = Path(temp_dir).name
            assert dir_name in content

    @pytest.mark.requirement("FR-006")
    def test_init_validates_project_name(self) -> None:
        """Verify init command validates project name format."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["init", "--name", "invalid name with spaces!"])

            assert result.exit_code == 1
            assert "invalid" in result.output.lower()


class TestCommandChaining:
    """Integration tests for command chaining workflows."""

    @pytest.mark.requirement("FR-006")
    def test_init_then_validate_workflow(self) -> None:
        """Verify init creates config that passes validation."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Run init
            init_result = runner.invoke(cli, ["init", "--name", "workflow-test"])
            assert init_result.exit_code == 0

            # Run validate on the created config
            validate_result = runner.invoke(cli, ["validate"])
            assert validate_result.exit_code == 0
            assert "valid" in validate_result.output.lower()

    @pytest.mark.requirement("FR-006")
    def test_init_then_compile_workflow(self) -> None:
        """Verify init creates config that can be compiled."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Run init
            init_result = runner.invoke(cli, ["init", "--name", "compile-test"])
            assert init_result.exit_code == 0

            # Run compile on the created config
            compile_result = runner.invoke(cli, ["compile"])
            assert compile_result.exit_code == 0
            assert Path(".floe/compiled_artifacts.json").exists()

    @pytest.mark.requirement("FR-006")
    def test_full_workflow_init_validate_compile(self) -> None:
        """Verify complete init → validate → compile workflow."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Initialize project
            result = runner.invoke(cli, ["init", "--name", "full-workflow"])
            assert result.exit_code == 0

            # Validate configuration
            result = runner.invoke(cli, ["validate"])
            assert result.exit_code == 0

            # Compile artifacts
            result = runner.invoke(cli, ["compile"])
            assert result.exit_code == 0

            # Verify artifacts
            artifacts = json.loads(Path(".floe/compiled_artifacts.json").read_text())
            assert artifacts["metadata"]["source_hash"] is not None
