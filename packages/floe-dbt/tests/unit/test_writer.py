"""Unit tests for ProfileWriter.

T023: [P] [US2] Unit tests for ProfileWriter
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml


class TestProfileWriter:
    """Test suite for ProfileWriter."""

    @pytest.fixture
    def writer(self) -> Any:
        """Get ProfileWriter instance."""
        from floe_dbt.writer import ProfileWriter

        return ProfileWriter()

    @pytest.fixture
    def sample_profile(self) -> dict[str, Any]:
        """Sample profile structure for testing."""
        return {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "duckdb",
                        "path": ":memory:",
                        "threads": 4,
                    }
                },
            }
        }

    def test_write_creates_file(
        self,
        writer: Any,
        sample_profile: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test that write creates the profiles.yml file."""
        output_path = tmp_path / "profiles.yml"

        writer.write(sample_profile, output_path)

        assert output_path.exists()

    def test_write_creates_parent_directories(
        self,
        writer: Any,
        sample_profile: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test that write creates parent directories if needed."""
        output_path = tmp_path / "nested" / "path" / "profiles.yml"

        writer.write(sample_profile, output_path)

        assert output_path.exists()
        assert output_path.parent.exists()

    def test_write_outputs_valid_yaml(
        self,
        writer: Any,
        sample_profile: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test that output is valid YAML."""
        output_path = tmp_path / "profiles.yml"

        writer.write(sample_profile, output_path)

        # Read back and parse
        content = output_path.read_text()
        parsed = yaml.safe_load(content)

        assert parsed == sample_profile

    def test_write_preserves_structure(
        self,
        writer: Any,
        tmp_path: Path,
    ) -> None:
        """Test that complex profile structure is preserved."""
        profile = {
            "floe": {
                "target": "prod",
                "outputs": {
                    "dev": {
                        "type": "snowflake",
                        "account": "xy12345.us-east-1",
                        "user": "{{ env_var('SNOWFLAKE_USER') }}",
                        "password": "{{ env_var('SNOWFLAKE_PASSWORD') }}",
                        "role": "TRANSFORMER",
                        "warehouse": "COMPUTE_WH",
                        "database": "ANALYTICS",
                        "schema": "DBT",
                        "threads": 8,
                    },
                    "prod": {
                        "type": "snowflake",
                        "account": "xy12345.us-east-1",
                        "user": "{{ env_var('SNOWFLAKE_USER') }}",
                        "password": "{{ env_var('SNOWFLAKE_PASSWORD') }}",
                        "role": "TRANSFORMER",
                        "warehouse": "COMPUTE_WH_XL",
                        "database": "ANALYTICS",
                        "schema": "PROD",
                        "threads": 16,
                    },
                },
            }
        }
        output_path = tmp_path / "profiles.yml"

        writer.write(profile, output_path)

        parsed = yaml.safe_load(output_path.read_text())
        assert parsed == profile
        assert parsed["floe"]["target"] == "prod"
        assert len(parsed["floe"]["outputs"]) == 2

    def test_write_overwrites_existing_file(
        self,
        writer: Any,
        sample_profile: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test that write overwrites existing file (FR-005)."""
        output_path = tmp_path / "profiles.yml"

        # Create initial file
        output_path.write_text("old content")

        # Write new profile
        writer.write(sample_profile, output_path)

        # Verify overwritten
        parsed = yaml.safe_load(output_path.read_text())
        assert parsed == sample_profile
        assert "old content" not in output_path.read_text()

    def test_write_handles_env_var_syntax(
        self,
        writer: Any,
        tmp_path: Path,
    ) -> None:
        """Test that env_var template syntax is preserved."""
        profile = {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "postgres",
                        "host": "localhost",
                        "user": "{{ env_var('POSTGRES_USER') }}",
                        "password": "{{ env_var('POSTGRES_PASSWORD') }}",
                        "dbname": "analytics",
                        "port": 5432,
                        "threads": 4,
                    }
                },
            }
        }
        output_path = tmp_path / "profiles.yml"

        writer.write(profile, output_path)

        content = output_path.read_text()
        # YAML might quote the template syntax, but it should be preserved
        assert "env_var" in content
        assert "POSTGRES_USER" in content
        assert "POSTGRES_PASSWORD" in content

    def test_write_to_string(
        self,
        writer: Any,
        sample_profile: dict[str, Any],
    ) -> None:
        """Test writing profile to string instead of file."""
        result = writer.to_yaml_string(sample_profile)

        assert isinstance(result, str)
        parsed = yaml.safe_load(result)
        assert parsed == sample_profile

    def test_write_includes_comment_header(
        self,
        writer: Any,
        sample_profile: dict[str, Any],
        tmp_path: Path,
    ) -> None:
        """Test that output includes a generated comment header."""
        output_path = tmp_path / "profiles.yml"

        writer.write(sample_profile, output_path)

        content = output_path.read_text()
        # Should have a comment indicating it's auto-generated
        assert "# " in content  # At minimum has some comment
        # Implementation may include something like:
        # "# Generated by floe-dbt" or "# Auto-generated - do not edit"

    def test_write_uses_safe_yaml_dump(
        self,
        writer: Any,
        tmp_path: Path,
    ) -> None:
        """Test that YAML is written with safe defaults."""
        profile = {
            "floe": {
                "target": "dev",
                "outputs": {
                    "dev": {
                        "type": "duckdb",
                        "path": ":memory:",
                        "threads": 4,
                        # Include values that might trigger unsafe YAML
                        "description": "Test profile with special chars: &*[]{}",
                    }
                },
            }
        }
        output_path = tmp_path / "profiles.yml"

        writer.write(profile, output_path)

        # Should be parseable with safe_load
        parsed = yaml.safe_load(output_path.read_text())
        assert parsed is not None
