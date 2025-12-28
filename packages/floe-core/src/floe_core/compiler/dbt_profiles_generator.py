"""dbt profiles.yml generator for floe-runtime.

This module generates dbt profiles.yml from PlatformSpec configuration,
enabling Two-Tier Architecture where platform.yaml is the single source
of truth for infrastructure configuration.

Key Features:
    - Generate adapter-specific profiles (duckdb, snowflake, bigquery, etc.)
    - Configure dbt-duckdb plugin for external materializations
    - Use environment variable interpolation for secret_ref patterns
    - Support multiple compute targets from same platform.yaml

Example:
    >>> from floe_core.compiler import DbtProfilesGenerator, PlatformResolver
    >>> from floe_core.schemas import FloeSpec
    >>>
    >>> platform = PlatformResolver().load()
    >>> floe = FloeSpec.from_yaml("floe.yaml")
    >>> generator = DbtProfilesGenerator(platform, floe)
    >>>
    >>> profiles = generator.generate_profiles()
    >>> generator.write_profiles_yml(Path("profiles.yml"), profiles)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from floe_core.schemas.catalog_profile import CatalogProfile
    from floe_core.schemas.compute_profile import ComputeProfile
    from floe_core.schemas.floe_spec import FloeSpec
    from floe_core.schemas.platform_spec import PlatformSpec
    from floe_core.schemas.storage_profile import StorageProfile

logger = logging.getLogger(__name__)


class DbtProfilesGenerator:
    """Generate dbt profiles.yml from PlatformSpec + FloeSpec.

    DbtProfilesGenerator transforms platform.yaml infrastructure configuration
    into dbt-compatible profiles.yml, eliminating the need for custom demo-specific
    infrastructure code.

    Architecture:
        - Reads CatalogProfile, StorageProfile, ComputeProfile from platform.yaml
        - Generates adapter-specific output configurations
        - Configures dbt-duckdb plugin for Iceberg external materializations
        - Uses env var interpolation ({{ env_var('VAR') }}) for secret_ref fields

    Supported Adapters:
        - duckdb (with Polaris/Iceberg plugin)
        - snowflake (future)
        - bigquery (future)
        - databricks (future)

    Example:
        >>> generator = DbtProfilesGenerator(platform, floe)
        >>> profiles = generator.generate_profiles(profile_name="default")
        >>> generator.write_profiles_yml(Path("demo/profiles.yml"), profiles)
    """

    def __init__(self, platform: PlatformSpec, floe: FloeSpec) -> None:
        """Initialize the DbtProfilesGenerator.

        Args:
            platform: PlatformSpec containing infrastructure configuration.
            floe: FloeSpec containing pipeline and orchestration configuration.
        """
        self.platform = platform
        self.floe = floe

    def generate_profiles(
        self,
        profile_name: str = "default",
        target_name: str = "dev",
    ) -> dict[str, Any]:
        """Generate complete dbt profiles.yml structure.

        Args:
            profile_name: Name of platform profile to use (default: "default").
            target_name: dbt target name (default: "dev").

        Returns:
            Dictionary representing complete profiles.yml structure.

        Raises:
            ValueError: If required profiles not found in platform.yaml.

        Example:
            >>> profiles = generator.generate_profiles()
            >>> # profiles = {
            >>> #   "demo": {
            >>> #     "target": "dev",
            >>> #     "outputs": {
            >>> #       "dev": {
            >>> #         "type": "duckdb",
            >>> #         "path": ":memory:",
            >>> #         ...
            >>> #       }
            >>> #     }
            >>> #   }
            >>> # }
        """
        try:
            catalog = self.platform.get_catalog_profile(profile_name)
            storage = self.platform.get_storage_profile(profile_name)
            compute = self.platform.get_compute_profile(profile_name)
        except KeyError as e:
            raise ValueError(f"Profile '{profile_name}' not found in platform.yaml: {e}") from e

        adapter_type = self._detect_adapter_type(compute)

        if adapter_type == "duckdb":
            output_config = self._build_duckdb_output(catalog, storage, compute)
        else:
            raise NotImplementedError(
                f"Adapter type '{adapter_type}' not yet supported. "
                "Only 'duckdb' is currently implemented."
            )

        project_name = self.floe.name.replace("-", "_")

        return {
            project_name: {
                "target": target_name,
                "outputs": {target_name: output_config},
            }
        }

    def _detect_adapter_type(self, compute: ComputeProfile) -> str:
        """Detect dbt adapter type from ComputeProfile.

        Args:
            compute: ComputeProfile to inspect.

        Returns:
            Adapter type string (e.g., "duckdb", "snowflake").
        """
        if hasattr(compute, "adapter"):
            return compute.adapter.lower()

        type_str = str(type(compute).__name__).lower()
        if "duckdb" in type_str:
            return "duckdb"
        elif "snowflake" in type_str:
            return "snowflake"
        elif "bigquery" in type_str:
            return "bigquery"
        else:
            return "duckdb"

    def _build_duckdb_output(
        self,
        catalog: CatalogProfile,
        storage: StorageProfile,
        compute: ComputeProfile,
    ) -> dict[str, Any]:
        """Build dbt-duckdb output configuration with Iceberg extension support.

        Configures DuckDB with:
        - Iceberg extension for catalog-native table access
        - httpfs extension for S3 connectivity
        - ATTACH configuration for Polaris REST catalog
        - Platform mappings injected as dbt vars for native Iceberg writes

        Args:
            catalog: CatalogProfile for Iceberg catalog configuration.
            storage: StorageProfile for S3/storage configuration.
            compute: ComputeProfile for compute-specific settings.

        Returns:
            dbt output configuration dictionary with extensions and attach config.
        """
        threads = getattr(compute, "threads", 4)
        database_path = getattr(compute, "database", ":memory:")

        output: dict[str, Any] = {
            "type": "duckdb",
            "path": database_path,
            "threads": threads,
            "extensions": ["iceberg", "httpfs"],
            "settings": {
                "allow_persistent_secrets": "true",
            },
        }

        catalog_mappings = self._build_catalog_mappings(catalog)
        storage_mappings = self._build_storage_mapping()

        if catalog_mappings or storage_mappings:
            output["vars"] = {}
            if catalog_mappings:
                output["vars"]["floe_catalog_mappings"] = catalog_mappings
            if storage_mappings:
                output["vars"]["floe_storage_mappings"] = storage_mappings

        # ATTACH is handled by plugin.configure_connection() - no profiles.yml config needed
        # attach_config = self._build_attach_config(catalog, storage)
        # if attach_config:
        #     output["attach"] = [attach_config]

        plugin_config = self._build_polaris_plugin_config(catalog, storage)
        if plugin_config:
            output["plugins"] = [
                {
                    "module": "floe_dbt.plugins.polaris",
                    "config": plugin_config,
                }
            ]

        return output

    def _build_attach_config(
        self,
        catalog: CatalogProfile,
        storage: StorageProfile,
    ) -> dict[str, Any] | None:
        """Build DuckDB ATTACH configuration for Iceberg REST catalog.

        Generates configuration for DuckDB to attach an Iceberg catalog
        at session startup. Uses environment variable interpolation for
        credentials and endpoints.

        The ATTACH configuration allows dbt models to reference tables via:
            polaris_catalog.namespace.table_name

        Args:
            catalog: CatalogProfile containing catalog endpoint and warehouse.
            storage: StorageProfile containing S3 configuration.

        Returns:
            ATTACH configuration dict, or None if not Polaris catalog.
        """
        from floe_core.schemas.catalog_profile import CatalogType

        if catalog.type != CatalogType.POLARIS:
            logger.info(
                "Non-Polaris catalog (type=%s). ATTACH configuration skipped.",
                catalog.type.value,
            )
            return None

        attach_config: dict[str, Any] = {
            "alias": "polaris_catalog",
            "type": "iceberg",
            "catalog": f"{{{{ env_var('FLOE_CATALOG_WAREHOUSE', '{catalog.warehouse}') }}}}",
        }

        return attach_config

    def _build_polaris_plugin_config(
        self,
        catalog: CatalogProfile,
        storage: StorageProfile,
    ) -> dict[str, Any] | None:
        """Build Polaris plugin configuration for dbt-duckdb.

        Uses environment variable interpolation for secrets to maintain
        Two-Tier Architecture separation.

        Includes storage_mapping from platform.yaml to enable automatic
        resolution of schema → S3 bucket paths for Iceberg tables.

        Args:
            catalog: CatalogProfile containing catalog endpoint and warehouse.
            storage: StorageProfile containing S3 configuration.

        Returns:
            Plugin configuration dict, or None if not Polaris catalog.
        """
        from floe_core.schemas.catalog_profile import CatalogType

        if catalog.type != CatalogType.POLARIS:
            logger.warning(
                "Non-Polaris catalog detected (type=%s). Polaris plugin will not be configured.",
                catalog.type.value,
            )
            return None

        config: dict[str, Any] = {
            "catalog_uri": f"{{{{ env_var('FLOE_CATALOG_URI', '{catalog.get_uri()}') }}}}",
            "warehouse": f"{{{{ env_var('FLOE_CATALOG_WAREHOUSE', '{catalog.warehouse}') }}}}",
        }

        if catalog.credentials:
            config["client_id"] = "{{ env_var('POLARIS_CLIENT_ID') }}"
            config["client_secret"] = "{{ env_var('POLARIS_CLIENT_SECRET') }}"
            scope = catalog.credentials.scope or "PRINCIPAL_ROLE:ALL"
            config["scope"] = f"{{{{ env_var('POLARIS_SCOPE', '{scope}') }}}}"

        storage_endpoint = storage.get_endpoint()
        config["s3_endpoint"] = f"{{{{ env_var('FLOE_STORAGE_ENDPOINT', '{storage_endpoint}') }}}}"
        config["s3_region"] = f"{{{{ env_var('AWS_REGION', '{storage.region}') }}}}"
        config["s3_access_key_id"] = "{{ env_var('AWS_ACCESS_KEY_ID') }}"
        config["s3_secret_access_key"] = "{{ env_var('AWS_SECRET_ACCESS_KEY') }}"

        storage_mapping = self._build_storage_mapping()
        if storage_mapping:
            config["storage_mapping"] = storage_mapping

        return config

    def _build_catalog_mappings(self, catalog: CatalogProfile) -> dict[str, str]:
        """Build catalog namespace mappings from platform.yaml.

        Maps logical schema names (bronze, silver, gold) to physical catalog
        namespace paths. This enables dbt macros to automatically resolve:
            schema='gold' → 'polaris_catalog.demo.gold'

        Injected as dbt vars for use in custom table materialization macro.

        Args:
            catalog: CatalogProfile containing warehouse/namespace info.

        Returns:
            Catalog mapping dictionary: {schema: catalog_namespace}

        Example:
            >>> {
            ...     'bronze': 'polaris_catalog.demo.bronze',
            ...     'silver': 'polaris_catalog.demo.silver',
            ...     'gold': 'polaris_catalog.demo.gold',
            ...     'default': 'polaris_catalog.demo.default'
            ... }
        """
        from floe_core.schemas.catalog_profile import CatalogType

        if catalog.type != CatalogType.POLARIS:
            logger.info("Non-Polaris catalog. Catalog mappings not generated.")
            return {}

        catalog_alias = "polaris_catalog"
        base_namespace = "demo"

        mapping = {}
        for schema_name in ["bronze", "silver", "gold", "default"]:
            mapping[schema_name] = f"{catalog_alias}.{base_namespace}.{schema_name}"

        return mapping

    def _build_storage_mapping(self) -> dict[str, dict[str, str]]:
        """Build storage mapping from platform.yaml storage profiles.

        Creates a mapping from logical schema names (bronze, silver, gold)
        to their physical storage configuration (bucket, endpoint).

        This enables macros to automatically resolve:
            schema='gold' → s3://iceberg-gold/... (via platform.yaml)

        Returns:
            Storage mapping dictionary: {schema: {bucket, endpoint}}

        Example:
            >>> {
            ...     'bronze': {'bucket': 'iceberg-bronze', 'endpoint': 'http://...'},
            ...     'silver': {'bucket': 'iceberg-silver', 'endpoint': 'http://...'},
            ...     'gold': {'bucket': 'iceberg-gold', 'endpoint': 'http://...'}
            ... }
        """
        mapping = {}

        for schema_name in ["bronze", "silver", "gold", "default"]:
            try:
                profile = self.platform.get_storage_profile(schema_name)
                mapping[schema_name] = {
                    "bucket": profile.bucket,
                    "endpoint": profile.get_endpoint(),
                    "region": profile.region,
                }
            except KeyError:
                continue

        return mapping

    def write_profiles_yml(
        self,
        output_path: Path,
        profiles: dict[str, Any],
    ) -> None:
        """Write profiles dictionary to profiles.yml file.

        Args:
            output_path: Path where profiles.yml should be written.
            profiles: Profiles dictionary from generate_profiles().

        Example:
            >>> profiles = generator.generate_profiles()
            >>> generator.write_profiles_yml(Path("demo/profiles.yml"), profiles)
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            yaml.dump(
                profiles,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

        logger.info("Generated dbt profiles.yml at %s", output_path)

    @classmethod
    def generate_from_env(
        cls,
        floe_path: Path,
        output_path: Path,
        platform_file_env: str = "FLOE_PLATFORM_FILE",
        profile_name: str = "default",
    ) -> None:
        """Generate profiles.yml from environment-specified platform.yaml.

        Convenience method for container entrypoint scripts.

        Args:
            floe_path: Path to floe.yaml.
            output_path: Path where profiles.yml should be written.
            platform_file_env: Environment variable containing platform.yaml path.
            profile_name: Platform profile name to use.

        Example:
            >>> # In docker/entrypoint.sh
            >>> DbtProfilesGenerator.generate_from_env(
            ...     floe_path=Path("demo/data_engineering/floe.yaml"),
            ...     output_path=Path("demo/data_engineering/dbt/profiles.yml"),
            ... )
        """
        from floe_core.compiler.platform_resolver import PlatformResolver
        from floe_core.schemas.floe_spec import FloeSpec

        platform_file = os.getenv(platform_file_env)
        if not platform_file:
            raise ValueError(
                f"Environment variable {platform_file_env} not set. "
                "Cannot generate dbt profiles.yml without platform.yaml."
            )

        platform_path = Path(platform_file)
        if not platform_path.exists():
            raise FileNotFoundError(
                f"Platform file not found: {platform_path} (from {platform_file_env})"
            )

        resolver = PlatformResolver()
        platform = resolver.load(path=platform_path)

        floe = FloeSpec.from_yaml(str(floe_path))

        generator = cls(platform, floe)
        profiles = generator.generate_profiles(profile_name=profile_name)
        generator.write_profiles_yml(output_path, profiles)
