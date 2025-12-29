"""Unit tests for DbtProfilesGenerator.

This module tests:
- dbt profiles.yml generation from FloeSpec + PlatformSpec
- DuckDB output configuration with Iceberg extension
- ATTACH configuration for Polaris catalog
- Polaris plugin configuration for external materialization
- Environment variable interpolation in generated profiles
"""

from __future__ import annotations

import pytest
from floe_core.schemas.credentials import CredentialsConfig, OAuth2Credentials

from floe_core.compiler.dbt_profiles_generator import DbtProfilesGenerator
from floe_core.schemas.catalog_profile import CatalogProfile, CatalogType
from floe_core.schemas.compute_profile import ComputeProfile
from floe_core.schemas.floe_spec import FloeSpec
from floe_core.schemas.platform_spec import PlatformSpec
from floe_core.schemas.storage_profile import StorageProfile, StorageType


@pytest.fixture
def polaris_catalog_profile() -> CatalogProfile:
    """Create a Polaris catalog profile for testing."""
    return CatalogProfile(
        type=CatalogType.POLARIS,
        uri="http://polaris:8181/api/catalog",
        warehouse="demo_catalog",
        credentials=CredentialsConfig(
            mode="oauth2",
            oauth2=OAuth2Credentials(
                client_id="test_client",
                client_secret="test_secret",
                scope="PRINCIPAL_ROLE:demo_service",
            ),
        ),
    )


@pytest.fixture
def s3_storage_profile() -> StorageProfile:
    """Create an S3 storage profile for testing."""
    return StorageProfile(
        type=StorageType.S3,
        endpoint="http://localstack:4566",
        region="us-east-1",
        access_key_id="test",
        secret_access_key="test",
    )


@pytest.fixture
def duckdb_compute_profile() -> ComputeProfile:
    """Create a DuckDB compute profile for testing."""
    return ComputeProfile(
        adapter="duckdb",
        database=":memory:",
        threads=4,
    )


@pytest.fixture
def platform_spec(
    polaris_catalog_profile: CatalogProfile,
    s3_storage_profile: StorageProfile,
    duckdb_compute_profile: ComputeProfile,
) -> PlatformSpec:
    """Create a PlatformSpec with default profiles."""
    return PlatformSpec(
        storage={
            "default": s3_storage_profile,
        },
        catalogs={
            "default": polaris_catalog_profile,
        },
        compute={
            "default": duckdb_compute_profile,
        },
    )


@pytest.fixture
def floe_spec() -> FloeSpec:
    """Create a minimal FloeSpec for testing."""
    return FloeSpec(
        name="test-project",
        version="1.0.0",
        storage="default",
        catalog="default",
        compute="default",
    )


@pytest.fixture
def generator(floe_spec: FloeSpec, platform_spec: PlatformSpec) -> DbtProfilesGenerator:
    """Create a DbtProfilesGenerator for testing."""
    return DbtProfilesGenerator(floe=floe_spec, platform=platform_spec)


class TestDbtProfilesGeneratorInit:
    """Tests for DbtProfilesGenerator initialization."""

    def test_init_with_valid_specs(self, floe_spec: FloeSpec, platform_spec: PlatformSpec) -> None:
        """Verify generator initializes with valid specs."""
        generator = DbtProfilesGenerator(floe=floe_spec, platform=platform_spec)
        assert generator.floe == floe_spec
        assert generator.platform == platform_spec

    def test_init_stores_floe_spec(self, generator: DbtProfilesGenerator) -> None:
        """Verify FloeSpec is stored correctly."""
        assert generator.floe.name == "test-project"
        assert generator.floe.version == "1.0.0"

    def test_init_stores_platform_spec(self, generator: DbtProfilesGenerator) -> None:
        """Verify PlatformSpec is stored correctly."""
        assert "default" in generator.platform.storage
        assert "default" in generator.platform.catalogs
        assert "default" in generator.platform.compute


class TestGenerateProfiles:
    """Tests for generate_profiles method."""

    def test_generates_valid_profiles_structure(self, generator: DbtProfilesGenerator) -> None:
        """Verify generated profiles have correct structure."""
        profiles = generator.generate_profiles()

        assert "test_project" in profiles
        project_config = profiles["test_project"]
        assert "target" in project_config
        assert "outputs" in project_config
        assert project_config["target"] == "dev"

    def test_output_contains_duckdb_config(self, generator: DbtProfilesGenerator) -> None:
        """Verify output contains DuckDB configuration."""
        profiles = generator.generate_profiles()
        output = profiles["test_project"]["outputs"]["dev"]

        assert output["type"] == "duckdb"
        assert output["path"] == ":memory:"
        assert output["threads"] == 4

    def test_output_contains_iceberg_extension(self, generator: DbtProfilesGenerator) -> None:
        """Verify output includes Iceberg and httpfs extensions."""
        profiles = generator.generate_profiles()
        output = profiles["test_project"]["outputs"]["dev"]

        assert "extensions" in output
        assert "iceberg" in output["extensions"]
        assert "httpfs" in output["extensions"]

    def test_output_no_persistent_secrets_setting(self, generator: DbtProfilesGenerator) -> None:
        """Verify output does not include persistent secrets setting.

        This prevents DuckDB secret manager conflicts during ATTACH operations.
        """
        profiles = generator.generate_profiles()
        output = profiles["test_project"]["outputs"]["dev"]

        # No settings section should be present since allow_persistent_secrets is removed
        # to prevent "Changing Secret Manager settings after the secret manager is used" error
        assert "settings" not in output


class TestBuildAttachConfig:
    """Tests for _build_attach_config method."""

    def test_attach_config_for_polaris_catalog(
        self,
        generator: DbtProfilesGenerator,
        polaris_catalog_profile: CatalogProfile,
        s3_storage_profile: StorageProfile,
    ) -> None:
        """Verify ATTACH configuration for Polaris catalog."""
        attach = generator._build_attach_config(polaris_catalog_profile, s3_storage_profile)

        assert attach is not None
        assert attach["alias"] == "polaris_catalog"
        assert attach["type"] == "iceberg"
        assert "demo_catalog" in attach["catalog"]

    def test_attach_config_uses_env_var_interpolation(
        self,
        generator: DbtProfilesGenerator,
        polaris_catalog_profile: CatalogProfile,
        s3_storage_profile: StorageProfile,
    ) -> None:
        """Verify ATTACH config uses environment variable interpolation."""
        attach = generator._build_attach_config(polaris_catalog_profile, s3_storage_profile)

        assert attach is not None
        assert "{{ env_var(" in attach["catalog"]
        assert "FLOE_CATALOG_WAREHOUSE" in attach["catalog"]

    def test_attach_config_returns_none_for_non_polaris(
        self,
        generator: DbtProfilesGenerator,
        s3_storage_profile: StorageProfile,
    ) -> None:
        """Verify ATTACH config returns None for non-Polaris catalogs."""
        glue_catalog = CatalogProfile(
            type=CatalogType.GLUE,
            uri="https://glue.us-east-1.amazonaws.com",
            warehouse="my_database",
        )

        attach = generator._build_attach_config(glue_catalog, s3_storage_profile)
        assert attach is None


class TestBuildPolarisPluginConfig:
    """Tests for _build_polaris_plugin_config method."""

    def test_plugin_config_for_polaris_catalog(
        self,
        generator: DbtProfilesGenerator,
        polaris_catalog_profile: CatalogProfile,
        s3_storage_profile: StorageProfile,
    ) -> None:
        """Verify Polaris plugin configuration."""
        plugin = generator._build_polaris_plugin_config(polaris_catalog_profile, s3_storage_profile)

        assert plugin is not None
        assert "catalog_uri" in plugin
        assert "warehouse" in plugin
        assert "client_id" in plugin
        assert "client_secret" in plugin

    def test_plugin_uses_env_var_interpolation(
        self,
        generator: DbtProfilesGenerator,
        polaris_catalog_profile: CatalogProfile,
        s3_storage_profile: StorageProfile,
    ) -> None:
        """Verify plugin config uses env var interpolation."""
        plugin = generator._build_polaris_plugin_config(polaris_catalog_profile, s3_storage_profile)

        assert plugin is not None
        assert "{{ env_var(" in plugin["catalog_uri"]
        assert "{{ env_var(" in plugin["client_id"]
        assert "{{ env_var(" in plugin["s3_endpoint"]

    def test_plugin_includes_storage_config(
        self,
        generator: DbtProfilesGenerator,
        polaris_catalog_profile: CatalogProfile,
        s3_storage_profile: StorageProfile,
    ) -> None:
        """Verify plugin includes S3 storage configuration."""
        plugin = generator._build_polaris_plugin_config(polaris_catalog_profile, s3_storage_profile)

        assert plugin is not None
        assert "s3_endpoint" in plugin
        assert "s3_region" in plugin
        assert "s3_access_key_id" in plugin
        assert "s3_secret_access_key" in plugin

    def test_plugin_returns_none_for_non_polaris(
        self,
        generator: DbtProfilesGenerator,
        s3_storage_profile: StorageProfile,
    ) -> None:
        """Verify plugin config returns None for non-Polaris catalogs."""
        glue_catalog = CatalogProfile(
            type=CatalogType.GLUE,
            uri="https://glue.us-east-1.amazonaws.com",
            warehouse="my_database",
        )

        plugin = generator._build_polaris_plugin_config(glue_catalog, s3_storage_profile)
        assert plugin is None


class TestProfilesOutputIntegration:
    """Integration tests for complete profiles output."""

    def test_full_profiles_with_attach_and_plugin(self, generator: DbtProfilesGenerator) -> None:
        """Verify complete profiles include both ATTACH and plugin configs."""
        profiles = generator.generate_profiles()
        output = profiles["test_project"]["outputs"]["dev"]

        assert "attach" in output
        assert "plugins" in output
        assert len(output["attach"]) == 1
        assert len(output["plugins"]) == 1

    def test_attach_and_plugin_have_consistent_config(
        self, generator: DbtProfilesGenerator
    ) -> None:
        """Verify ATTACH and plugin configs reference same warehouse."""
        profiles = generator.generate_profiles()
        output = profiles["test_project"]["outputs"]["dev"]

        attach_catalog = output["attach"][0]["catalog"]
        plugin_warehouse = output["plugins"][0]["config"]["warehouse"]

        assert "demo_catalog" in attach_catalog
        assert "demo_catalog" in plugin_warehouse
