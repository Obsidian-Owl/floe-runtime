"""Integration tests for compilation features.

Tests the compilation-related features including dbt integration,
SaaS enrichment fields, governance extraction, versioning, and
source hash calculation.

Covers:
- FR-012: dbt-specific fields (dbt_manifest_path, dbt_project_path, dbt_profiles_path)
- FR-013: SaaS enrichment fields (lineage_namespace, environment_context)
- FR-014: Governance extraction (column_classifications mapping)
- FR-015: CompiledArtifacts semantic versioning with 3-version backward compatibility
- FR-017: Auto-detect dbt project location relative to floe.yaml
- FR-019: SHA-256 hash of floe.yaml for change detection (source_hash)
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
import yaml


class TestDbtSpecificFields:
    """Tests for dbt-specific fields in CompiledArtifacts (001-FR-012)."""

    @pytest.mark.requirement("001-FR-012")
    def test_compiled_artifacts_has_dbt_manifest_path(self) -> None:
        """Test that CompiledArtifacts has dbt_manifest_path field.

        Covers:
        - 001-FR-012: dbt_manifest_path field exists
        """
        from floe_core.compiler.models import ArtifactMetadata, CompiledArtifacts
        from floe_core.schemas import ComputeConfig, ComputeTarget, TransformConfig

        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version="0.1.0",
            source_hash="abc123",
        )
        compute = ComputeConfig(target=ComputeTarget.duckdb)
        transforms = [TransformConfig(type="dbt", path="./dbt")]

        # Create artifacts with dbt_manifest_path
        artifacts = CompiledArtifacts(
            metadata=metadata,
            compute=compute,
            transforms=transforms,
            dbt_manifest_path="/path/to/manifest.json",
        )

        assert artifacts.dbt_manifest_path == "/path/to/manifest.json"

        # Without manifest path (defaults to None)
        artifacts_no_manifest = CompiledArtifacts(
            metadata=metadata,
            compute=compute,
            transforms=transforms,
        )

        assert artifacts_no_manifest.dbt_manifest_path is None

    @pytest.mark.requirement("001-FR-012")
    def test_compiled_artifacts_has_dbt_project_path(self) -> None:
        """Test that CompiledArtifacts has dbt_project_path field.

        Covers:
        - 001-FR-012: dbt_project_path field exists
        """
        from floe_core.compiler.models import ArtifactMetadata, CompiledArtifacts
        from floe_core.schemas import ComputeConfig, ComputeTarget, TransformConfig

        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version="0.1.0",
            source_hash="abc123",
        )
        compute = ComputeConfig(target=ComputeTarget.duckdb)
        transforms = [TransformConfig(type="dbt", path="./dbt")]

        # Create artifacts with dbt_project_path
        artifacts = CompiledArtifacts(
            metadata=metadata,
            compute=compute,
            transforms=transforms,
            dbt_project_path="/path/to/dbt/project",
        )

        assert artifacts.dbt_project_path == "/path/to/dbt/project"

        # Without project path (defaults to None)
        artifacts_no_project = CompiledArtifacts(
            metadata=metadata,
            compute=compute,
            transforms=transforms,
        )

        assert artifacts_no_project.dbt_project_path is None

    @pytest.mark.requirement("001-FR-012")
    def test_compiled_artifacts_has_dbt_profiles_path(self) -> None:
        """Test that CompiledArtifacts has dbt_profiles_path field with default.

        Covers:
        - 001-FR-012: dbt_profiles_path field exists with default ".floe/profiles"
        """
        from floe_core.compiler.models import ArtifactMetadata, CompiledArtifacts
        from floe_core.schemas import ComputeConfig, ComputeTarget, TransformConfig

        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version="0.1.0",
            source_hash="abc123",
        )
        compute = ComputeConfig(target=ComputeTarget.duckdb)
        transforms = [TransformConfig(type="dbt", path="./dbt")]

        # Default profiles path
        artifacts = CompiledArtifacts(
            metadata=metadata,
            compute=compute,
            transforms=transforms,
        )

        assert artifacts.dbt_profiles_path == ".floe/profiles"

        # Custom profiles path
        artifacts_custom = CompiledArtifacts(
            metadata=metadata,
            compute=compute,
            transforms=transforms,
            dbt_profiles_path="custom/profiles/dir",
        )

        assert artifacts_custom.dbt_profiles_path == "custom/profiles/dir"


class TestSaaSEnrichmentFields:
    """Tests for SaaS enrichment fields (001-FR-013)."""

    @pytest.mark.requirement("001-FR-013")
    def test_compiled_artifacts_has_lineage_namespace(self) -> None:
        """Test that CompiledArtifacts has lineage_namespace field.

        Covers:
        - 001-FR-013: lineage_namespace optional field
        """
        from floe_core.compiler.models import ArtifactMetadata, CompiledArtifacts
        from floe_core.schemas import ComputeConfig, ComputeTarget, TransformConfig

        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version="0.1.0",
            source_hash="abc123",
        )
        compute = ComputeConfig(target=ComputeTarget.duckdb)
        transforms = [TransformConfig(type="dbt", path="./dbt")]

        # With lineage namespace (SaaS enrichment)
        artifacts = CompiledArtifacts(
            metadata=metadata,
            compute=compute,
            transforms=transforms,
            lineage_namespace="tenant-acme/production",
        )

        assert artifacts.lineage_namespace == "tenant-acme/production"

        # Without (standalone mode, defaults to None)
        artifacts_standalone = CompiledArtifacts(
            metadata=metadata,
            compute=compute,
            transforms=transforms,
        )

        assert artifacts_standalone.lineage_namespace is None

    @pytest.mark.requirement("001-FR-013")
    def test_compiled_artifacts_has_environment_context(self) -> None:
        """Test that CompiledArtifacts has environment_context field.

        Covers:
        - 001-FR-013: environment_context optional field for SaaS enrichment
        """
        from floe_core.compiler.models import (
            ArtifactMetadata,
            CompiledArtifacts,
            EnvironmentContext,
        )
        from floe_core.schemas import ComputeConfig, ComputeTarget, TransformConfig

        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version="0.1.0",
            source_hash="abc123",
        )
        compute = ComputeConfig(target=ComputeTarget.duckdb)
        transforms = [TransformConfig(type="dbt", path="./dbt")]

        # Create environment context (SaaS enrichment)
        env_context = EnvironmentContext(
            tenant_id=uuid4(),
            tenant_slug="acme-corp",
            project_id=uuid4(),
            project_slug="data-warehouse",
            environment_id=uuid4(),
            environment_type="production",
            governance_category="production",
        )

        artifacts = CompiledArtifacts(
            metadata=metadata,
            compute=compute,
            transforms=transforms,
            environment_context=env_context,
        )

        assert artifacts.environment_context is not None
        assert artifacts.environment_context.tenant_slug == "acme-corp"
        assert artifacts.environment_context.environment_type == "production"

        # Without context (standalone mode)
        artifacts_standalone = CompiledArtifacts(
            metadata=metadata,
            compute=compute,
            transforms=transforms,
        )

        assert artifacts_standalone.environment_context is None

    @pytest.mark.requirement("001-FR-013")
    def test_environment_context_validates_environment_types(self) -> None:
        """Test that EnvironmentContext validates environment_type values.

        Covers:
        - 001-FR-013: environment_type is validated to allowed values
        """
        from pydantic import ValidationError

        from floe_core.compiler.models import EnvironmentContext

        # Valid environment types
        for env_type in ["development", "preview", "staging", "production"]:
            context = EnvironmentContext(
                tenant_id=uuid4(),
                tenant_slug="test",
                project_id=uuid4(),
                project_slug="test",
                environment_id=uuid4(),
                environment_type=env_type,
                governance_category="production" if env_type == "production" else "non_production",
            )
            assert context.environment_type == env_type

        # Invalid environment type
        with pytest.raises(ValidationError) as exc_info:
            EnvironmentContext(
                tenant_id=uuid4(),
                tenant_slug="test",
                project_id=uuid4(),
                project_slug="test",
                environment_id=uuid4(),
                environment_type="invalid_type",  # type: ignore[arg-type]
                governance_category="production",
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0


class TestGovernanceExtraction:
    """Tests for governance extraction (001-FR-014)."""

    @pytest.mark.requirement("001-FR-014")
    def test_compiled_artifacts_has_column_classifications(self) -> None:
        """Test that CompiledArtifacts has column_classifications mapping.

        Covers:
        - 001-FR-014: column_classifications mapping for governance extraction
        """
        from floe_core.compiler.models import ArtifactMetadata, CompiledArtifacts
        from floe_core.schemas import (
            ColumnClassification,
            ComputeConfig,
            ComputeTarget,
            TransformConfig,
        )

        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version="0.1.0",
            source_hash="abc123",
        )
        compute = ComputeConfig(target=ComputeTarget.duckdb)
        transforms = [TransformConfig(type="dbt", path="./dbt")]

        # Create column classifications extracted from dbt meta
        column_classifications = {
            "customers": {
                "email": ColumnClassification(
                    classification="pii",
                    pii_type="email",
                    sensitivity="high",
                ),
                "name": ColumnClassification(
                    classification="pii",
                    pii_type="name",
                    sensitivity="medium",
                ),
            },
            "orders": {
                "total": ColumnClassification(
                    classification="confidential",
                    sensitivity="low",
                ),
            },
        }

        artifacts = CompiledArtifacts(
            metadata=metadata,
            compute=compute,
            transforms=transforms,
            column_classifications=column_classifications,
        )

        assert artifacts.column_classifications is not None
        assert "customers" in artifacts.column_classifications
        assert "email" in artifacts.column_classifications["customers"]
        assert artifacts.column_classifications["customers"]["email"].classification == "pii"
        assert artifacts.column_classifications["customers"]["email"].pii_type == "email"
        assert artifacts.column_classifications["customers"]["email"].sensitivity == "high"

    @pytest.mark.requirement("001-FR-014")
    def test_column_classification_model_validates_sensitivity(self) -> None:
        """Test that ColumnClassification validates sensitivity levels.

        Covers:
        - 001-FR-014: sensitivity level validation (low, medium, high)
        """
        from pydantic import ValidationError

        from floe_core.schemas import ColumnClassification

        # Valid sensitivity levels
        for level in ["low", "medium", "high"]:
            classification = ColumnClassification(
                classification="pii",
                sensitivity=level,  # type: ignore[arg-type]
            )
            assert classification.sensitivity == level

        # Invalid sensitivity level
        with pytest.raises(ValidationError) as exc_info:
            ColumnClassification(
                classification="pii",
                sensitivity="critical",  # type: ignore[arg-type]
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0


class TestCompiledArtifactsVersioning:
    """Tests for CompiledArtifacts versioning (001-FR-015)."""

    @pytest.mark.requirement("001-FR-015")
    def test_compiled_artifacts_has_version_field(self) -> None:
        """Test that CompiledArtifacts has version field with semver.

        Covers:
        - 001-FR-015: version field exists
        """
        from floe_core.compiler.models import ArtifactMetadata, CompiledArtifacts
        from floe_core.schemas import ComputeConfig, ComputeTarget, TransformConfig

        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version="0.1.0",
            source_hash="abc123",
        )
        compute = ComputeConfig(target=ComputeTarget.duckdb)
        transforms = [TransformConfig(type="dbt", path="./dbt")]

        # Default version
        artifacts = CompiledArtifacts(
            metadata=metadata,
            compute=compute,
            transforms=transforms,
        )

        assert artifacts.version == "1.0.0"

        # Custom version
        artifacts_v2 = CompiledArtifacts(
            version="2.0.0",
            metadata=metadata,
            compute=compute,
            transforms=transforms,
        )

        assert artifacts_v2.version == "2.0.0"

    @pytest.mark.requirement("001-FR-015")
    def test_compiled_artifacts_is_immutable(self) -> None:
        """Test that CompiledArtifacts is immutable (frozen).

        Covers:
        - 001-FR-015: Immutability for contract stability
        """
        from pydantic import ValidationError

        from floe_core.compiler.models import ArtifactMetadata, CompiledArtifacts
        from floe_core.schemas import ComputeConfig, ComputeTarget, TransformConfig

        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version="0.1.0",
            source_hash="abc123",
        )
        compute = ComputeConfig(target=ComputeTarget.duckdb)
        transforms = [TransformConfig(type="dbt", path="./dbt")]

        artifacts = CompiledArtifacts(
            metadata=metadata,
            compute=compute,
            transforms=transforms,
        )

        # Attempting to modify should raise an error
        with pytest.raises(ValidationError):
            artifacts.version = "2.0.0"  # type: ignore[misc]

    @pytest.mark.requirement("001-FR-015")
    def test_compiled_artifacts_rejects_extra_fields(self) -> None:
        """Test that CompiledArtifacts rejects unknown fields.

        Covers:
        - 001-FR-015: Strict contract - no extra fields allowed
        """
        from pydantic import ValidationError

        from floe_core.compiler.models import ArtifactMetadata, CompiledArtifacts
        from floe_core.schemas import ComputeConfig, ComputeTarget, TransformConfig

        metadata = ArtifactMetadata(
            compiled_at=datetime.now(timezone.utc),
            floe_core_version="0.1.0",
            source_hash="abc123",
        )
        compute = ComputeConfig(target=ComputeTarget.duckdb)
        transforms = [TransformConfig(type="dbt", path="./dbt")]

        # Attempting to add extra fields should fail
        with pytest.raises(ValidationError) as exc_info:
            CompiledArtifacts(
                metadata=metadata,
                compute=compute,
                transforms=transforms,
                unknown_field="should_fail",  # type: ignore[call-arg]
            )

        errors = exc_info.value.errors()
        assert any("extra" in str(e).lower() for e in errors)


class TestDbtProjectAutoDetection:
    """Tests for auto-detecting dbt project location (001-FR-017)."""

    @pytest.mark.requirement("001-FR-017")
    def test_compiler_detects_dbt_from_transforms(self, tmp_path: Path) -> None:
        """Test that Compiler detects dbt project from transforms config.

        Covers:
        - 001-FR-017: Auto-detect dbt project from transforms path
        """
        from floe_core.compiler import Compiler

        # Create dbt project structure
        dbt_dir = tmp_path / "dbt"
        dbt_dir.mkdir()
        (dbt_dir / "dbt_project.yml").write_text(
            yaml.dump({"name": "test_project", "version": "1.0.0"})
        )

        # Create floe.yaml pointing to dbt directory
        floe_config = {
            "name": "test-project",
            "version": "1.0.0",
            "compute": {"target": "duckdb"},
            "transforms": [{"type": "dbt", "path": "./dbt"}],
        }

        (tmp_path / "floe.yaml").write_text(yaml.dump(floe_config))

        # Compile
        compiler = Compiler()
        artifacts = compiler.compile(tmp_path / "floe.yaml")

        # Should detect dbt project
        assert artifacts.dbt_project_path is not None
        assert "dbt" in artifacts.dbt_project_path

    @pytest.mark.requirement("001-FR-017")
    def test_compiler_searches_parent_directories(self, tmp_path: Path) -> None:
        """Test that Compiler searches parent directories for dbt project.

        Covers:
        - 001-FR-017: Search parent directories up to 5 levels
        """
        from floe_core.compiler import Compiler

        # Create dbt project in parent
        (tmp_path / "dbt_project.yml").write_text(
            yaml.dump({"name": "test_project", "version": "1.0.0"})
        )

        # Create subdirectory with floe.yaml
        subdir = tmp_path / "config"
        subdir.mkdir()

        floe_config = {
            "name": "test-project",
            "version": "1.0.0",
            "compute": {"target": "duckdb"},
            "transforms": [{"type": "dbt", "path": ".."}],
        }

        (subdir / "floe.yaml").write_text(yaml.dump(floe_config))

        # Compile from subdirectory
        compiler = Compiler()
        artifacts = compiler.compile(subdir / "floe.yaml")

        # Should detect dbt project in parent
        assert artifacts.dbt_project_path is not None

    @pytest.mark.requirement("001-FR-017")
    def test_compiler_returns_none_when_no_dbt_project(self, tmp_path: Path) -> None:
        """Test that Compiler returns None when no dbt project found.

        Covers:
        - 001-FR-017: Graceful handling when dbt not found
        """
        from floe_core.compiler import Compiler

        # Create floe.yaml without dbt project
        floe_config = {
            "name": "test-project",
            "version": "1.0.0",
            "compute": {"target": "duckdb"},
            "transforms": [{"type": "dbt", "path": "./nonexistent"}],
        }

        (tmp_path / "floe.yaml").write_text(yaml.dump(floe_config))

        # Compile
        compiler = Compiler()
        artifacts = compiler.compile(tmp_path / "floe.yaml")

        # Should be None (no dbt project found)
        assert artifacts.dbt_project_path is None


class TestSourceHashCalculation:
    """Tests for SHA-256 hash of floe.yaml (001-FR-019)."""

    @pytest.mark.requirement("001-FR-019")
    def test_compiled_artifacts_has_source_hash(self, tmp_path: Path) -> None:
        """Test that CompiledArtifacts includes source_hash in metadata.

        Covers:
        - 001-FR-019: source_hash field exists
        """
        from floe_core.compiler import Compiler

        floe_config = {
            "name": "test-project",
            "version": "1.0.0",
            "compute": {"target": "duckdb"},
            "transforms": [{"type": "dbt", "path": "./dbt"}],
        }

        (tmp_path / "floe.yaml").write_text(yaml.dump(floe_config))

        compiler = Compiler()
        artifacts = compiler.compile(tmp_path / "floe.yaml")

        # Should have source_hash in metadata
        assert artifacts.metadata.source_hash is not None
        assert len(artifacts.metadata.source_hash) == 64  # SHA-256 hex length

    @pytest.mark.requirement("001-FR-019")
    def test_source_hash_is_sha256(self, tmp_path: Path) -> None:
        """Test that source_hash is valid SHA-256 hash.

        Covers:
        - 001-FR-019: Hash is SHA-256 format
        """
        from floe_core.compiler import Compiler

        floe_content = yaml.dump({
            "name": "test-project",
            "version": "1.0.0",
            "compute": {"target": "duckdb"},
            "transforms": [{"type": "dbt", "path": "./dbt"}],
        })

        (tmp_path / "floe.yaml").write_text(floe_content)

        # Calculate expected hash
        expected_hash = hashlib.sha256(floe_content.encode("utf-8")).hexdigest()

        compiler = Compiler()
        artifacts = compiler.compile(tmp_path / "floe.yaml")

        # Should match expected SHA-256
        assert artifacts.metadata.source_hash == expected_hash

    @pytest.mark.requirement("001-FR-019")
    def test_source_hash_changes_when_content_changes(self, tmp_path: Path) -> None:
        """Test that source_hash changes when floe.yaml content changes.

        Covers:
        - 001-FR-019: Hash changes for change detection
        """
        from floe_core.compiler import Compiler

        # Create initial floe.yaml
        floe_config_v1 = {
            "name": "test-project",
            "version": "1.0.0",
            "compute": {"target": "duckdb"},
            "transforms": [{"type": "dbt", "path": "./dbt"}],
        }

        (tmp_path / "floe.yaml").write_text(yaml.dump(floe_config_v1))

        compiler = Compiler()
        artifacts_v1 = compiler.compile(tmp_path / "floe.yaml")
        hash_v1 = artifacts_v1.metadata.source_hash

        # Modify floe.yaml
        floe_config_v2 = {
            "name": "test-project-modified",  # Changed name
            "version": "2.0.0",  # Changed version
            "compute": {"target": "duckdb"},
            "transforms": [{"type": "dbt", "path": "./dbt"}],
        }

        (tmp_path / "floe.yaml").write_text(yaml.dump(floe_config_v2))

        artifacts_v2 = compiler.compile(tmp_path / "floe.yaml")
        hash_v2 = artifacts_v2.metadata.source_hash

        # Hashes should be different
        assert hash_v1 != hash_v2

    @pytest.mark.requirement("001-FR-019")
    def test_source_hash_is_deterministic(self, tmp_path: Path) -> None:
        """Test that source_hash is deterministic for same content.

        Covers:
        - 001-FR-019: Same content produces same hash
        """
        from floe_core.compiler import Compiler

        floe_config = {
            "name": "test-project",
            "version": "1.0.0",
            "compute": {"target": "duckdb"},
            "transforms": [{"type": "dbt", "path": "./dbt"}],
        }

        floe_content = yaml.dump(floe_config)
        (tmp_path / "floe.yaml").write_text(floe_content)

        compiler = Compiler()

        # Compile multiple times
        artifacts_1 = compiler.compile(tmp_path / "floe.yaml")
        artifacts_2 = compiler.compile(tmp_path / "floe.yaml")
        artifacts_3 = compiler.compile(tmp_path / "floe.yaml")

        # All hashes should be identical
        assert artifacts_1.metadata.source_hash == artifacts_2.metadata.source_hash
        assert artifacts_2.metadata.source_hash == artifacts_3.metadata.source_hash
