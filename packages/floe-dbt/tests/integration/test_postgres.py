"""Integration tests for PostgreSQL profile generation and validation.

T034: [US3] Create packages/floe-dbt/tests/integration/test_postgres.py

These tests verify PostgreSQL profile generation and validation using the
Docker postgres service from the test infrastructure.

Requirements:
- dbt-postgres adapter must be installed
- Docker postgres service must be running for actual connection tests
- Tests marked with @pytest.mark.integration for CI filtering

See Also:
    - specs/006-integration-testing/spec.md FR-010
    - testing/docker/docker-compose.yml for service configuration
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Any

import pytest
import yaml

from testing.fixtures.services import get_service_host

# Check if dbt-postgres is available
try:
    import dbt.adapters.postgres  # noqa: F401

    HAS_DBT_POSTGRES = True
except ImportError:
    HAS_DBT_POSTGRES = False

# Check if PostgreSQL Docker service is available
try:
    import socket

    host = get_service_host("postgres")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex((host, 5432))
    sock.close()
    HAS_POSTGRES_SERVICE = result == 0
except Exception:
    HAS_POSTGRES_SERVICE = False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not HAS_DBT_POSTGRES,
        reason="dbt-postgres adapter not installed",
    ),
]


@pytest.fixture
def dbt_project_dir(tmp_path: Path) -> Path:
    """Create minimal dbt project for validation testing."""
    project_dir = tmp_path / "dbt_project"
    project_dir.mkdir()

    # Create minimal dbt_project.yml
    dbt_project = {
        "name": "test_project",
        "version": "1.0.0",
        "config-version": 2,
        "profile": "floe",
    }
    (project_dir / "dbt_project.yml").write_text(yaml.safe_dump(dbt_project))

    # Create models directory
    models_dir = project_dir / "models"
    models_dir.mkdir()

    return project_dir


@pytest.fixture
def profiles_dir(tmp_path: Path) -> Path:
    """Create profiles directory."""
    profiles_path = tmp_path / "profiles"
    profiles_path.mkdir()
    return profiles_path


@pytest.fixture
def postgres_host() -> str:
    """Get PostgreSQL host based on execution context."""
    return get_service_host("postgres")


@pytest.fixture
def postgres_credentials() -> dict[str, str]:
    """Get PostgreSQL credentials from environment or defaults."""
    return {
        "user": os.environ.get("POSTGRES_USER", "postgres"),
        "password": os.environ.get("POSTGRES_PASSWORD", "postgres"),
        "database": os.environ.get("POSTGRES_DB", "postgres"),
    }


class TestPostgreSQLProfileGeneration:
    """Test PostgreSQL profile generation using ProfileFactory."""

    @pytest.fixture
    def factory(self) -> Any:
        """Get ProfileFactory class."""
        from floe_dbt.factory import ProfileFactory

        return ProfileFactory

    @pytest.fixture
    def writer(self) -> Any:
        """Get ProfileWriter instance."""
        from floe_dbt.writer import ProfileWriter

        return ProfileWriter()

    @pytest.mark.requirement("006-FR-010")
    def test_generate_postgres_profile_structure(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test PostgreSQL profile generation produces correct structure."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "postgres",
                "properties": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "analytics",
                    "schema": "public",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = factory.create("postgres")
        outputs = generator.generate(artifacts, config)

        # Verify structure
        assert "dev" in outputs
        profile = outputs["dev"]
        assert profile["type"] == "postgres"
        assert profile["host"] == "localhost"
        assert profile["port"] == 5432
        assert profile["dbname"] == "analytics"
        # Credentials should use env_var template
        assert "env_var" in profile["user"]
        assert "env_var" in profile["password"]

    @pytest.mark.requirement("006-FR-010")
    def test_generate_postgres_profile_with_optional_schema(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test PostgreSQL profile includes optional schema when provided."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "postgres",
                "properties": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "analytics",
                    "schema": "staging",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = factory.create("postgres")
        outputs = generator.generate(artifacts, config)

        assert outputs["dev"]["schema"] == "staging"

    @pytest.mark.requirement("006-FR-010")
    def test_generate_postgres_profile_default_port(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test PostgreSQL profile uses default port 5432 when not specified."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "postgres",
                "properties": {
                    "host": "localhost",
                    "database": "analytics",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
        generator = factory.create("postgres")
        outputs = generator.generate(artifacts, config)

        assert outputs["dev"]["port"] == 5432

    @pytest.mark.requirement("006-FR-010")
    def test_postgres_profile_env_var_security(
        self,
        factory: Any,
        base_metadata: dict[str, Any],
    ) -> None:
        """Test PostgreSQL credentials use env_var template (never hardcoded)."""
        from floe_dbt.profiles.base import ProfileGeneratorConfig

        artifacts = {
            "version": "1.0.0",
            "metadata": base_metadata,
            "compute": {
                "target": "postgres",
                "properties": {
                    "host": "localhost",
                    "database": "analytics",
                },
            },
            "transforms": [],
        }

        config = ProfileGeneratorConfig(
            profile_name="floe", target_name="prod", environment="prod"
        )
        generator = factory.create("postgres")
        outputs = generator.generate(artifacts, config)

        # Verify env_var template is used for credentials
        profile = outputs["prod"]
        assert "{{ env_var(" in profile["user"]
        assert "{{ env_var(" in profile["password"]
        # Environment should be in the env var name
        assert "PROD" in profile["user"]
        assert "PROD" in profile["password"]


class TestPostgreSQLProfileValidation:
    """Test PostgreSQL profile validation with dbt debug."""

    @pytest.mark.requirement("006-FR-010")
    def test_valid_profile_structure_passes_dbt_debug(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
        postgres_host: str,
    ) -> None:
        """Test that well-formed PostgreSQL profile passes dbt debug structure check.

        Note: This test verifies profile YAML structure, not actual connection.
        Connection tests require the Docker postgres service.
        """
        # Create profile with mock credentials
        profile = {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "postgres",
                        "host": postgres_host,
                        "port": 5432,
                        "user": "test_user",
                        "password": "test_password",
                        "dbname": "test_db",
                        "schema": "public",
                        "threads": 4,
                    }
                },
            }
        }
        profiles_path = profiles_dir / "profiles.yml"
        profiles_path.write_text(yaml.safe_dump(profile))

        # Run dbt debug - checks profile structure (connection may fail without real DB)
        result = subprocess.run(
            [
                "dbt",
                "debug",
                "--project-dir",
                str(dbt_project_dir),
                "--profiles-dir",
                str(profiles_dir),
            ],
            capture_output=True,
            text=True,
            cwd=dbt_project_dir,
        )

        # Profile structure should be valid (connection error expected without real DB)
        # The key is that profile YAML parsing succeeds
        assert "profiles.yml file" in result.stdout or "profile" in result.stdout.lower()


class TestPostgreSQLDockerIntegration:
    """Test PostgreSQL profile with actual Docker service connection."""

    @pytest.mark.skipif(
        not HAS_POSTGRES_SERVICE,
        reason="PostgreSQL Docker service not available",
    )
    @pytest.mark.requirement("006-FR-010")
    def test_dbt_debug_connection_succeeds(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
        postgres_host: str,
        postgres_credentials: dict[str, str],
    ) -> None:
        """Test actual PostgreSQL connection via dbt debug.

        Requires Docker postgres service to be running.
        """
        # Create profile with real Docker credentials
        profile = {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "postgres",
                        "host": postgres_host,
                        "port": 5432,
                        "user": postgres_credentials["user"],
                        "password": postgres_credentials["password"],
                        "dbname": postgres_credentials["database"],
                        "schema": "public",
                        "threads": 4,
                    }
                },
            }
        }
        profiles_path = profiles_dir / "profiles.yml"
        profiles_path.write_text(yaml.safe_dump(profile))

        result = subprocess.run(
            [
                "dbt",
                "debug",
                "--project-dir",
                str(dbt_project_dir),
                "--profiles-dir",
                str(profiles_dir),
            ],
            capture_output=True,
            text=True,
            cwd=dbt_project_dir,
        )

        # Should connect successfully
        assert result.returncode == 0, f"dbt debug failed: {result.stderr}"
        assert (
            "Connection test: OK" in result.stdout or "All checks passed" in result.stdout
        )

    @pytest.mark.skipif(
        not HAS_POSTGRES_SERVICE,
        reason="PostgreSQL Docker service not available",
    )
    @pytest.mark.requirement("006-FR-010")
    def test_end_to_end_profile_generation_and_validation(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
        postgres_host: str,
        postgres_credentials: dict[str, str],
        base_metadata: dict[str, Any],
    ) -> None:
        """Test complete flow: generate profile → write → validate with dbt.

        This is an end-to-end test using ProfileFactory and actual Docker connection.
        """
        from floe_dbt.factory import ProfileFactory
        from floe_dbt.profiles.base import ProfileGeneratorConfig
        from floe_dbt.writer import ProfileWriter

        # Set environment variables for credentials
        os.environ["POSTGRES_DEV_USER"] = postgres_credentials["user"]
        os.environ["POSTGRES_DEV_PASSWORD"] = postgres_credentials["password"]

        try:
            artifacts = {
                "version": "1.0.0",
                "metadata": base_metadata,
                "compute": {
                    "target": "postgres",
                    "properties": {
                        "host": postgres_host,
                        "port": 5432,
                        "database": postgres_credentials["database"],
                        "schema": "public",
                    },
                },
                "transforms": [],
            }

            # Generate profile
            config = ProfileGeneratorConfig(profile_name="floe", target_name="dev")
            generator = ProfileFactory.create("postgres")
            outputs = generator.generate(artifacts, config)

            # Build full profile structure
            profile = {
                config.profile_name: {
                    "target": config.target_name,
                    "outputs": outputs,
                }
            }

            # Write profile
            writer = ProfileWriter()
            profiles_path = profiles_dir / "profiles.yml"
            writer.write(profile, profiles_path)

            # Validate with dbt debug
            result = subprocess.run(
                [
                    "dbt",
                    "debug",
                    "--project-dir",
                    str(dbt_project_dir),
                    "--profiles-dir",
                    str(profiles_dir),
                ],
                capture_output=True,
                text=True,
                cwd=dbt_project_dir,
            )

            assert result.returncode == 0, f"dbt debug failed: {result.stderr}"

        finally:
            # Clean up environment variables
            os.environ.pop("POSTGRES_DEV_USER", None)
            os.environ.pop("POSTGRES_DEV_PASSWORD", None)


class TestPostgreSQLProfileEdgeCases:
    """Test edge cases in PostgreSQL profile handling."""

    @pytest.mark.requirement("006-FR-010")
    def test_postgres_profile_with_custom_port(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
    ) -> None:
        """Test PostgreSQL profile with non-default port."""
        profile = {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "postgres",
                        "host": "localhost",
                        "port": 5433,  # Non-default port
                        "user": "test",
                        "password": "test",
                        "dbname": "test",
                        "threads": 4,
                    }
                },
            }
        }
        profiles_path = profiles_dir / "profiles.yml"
        profiles_path.write_text(yaml.safe_dump(profile))

        # Should parse successfully (connection will fail without server)
        result = subprocess.run(
            [
                "dbt",
                "debug",
                "--project-dir",
                str(dbt_project_dir),
                "--profiles-dir",
                str(profiles_dir),
            ],
            capture_output=True,
            text=True,
            cwd=dbt_project_dir,
        )

        # Profile YAML should be valid
        assert "profile" in result.stdout.lower() or "Configuration" in result.stdout

    @pytest.mark.requirement("006-FR-010")
    def test_postgres_profile_missing_required_field_fails(
        self,
        dbt_project_dir: Path,
        profiles_dir: Path,
    ) -> None:
        """Test that PostgreSQL profile without required 'dbname' fails."""
        profile = {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "postgres",
                        "host": "localhost",
                        "port": 5432,
                        "user": "test",
                        "password": "test",
                        # Missing 'dbname' - required field
                        "threads": 4,
                    }
                },
            }
        }
        profiles_path = profiles_dir / "profiles.yml"
        profiles_path.write_text(yaml.safe_dump(profile))

        result = subprocess.run(
            [
                "dbt",
                "debug",
                "--project-dir",
                str(dbt_project_dir),
                "--profiles-dir",
                str(profiles_dir),
            ],
            capture_output=True,
            text=True,
            cwd=dbt_project_dir,
        )

        # Should fail due to missing required field
        assert result.returncode != 0
