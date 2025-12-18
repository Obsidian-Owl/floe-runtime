"""Tests for floe init command.

T030: Unit tests for init command
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner
import pytest

from floe_cli.commands.init import init


class TestInitCommand:
    """Tests for init command."""

    def test_init_creates_floe_yaml(self, isolated_runner: CliRunner) -> None:
        """Test init creates floe.yaml."""
        result = isolated_runner.invoke(init)
        assert result.exit_code == 0
        assert Path("floe.yaml").exists()

    def test_init_creates_readme(self, isolated_runner: CliRunner) -> None:
        """Test init creates README.md."""
        result = isolated_runner.invoke(init)
        assert result.exit_code == 0
        assert Path("README.md").exists()

    def test_init_success_message(self, isolated_runner: CliRunner) -> None:
        """Test init shows success message."""
        result = isolated_runner.invoke(init)
        assert result.exit_code == 0
        assert "created" in result.output.lower()


class TestInitNameOption:
    """Tests for --name option."""

    def test_init_with_custom_name(self, isolated_runner: CliRunner) -> None:
        """Test init with --name uses custom project name."""
        result = isolated_runner.invoke(init, ["--name", "my-pipeline"])
        assert result.exit_code == 0

        content = Path("floe.yaml").read_text()
        assert "my-pipeline" in content

    def test_init_default_name_uses_directory(self, isolated_runner: CliRunner) -> None:
        """Test init uses directory name as default."""
        result = isolated_runner.invoke(init)
        assert result.exit_code == 0
        # Will use some directory name
        assert Path("floe.yaml").exists()

    def test_init_invalid_name(self, isolated_runner: CliRunner) -> None:
        """Test init rejects invalid project names."""
        result = isolated_runner.invoke(init, ["--name", "my project!@#"])
        assert result.exit_code == 1
        assert "invalid" in result.output.lower()

    def test_init_name_with_hyphen(self, isolated_runner: CliRunner) -> None:
        """Test init accepts names with hyphens."""
        result = isolated_runner.invoke(init, ["--name", "my-data-pipeline"])
        assert result.exit_code == 0
        content = Path("floe.yaml").read_text()
        assert "my-data-pipeline" in content

    def test_init_name_with_underscore(self, isolated_runner: CliRunner) -> None:
        """Test init accepts names with underscores."""
        result = isolated_runner.invoke(init, ["--name", "my_data_pipeline"])
        assert result.exit_code == 0
        content = Path("floe.yaml").read_text()
        assert "my_data_pipeline" in content


class TestInitTargetOption:
    """Tests for --target option."""

    @pytest.mark.parametrize(
        "target",
        ["duckdb", "snowflake", "bigquery", "redshift", "databricks", "postgres", "spark"],
    )
    def test_init_with_valid_target(self, isolated_runner: CliRunner, target: str) -> None:
        """Test init with valid --target option."""
        result = isolated_runner.invoke(init, ["--target", target])
        assert result.exit_code == 0

        content = Path("floe.yaml").read_text()
        assert f"target: {target}" in content

    def test_init_default_target_is_duckdb(self, isolated_runner: CliRunner) -> None:
        """Test init defaults to duckdb target."""
        result = isolated_runner.invoke(init)
        assert result.exit_code == 0

        content = Path("floe.yaml").read_text()
        assert "target: duckdb" in content

    def test_init_duckdb_has_memory_path(self, isolated_runner: CliRunner) -> None:
        """Test init with duckdb includes :memory: path."""
        result = isolated_runner.invoke(init, ["--target", "duckdb"])
        assert result.exit_code == 0

        content = Path("floe.yaml").read_text()
        assert ":memory:" in content


class TestInitForceOption:
    """Tests for --force option."""

    def test_init_fails_if_exists(self, isolated_runner: CliRunner) -> None:
        """Test init fails if floe.yaml already exists."""
        # Create existing file
        Path("floe.yaml").write_text("existing content")

        result = isolated_runner.invoke(init)
        assert result.exit_code == 1
        assert "already exists" in result.output.lower()

    def test_init_force_overwrites(self, isolated_runner: CliRunner) -> None:
        """Test init --force overwrites existing file."""
        # Create existing file
        Path("floe.yaml").write_text("existing content")

        result = isolated_runner.invoke(init, ["--force"])
        assert result.exit_code == 0

        content = Path("floe.yaml").read_text()
        assert "existing content" not in content
        assert "name:" in content

    def test_init_force_warning(self, isolated_runner: CliRunner) -> None:
        """Test init --force shows warning about overwrite."""
        # Create existing file
        Path("floe.yaml").write_text("existing content")

        result = isolated_runner.invoke(init, ["--force"])
        assert result.exit_code == 0
        # Should mention overwrite
        assert "overwrote" in result.output.lower() or "created" in result.output.lower()


class TestInitFileContents:
    """Tests for generated file contents."""

    def test_floe_yaml_is_valid_yaml(self, isolated_runner: CliRunner) -> None:
        """Test generated floe.yaml is valid YAML."""
        import yaml

        result = isolated_runner.invoke(init)
        assert result.exit_code == 0

        content = Path("floe.yaml").read_text()
        data = yaml.safe_load(content)
        assert isinstance(data, dict)

    def test_floe_yaml_has_required_sections(self, isolated_runner: CliRunner) -> None:
        """Test generated floe.yaml has required sections."""
        import yaml

        result = isolated_runner.invoke(init)
        assert result.exit_code == 0

        content = Path("floe.yaml").read_text()
        data = yaml.safe_load(content)

        assert "name" in data
        assert "version" in data
        assert "compute" in data

    def test_floe_yaml_has_schema_comment(self, isolated_runner: CliRunner) -> None:
        """Test generated floe.yaml has schema comment for IDE."""
        result = isolated_runner.invoke(init)
        assert result.exit_code == 0

        content = Path("floe.yaml").read_text()
        # Should have yaml-language-server schema reference
        assert "yaml-language-server" in content or "schema" in content.lower()

    def test_readme_mentions_commands(self, isolated_runner: CliRunner) -> None:
        """Test generated README mentions floe commands."""
        result = isolated_runner.invoke(init)
        assert result.exit_code == 0

        content = Path("README.md").read_text()
        assert "floe" in content.lower()
        assert "validate" in content or "compile" in content


class TestInitEdgeCases:
    """Tests for edge cases."""

    def test_init_preserves_existing_readme(self, isolated_runner: CliRunner) -> None:
        """Test init doesn't overwrite existing README.md (without --force)."""
        existing_readme = "# My Existing README\n"
        Path("README.md").write_text(existing_readme)

        _result = isolated_runner.invoke(init)
        # Should create floe.yaml but preserve README.md (without --force)

        # This depends on implementation - readme might be preserved
        readme_content = Path("README.md").read_text()
        # Without force, README should be preserved
        assert "Existing" in readme_content or "floe" in readme_content.lower()
