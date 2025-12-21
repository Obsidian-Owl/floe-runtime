"""Unit tests for Dagster definitions entry point.

Tests for load_definitions_from_artifacts and load_definitions_from_dict.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestLoadDefinitionsFromArtifacts:
    """Tests for load_definitions_from_artifacts function."""

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        """Test that missing artifacts file raises FileNotFoundError."""
        from floe_dagster.definitions import load_definitions_from_artifacts

        with pytest.raises(FileNotFoundError) as exc_info:
            load_definitions_from_artifacts(tmp_path / "nonexistent.json")

        assert "CompiledArtifacts not found" in str(exc_info.value)
        assert "floe compile" in str(exc_info.value)

    def test_loads_from_valid_file(self, tmp_path: Path) -> None:
        """Test loading from valid artifacts file."""
        from floe_dagster.definitions import load_definitions_from_artifacts

        # Create minimal artifacts file
        artifacts = {
            "version": "1.0.0",
            "dbt_manifest_path": str(tmp_path / "manifest.json"),
            "dbt_project_path": str(tmp_path),
            "compute": {"target": "duckdb", "properties": {}},
        }
        artifacts_path = tmp_path / "compiled_artifacts.json"
        artifacts_path.write_text(json.dumps(artifacts))

        # Create mock manifest
        manifest = {"nodes": {}, "metadata": {}}
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest))

        # Should not raise - loads successfully
        with patch("floe_dagster.definitions.FloeAssetFactory.create_definitions") as mock_create:
            mock_create.return_value = MagicMock()
            result = load_definitions_from_artifacts(str(artifacts_path))
            assert result is not None
            mock_create.assert_called_once_with(artifacts)


class TestLoadDefinitionsFromDict:
    """Tests for load_definitions_from_dict function."""

    def test_creates_definitions_from_dict(self) -> None:
        """Test creating definitions from dictionary."""
        from floe_dagster.definitions import load_definitions_from_dict

        artifacts: dict[str, Any] = {
            "version": "1.0.0",
            "dbt_manifest_path": "/path/to/manifest.json",
            "dbt_project_path": "/path/to/project",
            "compute": {"target": "duckdb", "properties": {}},
        }

        with patch("floe_dagster.definitions.FloeAssetFactory.create_definitions") as mock_create:
            mock_create.return_value = MagicMock()
            result = load_definitions_from_dict(artifacts)
            assert result is not None
            mock_create.assert_called_once_with(artifacts)
