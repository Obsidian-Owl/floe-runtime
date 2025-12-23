"""Unit tests for CompiledArtifacts model.

T034: [US2] Unit tests for CompiledArtifacts immutability
T035: [US2] Unit tests for CompiledArtifacts JSON round-trip
T024: [US2] Unit tests for ResolvedPlatformProfiles and CompiledArtifacts v2.0

Tests the output contract model that downstream packages consume.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError


class TestCompiledArtifactsModel:
    """Tests for CompiledArtifacts model structure."""

    def test_compiled_artifacts_import(self) -> None:
        """Test CompiledArtifacts can be imported from compiler package."""
        from floe_core.compiler import CompiledArtifacts

        assert CompiledArtifacts is not None

    def test_compiled_artifacts_required_fields(self) -> None:
        """Test CompiledArtifacts requires metadata, compute, transforms."""
        from floe_core.compiler import CompiledArtifacts

        with pytest.raises(ValidationError) as exc_info:
            CompiledArtifacts()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        field_names = {e["loc"][0] for e in errors}
        assert "metadata" in field_names
        assert "compute" in field_names
        assert "transforms" in field_names

    def test_compiled_artifacts_valid_creation(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test CompiledArtifacts with valid fields."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
        )

        assert artifacts.version == "1.0.0"  # Default version
        assert artifacts.metadata is not None
        assert artifacts.compute is not None
        assert len(artifacts.transforms) == 1

    def test_compiled_artifacts_default_version(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test CompiledArtifacts has default version 1.0.0."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
        )

        assert artifacts.version == "1.0.0"

    def test_compiled_artifacts_custom_version(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test CompiledArtifacts can have custom version."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            version="2.0.0",
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
        )

        assert artifacts.version == "2.0.0"


class TestCompiledArtifactsImmutability:
    """T034: Tests for CompiledArtifacts immutability."""

    def test_compiled_artifacts_frozen(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test CompiledArtifacts is immutable (frozen=True)."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
        )

        with pytest.raises(ValidationError):
            artifacts.version = "2.0.0"  # type: ignore[misc]

    def test_compiled_artifacts_extra_forbid(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test CompiledArtifacts rejects unknown fields."""
        from floe_core.compiler import CompiledArtifacts

        with pytest.raises(ValidationError) as exc_info:
            CompiledArtifacts(
                metadata=sample_artifact_metadata,
                compute=sample_compute_config,
                transforms=[sample_transform_config],
                unknown_field="should_fail",
            )

        assert "extra_forbidden" in str(exc_info.value)

    def test_compiled_artifacts_nested_configs_immutable(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test nested config models are also immutable."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
        )

        # Nested metadata should also be frozen
        with pytest.raises(ValidationError):
            artifacts.metadata.floe_core_version = "new_version"  # type: ignore[misc]


class TestCompiledArtifactsJSONRoundTrip:
    """T035: Tests for CompiledArtifacts JSON serialization."""

    def test_compiled_artifacts_to_json(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test CompiledArtifacts can be serialized to JSON."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
        )

        json_str = artifacts.model_dump_json()
        assert isinstance(json_str, str)
        assert '"version":"1.0.0"' in json_str

    def test_compiled_artifacts_from_json(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test CompiledArtifacts can be deserialized from JSON."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
        )

        json_str = artifacts.model_dump_json()
        loaded = CompiledArtifacts.model_validate_json(json_str)

        assert loaded.version == artifacts.version
        assert loaded.metadata.floe_core_version == artifacts.metadata.floe_core_version

    def test_compiled_artifacts_json_round_trip(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test JSON round-trip preserves all data."""
        from floe_core.compiler import CompiledArtifacts

        original = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
        )

        # Serialize and deserialize
        json_str = original.model_dump_json()
        loaded = CompiledArtifacts.model_validate_json(json_str)

        # Compare via dict (since models are frozen)
        assert original.model_dump() == loaded.model_dump()

    def test_compiled_artifacts_json_includes_optional_fields(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test JSON serialization includes optional fields when set."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
            dbt_manifest_path="/path/to/manifest.json",
            dbt_project_path="/path/to/dbt",
        )

        json_str = artifacts.model_dump_json()
        assert "dbt_manifest_path" in json_str
        assert "dbt_project_path" in json_str


class TestCompiledArtifactsOptionalFields:
    """Tests for optional fields in CompiledArtifacts."""

    def test_compiled_artifacts_optional_catalog(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test catalog is optional."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
        )

        assert artifacts.catalog is None

    def test_compiled_artifacts_with_catalog(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
        sample_catalog_config: dict,
    ) -> None:
        """Test CompiledArtifacts with catalog config."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
            catalog=sample_catalog_config,
        )

        assert artifacts.catalog is not None
        assert artifacts.catalog.type == "polaris"

    def test_compiled_artifacts_optional_dbt_paths(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test dbt paths are optional."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
        )

        assert artifacts.dbt_manifest_path is None
        assert artifacts.dbt_project_path is None

    def test_compiled_artifacts_dbt_profiles_path_default(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test dbt_profiles_path has default value."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
        )

        assert artifacts.dbt_profiles_path == ".floe/profiles"

    def test_compiled_artifacts_optional_lineage_namespace(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test lineage_namespace is optional (SaaS enrichment)."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
        )

        assert artifacts.lineage_namespace is None

    def test_compiled_artifacts_optional_environment_context(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test environment_context is optional (SaaS enrichment)."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
        )

        assert artifacts.environment_context is None

    def test_compiled_artifacts_with_environment_context(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
        sample_environment_context: dict,
    ) -> None:
        """Test CompiledArtifacts with environment context."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
            environment_context=sample_environment_context,
        )

        assert artifacts.environment_context is not None
        assert artifacts.environment_context.tenant_slug == "acme-corp"

    def test_compiled_artifacts_optional_column_classifications(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test column_classifications is optional."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
        )

        assert artifacts.column_classifications is None


class TestCompiledArtifactsWithClassifications:
    """Tests for CompiledArtifacts with column classifications."""

    def test_compiled_artifacts_with_classifications(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test CompiledArtifacts with column classifications."""
        from floe_core.compiler import CompiledArtifacts
        from floe_core.schemas import ColumnClassification

        classifications = {
            "customers": {
                "email": ColumnClassification(
                    classification="pii",
                    pii_type="email",
                    sensitivity="high",
                ),
            }
        }

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
            column_classifications=classifications,
        )

        assert artifacts.column_classifications is not None
        assert "customers" in artifacts.column_classifications
        assert artifacts.column_classifications["customers"]["email"].classification == "pii"


# Fixtures for compiler tests
@pytest.fixture
def sample_artifact_metadata() -> dict:
    """Return sample ArtifactMetadata as dict."""
    return {
        "compiled_at": datetime.now(timezone.utc).isoformat(),
        "floe_core_version": "0.1.0",
        "source_hash": "abc123def456",
    }


@pytest.fixture
def sample_compute_config() -> dict:
    """Return sample ComputeConfig as dict."""
    return {
        "target": "duckdb",
    }


@pytest.fixture
def sample_transform_config() -> dict:
    """Return sample TransformConfig as dict."""
    return {
        "type": "dbt",
        "path": "./dbt",
    }


@pytest.fixture
def sample_catalog_config() -> dict:
    """Return sample CatalogConfig as dict."""
    return {
        "type": "polaris",
        "uri": "https://polaris.example.com/api/catalog",
        "warehouse": "my_warehouse",
    }


@pytest.fixture
def sample_environment_context() -> dict:
    """Return sample EnvironmentContext as dict."""
    return {
        "tenant_id": str(uuid4()),
        "tenant_slug": "acme-corp",
        "project_id": str(uuid4()),
        "project_slug": "data-warehouse",
        "environment_id": str(uuid4()),
        "environment_type": "production",
        "governance_category": "production",
    }


@pytest.fixture
def sample_storage_profile() -> dict:
    """Return sample StorageProfile as dict."""
    return {
        "bucket": "my-data-bucket",
        "region": "us-east-1",
    }


@pytest.fixture
def sample_catalog_profile() -> dict:
    """Return sample CatalogProfile as dict."""
    return {
        "uri": "http://polaris:8181/api/catalog",
        "warehouse": "demo_warehouse",
    }


@pytest.fixture
def sample_compute_profile() -> dict:
    """Return sample ComputeProfile as dict."""
    return {}


@pytest.fixture
def sample_resolved_profiles(
    sample_storage_profile: dict,
    sample_catalog_profile: dict,
    sample_compute_profile: dict,
) -> dict:
    """Return sample ResolvedPlatformProfiles as dict."""
    return {
        "storage": sample_storage_profile,
        "catalog": sample_catalog_profile,
        "compute": sample_compute_profile,
        "platform_env": "local",
    }


class TestResolvedPlatformProfilesModel:
    """T024: Tests for ResolvedPlatformProfiles model."""

    def test_resolved_platform_profiles_import(self) -> None:
        """Test ResolvedPlatformProfiles can be imported from compiler package."""
        from floe_core.compiler import ResolvedPlatformProfiles

        assert ResolvedPlatformProfiles is not None

    def test_resolved_platform_profiles_required_fields(self) -> None:
        """Test ResolvedPlatformProfiles requires storage, catalog, compute."""
        from floe_core.compiler import ResolvedPlatformProfiles

        with pytest.raises(ValidationError) as exc_info:
            ResolvedPlatformProfiles()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        field_names = {e["loc"][0] for e in errors}
        assert "storage" in field_names
        assert "catalog" in field_names
        assert "compute" in field_names

    def test_resolved_platform_profiles_valid_creation(
        self,
        sample_resolved_profiles: dict,
    ) -> None:
        """Test ResolvedPlatformProfiles with valid fields."""
        from floe_core.compiler import ResolvedPlatformProfiles

        profiles = ResolvedPlatformProfiles(**sample_resolved_profiles)

        assert profiles.storage is not None
        assert profiles.catalog is not None
        assert profiles.compute is not None
        assert profiles.platform_env == "local"

    def test_resolved_platform_profiles_default_env(
        self,
        sample_storage_profile: dict,
        sample_catalog_profile: dict,
        sample_compute_profile: dict,
    ) -> None:
        """Test ResolvedPlatformProfiles has default platform_env."""
        from floe_core.compiler import ResolvedPlatformProfiles

        profiles = ResolvedPlatformProfiles(
            storage=sample_storage_profile,
            catalog=sample_catalog_profile,
            compute=sample_compute_profile,
        )

        assert profiles.platform_env == "local"

    def test_resolved_platform_profiles_custom_env(
        self,
        sample_storage_profile: dict,
        sample_catalog_profile: dict,
        sample_compute_profile: dict,
    ) -> None:
        """Test ResolvedPlatformProfiles with custom platform_env."""
        from floe_core.compiler import ResolvedPlatformProfiles

        profiles = ResolvedPlatformProfiles(
            storage=sample_storage_profile,
            catalog=sample_catalog_profile,
            compute=sample_compute_profile,
            platform_env="production",
        )

        assert profiles.platform_env == "production"

    def test_resolved_platform_profiles_immutable(
        self,
        sample_resolved_profiles: dict,
    ) -> None:
        """Test ResolvedPlatformProfiles is frozen (immutable)."""
        from floe_core.compiler import ResolvedPlatformProfiles

        profiles = ResolvedPlatformProfiles(**sample_resolved_profiles)

        with pytest.raises(ValidationError):
            profiles.platform_env = "production"  # type: ignore[misc]

    def test_resolved_platform_profiles_extra_forbid(
        self,
        sample_storage_profile: dict,
        sample_catalog_profile: dict,
        sample_compute_profile: dict,
    ) -> None:
        """Test ResolvedPlatformProfiles rejects unknown fields."""
        from floe_core.compiler import ResolvedPlatformProfiles

        with pytest.raises(ValidationError) as exc_info:
            ResolvedPlatformProfiles(
                storage=sample_storage_profile,
                catalog=sample_catalog_profile,
                compute=sample_compute_profile,
                unknown_field="should_fail",
            )

        assert "extra_forbidden" in str(exc_info.value)

    def test_resolved_platform_profiles_json_round_trip(
        self,
        sample_resolved_profiles: dict,
    ) -> None:
        """Test JSON round-trip preserves all data."""
        from floe_core.compiler import ResolvedPlatformProfiles

        original = ResolvedPlatformProfiles(**sample_resolved_profiles)

        json_str = original.model_dump_json()
        loaded = ResolvedPlatformProfiles.model_validate_json(json_str)

        assert original.model_dump() == loaded.model_dump()


class TestCompiledArtifactsWithResolvedProfiles:
    """T024: Tests for CompiledArtifacts v2.0 with resolved_profiles."""

    def test_compiled_artifacts_optional_resolved_profiles(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test resolved_profiles is optional for backward compatibility."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
        )

        assert artifacts.resolved_profiles is None

    def test_compiled_artifacts_with_resolved_profiles(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
        sample_resolved_profiles: dict,
    ) -> None:
        """Test CompiledArtifacts with resolved_profiles."""
        from floe_core.compiler import CompiledArtifacts

        artifacts = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
            resolved_profiles=sample_resolved_profiles,
        )

        assert artifacts.resolved_profiles is not None
        assert artifacts.resolved_profiles.platform_env == "local"
        assert artifacts.resolved_profiles.storage.bucket == "my-data-bucket"
        assert artifacts.resolved_profiles.catalog.uri == "http://polaris:8181/api/catalog"

    def test_compiled_artifacts_resolved_profiles_json_round_trip(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
        sample_resolved_profiles: dict,
    ) -> None:
        """Test JSON round-trip with resolved_profiles."""
        from floe_core.compiler import CompiledArtifacts

        original = CompiledArtifacts(
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
            resolved_profiles=sample_resolved_profiles,
        )

        json_str = original.model_dump_json()
        loaded = CompiledArtifacts.model_validate_json(json_str)

        assert original.model_dump() == loaded.model_dump()
        assert loaded.resolved_profiles is not None
        assert loaded.resolved_profiles.platform_env == "local"

    def test_compiled_artifacts_backward_compatibility(
        self,
        sample_artifact_metadata: dict,
        sample_compute_config: dict,
        sample_transform_config: dict,
    ) -> None:
        """Test v1.0 artifacts (no resolved_profiles) still work."""
        from floe_core.compiler import CompiledArtifacts

        # Create artifacts without resolved_profiles (v1.0 style)
        v1_artifacts = CompiledArtifacts(
            version="1.0.0",
            metadata=sample_artifact_metadata,
            compute=sample_compute_config,
            transforms=[sample_transform_config],
        )

        # v1.0 artifacts should work and have None resolved_profiles
        assert v1_artifacts.version == "1.0.0"
        assert v1_artifacts.resolved_profiles is None

        # JSON round-trip should work
        json_str = v1_artifacts.model_dump_json()
        loaded = CompiledArtifacts.model_validate_json(json_str)
        assert loaded.resolved_profiles is None
