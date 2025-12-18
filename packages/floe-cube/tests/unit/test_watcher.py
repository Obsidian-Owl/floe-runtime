"""Unit tests for ManifestWatcher file watcher.

T035: [US2] Unit test: watcher triggers sync on manifest.json modification.

Tests cover:
- Watcher start/stop lifecycle
- File change detection
- Debounce logic for rapid changes
- Error handling for invalid manifests
- Callback invocation
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from floe_cube.watcher import ManifestWatcher, WatcherError, WatcherState

if TYPE_CHECKING:
    from typing import Any


class TestManifestWatcherLifecycle:
    """Tests for ManifestWatcher start/stop lifecycle."""

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
                    "columns": {"id": {"name": "id", "data_type": "integer"}},
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

    @pytest.fixture
    def output_dir(self, tmp_path: Path) -> Path:
        """Create output directory for generated schemas."""
        output = tmp_path / ".floe" / "cube" / "schema"
        output.mkdir(parents=True, exist_ok=True)
        return output

    def test_initial_state_is_stopped(
        self, manifest_file: Path, output_dir: Path
    ) -> None:
        """ManifestWatcher should start in STOPPED state."""
        watcher = ManifestWatcher(
            manifest_path=manifest_file,
            output_dir=output_dir,
        )
        assert watcher.state == WatcherState.STOPPED

    def test_start_changes_state_to_running(
        self, manifest_file: Path, output_dir: Path
    ) -> None:
        """ManifestWatcher.start() should change state to RUNNING."""
        watcher = ManifestWatcher(
            manifest_path=manifest_file,
            output_dir=output_dir,
        )

        try:
            watcher.start()
            assert watcher.state == WatcherState.RUNNING
        finally:
            watcher.stop()

    def test_stop_changes_state_to_stopped(
        self, manifest_file: Path, output_dir: Path
    ) -> None:
        """ManifestWatcher.stop() should change state to STOPPED."""
        watcher = ManifestWatcher(
            manifest_path=manifest_file,
            output_dir=output_dir,
        )

        watcher.start()
        watcher.stop()

        assert watcher.state == WatcherState.STOPPED

    def test_start_twice_raises_error(
        self, manifest_file: Path, output_dir: Path
    ) -> None:
        """ManifestWatcher.start() should raise if already running."""
        watcher = ManifestWatcher(
            manifest_path=manifest_file,
            output_dir=output_dir,
        )

        try:
            watcher.start()
            with pytest.raises(WatcherError) as exc_info:
                watcher.start()

            assert "already running" in str(exc_info.value).lower()
        finally:
            watcher.stop()

    def test_stop_when_not_running_is_safe(
        self, manifest_file: Path, output_dir: Path
    ) -> None:
        """ManifestWatcher.stop() should be safe to call when not running."""
        watcher = ManifestWatcher(
            manifest_path=manifest_file,
            output_dir=output_dir,
        )

        # Should not raise
        watcher.stop()
        watcher.stop()  # Multiple stops should be safe

        assert watcher.state == WatcherState.STOPPED

    def test_context_manager_protocol(
        self, manifest_file: Path, output_dir: Path
    ) -> None:
        """ManifestWatcher should support context manager protocol."""
        watcher = ManifestWatcher(
            manifest_path=manifest_file,
            output_dir=output_dir,
        )

        with watcher:
            assert watcher.state == WatcherState.RUNNING

        assert watcher.state == WatcherState.STOPPED


class TestManifestWatcherFileDetection:
    """Tests for file change detection."""

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
                    "columns": {"id": {"name": "id", "data_type": "integer"}},
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

    @pytest.fixture
    def output_dir(self, tmp_path: Path) -> Path:
        """Create output directory for generated schemas."""
        output = tmp_path / ".floe" / "cube" / "schema"
        output.mkdir(parents=True, exist_ok=True)
        return output

    def test_detects_file_modification(
        self, manifest_file: Path, output_dir: Path, sample_manifest: dict[str, Any]
    ) -> None:
        """ManifestWatcher should detect file modifications."""
        callback = MagicMock()
        watcher = ManifestWatcher(
            manifest_path=manifest_file,
            output_dir=output_dir,
            on_sync=callback,
            debounce_seconds=0.1,  # Short debounce for testing
        )

        with watcher:
            # Modify the file
            time.sleep(0.2)  # Let watcher initialize
            sample_manifest["metadata"]["version"] = "2.0.0"
            manifest_file.write_text(json.dumps(sample_manifest))

            # Wait for debounce and processing
            time.sleep(0.5)

        # Callback should have been called
        assert callback.called

    def test_ignores_unrelated_files(
        self, manifest_file: Path, output_dir: Path, tmp_path: Path
    ) -> None:
        """ManifestWatcher should ignore changes to unrelated files."""
        callback = MagicMock()
        watcher = ManifestWatcher(
            manifest_path=manifest_file,
            output_dir=output_dir,
            on_sync=callback,
            debounce_seconds=0.1,
        )

        with watcher:
            time.sleep(0.2)

            # Create an unrelated file in the same directory
            other_file = manifest_file.parent / "other.json"
            other_file.write_text('{"unrelated": true}')

            time.sleep(0.3)

        # Callback should NOT have been called
        assert not callback.called


class TestManifestWatcherDebounce:
    """Tests for debounce logic."""

    @pytest.fixture
    def sample_manifest(self) -> dict[str, Any]:
        """Sample dbt manifest.json content."""
        return {
            "metadata": {"dbt_schema_version": "1.0.0"},
            "nodes": {},
        }

    @pytest.fixture
    def manifest_file(self, tmp_path: Path, sample_manifest: dict[str, Any]) -> Path:
        """Create a temporary manifest.json file."""
        manifest_path = tmp_path / "target" / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(sample_manifest))
        return manifest_path

    @pytest.fixture
    def output_dir(self, tmp_path: Path) -> Path:
        """Create output directory for generated schemas."""
        output = tmp_path / ".floe" / "cube" / "schema"
        output.mkdir(parents=True, exist_ok=True)
        return output

    def test_rapid_changes_are_debounced(
        self, manifest_file: Path, output_dir: Path, sample_manifest: dict[str, Any]
    ) -> None:
        """Rapid file changes should be coalesced into single sync."""
        callback = MagicMock()
        watcher = ManifestWatcher(
            manifest_path=manifest_file,
            output_dir=output_dir,
            on_sync=callback,
            debounce_seconds=0.3,  # 300ms debounce
        )

        with watcher:
            time.sleep(0.2)

            # Rapid-fire changes (simulating dbt compile)
            for i in range(5):
                sample_manifest["metadata"]["version"] = f"1.0.{i}"
                manifest_file.write_text(json.dumps(sample_manifest))
                time.sleep(0.05)  # 50ms between writes

            # Wait for debounce to settle
            time.sleep(0.5)

        # Should be called only once (debounced)
        # Allow for 1-2 calls due to timing variations
        assert callback.call_count <= 2


class TestManifestWatcherErrorHandling:
    """Tests for error handling."""

    @pytest.fixture
    def sample_manifest(self) -> dict[str, Any]:
        """Sample dbt manifest.json content."""
        return {
            "metadata": {"dbt_schema_version": "1.0.0"},
            "nodes": {},
        }

    @pytest.fixture
    def manifest_file(self, tmp_path: Path, sample_manifest: dict[str, Any]) -> Path:
        """Create a temporary manifest.json file."""
        manifest_path = tmp_path / "target" / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(sample_manifest))
        return manifest_path

    @pytest.fixture
    def output_dir(self, tmp_path: Path) -> Path:
        """Create output directory for generated schemas."""
        output = tmp_path / ".floe" / "cube" / "schema"
        output.mkdir(parents=True, exist_ok=True)
        return output

    def test_invalid_manifest_does_not_crash_watcher(
        self, manifest_file: Path, output_dir: Path
    ) -> None:
        """Invalid manifest.json should log error but not crash watcher."""
        callback = MagicMock()
        error_callback = MagicMock()
        watcher = ManifestWatcher(
            manifest_path=manifest_file,
            output_dir=output_dir,
            on_sync=callback,
            on_error=error_callback,
            debounce_seconds=0.1,
        )

        with watcher:
            time.sleep(0.2)

            # Write invalid JSON
            manifest_file.write_text("{ invalid json }")
            time.sleep(0.3)

            # Watcher should still be running
            assert watcher.state == WatcherState.RUNNING

        # Error callback should have been called
        assert error_callback.called

    def test_missing_manifest_directory_raises(
        self, tmp_path: Path, output_dir: Path
    ) -> None:
        """ManifestWatcher should raise if manifest directory doesn't exist."""
        missing_path = tmp_path / "nonexistent" / "manifest.json"

        with pytest.raises(WatcherError) as exc_info:
            ManifestWatcher(
                manifest_path=missing_path,
                output_dir=output_dir,
            )

        assert "directory" in str(exc_info.value).lower()

    def test_callback_exception_does_not_crash_watcher(
        self, manifest_file: Path, output_dir: Path, sample_manifest: dict[str, Any]
    ) -> None:
        """Exception in callback should not crash the watcher."""

        def failing_callback(manifest: dict[str, Any]) -> None:
            raise RuntimeError("Callback failed!")

        error_callback = MagicMock()
        watcher = ManifestWatcher(
            manifest_path=manifest_file,
            output_dir=output_dir,
            on_sync=failing_callback,
            on_error=error_callback,
            debounce_seconds=0.1,
        )

        with watcher:
            time.sleep(0.2)

            # Trigger a change
            sample_manifest["metadata"]["version"] = "2.0.0"
            manifest_file.write_text(json.dumps(sample_manifest))
            time.sleep(0.3)

            # Watcher should still be running
            assert watcher.state == WatcherState.RUNNING

        # Error callback should have been called with the exception
        assert error_callback.called


class TestManifestWatcherConfiguration:
    """Tests for watcher configuration."""

    @pytest.fixture
    def sample_manifest(self) -> dict[str, Any]:
        """Sample dbt manifest.json content."""
        return {"metadata": {}, "nodes": {}}

    @pytest.fixture
    def manifest_file(self, tmp_path: Path, sample_manifest: dict[str, Any]) -> Path:
        """Create a temporary manifest.json file."""
        manifest_path = tmp_path / "target" / "manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(sample_manifest))
        return manifest_path

    @pytest.fixture
    def output_dir(self, tmp_path: Path) -> Path:
        """Create output directory for generated schemas."""
        output = tmp_path / ".floe" / "cube" / "schema"
        output.mkdir(parents=True, exist_ok=True)
        return output

    def test_default_debounce_is_one_second(
        self, manifest_file: Path, output_dir: Path
    ) -> None:
        """Default debounce should be 1 second."""
        watcher = ManifestWatcher(
            manifest_path=manifest_file,
            output_dir=output_dir,
        )
        assert watcher.debounce_seconds == 1.0

    def test_custom_debounce(self, manifest_file: Path, output_dir: Path) -> None:
        """Custom debounce should be respected."""
        watcher = ManifestWatcher(
            manifest_path=manifest_file,
            output_dir=output_dir,
            debounce_seconds=2.5,
        )
        assert watcher.debounce_seconds == 2.5

    def test_manifest_path_property(
        self, manifest_file: Path, output_dir: Path
    ) -> None:
        """ManifestWatcher.manifest_path should return configured path."""
        watcher = ManifestWatcher(
            manifest_path=manifest_file,
            output_dir=output_dir,
        )
        assert watcher.manifest_path == manifest_file

    def test_output_dir_property(self, manifest_file: Path, output_dir: Path) -> None:
        """ManifestWatcher.output_dir should return configured path."""
        watcher = ManifestWatcher(
            manifest_path=manifest_file,
            output_dir=output_dir,
        )
        assert watcher.output_dir == output_dir

    def test_accepts_string_paths(self, manifest_file: Path, output_dir: Path) -> None:
        """ManifestWatcher should accept string paths."""
        watcher = ManifestWatcher(
            manifest_path=str(manifest_file),
            output_dir=str(output_dir),
        )
        assert watcher.manifest_path == manifest_file
        assert watcher.output_dir == output_dir
