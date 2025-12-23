"""Unit tests for floe platform command.

T058-T059: Tests for platform CLI commands
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner
import pytest

from floe_cli.commands.platform import list_profiles, platform, validate_platform

# Patch path for PlatformResolver - it's imported inside the functions from floe_core.compiler
PLATFORM_RESOLVER_PATCH = "floe_core.compiler.PlatformResolver"


@pytest.fixture
def runner() -> CliRunner:
    """Create Click CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_platform_spec() -> MagicMock:
    """Create mock PlatformSpec with profiles."""
    spec = MagicMock()

    # Mock storage profiles
    storage_profile = MagicMock()
    storage_profile.type.value = "s3"
    spec.storage = {"default": storage_profile}

    # Mock catalog profiles
    catalog_profile = MagicMock()
    catalog_profile.uri = "http://polaris:8181/api/catalog"
    spec.catalogs = {"default": catalog_profile}

    # Mock compute profiles
    compute_profile = MagicMock()
    compute_profile.type.value = "duckdb"
    spec.compute = {"default": compute_profile}

    return spec


class TestPlatformGroup:
    """Tests for platform command group."""

    def test_platform_group_help(self, runner: CliRunner) -> None:
        """Platform group shows help."""
        result = runner.invoke(platform, ["--help"])
        assert result.exit_code == 0
        assert "Manage platform configuration" in result.output
        assert "list-profiles" in result.output
        assert "validate" in result.output


class TestListProfiles:
    """Tests for list-profiles command."""

    @patch(PLATFORM_RESOLVER_PATCH)
    def test_list_profiles_success(
        self, mock_resolver_cls: MagicMock, runner: CliRunner, mock_platform_spec: MagicMock
    ) -> None:
        """list-profiles shows available profiles."""
        mock_resolver_cls.load_default.return_value = mock_platform_spec

        result = runner.invoke(list_profiles)

        assert result.exit_code == 0
        assert "Storage:" in result.output
        assert "default" in result.output
        assert "s3" in result.output
        assert "Catalogs:" in result.output
        assert "polaris:8181" in result.output
        assert "Compute:" in result.output
        assert "duckdb" in result.output

    @patch(PLATFORM_RESOLVER_PATCH)
    def test_list_profiles_json_output(
        self, mock_resolver_cls: MagicMock, runner: CliRunner, mock_platform_spec: MagicMock
    ) -> None:
        """list-profiles --json outputs JSON format."""
        mock_resolver_cls.load_default.return_value = mock_platform_spec

        result = runner.invoke(list_profiles, ["--json"])

        assert result.exit_code == 0
        # Check JSON structure - extract JSON before success message (contains checkmark)
        import json

        # Split on newline before success message, take first JSON block
        lines = result.output.strip().split("\n")
        # Find where JSON ends (closing brace)
        json_end = next(i for i, line in enumerate(lines) if line.strip() == "}")
        json_text = "\n".join(lines[: json_end + 1])
        data = json.loads(json_text)
        assert "storage" in data
        assert "catalogs" in data
        assert "compute" in data
        assert "default" in data["storage"]

    @patch(PLATFORM_RESOLVER_PATCH)
    def test_list_profiles_from_file(
        self, mock_resolver_cls: MagicMock, runner: CliRunner, mock_platform_spec: MagicMock
    ) -> None:
        """list-profiles with --platform-file loads from specified file."""
        mock_resolver_cls.load_from_file.return_value = mock_platform_spec

        with runner.isolated_filesystem():
            Path("platform.yaml").write_text("version: '1.0.0'")
            result = runner.invoke(list_profiles, ["--platform-file", "platform.yaml"])

        assert result.exit_code == 0
        mock_resolver_cls.load_from_file.assert_called_once()

    @patch(PLATFORM_RESOLVER_PATCH)
    def test_list_profiles_no_config_found(
        self, mock_resolver_cls: MagicMock, runner: CliRunner
    ) -> None:
        """list-profiles shows error when no config found."""
        mock_resolver_cls.load_default.side_effect = FileNotFoundError("Not found")

        result = runner.invoke(list_profiles)

        assert result.exit_code == 2
        assert "No platform configuration found" in result.output

    @patch(PLATFORM_RESOLVER_PATCH)
    def test_list_profiles_empty_profiles(
        self, mock_resolver_cls: MagicMock, runner: CliRunner
    ) -> None:
        """list-profiles shows (none) for empty profile types."""
        spec = MagicMock()
        spec.storage = {}
        spec.catalogs = {}
        spec.compute = {}
        mock_resolver_cls.load_default.return_value = spec

        result = runner.invoke(list_profiles)

        assert result.exit_code == 0
        assert "(none)" in result.output


class TestValidatePlatform:
    """Tests for validate command."""

    @patch(PLATFORM_RESOLVER_PATCH)
    def test_validate_success(
        self, mock_resolver_cls: MagicMock, runner: CliRunner, mock_platform_spec: MagicMock
    ) -> None:
        """validate shows success message."""
        mock_resolver_cls.load_default.return_value = mock_platform_spec

        result = runner.invoke(validate_platform)

        assert result.exit_code == 0
        assert "Platform configuration is valid" in result.output
        assert "Storage profiles: 1" in result.output
        assert "Catalog profiles: 1" in result.output
        assert "Compute profiles: 1" in result.output

    @patch(PLATFORM_RESOLVER_PATCH)
    def test_validate_from_file(
        self, mock_resolver_cls: MagicMock, runner: CliRunner, mock_platform_spec: MagicMock
    ) -> None:
        """validate with --platform-file loads from specified file."""
        mock_resolver_cls.load_from_file.return_value = mock_platform_spec

        with runner.isolated_filesystem():
            Path("custom.yaml").write_text("version: '1.0.0'")
            result = runner.invoke(validate_platform, ["--platform-file", "custom.yaml"])

        assert result.exit_code == 0
        assert "Validated: custom.yaml" in result.output

    @patch(PLATFORM_RESOLVER_PATCH)
    def test_validate_no_config_found(
        self, mock_resolver_cls: MagicMock, runner: CliRunner
    ) -> None:
        """validate shows error when no config found."""
        mock_resolver_cls.load_default.side_effect = FileNotFoundError("Not found")

        result = runner.invoke(validate_platform)

        assert result.exit_code == 2
        assert "No platform configuration found" in result.output

    @patch(PLATFORM_RESOLVER_PATCH)
    def test_validate_invalid_config(self, mock_resolver_cls: MagicMock, runner: CliRunner) -> None:
        """validate shows error for invalid config."""
        mock_resolver_cls.load_default.side_effect = ValueError("Invalid field")

        result = runner.invoke(validate_platform)

        assert result.exit_code == 1
        assert "Validation failed" in result.output
