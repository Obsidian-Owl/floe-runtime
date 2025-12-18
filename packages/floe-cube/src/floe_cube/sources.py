"""Manifest source abstraction for dbt manifest.json access.

This module provides a pluggable abstraction for loading dbt manifest.json
from different sources (local filesystem, S3, GCS, etc.).

T034: Implement manifest source abstraction layer.

Functional Requirements:
- FR-028: Support manifest.json access from various sources

Architecture:
- ManifestSource protocol defines the interface
- FileManifestSource implements local filesystem access
- Future: S3ManifestSource, GCSManifestSource for cloud storage
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import structlog

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


class ManifestLoadError(Exception):
    """Error loading manifest.json from source.

    Raised when:
    - File/object does not exist
    - Content is not valid JSON
    - Content is not a JSON object (dict)
    - Network/permission errors for remote sources

    Attributes:
        source: Description of the source that failed to load
        cause: Original exception that caused the error

    Example:
        >>> try:
        ...     source.load()
        ... except ManifestLoadError as e:
        ...     print(f"Failed to load manifest: {e}")
    """

    def __init__(
        self, message: str, source: str | None = None, cause: Exception | None = None
    ) -> None:
        """Initialize ManifestLoadError.

        Args:
            message: Error description
            source: Optional source identifier
            cause: Optional original exception
        """
        super().__init__(message)
        self.source = source
        self.cause = cause


@runtime_checkable
class ManifestSource(Protocol):
    """Protocol for manifest.json sources.

    This protocol defines the interface for loading dbt manifest.json
    from various sources. Implementations can support local files,
    S3, GCS, or other storage backends.

    Methods:
        load: Load and parse the manifest
        exists: Check if the manifest exists
        last_modified: Get the last modification time

    Example:
        >>> source: ManifestSource = FileManifestSource(Path("target/manifest.json"))
        >>> if source.exists():
        ...     manifest = source.load()
        ...     print(f"Loaded {len(manifest.get('nodes', {}))} nodes")
    """

    def load(self) -> dict[str, Any]:
        """Load and parse the manifest.json.

        Returns:
            Parsed manifest as dictionary

        Raises:
            ManifestLoadError: If manifest cannot be loaded or parsed
        """
        ...

    def exists(self) -> bool:
        """Check if the manifest exists at the source.

        Returns:
            True if manifest exists and is accessible
        """
        ...

    def last_modified(self) -> datetime | None:
        """Get the last modification timestamp.

        Returns:
            UTC datetime of last modification, or None if unavailable
        """
        ...


class FileManifestSource:
    """Local filesystem manifest source.

    Loads dbt manifest.json from the local filesystem.

    Attributes:
        path: Path to the manifest.json file

    Example:
        >>> source = FileManifestSource(Path("target/manifest.json"))
        >>> if source.exists():
        ...     manifest = source.load()
        ...     mtime = source.last_modified()
        ...     print(f"Manifest modified at {mtime}")

        >>> # Also accepts string paths
        >>> source = FileManifestSource("./target/manifest.json")
    """

    def __init__(self, path: Path | str) -> None:
        """Initialize FileManifestSource.

        Args:
            path: Path to manifest.json (Path or string)
        """
        self._path = Path(path) if isinstance(path, str) else path
        self._log = logger.bind(path=str(self._path))

    @property
    def path(self) -> Path:
        """Get the manifest file path.

        Returns:
            Path to the manifest.json file
        """
        return self._path

    def load(self) -> dict[str, Any]:
        """Load and parse manifest.json from filesystem.

        Returns:
            Parsed manifest dictionary

        Raises:
            ManifestLoadError: If file not found, invalid JSON, or not a dict

        Example:
            >>> source = FileManifestSource("target/manifest.json")
            >>> manifest = source.load()
            >>> print(manifest["metadata"]["dbt_schema_version"])
        """
        self._log.debug("loading_manifest")

        if not self._path.exists():
            msg = f"Manifest file not found: {self._path}"
            self._log.error("manifest_not_found")
            raise ManifestLoadError(msg, source=str(self._path))

        try:
            content = self._path.read_text()
        except OSError as e:
            msg = f"Failed to read manifest file: {self._path} - {e}"
            self._log.error("manifest_read_error", error=str(e))
            raise ManifestLoadError(msg, source=str(self._path), cause=e) from e

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON in manifest file: {self._path} - {e}"
            self._log.error("manifest_parse_error", error=str(e))
            raise ManifestLoadError(msg, source=str(self._path), cause=e) from e

        if not isinstance(data, dict):
            msg = f"Manifest must be a JSON object (dict), got {type(data).__name__}: {self._path}"
            self._log.error("manifest_type_error", actual_type=type(data).__name__)
            raise ManifestLoadError(msg, source=str(self._path))

        node_count = len(data.get("nodes", {}))
        self._log.info("manifest_loaded", node_count=node_count)

        return data

    def exists(self) -> bool:
        """Check if manifest.json exists on filesystem.

        Returns:
            True if file exists

        Example:
            >>> source = FileManifestSource("target/manifest.json")
            >>> if source.exists():
            ...     print("Manifest found!")
        """
        return self._path.exists()

    def last_modified(self) -> datetime | None:
        """Get manifest file modification time.

        Returns:
            UTC datetime of last modification, or None if file doesn't exist

        Example:
            >>> source = FileManifestSource("target/manifest.json")
            >>> mtime = source.last_modified()
            >>> if mtime:
            ...     print(f"Last modified: {mtime.isoformat()}")
        """
        if not self._path.exists():
            return None

        try:
            stat = self._path.stat()
            return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        except OSError:
            return None

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            String representation with path
        """
        return f"FileManifestSource({self._path!s})"
