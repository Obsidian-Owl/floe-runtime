"""Unit tests for ManifestSource protocol and implementations.

T035: [US2] Unit test for manifest source abstraction layer.

Tests cover:
- FileManifestSource loading and validation
- Existence checks
- Last modified timestamp
- Error handling for missing/invalid manifests
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from floe_cube.sources import FileManifestSource, ManifestLoadError

if TYPE_CHECKING:
    from typing import Any


class TestFileManifestSource:
    """Tests for FileManifestSource implementation."""

    @pytest.fixture
    def sample_manifest(self) -> dict[str, Any]:
        """Sample dbt manifest.json content."""
        return {
            "metadata": {"dbt_schema_version": "1.0.0"},
            "nodes": {
                "model.my_project.customers": {
                    "name": "customers",
                    "resource_type": "model",
                    "schema": "public",
                    "columns": {
                        "id": {"name": "id", "data_type": "integer"},
                        "email": {"name": "email", "data_type": "text"},
                    },
                }
            },
        }

    @pytest.fixture
    def manifest_file(self, tmp_path: Path, sample_manifest: dict[str, Any]) -> Path:
        """Create a temporary manifest.json file."""
        manifest_path = tmp_path / "target" / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(sample_manifest))
        return manifest_path

    def test_load_valid_manifest(
        self, manifest_file: Path, sample_manifest: dict[str, Any]
    ) -> None:
        """FileManifestSource should load valid manifest.json."""
        source = FileManifestSource(manifest_file)
        loaded = source.load()

        assert loaded == sample_manifest
        assert "nodes" in loaded
        assert "model.my_project.customers" in loaded["nodes"]

    def test_exists_returns_true_for_existing_file(self, manifest_file: Path) -> None:
        """FileManifestSource.exists() should return True for existing file."""
        source = FileManifestSource(manifest_file)
        assert source.exists() is True

    def test_exists_returns_false_for_missing_file(self, tmp_path: Path) -> None:
        """FileManifestSource.exists() should return False for missing file."""
        source = FileManifestSource(tmp_path / "nonexistent" / "manifest.json")
        assert source.exists() is False

    def test_last_modified_returns_timestamp(self, manifest_file: Path) -> None:
        """FileManifestSource.last_modified() should return file mtime."""
        source = FileManifestSource(manifest_file)
        mtime = source.last_modified()

        assert mtime is not None
        assert isinstance(mtime, datetime)
        # Should be recent (within last minute)
        now = datetime.now(tz=timezone.utc)
        assert (now - mtime).total_seconds() < 60

    def test_last_modified_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        """FileManifestSource.last_modified() should return None for missing file."""
        source = FileManifestSource(tmp_path / "nonexistent" / "manifest.json")
        assert source.last_modified() is None

    def test_load_raises_for_missing_file(self, tmp_path: Path) -> None:
        """FileManifestSource.load() should raise ManifestLoadError for missing file."""
        source = FileManifestSource(tmp_path / "nonexistent" / "manifest.json")

        with pytest.raises(ManifestLoadError) as exc_info:
            source.load()

        assert "not found" in str(exc_info.value).lower()

    def test_load_raises_for_invalid_json(self, tmp_path: Path) -> None:
        """FileManifestSource.load() should raise ManifestLoadError for invalid JSON."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ not valid json }")

        source = FileManifestSource(invalid_file)

        with pytest.raises(ManifestLoadError) as exc_info:
            source.load()

        assert "invalid" in str(exc_info.value).lower() or "parse" in str(exc_info.value).lower()

    def test_load_raises_for_non_dict_json(self, tmp_path: Path) -> None:
        """FileManifestSource.load() should raise ManifestLoadError for non-dict JSON."""
        array_file = tmp_path / "array.json"
        array_file.write_text('["not", "a", "dict"]')

        source = FileManifestSource(array_file)

        with pytest.raises(ManifestLoadError) as exc_info:
            source.load()

        assert "dict" in str(exc_info.value).lower() or "object" in str(exc_info.value).lower()

    def test_path_property_returns_path(self, manifest_file: Path) -> None:
        """FileManifestSource.path should return the configured path."""
        source = FileManifestSource(manifest_file)
        assert source.path == manifest_file

    def test_accepts_string_path(self, manifest_file: Path) -> None:
        """FileManifestSource should accept string path and convert to Path."""
        source = FileManifestSource(str(manifest_file))
        assert source.path == manifest_file
        assert source.exists() is True

    def test_load_caches_result(self, manifest_file: Path) -> None:
        """FileManifestSource.load() should return fresh data on each call."""
        source = FileManifestSource(manifest_file)

        # First load
        first = source.load()

        # Modify the file
        new_content = {"metadata": {"version": "2.0.0"}, "nodes": {}}
        manifest_file.write_text(json.dumps(new_content))

        # Second load should get new content
        second = source.load()

        assert first != second
        assert second["metadata"]["version"] == "2.0.0"

    def test_repr(self, manifest_file: Path) -> None:
        """FileManifestSource should have useful repr."""
        source = FileManifestSource(manifest_file)
        repr_str = repr(source)

        assert "FileManifestSource" in repr_str
        assert str(manifest_file) in repr_str


class TestManifestLoadError:
    """Tests for ManifestLoadError exception."""

    def test_error_includes_path(self, tmp_path: Path) -> None:
        """ManifestLoadError should include the file path in message."""
        source = FileManifestSource(tmp_path / "missing.json")

        with pytest.raises(ManifestLoadError) as exc_info:
            source.load()

        assert "missing.json" in str(exc_info.value)

    def test_error_is_exception(self) -> None:
        """ManifestLoadError should be a proper exception."""
        error = ManifestLoadError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"
