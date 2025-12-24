"""Unit tests for platform specification models.

This module tests:
- PlatformSpec parsing and validation
- Profile name validation
- from_yaml loading
- Profile getter methods
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from floe_core.schemas.catalog_profile import CatalogProfile
from floe_core.schemas.compute_profile import ComputeProfile
from floe_core.schemas.observability import ObservabilityConfig
from floe_core.schemas.platform_spec import (
    ENVIRONMENT_TYPES,
    PLATFORM_SPEC_VERSION,
    PROFILE_NAME_PATTERN,
    PlatformSpec,
)
from floe_core.schemas.storage_profile import StorageProfile


class TestPlatformSpecConstants:
    """Tests for PlatformSpec module constants."""

    def test_environment_types_defined(self) -> None:
        """Verify environment types are defined."""
        assert ENVIRONMENT_TYPES is not None
        assert "local" in ENVIRONMENT_TYPES
        assert "dev" in ENVIRONMENT_TYPES
        assert "staging" in ENVIRONMENT_TYPES
        assert "prod" in ENVIRONMENT_TYPES
        assert len(ENVIRONMENT_TYPES) == 4

    def test_platform_spec_version(self) -> None:
        """Verify platform spec version is set."""
        assert PLATFORM_SPEC_VERSION == "1.1.0"

    def test_profile_name_pattern(self) -> None:
        """Verify profile name pattern is defined."""
        import re

        # Valid names
        assert re.match(PROFILE_NAME_PATTERN, "default")
        assert re.match(PROFILE_NAME_PATTERN, "my-profile")
        assert re.match(PROFILE_NAME_PATTERN, "profile_name")
        assert re.match(PROFILE_NAME_PATTERN, "myProfile123")
        # Invalid names
        assert not re.match(PROFILE_NAME_PATTERN, "123invalid")
        assert not re.match(PROFILE_NAME_PATTERN, "-invalid")
        assert not re.match(PROFILE_NAME_PATTERN, "_invalid")


class TestPlatformSpecCreation:
    """Tests for PlatformSpec creation."""

    def test_empty_spec_valid(self) -> None:
        """Empty PlatformSpec is valid (all fields optional)."""
        spec = PlatformSpec()
        assert spec.version == PLATFORM_SPEC_VERSION
        assert spec.storage == {}
        assert spec.catalogs == {}
        assert spec.compute == {}
        assert spec.observability is None

    def test_spec_with_storage_profile(self) -> None:
        """PlatformSpec accepts storage profiles."""
        spec = PlatformSpec(
            storage={"default": StorageProfile(bucket="iceberg-data")},
        )
        assert "default" in spec.storage
        assert spec.storage["default"].bucket == "iceberg-data"

    def test_spec_with_catalog_profile(self) -> None:
        """PlatformSpec accepts catalog profiles."""
        spec = PlatformSpec(
            catalogs={
                "default": CatalogProfile(
                    uri="http://polaris:8181/api/catalog",
                    warehouse="demo",
                )
            },
        )
        assert "default" in spec.catalogs
        assert spec.catalogs["default"].warehouse == "demo"

    def test_spec_with_compute_profile(self) -> None:
        """PlatformSpec accepts compute profiles."""
        spec = PlatformSpec(
            compute={"default": ComputeProfile()},
        )
        assert "default" in spec.compute

    def test_spec_is_frozen(self) -> None:
        """PlatformSpec is immutable."""
        spec = PlatformSpec()
        with pytest.raises(ValidationError):
            spec.version = "2.0.0"

    def test_spec_rejects_extra_fields(self) -> None:
        """PlatformSpec rejects unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            PlatformSpec(unknown_field="value")  # type: ignore[call-arg]
        assert "unknown_field" in str(exc_info.value)


class TestPlatformSpecVersionValidation:
    """Tests for PlatformSpec version validation."""

    def test_valid_semver(self) -> None:
        """Valid semver versions are accepted."""
        spec = PlatformSpec(version="1.0.0")
        assert spec.version == "1.0.0"

        spec = PlatformSpec(version="2.10.3")
        assert spec.version == "2.10.3"

    def test_invalid_version_format(self) -> None:
        """Invalid version formats are rejected."""
        with pytest.raises(ValidationError):
            PlatformSpec(version="1.0")

        with pytest.raises(ValidationError):
            PlatformSpec(version="v1.0.0")

        with pytest.raises(ValidationError):
            PlatformSpec(version="invalid")


class TestPlatformSpecProfileNameValidation:
    """Tests for profile name validation."""

    def test_valid_profile_names(self) -> None:
        """Valid profile names are accepted."""
        spec = PlatformSpec(
            storage={
                "default": StorageProfile(bucket="bucket1"),
                "production": StorageProfile(bucket="bucket2"),
                "my-profile": StorageProfile(bucket="bucket3"),
                "profile_name": StorageProfile(bucket="bucket4"),
            },
        )
        assert len(spec.storage) == 4

    def test_invalid_profile_name_rejected(self) -> None:
        """Invalid profile names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PlatformSpec(
                storage={"123-invalid": StorageProfile(bucket="bucket")},
            )
        assert "123-invalid" in str(exc_info.value)

    def test_profile_name_starting_with_hyphen_rejected(self) -> None:
        """Profile names starting with hyphen are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PlatformSpec(
                catalogs={
                    "-invalid": CatalogProfile(
                        uri="http://example.com",
                        warehouse="demo",
                    )
                },
            )
        assert "-invalid" in str(exc_info.value)


class TestPlatformSpecFromYaml:
    """Tests for PlatformSpec.from_yaml method."""

    def test_from_yaml_valid_file(self) -> None:
        """from_yaml loads valid YAML file."""
        yaml_content = """
version: "1.0.0"
storage:
  default:
    type: s3
    bucket: iceberg-data
    region: us-east-1
catalogs:
  default:
    type: polaris
    uri: http://polaris:8181/api/catalog
    warehouse: demo
"""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml_content)
            f.flush()
            spec = PlatformSpec.from_yaml(Path(f.name))

        assert spec.version == "1.0.0"
        assert "default" in spec.storage
        assert spec.storage["default"].bucket == "iceberg-data"
        assert "default" in spec.catalogs
        assert spec.catalogs["default"].warehouse == "demo"

    def test_from_yaml_empty_file(self) -> None:
        """from_yaml handles empty YAML file."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write("")
            f.flush()
            spec = PlatformSpec.from_yaml(Path(f.name))

        assert spec.version == PLATFORM_SPEC_VERSION
        assert spec.storage == {}

    def test_from_yaml_file_not_found(self) -> None:
        """from_yaml raises error for missing file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            PlatformSpec.from_yaml(Path("/nonexistent/path.yaml"))
        assert "Platform spec not found" in str(exc_info.value)

    def test_from_yaml_invalid_content(self) -> None:
        """from_yaml raises error for invalid YAML content."""
        yaml_content = """
version: "invalid-version"
"""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml_content)
            f.flush()

        with pytest.raises(ValidationError):
            PlatformSpec.from_yaml(Path(f.name))


class TestPlatformSpecGetterMethods:
    """Tests for PlatformSpec getter methods."""

    @pytest.fixture
    def spec_with_profiles(self) -> PlatformSpec:
        """Create PlatformSpec with all profile types."""
        return PlatformSpec(
            storage={
                "default": StorageProfile(bucket="default-bucket"),
                "production": StorageProfile(bucket="prod-bucket"),
            },
            catalogs={
                "default": CatalogProfile(
                    uri="http://polaris:8181/api/catalog",
                    warehouse="demo",
                ),
                "production": CatalogProfile(
                    uri="http://polaris-prod:8181/api/catalog",
                    warehouse="production",
                ),
            },
            compute={
                "default": ComputeProfile(),
                "snowflake": ComputeProfile(
                    properties={"account": "acme.us-east-1"},
                ),
            },
        )

    def test_get_storage_profile_default(self, spec_with_profiles: PlatformSpec) -> None:
        """get_storage_profile returns default profile."""
        profile = spec_with_profiles.get_storage_profile()
        assert profile.bucket == "default-bucket"

    def test_get_storage_profile_named(self, spec_with_profiles: PlatformSpec) -> None:
        """get_storage_profile returns named profile."""
        profile = spec_with_profiles.get_storage_profile("production")
        assert profile.bucket == "prod-bucket"

    def test_get_storage_profile_not_found(self, spec_with_profiles: PlatformSpec) -> None:
        """get_storage_profile raises error for missing profile."""
        with pytest.raises(KeyError) as exc_info:
            spec_with_profiles.get_storage_profile("nonexistent")
        assert "nonexistent" in str(exc_info.value)
        assert "Available profiles" in str(exc_info.value)

    def test_get_catalog_profile_default(self, spec_with_profiles: PlatformSpec) -> None:
        """get_catalog_profile returns default profile."""
        profile = spec_with_profiles.get_catalog_profile()
        assert profile.warehouse == "demo"

    def test_get_catalog_profile_named(self, spec_with_profiles: PlatformSpec) -> None:
        """get_catalog_profile returns named profile."""
        profile = spec_with_profiles.get_catalog_profile("production")
        assert profile.warehouse == "production"

    def test_get_catalog_profile_not_found(self, spec_with_profiles: PlatformSpec) -> None:
        """get_catalog_profile raises error for missing profile."""
        with pytest.raises(KeyError) as exc_info:
            spec_with_profiles.get_catalog_profile("nonexistent")
        assert "nonexistent" in str(exc_info.value)

    def test_get_compute_profile_default(self, spec_with_profiles: PlatformSpec) -> None:
        """get_compute_profile returns default profile."""
        profile = spec_with_profiles.get_compute_profile()
        assert profile is not None

    def test_get_compute_profile_named(self, spec_with_profiles: PlatformSpec) -> None:
        """get_compute_profile returns named profile."""
        profile = spec_with_profiles.get_compute_profile("snowflake")
        assert "account" in profile.properties

    def test_get_compute_profile_not_found(self, spec_with_profiles: PlatformSpec) -> None:
        """get_compute_profile raises error for missing profile."""
        with pytest.raises(KeyError) as exc_info:
            spec_with_profiles.get_compute_profile("nonexistent")
        assert "nonexistent" in str(exc_info.value)


class TestPlatformSpecWithObservability:
    """Tests for PlatformSpec with observability configuration."""

    def test_spec_with_observability(self) -> None:
        """PlatformSpec accepts observability config."""
        spec = PlatformSpec(
            observability=ObservabilityConfig(
                traces=True,
                metrics=True,
                lineage=True,
                otlp_endpoint="http://jaeger:4317",
                lineage_endpoint="http://marquez:5000",
            ),
        )
        assert spec.observability is not None
        assert spec.observability.traces is True
        assert spec.observability.otlp_endpoint == "http://jaeger:4317"
        assert spec.observability.lineage_endpoint == "http://marquez:5000"

    def test_spec_with_observability_attributes(self) -> None:
        """PlatformSpec observability accepts custom attributes."""
        spec = PlatformSpec(
            observability=ObservabilityConfig(
                traces=True,
                attributes={
                    "service.name": "floe-local",
                    "deployment.environment": "local",
                },
            ),
        )
        assert spec.observability is not None
        assert spec.observability.attributes["service.name"] == "floe-local"

    def test_spec_without_observability(self) -> None:
        """PlatformSpec works without observability config."""
        spec = PlatformSpec()
        assert spec.observability is None

    def test_observability_is_frozen(self) -> None:
        """Observability config is immutable."""
        spec = PlatformSpec(
            observability=ObservabilityConfig(traces=True),
        )
        with pytest.raises(ValidationError):
            spec.observability.traces = False  # type: ignore[union-attr]


class TestPlatformSpecCompleteConfig:
    """Tests for complete PlatformSpec configurations."""

    def test_complete_local_config(self) -> None:
        """Complete local development configuration."""
        yaml_content = """
version: "1.0.0"
storage:
  default:
    type: s3
    endpoint: "http://minio:9000"
    region: us-east-1
    bucket: iceberg-data
    path_style_access: true
    credentials:
      mode: static
      secret_ref: minio-credentials
catalogs:
  default:
    type: polaris
    uri: http://polaris:8181/api/catalog
    warehouse: demo
    namespace: default
    credentials:
      mode: oauth2
      client_id: root
      client_secret:
        secret_ref: polaris-client-secret
      scope: "PRINCIPAL_ROLE:ALL"
    access_delegation: vended-credentials
compute:
  default:
    type: duckdb
    properties:
      path: ":memory:"
      threads: 4
observability:
  traces: true
  metrics: true
  lineage: true
  otlp_endpoint: http://jaeger:4317
  lineage_endpoint: http://marquez:5000
  attributes:
    service.name: floe-local
    deployment.environment: local
"""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml_content)
            f.flush()
            spec = PlatformSpec.from_yaml(Path(f.name))

        # Verify storage profile
        assert "default" in spec.storage
        storage = spec.storage["default"]
        assert storage.bucket == "iceberg-data"
        assert storage.path_style_access is True
        assert storage.credentials.mode.value == "static"

        # Verify catalog profile
        assert "default" in spec.catalogs
        catalog = spec.catalogs["default"]
        assert catalog.warehouse == "demo"
        assert catalog.credentials.mode.value == "oauth2"
        assert catalog.credentials.scope == "PRINCIPAL_ROLE:ALL"

        # Verify compute profile
        assert "default" in spec.compute
        compute = spec.compute["default"]
        assert compute.properties["path"] == ":memory:"

        # Verify observability
        assert spec.observability is not None
        assert spec.observability.traces is True
        assert spec.observability.attributes["service.name"] == "floe-local"

    def test_multi_profile_config(self) -> None:
        """Config with multiple named profiles."""
        yaml_content = """
version: "1.0.0"
storage:
  default:
    bucket: dev-bucket
    region: us-east-1
  production:
    bucket: prod-bucket
    region: us-west-2
catalogs:
  default:
    uri: http://polaris:8181/api/catalog
    warehouse: dev
  analytics:
    uri: http://polaris:8181/api/catalog
    warehouse: analytics
compute:
  default:
    type: duckdb
  snowflake:
    type: snowflake
    properties:
      account: acme.us-east-1
      warehouse: ANALYTICS_WH
"""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write(yaml_content)
            f.flush()
            spec = PlatformSpec.from_yaml(Path(f.name))

        # Verify multiple storage profiles
        assert len(spec.storage) == 2
        assert spec.get_storage_profile("default").bucket == "dev-bucket"
        assert spec.get_storage_profile("production").bucket == "prod-bucket"

        # Verify multiple catalog profiles
        assert len(spec.catalogs) == 2
        assert spec.get_catalog_profile("default").warehouse == "dev"
        assert spec.get_catalog_profile("analytics").warehouse == "analytics"

        # Verify multiple compute profiles
        assert len(spec.compute) == 2
        assert spec.get_compute_profile("snowflake").properties["account"] == "acme.us-east-1"


class TestPlatformSpecValidationErrors:
    """Tests for PlatformSpec validation error messages."""

    def test_invalid_storage_bucket_too_short(self) -> None:
        """Storage bucket name too short triggers error."""
        with pytest.raises(ValidationError) as exc_info:
            PlatformSpec(
                storage={"default": StorageProfile(bucket="ab")},  # Min is 3
            )
        assert "bucket" in str(exc_info.value).lower() or "string" in str(exc_info.value).lower()

    def test_invalid_catalog_warehouse_empty(self) -> None:
        """Catalog warehouse cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            PlatformSpec(
                catalogs={
                    "default": CatalogProfile(
                        uri="http://example.com",
                        warehouse="",  # Empty not allowed
                    )
                },
            )
        assert "warehouse" in str(exc_info.value).lower() or "string" in str(exc_info.value).lower()

    def test_invalid_observability_extra_field(self) -> None:
        """Observability rejects extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            ObservabilityConfig(
                traces=True,
                unknown_field="value",  # type: ignore[call-arg]  # Extra field
            )
        assert "unknown_field" in str(exc_info.value)

    def test_profile_name_with_special_chars(self) -> None:
        """Profile names with special characters are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PlatformSpec(
                storage={"invalid@profile": StorageProfile(bucket="bucket")},
            )
        assert "invalid@profile" in str(exc_info.value)

    def test_catalog_missing_required_fields(self) -> None:
        """Catalog profile requires uri and warehouse."""
        with pytest.raises(ValidationError):
            # Missing required fields - CatalogProfile requires uri and warehouse
            CatalogProfile()  # type: ignore[call-arg]
