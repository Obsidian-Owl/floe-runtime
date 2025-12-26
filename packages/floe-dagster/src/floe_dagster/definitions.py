"""Dagster definitions entry point.

T047: [US1] Create Dagster definitions entry point
T098: [US6] Create FloeDefinitions.from_compiled_artifacts() factory
T099: [US7] Auto-load platform.yaml via FLOE_PLATFORM_FILE

This module provides the main entry point for loading Dagster definitions
from CompiledArtifacts configuration, with batteries-included observability.

Key Features:
    - FloeDefinitions.from_compiled_artifacts(): One-line Definitions factory
    - Automatic platform.yaml loading via FLOE_PLATFORM_FILE env var
    - Automatic ObservabilityOrchestrator initialization
    - Automatic PolarisCatalogResource creation
    - Support for custom assets, jobs, and schedules

Two-Tier Configuration Architecture:
    Data engineers call FloeDefinitions.from_compiled_artifacts() with NO configuration.
    Platform engineers configure platform.yaml and mount it via ConfigMap.
    The factory automatically:
    1. Loads platform.yaml from FLOE_PLATFORM_FILE (K8s ConfigMap mount)
    2. Resolves catalog profiles (Polaris, Glue, Unity, etc.)
    3. Resolves observability config (tracing + lineage endpoints)
    4. Wires all resources into Dagster Definitions
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dagster import Definitions, IOManager, io_manager

from floe_dagster.assets import FloeAssetFactory
from floe_dagster.decorators import ORCHESTRATOR_RESOURCE_KEY
from floe_dagster.observability import ObservabilityOrchestrator
from floe_dagster.resources import PolarisCatalogResource, create_dbt_cli_resource

if TYPE_CHECKING:
    from dagster import (
        AssetsDefinition,
        JobDefinition,
        ScheduleDefinition,
        SensorDefinition,
    )
    from dagster._core.definitions.unresolved_asset_job_definition import (
        UnresolvedAssetJobDefinition,
    )

    from floe_core.schemas.floe_spec import FloeSpec
    from floe_core.schemas.platform_spec import PlatformSpec

logger = logging.getLogger(__name__)

# Default platform file path (K8s ConfigMap mount location)
DEFAULT_PLATFORM_FILE_PATH = "/etc/floe/platform.yaml"


class NoOpIOManager(IOManager):
    """IO manager that does nothing - for assets that persist their own data.

    Use this for assets that handle their own persistence (e.g., writing to Iceberg
    via CatalogResource). The assets can still return metadata dicts for observability,
    but this IO manager won't attempt to store them to disk.

    This avoids permission errors when running in Kubernetes pods where the default
    storage location (/opt/dagster) may not be writable.
    """

    def handle_output(self, context: Any, obj: Any) -> None:
        """Do nothing - asset already persisted its data."""
        pass

    def load_input(self, context: Any) -> Any:
        """Return None - assets don't pass data via IO manager."""
        return None


@io_manager
def noop_io_manager() -> NoOpIOManager:
    """Factory for NoOpIOManager."""
    return NoOpIOManager()


# Environment variable for direct platform file path
PLATFORM_FILE_ENV_VAR = "FLOE_PLATFORM_FILE"


class FloeDefinitions:
    """Factory for creating Dagster Definitions with batteries-included observability.

    FloeDefinitions provides a one-line factory method that automatically:
    - Loads CompiledArtifacts from file or dict
    - Initializes ObservabilityOrchestrator (tracing + lineage)
    - Creates PolarisCatalogResource from resolved catalog config
    - Wires all resources into Dagster Definitions

    This is the PRIMARY API for data engineers using floe-dagster.

    Example:
        >>> # In definitions.py at project root
        >>> from floe_dagster import floe_asset, FloeDefinitions
        >>>
        >>> @floe_asset(group_name="bronze", outputs=["demo.bronze_customers"])
        ... def bronze_customers(context, catalog):
        ...     # Pure business logic - observability handled automatically
        ...     return {"rows": 1000}
        >>>
        >>> defs = FloeDefinitions.from_compiled_artifacts(
        ...     assets=[bronze_customers],
        ...     schedules=[my_schedule],
        ... )
    """

    @classmethod
    def from_compiled_artifacts(
        cls,
        artifacts_path: str | Path = ".floe/compiled_artifacts.json",
        *,
        artifacts_dict: dict[str, Any] | None = None,
        assets: list[AssetsDefinition] | None = None,
        jobs: list[JobDefinition | UnresolvedAssetJobDefinition] | None = None,
        schedules: list[ScheduleDefinition] | None = None,
        sensors: list[SensorDefinition] | None = None,
        namespace: str = "floe",
    ) -> Definitions:
        """Create Dagster Definitions with batteries-included observability.

        This is the primary entry point for floe-dagster projects. It:
        1. Loads CompiledArtifacts (from file or dict)
        2. Initializes ObservabilityOrchestrator for tracing + lineage
        3. Creates PolarisCatalogResource from resolved catalog config
        4. Wires everything into Dagster Definitions

        Assets decorated with @floe_asset automatically get observability
        instrumentation when using the resources provided by this factory.

        Args:
            artifacts_path: Path to compiled_artifacts.json file.
                           Ignored if artifacts_dict is provided.
            artifacts_dict: CompiledArtifacts dictionary. If provided,
                           takes precedence over artifacts_path.
            assets: List of asset definitions (including @floe_asset decorated).
            jobs: List of job definitions.
            schedules: List of schedule definitions.
            sensors: List of sensor definitions.
            namespace: OpenLineage namespace (default: "floe").

        Returns:
            Dagster Definitions with all resources wired.

        Raises:
            FileNotFoundError: If artifacts file doesn't exist and no dict provided.

        Example:
            >>> # Minimal usage - auto-loads from platform.yaml
            >>> defs = FloeDefinitions.from_compiled_artifacts()
            >>>
            >>> # With custom assets and schedules
            >>> defs = FloeDefinitions.from_compiled_artifacts(
            ...     assets=[bronze_customers, bronze_products],
            ...     schedules=[hourly_schedule],
            ... )
            >>>
            >>> # With explicit artifacts dict (for testing)
            >>> defs = FloeDefinitions.from_compiled_artifacts(
            ...     artifacts_dict=my_artifacts,
            ...     assets=[test_asset],
            ... )
        """
        # Load artifacts with priority:
        # 1. Explicit artifacts_dict (highest priority)
        # 2. Platform.yaml + floe.yaml (Two-Tier Architecture)
        # 3. Compiled artifacts file (legacy/fallback)
        if artifacts_dict is not None:
            artifacts = artifacts_dict
            logger.debug("Using explicit artifacts_dict")
        else:
            # Try platform.yaml first (Two-Tier Architecture)
            platform = cls._load_platform_config()
            if platform is not None:
                # Also load floe.yaml for orchestration config
                floe_spec = cls._load_floe_spec(namespace=namespace)
                artifacts = cls._build_artifacts_from_platform(platform, floe_spec=floe_spec)
                if floe_spec:
                    logger.info(
                        "Loaded configuration from platform.yaml + floe.yaml "
                        "(Two-Tier Architecture)"
                    )
                else:
                    logger.info(
                        "Loaded configuration from platform.yaml (Two-Tier Architecture, "
                        "orchestration unavailable)"
                    )
            else:
                # Fall back to compiled_artifacts.json file
                path = Path(artifacts_path)
                if not path.exists():
                    raise FileNotFoundError(
                        f"CompiledArtifacts not found at {artifacts_path}. "
                        f"Either set {PLATFORM_FILE_ENV_VAR} to a platform.yaml path, "
                        "or run 'floe compile' to generate compiled_artifacts.json."
                    )
                with open(path) as f:
                    artifacts = json.load(f)
                logger.debug("Loaded artifacts from %s", artifacts_path)

        # Initialize observability orchestrator
        orchestrator = ObservabilityOrchestrator.from_compiled_artifacts(
            artifacts, namespace=namespace
        )
        logger.info(
            "ObservabilityOrchestrator initialized",
            extra={"namespace": namespace},
        )

        # Build resources dict
        resources: dict[str, Any] = {
            # Inject orchestrator for @floe_asset decorator
            ORCHESTRATOR_RESOURCE_KEY: orchestrator,
            # Use NoOpIOManager - assets persist to Iceberg themselves, don't need IO manager
            "io_manager": noop_io_manager,
        }

        # Create PolarisCatalogResource if catalog config available
        resolved_catalog = artifacts.get("resolved_catalog", {})
        catalogs = artifacts.get("catalogs", {})
        if resolved_catalog or catalogs:
            try:
                catalog_resource = PolarisCatalogResource.from_compiled_artifacts(artifacts)
                resources["catalog"] = catalog_resource
                logger.info(
                    "PolarisCatalogResource initialized",
                    extra={"warehouse": catalog_resource.warehouse},
                )
            except Exception as e:
                logger.warning(
                    "Failed to create PolarisCatalogResource: %s. "
                    "Catalog resource will not be available.",
                    e,
                )

        # Create DbtCliResource (batteries-included for demo)
        # Extract dbt paths from orchestration config if available
        dbt_project_dir = None
        dbt_profiles_dir = None
        orchestration = artifacts.get("orchestration", {})
        if orchestration and orchestration.get("dbt"):
            dbt_config = orchestration["dbt"]
            dbt_project_dir = dbt_config.get("project_dir")
            dbt_profiles_dir = dbt_config.get("profiles_dir")

        try:
            dbt_resource = create_dbt_cli_resource(
                artifacts,
                project_dir=dbt_project_dir,
                profiles_dir=dbt_profiles_dir,
            )
            resources["dbt"] = dbt_resource
            logger.info("DbtCliResource initialized")
        except Exception as e:
            logger.warning(
                "Failed to create DbtCliResource: %s. dbt resource will not be available.",
                e,
            )

        # Auto-load dbt assets from orchestration config
        if orchestration and orchestration.get("dbt"):
            try:
                from floe_core.schemas.orchestration_config import DbtConfig
                from floe_dagster.loaders.dbt_loader import load_dbt_assets

                dbt_config = DbtConfig(**orchestration["dbt"])
                dbt_assets = load_dbt_assets(dbt_config)
                if dbt_assets:
                    assets = list(assets or [])
                    assets.append(dbt_assets)
                    logger.info("Auto-loaded dbt assets from orchestration config")
            except Exception as e:
                logger.warning(
                    "Failed to auto-load dbt assets: %s. dbt assets will not be available.",
                    e,
                )

        # Auto-load assets from Python modules
        if orchestration and orchestration.get("asset_modules"):
            try:
                from floe_dagster.loaders.asset_loader import load_assets_from_module_dict

                loaded_assets = load_assets_from_module_dict(orchestration)
                if loaded_assets:
                    assets = list(assets or [])
                    assets.extend(loaded_assets)
                    logger.info(
                        "Auto-loaded %d assets from asset_modules in orchestration config",
                        len(loaded_assets),
                    )
            except Exception as e:
                logger.warning(
                    "Failed to auto-load asset modules: %s. Asset modules will not be available.",
                    e,
                )

        # Auto-load partitions from orchestration config
        loaded_partitions: dict[str, Any] = {}
        if orchestration and orchestration.get("partitions"):
            try:
                from floe_core.schemas.partition_definition import (
                    DynamicPartition,
                    MultiPartition,
                    StaticPartition,
                    TimeWindowPartition,
                )
                from floe_dagster.loaders.partition_loader import load_partitions

                partition_configs = orchestration["partitions"]
                partition_definitions = {}

                for partition_name, partition_config in partition_configs.items():
                    partition_type = partition_config.get("type")
                    if partition_type == "time_window":
                        partition_definitions[partition_name] = TimeWindowPartition(
                            **partition_config
                        )
                    elif partition_type == "static":
                        partition_definitions[partition_name] = StaticPartition(**partition_config)
                    elif partition_type == "multi":
                        partition_definitions[partition_name] = MultiPartition(**partition_config)
                    elif partition_type == "dynamic":
                        partition_definitions[partition_name] = DynamicPartition(**partition_config)

                loaded_partitions = load_partitions(partition_definitions)
                logger.info(
                    "Auto-loaded %d partitions from orchestration config", len(loaded_partitions)
                )
            except Exception as e:
                logger.warning(
                    "Failed to auto-load partitions: %s. Partitions will not be available.",
                    e,
                )

        # Auto-load jobs from orchestration config
        if orchestration and orchestration.get("jobs"):
            try:
                from floe_core.schemas.job_definition import BatchJob, OpsJob
                from floe_dagster.loaders.job_loader import load_jobs

                job_configs = orchestration["jobs"]
                job_definitions = {}

                for job_name, job_config in job_configs.items():
                    job_type = job_config.get("type")
                    if job_type == "batch":
                        job_definitions[job_name] = BatchJob(**job_config)
                    elif job_type == "ops":
                        job_definitions[job_name] = OpsJob(**job_config)

                loaded_jobs = load_jobs(job_definitions)
                if loaded_jobs:
                    jobs = list(jobs or [])
                    jobs.extend(loaded_jobs)
                    logger.info("Auto-loaded %d jobs from orchestration config", len(loaded_jobs))
            except Exception as e:
                logger.warning(
                    "Failed to auto-load jobs: %s. Jobs will not be available.",
                    e,
                )

        # Auto-load schedules from orchestration config
        if orchestration and orchestration.get("schedules"):
            try:
                from floe_core.schemas.schedule_definition import (
                    ScheduleDefinition as FloeScheduleDefinition,
                )
                from floe_dagster.loaders.schedule_loader import load_schedules

                schedule_configs = orchestration["schedules"]
                schedule_definitions = {}

                for schedule_name, schedule_config in schedule_configs.items():
                    schedule_definitions[schedule_name] = FloeScheduleDefinition(**schedule_config)

                dagster_jobs = {job.name: job for job in (jobs or [])}
                loaded_schedules = load_schedules(schedule_definitions, dagster_jobs)
                if loaded_schedules:
                    schedules = list(schedules or [])
                    schedules.extend(loaded_schedules)
                    logger.info(
                        "Auto-loaded %d schedules from orchestration config", len(loaded_schedules)
                    )
            except Exception as e:
                logger.warning(
                    "Failed to auto-load schedules: %s. Schedules will not be available.",
                    e,
                )

        # Auto-load sensors from orchestration config
        if orchestration and orchestration.get("sensors"):
            try:
                from floe_core.schemas.sensor_definition import (
                    AssetSensor,
                    CustomSensor,
                    FileWatcherSensor,
                    RunStatusSensor,
                )
                from floe_core.schemas.sensor_definition import (
                    SensorDefinition as FloeSensorDefinition,
                )
                from floe_dagster.loaders.sensor_loader import load_sensors

                sensor_configs = orchestration["sensors"]
                sensor_definitions: dict[str, FloeSensorDefinition] = {}

                for sensor_name, sensor_config in sensor_configs.items():
                    sensor_type = sensor_config.get("type")
                    if sensor_type == "file_watcher":
                        sensor_definitions[sensor_name] = FileWatcherSensor(**sensor_config)
                    elif sensor_type == "asset_sensor":
                        sensor_definitions[sensor_name] = AssetSensor(**sensor_config)
                    elif sensor_type == "run_status":
                        sensor_definitions[sensor_name] = RunStatusSensor(**sensor_config)
                    elif sensor_type == "custom":
                        sensor_definitions[sensor_name] = CustomSensor(**sensor_config)

                dagster_jobs_for_sensors: dict[str, JobDefinition] = {}
                for job in jobs or []:
                    if hasattr(job, "name"):
                        dagster_jobs_for_sensors[job.name] = job  # type: ignore[assignment]

                loaded_sensors = load_sensors(sensor_definitions, dagster_jobs_for_sensors)
                if loaded_sensors:
                    sensors = list(sensors or [])
                    sensors.extend(loaded_sensors)
                    logger.info(
                        "Auto-loaded %d sensors from orchestration config", len(loaded_sensors)
                    )
            except Exception as e:
                logger.warning(
                    "Failed to auto-load sensors: %s. Sensors will not be available.",
                    e,
                )

        # Combine all assets
        all_assets: list[Any] = list(assets or [])

        # Create Definitions
        return Definitions(
            assets=all_assets if all_assets else None,
            jobs=jobs,
            schedules=schedules,
            sensors=sensors,
            resources=resources,
        )

    @classmethod
    def from_dict(
        cls,
        artifacts: dict[str, Any],
        *,
        assets: list[AssetsDefinition] | None = None,
        jobs: list[JobDefinition | UnresolvedAssetJobDefinition] | None = None,
        schedules: list[ScheduleDefinition] | None = None,
        sensors: list[SensorDefinition] | None = None,
        namespace: str = "floe",
    ) -> Definitions:
        """Create Definitions from artifacts dictionary.

        Convenience method that wraps from_compiled_artifacts.

        Args:
            artifacts: CompiledArtifacts dictionary.
            assets: List of asset definitions.
            jobs: List of job definitions.
            schedules: List of schedule definitions.
            sensors: List of sensor definitions.
            namespace: OpenLineage namespace.

        Returns:
            Dagster Definitions with all resources wired.
        """
        return cls.from_compiled_artifacts(
            artifacts_dict=artifacts,
            assets=assets,
            jobs=jobs,
            schedules=schedules,
            sensors=sensors,
            namespace=namespace,
        )

    @classmethod
    def _load_platform_config(cls) -> PlatformSpec | None:
        """Load platform configuration from platform.yaml.

        Two-Tier Architecture: Loads platform.yaml for infrastructure configuration.
        The platform config is resolved in this order:

        1. FLOE_PLATFORM_FILE: Direct path to platform.yaml (K8s ConfigMap mount)
        2. FLOE_PLATFORM_ENV: Environment name to search for platform.yaml
        3. Default search: Look in standard locations (./platform/local, etc.)

        Returns:
            PlatformSpec instance, or None if not available.

        Note:
            This method gracefully degrades - if platform.yaml is not found,
            it returns None rather than raising an error. This allows
            fallback to explicit artifacts_dict or artifacts_path.
        """
        try:
            from floe_core.compiler.platform_resolver import PlatformResolver

            # Priority 1: Direct file path (K8s ConfigMap mount pattern)
            platform_file = os.environ.get(PLATFORM_FILE_ENV_VAR)
            if platform_file:
                platform_path = Path(platform_file)
                if platform_path.exists():
                    logger.info(
                        "Loading platform config from %s: %s",
                        PLATFORM_FILE_ENV_VAR,
                        platform_file,
                    )
                    resolver = PlatformResolver()
                    return resolver.load(path=platform_path)
                logger.warning(
                    "%s set but file not found: %s",
                    PLATFORM_FILE_ENV_VAR,
                    platform_file,
                )

            # Priority 2-3: Use standard PlatformResolver (FLOE_PLATFORM_ENV or search)
            resolver = PlatformResolver()
            return resolver.load()
        except ImportError:
            logger.debug("floe_core not available, platform config unavailable")
            return None
        except Exception as e:
            logger.debug("Platform config not found: %s", e)
            return None

    @classmethod
    def _load_floe_spec(cls, namespace: str | None = None) -> FloeSpec | None:
        """Load floe.yaml for orchestration configuration.

        Two-Tier Architecture: Loads floe.yaml for orchestration/business logic.
        Searches for floe.yaml in this order:

        1. {namespace}/data_engineering/floe.yaml (if namespace provided)
        2. {namespace}/floe.yaml (if namespace provided)
        3. floe.yaml in current directory
        4. None if not found

        Args:
            namespace: Optional namespace for namespace-specific floe.yaml discovery.

        Returns:
            FloeSpec instance, or None if not available.

        Note:
            This method gracefully degrades - if floe.yaml is not found,
            it returns None. The orchestration config becomes unavailable but
            the system continues to function.
        """
        try:
            from floe_core.schemas.floe_spec import FloeSpec

            # Try namespace-specific paths first
            if namespace:
                # Try {namespace}/data_engineering/floe.yaml (common demo pattern)
                data_eng_path = Path(namespace) / "data_engineering" / "floe.yaml"
                logger.info(
                    "Checking for floe.yaml at: %s (exists=%s)",
                    data_eng_path,
                    data_eng_path.exists(),
                )
                if data_eng_path.exists():
                    logger.info("Loading floe.yaml from %s", data_eng_path)
                    spec = FloeSpec.from_yaml(str(data_eng_path))
                    logger.info("Successfully loaded floe.yaml: %s", spec.name)
                    return spec

                # Try {namespace}/floe.yaml
                namespace_path = Path(namespace) / "floe.yaml"
                logger.info(
                    "Checking for floe.yaml at: %s (exists=%s)",
                    namespace_path,
                    namespace_path.exists(),
                )
                if namespace_path.exists():
                    logger.info("Loading floe.yaml from %s", namespace_path)
                    spec = FloeSpec.from_yaml(str(namespace_path))
                    logger.info("Successfully loaded floe.yaml: %s", spec.name)
                    return spec

            # Try current directory
            floe_path = Path("floe.yaml")
            logger.info("Checking for floe.yaml at: %s (exists=%s)", floe_path, floe_path.exists())
            if floe_path.exists():
                logger.info("Loading floe.yaml from current directory")
                spec = FloeSpec.from_yaml(str(floe_path))
                logger.info("Successfully loaded floe.yaml: %s", spec.name)
                return spec

            logger.warning("floe.yaml not found, orchestration config unavailable")
            return None
        except ImportError as e:
            logger.warning("floe_core not available, floe.yaml loading unavailable: %s", e)
            return None
        except Exception as e:
            logger.error("Failed to load floe.yaml: %s", e, exc_info=True)
            return None

    @classmethod
    def _build_artifacts_from_platform(
        cls,
        platform: PlatformSpec,
        floe_spec: FloeSpec | None = None,
        profile_name: str = "default",
    ) -> dict[str, Any]:
        """Build CompiledArtifacts-compatible dictionary from PlatformSpec and FloeSpec.

        Transforms platform.yaml and floe.yaml into the dictionary format expected
        by FloeDefinitions.from_compiled_artifacts().

        Args:
            platform: Loaded PlatformSpec from platform.yaml.
            floe_spec: Optional loaded FloeSpec from floe.yaml.
            profile_name: Name of profile to use (default: "default").

        Returns:
            Dictionary suitable for FloeDefinitions.from_compiled_artifacts().

        Note:
            Credentials are stored as secret_ref patterns for runtime resolution.
            Actual secret values are never stored in this dict.
        """
        resolved_catalog: dict[str, Any] = {}
        observability_config: dict[str, Any] = {}
        orchestration_config: dict[str, Any] = {}

        # Build resolved_catalog from catalog profile
        try:
            catalog = platform.get_catalog_profile(profile_name)
            resolved_catalog = {
                "uri": catalog.get_uri(),
                "warehouse": catalog.warehouse,
                "credentials": {
                    "client_id": (catalog.credentials.client_id if catalog.credentials else None),
                    "scope": (
                        catalog.credentials.scope if catalog.credentials else "PRINCIPAL_ROLE:ALL"
                    ),
                },
            }

            # Handle secret references for client_secret
            if catalog.credentials and catalog.credentials.client_secret:
                secret_ref = catalog.credentials.client_secret
                resolved_catalog["credentials"]["client_secret"] = {
                    "secret_ref": secret_ref.secret_ref
                }

            # Add storage config if available
            try:
                storage = platform.get_storage_profile(profile_name)
                resolved_catalog["s3_endpoint"] = storage.get_endpoint()
                resolved_catalog["s3_region"] = storage.region
                resolved_catalog["s3_path_style_access"] = storage.path_style_access
            except KeyError:
                pass  # Storage profile is optional
        except KeyError:
            logger.warning(
                "Catalog profile '%s' not found in platform.yaml",
                profile_name,
            )

        # Build observability config
        if platform.observability:
            obs = platform.observability
            observability_config = {
                "tracing": {
                    "enabled": obs.traces,
                    "endpoint": obs.otlp_endpoint,
                    "service_name": obs.attributes.get("service.name", "floe"),
                    "batch_export": True,
                },
                "lineage": {
                    "enabled": obs.lineage,
                    "endpoint": obs.lineage_endpoint,
                    "namespace": obs.attributes.get("namespace", "floe"),
                    "timeout": 5.0,
                },
            }

        # Build orchestration config from floe_spec
        if floe_spec and floe_spec.orchestration:
            orchestration_config = floe_spec.orchestration.model_dump(mode="json")

        return {
            "version": "2.0.0",
            "resolved_catalog": resolved_catalog,
            "observability": observability_config,
            "orchestration": orchestration_config,
        }


def load_definitions_from_artifacts(
    artifacts_path: str | Path = ".floe/compiled_artifacts.json",
) -> Definitions:
    """Load Dagster Definitions from CompiledArtifacts file.

    Reads CompiledArtifacts JSON file and creates complete Dagster
    Definitions including dbt assets and resources.

    Note:
        This is the legacy API. For new projects, use
        FloeDefinitions.from_compiled_artifacts() which provides
        batteries-included observability.

    Args:
        artifacts_path: Path to compiled_artifacts.json file.

    Returns:
        Dagster Definitions object.

    Raises:
        FileNotFoundError: If artifacts file doesn't exist.
        ValueError: If artifacts are invalid.

    Example:
        >>> # In definitions.py at project root
        >>> from floe_dagster.definitions import load_definitions_from_artifacts
        >>> defs = load_definitions_from_artifacts()
    """
    path = Path(artifacts_path)
    if not path.exists():
        raise FileNotFoundError(
            f"CompiledArtifacts not found at {artifacts_path}. Run 'floe compile' to generate it."
        )

    with open(path) as f:
        artifacts = json.load(f)

    return FloeAssetFactory.create_definitions(artifacts)


def load_definitions_from_dict(artifacts: dict[str, Any]) -> Definitions:
    """Load Dagster Definitions from CompiledArtifacts dictionary.

    Useful for testing or programmatic configuration.

    Note:
        This is the legacy API. For new projects, use
        FloeDefinitions.from_dict() which provides
        batteries-included observability.

    Args:
        artifacts: CompiledArtifacts dictionary.

    Returns:
        Dagster Definitions object.

    Example:
        >>> artifacts = {...}
        >>> defs = load_definitions_from_dict(artifacts)
    """
    return FloeAssetFactory.create_definitions(artifacts)


# Default definitions for Dagster to discover
# Uncomment and configure when deploying:
# defs = load_definitions_from_artifacts()
