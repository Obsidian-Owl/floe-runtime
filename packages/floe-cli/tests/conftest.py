"""Shared test fixtures for floe-cli tests.

Provides CliRunner fixtures and temporary directory helpers
for testing CLI commands.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING

from click.testing import CliRunner
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

# File name constants
FLOE_YAML_FILENAME = "floe.yaml"
PLATFORM_YAML_FILENAME = "platform.yaml"


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click test runner.

    Returns:
        CliRunner instance for testing CLI commands.
    """
    return CliRunner()


@pytest.fixture
def isolated_runner(cli_runner: CliRunner) -> Generator[CliRunner, None, None]:
    """Create a Click test runner with an isolated filesystem.

    This fixture creates a temporary directory and changes to it
    for the duration of the test.

    Yields:
        CliRunner instance with isolated filesystem.
    """
    with cli_runner.isolated_filesystem():
        yield cli_runner


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory.

    Returns:
        Path to fixtures directory.
    """
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def valid_floe_yaml(fixtures_dir: Path, tmp_path: Path) -> Path:
    """Return the path to a valid floe.yaml fixture with platform.yaml.

    Two-Tier Architecture requires both floe.yaml and platform.yaml.
    This fixture copies both to tmp_path to ensure platform resolution works.

    Returns:
        Path to valid_floe.yaml in tmp_path with platform.yaml alongside it.
    """
    # Copy floe.yaml
    floe_src = fixtures_dir / "valid_floe.yaml"
    floe_dst = tmp_path / FLOE_YAML_FILENAME
    floe_dst.write_text(floe_src.read_text())

    # Copy platform.yaml (required for Two-Tier)
    platform_src = fixtures_dir / PLATFORM_YAML_FILENAME
    if platform_src.exists():
        # Create platform/local directory for PlatformResolver
        platform_dir = tmp_path / "platform" / "local"
        platform_dir.mkdir(parents=True, exist_ok=True)
        (platform_dir / PLATFORM_YAML_FILENAME).write_text(platform_src.read_text())

    return floe_dst


@pytest.fixture
def invalid_floe_yaml(fixtures_dir: Path) -> Path:
    """Return the path to an invalid floe.yaml fixture.

    Returns:
        Path to invalid_floe.yaml test file.
    """
    return fixtures_dir / "invalid_floe.yaml"


@pytest.fixture
def valid_platform_yaml(fixtures_dir: Path) -> Path:
    """Return the path to a valid platform.yaml fixture.

    Returns:
        Path to platform.yaml test file.
    """
    return fixtures_dir / "platform.yaml"


@pytest.fixture
def temp_floe_yaml(isolated_runner: CliRunner, valid_floe_yaml: Path) -> Path:
    """Create a temporary floe.yaml in the isolated filesystem.

    Args:
        isolated_runner: CliRunner with isolated filesystem.
        valid_floe_yaml: Path to valid fixture.

    Returns:
        Path to the temporary floe.yaml.
    """
    content = valid_floe_yaml.read_text()
    temp_path = Path(FLOE_YAML_FILENAME)
    temp_path.write_text(content)
    return temp_path


@pytest.fixture
def create_floe_yaml(isolated_runner: CliRunner) -> Callable[[str], Path]:
    """Factory fixture to create floe.yaml files with custom content.

    Args:
        isolated_runner: CliRunner with isolated filesystem.

    Returns:
        Function that creates floe.yaml with given content.
    """

    def _create(content: str, filename: str = FLOE_YAML_FILENAME) -> Path:
        path = Path(filename)
        path.write_text(content)
        return path

    return _create
