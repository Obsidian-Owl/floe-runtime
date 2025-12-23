"""Tests for floe compile command.

T020: Unit tests for compile command
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from floe_cli.commands.compile import compile_cmd


class TestCompileCommand:
    """Tests for compile command."""

    def test_compile_valid_file(
        self, cli_runner: CliRunner, valid_floe_yaml: Path, tmp_path: Path
    ) -> None:
        """Test compilation of a valid floe.yaml."""
        output_dir = tmp_path / ".floe"
        result = cli_runner.invoke(
            compile_cmd,
            ["--file", str(valid_floe_yaml), "--output", str(output_dir)],
        )
        assert result.exit_code == 0
        assert "compiled" in result.output.lower()

        # Verify output file was created
        artifacts_file = output_dir / "compiled_artifacts.json"
        assert artifacts_file.exists()

        # Verify JSON is valid
        artifacts = json.loads(artifacts_file.read_text())
        assert "version" in artifacts
        assert "metadata" in artifacts

    def test_compile_creates_output_directory(
        self, cli_runner: CliRunner, valid_floe_yaml: Path, tmp_path: Path
    ) -> None:
        """Test that compile creates output directory if needed."""
        output_dir = tmp_path / "nested" / "output" / ".floe"
        result = cli_runner.invoke(
            compile_cmd,
            ["--file", str(valid_floe_yaml), "--output", str(output_dir)],
        )
        assert result.exit_code == 0
        assert output_dir.exists()

    def test_compile_missing_file(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test compilation when file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.yaml"
        result = cli_runner.invoke(
            compile_cmd,
            ["--file", str(nonexistent)],
        )
        assert result.exit_code == 2
        assert "not found" in result.output.lower()

    def test_compile_invalid_file(
        self, cli_runner: CliRunner, invalid_floe_yaml: Path, tmp_path: Path
    ) -> None:
        """Test compilation of invalid floe.yaml fails."""
        output_dir = tmp_path / ".floe"
        result = cli_runner.invoke(
            compile_cmd,
            ["--file", str(invalid_floe_yaml), "--output", str(output_dir)],
        )
        assert result.exit_code == 1

    def test_compile_default_output(self, isolated_runner: CliRunner, fixtures_dir: Path) -> None:
        """Test compilation uses default .floe/ output."""
        # Copy valid yaml to isolated dir (Two-Tier Architecture)
        Path("floe.yaml").write_text((fixtures_dir / "valid_floe.yaml").read_text())

        # Create platform.yaml for Two-Tier Architecture
        platform_dir = Path("platform") / "local"
        platform_dir.mkdir(parents=True, exist_ok=True)
        (platform_dir / "platform.yaml").write_text((fixtures_dir / "platform.yaml").read_text())

        result = isolated_runner.invoke(compile_cmd)
        assert result.exit_code == 0

        # Default output directory
        assert Path(".floe").exists()
        assert Path(".floe/compiled_artifacts.json").exists()


class TestCompileTargetOption:
    """Tests for --target option.

    In Two-Tier Architecture, --target must match the profile name (e.g., "default"),
    not the compute type (e.g., "duckdb"). The profile name is what's in floe.yaml.
    """

    def test_compile_with_valid_target(
        self, cli_runner: CliRunner, valid_floe_yaml: Path, tmp_path: Path
    ) -> None:
        """Test compilation with valid --target option."""
        output_dir = tmp_path / ".floe"
        # Target must match the compute profile name in floe.yaml ("default")
        result = cli_runner.invoke(
            compile_cmd,
            [
                "--file",
                str(valid_floe_yaml),
                "--output",
                str(output_dir),
                "--target",
                "default",  # Profile name, not compute type
            ],
        )
        assert result.exit_code == 0

    def test_compile_with_invalid_target(
        self, cli_runner: CliRunner, valid_floe_yaml: Path, tmp_path: Path
    ) -> None:
        """Test compilation fails with invalid --target."""
        output_dir = tmp_path / ".floe"
        result = cli_runner.invoke(
            compile_cmd,
            [
                "--file",
                str(valid_floe_yaml),
                "--output",
                str(output_dir),
                "--target",
                "nonexistent_target",
            ],
        )
        assert result.exit_code == 1
        assert "target" in result.output.lower()


class TestCompileArtifacts:
    """Tests for compiled artifacts structure."""

    def test_artifacts_contain_required_fields(
        self, cli_runner: CliRunner, valid_floe_yaml: Path, tmp_path: Path
    ) -> None:
        """Test artifacts contain all required fields."""
        output_dir = tmp_path / ".floe"
        result = cli_runner.invoke(
            compile_cmd,
            ["--file", str(valid_floe_yaml), "--output", str(output_dir)],
        )
        assert result.exit_code == 0

        artifacts_file = output_dir / "compiled_artifacts.json"
        artifacts = json.loads(artifacts_file.read_text())

        # Check required top-level fields
        assert "version" in artifacts
        assert "metadata" in artifacts
        assert "compute" in artifacts

    def test_artifacts_json_is_formatted(
        self, cli_runner: CliRunner, valid_floe_yaml: Path, tmp_path: Path
    ) -> None:
        """Test artifacts JSON is indented for readability."""
        output_dir = tmp_path / ".floe"
        result = cli_runner.invoke(
            compile_cmd,
            ["--file", str(valid_floe_yaml), "--output", str(output_dir)],
        )
        assert result.exit_code == 0

        artifacts_content = (output_dir / "compiled_artifacts.json").read_text()
        # Check it's formatted (has newlines and indentation)
        assert "\n" in artifacts_content
        assert "  " in artifacts_content  # Indentation


class TestCompileEdgeCases:
    """Tests for edge cases in compile command."""

    def test_compile_overwrites_existing_output(
        self, cli_runner: CliRunner, valid_floe_yaml: Path, tmp_path: Path
    ) -> None:
        """Test that compile overwrites existing artifacts."""
        output_dir = tmp_path / ".floe"
        output_dir.mkdir(parents=True)
        artifacts_file = output_dir / "compiled_artifacts.json"
        artifacts_file.write_text('{"old": "data"}')

        result = cli_runner.invoke(
            compile_cmd,
            ["--file", str(valid_floe_yaml), "--output", str(output_dir)],
        )
        assert result.exit_code == 0

        # Should have new content
        new_content = json.loads(artifacts_file.read_text())
        assert "old" not in new_content
        assert "version" in new_content

    def test_compile_empty_transforms(
        self, cli_runner: CliRunner, tmp_path: Path, fixtures_dir: Path
    ) -> None:
        """Test compilation with no transforms.

        Two-Tier Architecture requires platform.yaml alongside floe.yaml.
        """
        config_file = tmp_path / "minimal.yaml"
        config_file.write_text(
            """
name: minimal
version: "1.0.0"
# Two-Tier: use profile references
storage: default
catalog: default
compute: default
"""
        )

        # Create platform.yaml for Two-Tier Architecture
        platform_dir = tmp_path / "platform" / "local"
        platform_dir.mkdir(parents=True, exist_ok=True)
        (platform_dir / "platform.yaml").write_text((fixtures_dir / "platform.yaml").read_text())

        output_dir = tmp_path / ".floe"
        result = cli_runner.invoke(
            compile_cmd,
            ["--file", str(config_file), "--output", str(output_dir)],
        )
        assert result.exit_code == 0
