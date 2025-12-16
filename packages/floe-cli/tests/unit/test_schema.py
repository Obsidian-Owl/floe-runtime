"""Tests for floe schema command.

T026: Unit tests for schema export command
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from floe_cli.commands.schema import schema, export_schema


class TestSchemaGroup:
    """Tests for schema command group."""

    def test_schema_help(self, cli_runner: CliRunner) -> None:
        """Test schema --help shows subcommands."""
        result = cli_runner.invoke(schema, ["--help"])
        assert result.exit_code == 0
        assert "export" in result.output.lower()


class TestSchemaExport:
    """Tests for schema export command."""

    def test_export_creates_file(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test schema export creates JSON file."""
        output_file = tmp_path / "schema.json"
        result = cli_runner.invoke(
            export_schema, ["--output", str(output_file)]
        )
        assert result.exit_code == 0
        assert output_file.exists()

    def test_export_creates_valid_json(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test exported schema is valid JSON."""
        output_file = tmp_path / "schema.json"
        result = cli_runner.invoke(
            export_schema, ["--output", str(output_file)]
        )
        assert result.exit_code == 0

        content = json.loads(output_file.read_text())
        assert isinstance(content, dict)

    def test_export_creates_json_schema(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test exported schema is a valid JSON Schema."""
        output_file = tmp_path / "schema.json"
        result = cli_runner.invoke(
            export_schema, ["--output", str(output_file)]
        )
        assert result.exit_code == 0

        content = json.loads(output_file.read_text())
        # Check JSON Schema fields
        assert "$schema" in content
        assert "json-schema.org" in content["$schema"]
        assert "properties" in content or "type" in content

    def test_export_creates_directory_if_needed(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test export creates nested directories."""
        output_file = tmp_path / "nested" / "dir" / "schema.json"
        result = cli_runner.invoke(
            export_schema, ["--output", str(output_file)]
        )
        assert result.exit_code == 0
        assert output_file.exists()

    def test_export_default_output(self, isolated_runner: CliRunner) -> None:
        """Test export uses default output path."""
        result = isolated_runner.invoke(export_schema)
        assert result.exit_code == 0

        # Default path
        default_path = Path("schemas/floe.schema.json")
        assert default_path.exists()

    def test_export_overwrites_existing(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test export overwrites existing file."""
        output_file = tmp_path / "schema.json"
        output_file.write_text('{"old": "data"}')

        result = cli_runner.invoke(
            export_schema, ["--output", str(output_file)]
        )
        assert result.exit_code == 0

        content = json.loads(output_file.read_text())
        assert "old" not in content
        assert "$schema" in content


class TestSchemaContent:
    """Tests for schema content quality."""

    def test_schema_has_id(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test schema has $id field."""
        output_file = tmp_path / "schema.json"
        result = cli_runner.invoke(
            export_schema, ["--output", str(output_file)]
        )
        assert result.exit_code == 0

        content = json.loads(output_file.read_text())
        assert "$id" in content

    def test_schema_has_title(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test schema has title or describes FloeSpec."""
        output_file = tmp_path / "schema.json"
        result = cli_runner.invoke(
            export_schema, ["--output", str(output_file)]
        )
        assert result.exit_code == 0

        content = json.loads(output_file.read_text())
        # Should have title or $defs containing FloeSpec
        has_title = "title" in content
        has_floe_ref = "FloeSpec" in str(content)
        assert has_title or has_floe_ref

    def test_schema_has_required_fields(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test schema defines required fields."""
        output_file = tmp_path / "schema.json"
        result = cli_runner.invoke(
            export_schema, ["--output", str(output_file)]
        )
        assert result.exit_code == 0

        content = json.loads(output_file.read_text())
        # Should have required array or properties
        has_required = "required" in content
        has_properties = "properties" in content
        has_defs = "$defs" in content
        assert has_required or has_properties or has_defs

    def test_schema_formatted_nicely(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test schema JSON is formatted with indentation."""
        output_file = tmp_path / "schema.json"
        result = cli_runner.invoke(
            export_schema, ["--output", str(output_file)]
        )
        assert result.exit_code == 0

        content = output_file.read_text()
        # Should be formatted (has newlines and indentation)
        assert "\n" in content
        assert "  " in content
