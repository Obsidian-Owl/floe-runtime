"""Unit tests for Compiler.compile() method.

T037: [US2] Unit tests for Compiler.compile()

Tests the main Compiler class that transforms FloeSpec into CompiledArtifacts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml


class TestCompilerImport:
    """Tests for Compiler class import and instantiation."""

    def test_compiler_import(self) -> None:
        """Test Compiler can be imported from compiler package."""
        from floe_core.compiler import Compiler

        assert Compiler is not None

    def test_compiler_instantiation(self) -> None:
        """Test Compiler can be instantiated."""
        from floe_core.compiler import Compiler

        compiler = Compiler()
        assert compiler is not None

    def test_compiler_has_compile_method(self) -> None:
        """Test Compiler has compile() method."""
        from floe_core.compiler import Compiler

        compiler = Compiler()
        assert hasattr(compiler, "compile")
        assert callable(compiler.compile)


class TestCompilerCompile:
    """Tests for Compiler.compile() method."""

    def test_compile_minimal_spec(self, tmp_floe_project: Path) -> None:
        """Test compile() with minimal floe.yaml."""
        from floe_core.compiler import Compiler, CompiledArtifacts

        compiler = Compiler()
        floe_yaml_path = tmp_floe_project / "floe.yaml"

        artifacts = compiler.compile(floe_yaml_path)

        assert isinstance(artifacts, CompiledArtifacts)
        assert artifacts.version == "1.0.0"
        assert artifacts.metadata is not None
        assert artifacts.compute.target.value == "duckdb"

    def test_compile_full_spec(self, tmp_floe_project_full: Path) -> None:
        """Test compile() with full floe.yaml (all optional fields)."""
        from floe_core.compiler import Compiler, CompiledArtifacts

        compiler = Compiler()
        floe_yaml_path = tmp_floe_project_full / "floe.yaml"

        artifacts = compiler.compile(floe_yaml_path)

        assert isinstance(artifacts, CompiledArtifacts)
        assert artifacts.compute.target.value == "snowflake"
        assert artifacts.consumption.enabled is True
        assert artifacts.catalog is not None

    def test_compile_returns_immutable_artifacts(self, tmp_floe_project: Path) -> None:
        """Test compile() returns immutable CompiledArtifacts."""
        from floe_core.compiler import Compiler
        from pydantic import ValidationError

        compiler = Compiler()
        floe_yaml_path = tmp_floe_project / "floe.yaml"

        artifacts = compiler.compile(floe_yaml_path)

        with pytest.raises(ValidationError):
            artifacts.version = "2.0.0"  # type: ignore[misc]

    def test_compile_sets_metadata(self, tmp_floe_project: Path) -> None:
        """Test compile() sets correct metadata."""
        from floe_core.compiler import Compiler

        compiler = Compiler()
        floe_yaml_path = tmp_floe_project / "floe.yaml"

        artifacts = compiler.compile(floe_yaml_path)

        assert artifacts.metadata.compiled_at is not None
        assert artifacts.metadata.floe_core_version is not None
        assert artifacts.metadata.source_hash is not None

    def test_compile_metadata_timestamp_is_recent(self, tmp_floe_project: Path) -> None:
        """Test compiled_at timestamp is recent (within 5 seconds)."""
        from floe_core.compiler import Compiler

        before = datetime.now(timezone.utc)
        compiler = Compiler()
        floe_yaml_path = tmp_floe_project / "floe.yaml"

        artifacts = compiler.compile(floe_yaml_path)
        after = datetime.now(timezone.utc)

        assert before <= artifacts.metadata.compiled_at <= after

    def test_compile_computes_source_hash(self, tmp_floe_project: Path) -> None:
        """Test source_hash is computed from floe.yaml content."""
        from floe_core.compiler import Compiler

        compiler = Compiler()
        floe_yaml_path = tmp_floe_project / "floe.yaml"

        artifacts = compiler.compile(floe_yaml_path)

        # Hash should be a hex string (SHA-256 is 64 chars)
        assert len(artifacts.metadata.source_hash) == 64
        assert all(c in "0123456789abcdef" for c in artifacts.metadata.source_hash)

    def test_compile_same_content_same_hash(self, tmp_path: Path) -> None:
        """Test same content produces same hash."""
        from floe_core.compiler import Compiler

        content = {
            "name": "test-project",
            "version": "1.0.0",
            "compute": {"target": "duckdb"},
            "transforms": [{"type": "dbt", "path": "./dbt"}],
        }

        # Create two projects with same content
        project1 = tmp_path / "project1"
        project1.mkdir()
        (project1 / "floe.yaml").write_text(yaml.dump(content))

        project2 = tmp_path / "project2"
        project2.mkdir()
        (project2 / "floe.yaml").write_text(yaml.dump(content))

        compiler = Compiler()
        artifacts1 = compiler.compile(project1 / "floe.yaml")
        artifacts2 = compiler.compile(project2 / "floe.yaml")

        assert artifacts1.metadata.source_hash == artifacts2.metadata.source_hash

    def test_compile_different_content_different_hash(self, tmp_path: Path) -> None:
        """Test different content produces different hash."""
        from floe_core.compiler import Compiler

        # Create two projects with different content
        project1 = tmp_path / "project1"
        project1.mkdir()
        (project1 / "floe.yaml").write_text(
            yaml.dump(
                {
                    "name": "project-one",
                    "version": "1.0.0",
                    "compute": {"target": "duckdb"},
                    "transforms": [{"type": "dbt", "path": "./dbt"}],
                }
            )
        )

        project2 = tmp_path / "project2"
        project2.mkdir()
        (project2 / "floe.yaml").write_text(
            yaml.dump(
                {
                    "name": "project-two",
                    "version": "2.0.0",
                    "compute": {"target": "snowflake"},
                    "transforms": [{"type": "dbt", "path": "./dbt"}],
                }
            )
        )

        compiler = Compiler()
        artifacts1 = compiler.compile(project1 / "floe.yaml")
        artifacts2 = compiler.compile(project2 / "floe.yaml")

        assert artifacts1.metadata.source_hash != artifacts2.metadata.source_hash


class TestCompilerErrorHandling:
    """Tests for Compiler error handling."""

    def test_compile_missing_file_raises(self, tmp_path: Path) -> None:
        """Test compile() raises FileNotFoundError for missing file."""
        from floe_core.compiler import Compiler

        compiler = Compiler()
        missing_path = tmp_path / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            compiler.compile(missing_path)

    def test_compile_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Test compile() raises error for invalid YAML."""
        from floe_core.compiler import Compiler

        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("{{ invalid yaml")

        compiler = Compiler()

        with pytest.raises(Exception):  # yaml.YAMLError
            compiler.compile(invalid_yaml)

    def test_compile_invalid_spec_raises(self, tmp_path: Path) -> None:
        """Test compile() raises ValidationError for invalid spec."""
        from floe_core.compiler import Compiler
        from pydantic import ValidationError

        # Missing required fields
        invalid_spec = tmp_path / "floe.yaml"
        invalid_spec.write_text(yaml.dump({"name": "test"}))

        compiler = Compiler()

        with pytest.raises(ValidationError):
            compiler.compile(invalid_spec)


class TestCompilerWithDbtProject:
    """Tests for Compiler with dbt project integration."""

    def test_compile_detects_dbt_project(self, tmp_floe_with_dbt: Path) -> None:
        """Test compile() detects dbt project."""
        from floe_core.compiler import Compiler

        compiler = Compiler()
        artifacts = compiler.compile(tmp_floe_with_dbt / "floe.yaml")

        assert artifacts.dbt_project_path is not None

    def test_compile_sets_dbt_manifest_path(self, tmp_floe_with_dbt: Path) -> None:
        """Test compile() sets dbt_manifest_path when manifest exists."""
        from floe_core.compiler import Compiler

        # Create manifest.json
        dbt_dir = tmp_floe_with_dbt / "dbt"
        target_dir = dbt_dir / "target"
        target_dir.mkdir(parents=True)
        (target_dir / "manifest.json").write_text(
            json.dumps({"nodes": {}, "sources": {}})
        )

        compiler = Compiler()
        artifacts = compiler.compile(tmp_floe_with_dbt / "floe.yaml")

        assert artifacts.dbt_manifest_path is not None
        assert "manifest.json" in artifacts.dbt_manifest_path

    def test_compile_extracts_classifications(
        self, tmp_floe_with_dbt_classifications: Path
    ) -> None:
        """Test compile() extracts classifications from dbt manifest."""
        from floe_core.compiler import Compiler

        compiler = Compiler()
        artifacts = compiler.compile(tmp_floe_with_dbt_classifications / "floe.yaml")

        assert artifacts.column_classifications is not None
        assert "customers" in artifacts.column_classifications

    def test_compile_without_dbt_manifest(self, tmp_floe_with_dbt: Path) -> None:
        """Test compile() works without dbt manifest (graceful degradation)."""
        from floe_core.compiler import Compiler

        # No manifest.json created
        compiler = Compiler()
        artifacts = compiler.compile(tmp_floe_with_dbt / "floe.yaml")

        # Should still compile, classifications will be None
        assert artifacts is not None
        assert artifacts.column_classifications is None


class TestCompilerOutput:
    """Tests for Compiler output structure."""

    def test_compile_preserves_compute_config(self, tmp_floe_project: Path) -> None:
        """Test compile() preserves compute configuration."""
        from floe_core.compiler import Compiler

        compiler = Compiler()
        artifacts = compiler.compile(tmp_floe_project / "floe.yaml")

        assert artifacts.compute.target.value == "duckdb"

    def test_compile_preserves_transforms(self, tmp_floe_project: Path) -> None:
        """Test compile() preserves transform configurations."""
        from floe_core.compiler import Compiler

        compiler = Compiler()
        artifacts = compiler.compile(tmp_floe_project / "floe.yaml")

        assert len(artifacts.transforms) == 1
        assert artifacts.transforms[0].type == "dbt"
        assert artifacts.transforms[0].path == "./dbt"

    def test_compile_sets_default_consumption(self, tmp_floe_project: Path) -> None:
        """Test compile() sets default consumption config."""
        from floe_core.compiler import Compiler

        compiler = Compiler()
        artifacts = compiler.compile(tmp_floe_project / "floe.yaml")

        assert artifacts.consumption.enabled is False
        assert artifacts.consumption.port == 4000

    def test_compile_sets_default_governance(self, tmp_floe_project: Path) -> None:
        """Test compile() sets default governance config."""
        from floe_core.compiler import Compiler

        compiler = Compiler()
        artifacts = compiler.compile(tmp_floe_project / "floe.yaml")

        assert artifacts.governance.classification_source == "dbt_meta"
        assert artifacts.governance.emit_lineage is True

    def test_compile_sets_default_observability(self, tmp_floe_project: Path) -> None:
        """Test compile() sets default observability config."""
        from floe_core.compiler import Compiler

        compiler = Compiler()
        artifacts = compiler.compile(tmp_floe_project / "floe.yaml")

        assert artifacts.observability.traces is True
        assert artifacts.observability.metrics is True
        assert artifacts.observability.lineage is True


# Fixtures for compiler tests
@pytest.fixture
def tmp_floe_project(tmp_path: Path, sample_floe_yaml: dict[str, Any]) -> Path:
    """Create a temporary floe project with minimal floe.yaml."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    floe_yaml = project_dir / "floe.yaml"
    floe_yaml.write_text(yaml.dump(sample_floe_yaml))

    return project_dir


@pytest.fixture
def tmp_floe_project_full(tmp_path: Path, sample_floe_yaml_full: dict[str, Any]) -> Path:
    """Create a temporary floe project with full floe.yaml."""
    project_dir = tmp_path / "test-project-full"
    project_dir.mkdir()

    floe_yaml = project_dir / "floe.yaml"
    floe_yaml.write_text(yaml.dump(sample_floe_yaml_full))

    return project_dir


@pytest.fixture
def tmp_floe_with_dbt(tmp_path: Path, sample_floe_yaml: dict[str, Any]) -> Path:
    """Create a temporary floe project with dbt project."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    # Create floe.yaml
    floe_yaml = project_dir / "floe.yaml"
    floe_yaml.write_text(yaml.dump(sample_floe_yaml))

    # Create dbt project structure
    dbt_dir = project_dir / "dbt"
    dbt_dir.mkdir()
    (dbt_dir / "dbt_project.yml").write_text("name: test_dbt\nversion: 1.0.0")

    return project_dir


@pytest.fixture
def tmp_floe_with_dbt_classifications(
    tmp_path: Path, sample_floe_yaml: dict[str, Any]
) -> Path:
    """Create a floe project with dbt project containing classifications."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    # Create floe.yaml with dbt_meta classification source
    sample_floe_yaml["governance"] = {"classification_source": "dbt_meta"}
    floe_yaml = project_dir / "floe.yaml"
    floe_yaml.write_text(yaml.dump(sample_floe_yaml))

    # Create dbt project structure
    dbt_dir = project_dir / "dbt"
    dbt_dir.mkdir()
    (dbt_dir / "dbt_project.yml").write_text("name: test_dbt\nversion: 1.0.0")

    # Create manifest with classifications
    target_dir = dbt_dir / "target"
    target_dir.mkdir()
    manifest = {
        "nodes": {
            "model.test.customers": {
                "name": "customers",
                "resource_type": "model",
                "columns": {
                    "email": {
                        "name": "email",
                        "meta": {
                            "floe": {
                                "classification": "pii",
                                "pii_type": "email",
                                "sensitivity": "high",
                            }
                        },
                    },
                },
            }
        },
        "sources": {},
    }
    (target_dir / "manifest.json").write_text(json.dumps(manifest))

    return project_dir
