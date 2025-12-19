"""File watcher for dbt manifest.json changes.

This module provides a watchdog-based file watcher that monitors
manifest.json for changes and triggers model synchronization.

T034: Implement watchdog file watcher for manifest.json changes (FR-028).

Functional Requirements:
- FR-028: Automatically trigger model sync when manifest.json changes

Architecture:
- ManifestWatcher: Main watcher class with start/stop lifecycle
- Uses watchdog FileSystemEventHandler for file monitoring
- Debounces rapid changes (dbt compile writes multiple times)
- Calls ModelSynchronizer on valid manifest changes

Usage:
    Local development (auto-reload):
        >>> watcher = ManifestWatcher(
        ...     manifest_path=Path("target/manifest.json"),
        ...     output_dir=Path(".floe/cube/schema"),
        ... )
        >>> with watcher:
        ...     # Watcher runs until context exits
        ...     pass

    Production (CI/CD):
        Use `floe cube sync` command instead of watching.
"""

from __future__ import annotations

import enum
import threading
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from floe_cube.model_sync import DbtManifestParser, ModelSynchronizer
from floe_cube.sources import FileManifestSource, ManifestLoadError

if TYPE_CHECKING:
    from watchdog.observers.api import BaseObserver

logger = structlog.get_logger(__name__)


class WatcherState(enum.Enum):
    """State of the ManifestWatcher.

    Attributes:
        STOPPED: Watcher is not running
        RUNNING: Watcher is actively monitoring
    """

    STOPPED = "stopped"
    RUNNING = "running"


class WatcherError(Exception):
    """Error in ManifestWatcher operation.

    Raised when:
    - Watcher is started while already running
    - Watch directory does not exist
    - Observer fails to start

    Example:
        >>> try:
        ...     watcher.start()
        ... except WatcherError as e:
        ...     print(f"Failed to start watcher: {e}")
    """

    pass


# Type alias for callbacks
SyncCallback = Callable[[dict[str, Any]], None]
ErrorCallback = Callable[[Exception], None]


class _ManifestEventHandler(FileSystemEventHandler):
    """Internal handler for watchdog file events.

    Filters events to only react to manifest.json changes
    and implements debounce logic.
    """

    def __init__(
        self,
        manifest_path: Path,
        on_change: Callable[[], None],
        debounce_seconds: float,
    ) -> None:
        """Initialize event handler.

        Args:
            manifest_path: Path to manifest.json to watch
            on_change: Callback when manifest changes (debounced)
            debounce_seconds: Debounce delay in seconds
        """
        super().__init__()
        self._manifest_path = manifest_path
        self._manifest_name = manifest_path.name
        self._on_change = on_change
        self._debounce_seconds = debounce_seconds
        self._last_event_time: float = 0
        self._pending_timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._log = logger.bind(manifest=str(manifest_path))

    def on_modified(self, event: FileModifiedEvent) -> None:  # type: ignore[override]
        """Handle file modification events.

        Only reacts to modifications of the target manifest file.
        Implements debounce to coalesce rapid changes.

        Args:
            event: File system event
        """
        # Skip directory events
        if event.is_directory:
            return

        # Only react to our manifest file
        src_path = event.src_path
        if isinstance(src_path, bytes):
            src_path = src_path.decode("utf-8")
        event_path = Path(src_path)
        if event_path.name != self._manifest_name:
            return

        # Resolve to handle symlinks
        if event_path.resolve() != self._manifest_path.resolve():
            return

        self._log.debug("manifest_modified_event")
        self._schedule_debounced_callback()

    def _schedule_debounced_callback(self) -> None:
        """Schedule debounced callback.

        Cancels any pending timer and schedules a new one.
        The callback only fires after debounce_seconds of quiet.
        """
        with self._lock:
            # Cancel existing timer if any
            if self._pending_timer is not None:
                self._pending_timer.cancel()

            # Schedule new timer
            self._pending_timer = threading.Timer(
                self._debounce_seconds,
                self._fire_callback,
            )
            self._pending_timer.daemon = True
            self._pending_timer.start()

    def _fire_callback(self) -> None:
        """Fire the change callback."""
        with self._lock:
            self._pending_timer = None

        self._log.debug("debounce_complete_firing_callback")
        self._on_change()

    def cancel_pending(self) -> None:
        """Cancel any pending debounced callback."""
        with self._lock:
            if self._pending_timer is not None:
                self._pending_timer.cancel()
                self._pending_timer = None


class ManifestWatcher:
    """Watches manifest.json for changes and triggers sync.

    This class provides a watchdog-based file watcher for local
    development. It monitors manifest.json for changes and
    automatically triggers model synchronization to regenerate
    Cube schema files.

    Attributes:
        manifest_path: Path to manifest.json
        output_dir: Directory for generated Cube schemas
        debounce_seconds: Debounce delay for rapid changes
        state: Current watcher state (STOPPED or RUNNING)

    Example:
        >>> # Using context manager (recommended)
        >>> with ManifestWatcher(
        ...     manifest_path=Path("target/manifest.json"),
        ...     output_dir=Path(".floe/cube/schema"),
        ... ):
        ...     print("Watching for changes...")
        ...     time.sleep(3600)  # Run for an hour

        >>> # Manual start/stop
        >>> watcher = ManifestWatcher(...)
        >>> watcher.start()
        >>> try:
        ...     # Do work
        ...     pass
        ... finally:
        ...     watcher.stop()

        >>> # With custom callbacks
        >>> def on_sync(manifest: dict) -> None:
        ...     print(f"Synced {len(manifest['nodes'])} models")
        >>> watcher = ManifestWatcher(..., on_sync=on_sync)

    Note:
        For production deployments, use the `floe cube sync` CLI
        command instead of file watching. This watcher is intended
        for local development auto-reload.
    """

    def __init__(
        self,
        manifest_path: Path | str,
        output_dir: Path | str,
        *,
        debounce_seconds: float = 1.0,
        on_sync: SyncCallback | None = None,
        on_error: ErrorCallback | None = None,
    ) -> None:
        """Initialize ManifestWatcher.

        Args:
            manifest_path: Path to manifest.json to watch
            output_dir: Directory for generated Cube schema files
            debounce_seconds: Delay before triggering sync after changes
            on_sync: Optional callback after successful sync
            on_error: Optional callback on sync errors

        Raises:
            WatcherError: If manifest directory does not exist
        """
        if isinstance(manifest_path, str):
            self._manifest_path = Path(manifest_path)
        else:
            self._manifest_path = manifest_path
        self._output_dir = Path(output_dir) if isinstance(output_dir, str) else output_dir
        self._debounce_seconds = debounce_seconds
        self._on_sync = on_sync
        self._on_error = on_error

        # Validate watch directory exists
        watch_dir = self._manifest_path.parent
        if not watch_dir.exists():
            msg = f"Manifest directory does not exist: {watch_dir}"
            raise WatcherError(msg)

        # Internal state
        self._state = WatcherState.STOPPED
        self._observer: BaseObserver | None = None
        self._handler: _ManifestEventHandler | None = None
        self._lock = threading.Lock()
        self._log = logger.bind(
            manifest=str(self._manifest_path),
            output=str(self._output_dir),
        )

    @property
    def manifest_path(self) -> Path:
        """Get the manifest file path."""
        return self._manifest_path

    @property
    def output_dir(self) -> Path:
        """Get the output directory path."""
        return self._output_dir

    @property
    def debounce_seconds(self) -> float:
        """Get the debounce delay in seconds."""
        return self._debounce_seconds

    @property
    def state(self) -> WatcherState:
        """Get the current watcher state."""
        with self._lock:
            return self._state

    def start(self) -> None:
        """Start watching for manifest.json changes.

        Raises:
            WatcherError: If watcher is already running

        Example:
            >>> watcher = ManifestWatcher(...)
            >>> watcher.start()
            >>> print(watcher.state)
            WatcherState.RUNNING
        """
        with self._lock:
            if self._state == WatcherState.RUNNING:
                raise WatcherError("Watcher is already running")

            self._log.info("starting_watcher")

            # Create handler
            self._handler = _ManifestEventHandler(
                manifest_path=self._manifest_path,
                on_change=self._on_manifest_changed,
                debounce_seconds=self._debounce_seconds,
            )

            # Create and start observer
            self._observer = Observer()
            self._observer.schedule(
                self._handler,
                str(self._manifest_path.parent),
                recursive=False,
            )
            self._observer.start()

            self._state = WatcherState.RUNNING
            self._log.info("watcher_started")

    def stop(self) -> None:
        """Stop watching for changes.

        Safe to call even if not running.

        Example:
            >>> watcher.stop()
            >>> print(watcher.state)
            WatcherState.STOPPED
        """
        with self._lock:
            if self._state == WatcherState.STOPPED:
                return

            self._log.info("stopping_watcher")

            # Cancel pending callbacks
            if self._handler is not None:
                self._handler.cancel_pending()
                self._handler = None

            # Stop observer
            if self._observer is not None:
                self._observer.stop()
                self._observer.join(timeout=5.0)
                self._observer = None

            self._state = WatcherState.STOPPED
            self._log.info("watcher_stopped")

    def __enter__(self) -> ManifestWatcher:
        """Context manager entry - start watching.

        Returns:
            Self for use in with statement
        """
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Context manager exit - stop watching."""
        self.stop()

    def _on_manifest_changed(self) -> None:
        """Handle manifest.json change (debounced).

        Loads the manifest and triggers model synchronization.
        Errors are logged and passed to error callback if provided.
        """
        self._log.info("manifest_change_detected")

        try:
            # Load manifest
            source = FileManifestSource(self._manifest_path)
            manifest = source.load()

            # Run synchronization
            parser = DbtManifestParser(manifest)
            synchronizer = ModelSynchronizer(parser)

            # Ensure output directory exists
            self._output_dir.mkdir(parents=True, exist_ok=True)

            # Generate and write schemas
            written_files = synchronizer.write_schemas(self._output_dir)

            self._log.info(
                "sync_completed",
                files_written=len(written_files),
            )

            # Call success callback
            if self._on_sync is not None:
                self._on_sync(manifest)

        except ManifestLoadError as e:
            self._log.error("manifest_load_error", error=str(e))
            if self._on_error is not None:
                self._on_error(e)

        except Exception as e:
            self._log.error("sync_error", error=str(e))
            if self._on_error is not None:
                self._on_error(e)
