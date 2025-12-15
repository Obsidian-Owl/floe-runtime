"""Unit tests for ArtifactMetadata model.

T032: [US2] Unit tests for ArtifactMetadata model

Tests the compilation metadata model that captures when artifacts
were compiled and from which source.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError


class TestArtifactMetadataModel:
    """Tests for ArtifactMetadata model structure and validation."""

    def test_artifact_metadata_import(self) -> None:
        """Test ArtifactMetadata can be imported from compiler package."""
        from floe_core.compiler import ArtifactMetadata

        assert ArtifactMetadata is not None

    def test_artifact_metadata_required_fields(self) -> None:
        """Test ArtifactMetadata requires all fields."""
        from floe_core.compiler import ArtifactMetadata

        # Should require compiled_at, floe_core_version, source_hash
        with pytest.raises(ValidationError) as exc_info:
            ArtifactMetadata()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        field_names = {e["loc"][0] for e in errors}
        assert "compiled_at" in field_names
        assert "floe_core_version" in field_names
        assert "source_hash" in field_names

    def test_artifact_metadata_valid_creation(self) -> None:
        """Test ArtifactMetadata with valid fields."""
        from floe_core.compiler import ArtifactMetadata

        now = datetime.now(timezone.utc)
        metadata = ArtifactMetadata(
            compiled_at=now,
            floe_core_version="0.1.0",
            source_hash="abc123def456",
        )

        assert metadata.compiled_at == now
        assert metadata.floe_core_version == "0.1.0"
        assert metadata.source_hash == "abc123def456"

    def test_artifact_metadata_datetime_utc(self) -> None:
        """Test compiled_at accepts datetime with UTC timezone."""
        from floe_core.compiler import ArtifactMetadata

        utc_time = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        metadata = ArtifactMetadata(
            compiled_at=utc_time,
            floe_core_version="0.1.0",
            source_hash="abc123",
        )

        assert metadata.compiled_at.tzinfo == timezone.utc

    def test_artifact_metadata_immutable(self) -> None:
        """Test ArtifactMetadata is immutable (frozen=True)."""
        from floe_core.compiler import ArtifactMetadata

        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version="0.1.0",
            source_hash="abc123",
        )

        with pytest.raises(ValidationError):
            metadata.floe_core_version = "0.2.0"  # type: ignore[misc]

    def test_artifact_metadata_extra_forbid(self) -> None:
        """Test ArtifactMetadata rejects unknown fields."""
        from floe_core.compiler import ArtifactMetadata

        with pytest.raises(ValidationError) as exc_info:
            ArtifactMetadata(
                compiled_at=datetime.now(timezone.utc),
                floe_core_version="0.1.0",
                source_hash="abc123",
                unknown_field="should_fail",
            )

        assert "extra_forbidden" in str(exc_info.value)

    def test_artifact_metadata_source_hash_sha256_format(self) -> None:
        """Test source_hash accepts SHA-256 format."""
        from floe_core.compiler import ArtifactMetadata

        sha256_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version="0.1.0",
            source_hash=sha256_hash,
        )

        assert metadata.source_hash == sha256_hash
        assert len(metadata.source_hash) == 64

    def test_artifact_metadata_version_string(self) -> None:
        """Test floe_core_version is a string."""
        from floe_core.compiler import ArtifactMetadata

        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version="1.2.3-beta",
            source_hash="abc123",
        )

        assert isinstance(metadata.floe_core_version, str)
        assert metadata.floe_core_version == "1.2.3-beta"

    def test_artifact_metadata_serialization(self) -> None:
        """Test ArtifactMetadata can be serialized to dict."""
        from floe_core.compiler import ArtifactMetadata

        now = datetime.now(timezone.utc)
        metadata = ArtifactMetadata(
            compiled_at=now,
            floe_core_version="0.1.0",
            source_hash="abc123",
        )

        data = metadata.model_dump()
        assert "compiled_at" in data
        assert "floe_core_version" in data
        assert "source_hash" in data

    def test_artifact_metadata_json_serialization(self) -> None:
        """Test ArtifactMetadata can be serialized to JSON."""
        from floe_core.compiler import ArtifactMetadata

        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version="0.1.0",
            source_hash="abc123",
        )

        json_str = metadata.model_dump_json()
        assert '"floe_core_version":"0.1.0"' in json_str
        assert '"source_hash":"abc123"' in json_str

    def test_artifact_metadata_empty_source_hash(self) -> None:
        """Test source_hash cannot be empty string."""
        from floe_core.compiler import ArtifactMetadata

        with pytest.raises(ValidationError):
            ArtifactMetadata(
                compiled_at=datetime.now(timezone.utc),
                floe_core_version="0.1.0",
                source_hash="",
            )

    def test_artifact_metadata_empty_version(self) -> None:
        """Test floe_core_version cannot be empty string."""
        from floe_core.compiler import ArtifactMetadata

        with pytest.raises(ValidationError):
            ArtifactMetadata(
                compiled_at=datetime.now(timezone.utc),
                floe_core_version="",
                source_hash="abc123",
            )
