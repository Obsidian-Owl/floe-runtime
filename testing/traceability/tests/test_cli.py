"""Tests for testing.traceability.__main__ CLI module.

These tests verify the CLI entry point for running traceability reports.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from textwrap import dedent


class TestCLIEntryPoint:
    """Tests for CLI entry point."""

    def test_module_can_be_run(self) -> None:
        """Verify module can be invoked with python -m."""
        result = subprocess.run(
            [sys.executable, "-m", "testing.traceability", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parents[3],  # Project root
        )

        assert result.returncode == 0
        assert "traceability" in result.stdout.lower() or "usage" in result.stdout.lower()

    def test_help_option(self) -> None:
        """--help shows usage information."""
        result = subprocess.run(
            [sys.executable, "-m", "testing.traceability", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parents[3],
        )

        assert result.returncode == 0
        assert "--feature-id" in result.stdout or "feature" in result.stdout.lower()


class TestCLIArguments:
    """Tests for CLI argument parsing."""

    def test_requires_feature_id(self) -> None:
        """CLI requires --feature-id argument."""
        result = subprocess.run(
            [sys.executable, "-m", "testing.traceability"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parents[3],
        )

        # Should fail or show usage when required args missing
        assert result.returncode != 0 or "error" in result.stderr.lower()


class TestCLIOutput:
    """Tests for CLI output formats."""

    def test_console_format_default(self, tmp_path: Path) -> None:
        """Default output is console format."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("- **FR-001**: Test requirement")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "testing.traceability",
                "--feature-id",
                "006",
                "--feature-name",
                "Integration Testing",
                "--spec-files",
                str(spec_file),
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parents[3],
        )

        assert result.returncode == 0
        assert "006" in result.stdout
        assert "FR-001" in result.stdout

    def test_json_format_option(self, tmp_path: Path) -> None:
        """--format json outputs JSON."""
        import json

        spec_file = tmp_path / "spec.md"
        spec_file.write_text("- **FR-001**: Test requirement")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "testing.traceability",
                "--feature-id",
                "006",
                "--feature-name",
                "Integration Testing",
                "--spec-files",
                str(spec_file),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parents[3],
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["feature_id"] == "006"


class TestCLIExitCodes:
    """Tests for CLI exit codes."""

    def test_exit_zero_when_coverage_met(self, tmp_path: Path) -> None:
        """Exit 0 when no threshold or threshold met."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("- **FR-001**: Test requirement")

        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        test_content = dedent(
            """
            import pytest

            @pytest.mark.requirement("006-FR-001")
            def test_covered():
                pass
        """
        )
        (test_dir / "test_example.py").write_text(test_content)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "testing.traceability",
                "--feature-id",
                "006",
                "--feature-name",
                "Integration Testing",
                "--spec-files",
                str(spec_file),
                "--test-dirs",
                str(test_dir),
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parents[3],
        )

        assert result.returncode == 0

    def test_exit_nonzero_when_threshold_not_met(self, tmp_path: Path) -> None:
        """Exit 1 when coverage below threshold."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("- **FR-001**: Uncovered requirement")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "testing.traceability",
                "--feature-id",
                "006",
                "--feature-name",
                "Integration Testing",
                "--spec-files",
                str(spec_file),
                "--threshold",
                "80",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parents[3],
        )

        assert result.returncode == 1
