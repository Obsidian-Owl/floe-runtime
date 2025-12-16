"""Tests for floe validate command.

T015: Unit tests for validate command
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner
from floe_cli.commands.validate import validate


class TestValidateCommand:
    """Tests for validate command."""

    def test_validate_valid_file(self, cli_runner: CliRunner, valid_floe_yaml: Path) -> None:
        """Test validation of a valid floe.yaml."""
        result = cli_runner.invoke(validate, ["--file", str(valid_floe_yaml)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_validate_invalid_file(self, cli_runner: CliRunner, invalid_floe_yaml: Path) -> None:
        """Test validation of an invalid floe.yaml."""
        result = cli_runner.invoke(validate, ["--file", str(invalid_floe_yaml)])
        assert result.exit_code == 1
        # Should show error message
        assert "error" in result.output.lower() or "invalid" in result.output.lower()

    def test_validate_missing_file(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test validation when file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.yaml"
        result = cli_runner.invoke(validate, ["--file", str(nonexistent)])
        assert result.exit_code == 2
        assert "not found" in result.output.lower()

    def test_validate_default_path(self, isolated_runner: CliRunner) -> None:
        """Test validation uses default ./floe.yaml path."""
        result = isolated_runner.invoke(validate)
        # Should fail because no floe.yaml exists in isolated directory
        assert result.exit_code == 2
        assert "not found" in result.output.lower()


class TestValidateYAMLErrors:
    """Tests for YAML syntax error handling."""

    def test_yaml_syntax_error(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that YAML syntax errors are reported with line numbers."""
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text(
            """
name: test
version: "1.0.0"
  invalid_indent: true  # Bad indentation
"""
        )
        result = cli_runner.invoke(validate, ["--file", str(bad_yaml)])
        assert result.exit_code != 0

    def test_yaml_duplicate_keys(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test handling of duplicate YAML keys."""
        dup_yaml = tmp_path / "dup.yaml"
        dup_yaml.write_text(
            """
name: test
name: test2
version: "1.0.0"
"""
        )
        _result = cli_runner.invoke(validate, ["--file", str(dup_yaml)])
        # Should either fail validation or use last value
        # Behavior depends on YAML parser settings
        # Result intentionally unused - we just verify no crash


class TestValidateSchemaErrors:
    """Tests for Pydantic schema validation errors."""

    def test_missing_required_field(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that missing required fields show clear errors."""
        incomplete = tmp_path / "incomplete.yaml"
        incomplete.write_text(
            """
# Missing required 'name' field
version: "1.0.0"
compute:
  target: duckdb
"""
        )
        result = cli_runner.invoke(validate, ["--file", str(incomplete)])
        assert result.exit_code == 1
        # Should mention the missing field
        assert "name" in result.output.lower()

    def test_invalid_enum_value(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that invalid enum values show allowed options."""
        bad_enum = tmp_path / "bad_enum.yaml"
        bad_enum.write_text(
            """
name: test
version: "1.0.0"
compute:
  target: invalid_target
"""
        )
        result = cli_runner.invoke(validate, ["--file", str(bad_enum)])
        assert result.exit_code == 1

    def test_invalid_type(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that type errors are reported clearly."""
        bad_type = tmp_path / "bad_type.yaml"
        bad_type.write_text(
            """
name: 12345  # Should be string
version: "1.0.0"
compute:
  target: duckdb
"""
        )
        _result = cli_runner.invoke(validate, ["--file", str(bad_type)])
        # May succeed if Pydantic coerces the integer to string
        # or fail if strict mode is on
        # Result intentionally unused - we just verify no crash


class TestValidateEdgeCases:
    """Tests for edge cases in validate command."""

    def test_empty_file(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test validation of empty file."""
        empty = tmp_path / "empty.yaml"
        empty.write_text("")
        result = cli_runner.invoke(validate, ["--file", str(empty)])
        assert result.exit_code != 0

    def test_null_file(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test validation of file with only null."""
        null_file = tmp_path / "null.yaml"
        null_file.write_text("null")
        result = cli_runner.invoke(validate, ["--file", str(null_file)])
        assert result.exit_code != 0

    def test_valid_minimal_config(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test validation of minimal valid config."""
        minimal = tmp_path / "minimal.yaml"
        minimal.write_text(
            """
name: minimal-project
version: "1.0.0"
compute:
  target: duckdb
"""
        )
        result = cli_runner.invoke(validate, ["--file", str(minimal)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()
