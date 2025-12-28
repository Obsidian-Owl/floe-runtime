"""Dagster instance.yaml generator from platform.yaml.

Platform-to-Dagster translation layer for compute logs storage configuration.
Part of the Two-Tier Configuration Architecture.

Architecture:
    platform.yaml → DagsterInstanceGenerator → instance.yaml (mounted ConfigMap)
                  → env vars (K8s secrets) → Dagster instance → S3ComputeLogManager

Usage:
    from floe_core.compiler.dagster_instance_generator import DagsterInstanceGenerator

    DagsterInstanceGenerator.generate_from_env(
        platform_file_env="FLOE_PLATFORM_FILE",
        output_path=Path("/tmp/dagster_home/dagster.yaml"),
    )

Generates instance.yaml with:
- run_monitoring configuration (faster polling for local dev)
- telemetry (disabled for privacy)
- compute_logs storage (S3/LocalStack/Azure/GCS based on platform.yaml)
"""

import os
from pathlib import Path
from typing import Any

import yaml

from floe_core.compiler.platform_resolver import PlatformResolver
from floe_core.schemas.observability import ComputeLogManagerType
from floe_core.schemas.platform_spec import PlatformSpec


class DagsterInstanceGenerator:
    """Generate Dagster instance.yaml from platform.yaml.

    Platform-managed Dagster configuration generator.
    Reads platform.yaml and generates instance.yaml for Dagster.
    """

    @staticmethod
    def generate_from_env(
        platform_file_env: str = "FLOE_PLATFORM_FILE",
        output_path: Path | None = None,
    ) -> None:
        """Generate instance.yaml from platform.yaml via environment variable.

        Args:
            platform_file_env: Environment variable containing platform.yaml path.
            output_path: Output path for instance.yaml (defaults to DAGSTER_HOME/dagster.yaml).

        Raises:
            FileNotFoundError: If platform file doesn't exist.
            ValueError: If platform_file_env is not set.
        """
        platform_file = os.getenv(platform_file_env)
        if not platform_file:
            raise ValueError(
                f"Environment variable {platform_file_env} not set. "
                "Set it to the path of platform.yaml."
            )

        platform_path = Path(platform_file)
        if not platform_path.exists():
            raise FileNotFoundError(
                f"Platform file not found: {platform_path}. "
                f"Ensure {platform_file_env} points to a valid platform.yaml file."
            )

        # Default output to DAGSTER_HOME/dagster.yaml
        if output_path is None:
            dagster_home = Path(os.getenv("DAGSTER_HOME", "/tmp/dagster_home"))
            dagster_home.mkdir(parents=True, exist_ok=True)
            output_path = dagster_home / "dagster.yaml"

        DagsterInstanceGenerator.generate_from_file(
            platform_path=platform_path,
            output_path=output_path,
        )

    @staticmethod
    def generate_from_file(
        platform_path: Path,
        output_path: Path,
    ) -> None:
        """Generate instance.yaml from platform.yaml file.

        Args:
            platform_path: Path to platform.yaml.
            output_path: Output path for instance.yaml.

        Raises:
            FileNotFoundError: If platform file doesn't exist.
            ValidationError: If platform.yaml is invalid.
        """
        # Load and validate platform configuration
        platform_yaml = yaml.safe_load(platform_path.read_text())
        platform_config = PlatformSpec(**platform_yaml)

        # Generate instance configuration
        instance_config = DagsterInstanceGenerator._generate_instance_config(platform_config)

        # Write instance.yaml
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(yaml.dump(instance_config, sort_keys=False))

    @staticmethod
    def _generate_instance_config(platform_config: PlatformSpec) -> dict[str, Any]:
        """Generate Dagster instance configuration from platform config.

        Args:
            platform_config: Validated platform configuration.

        Returns:
            Instance configuration dict for Dagster instance.yaml.
        """
        instance_config: dict[str, Any] = {
            # Fast run monitoring for better UX (especially local dev)
            "run_monitoring": {
                "enabled": True,
                "start_timeout_seconds": 60,  # Faster than default 300s
                "poll_interval_seconds": 10,  # Faster than default 120s
            },
            # Disable telemetry for privacy
            "telemetry": {
                "enabled": False,
            },
        }

        # Generate compute_logs configuration if observability is configured
        if (
            platform_config.observability
            and platform_config.observability.compute_logs
            and platform_config.observability.compute_logs.enabled
        ):
            compute_logs_config = platform_config.observability.compute_logs

            if compute_logs_config.manager_type == ComputeLogManagerType.S3:
                instance_config["compute_logs"] = (
                    DagsterInstanceGenerator._generate_s3_compute_logs(
                        platform_config,
                        compute_logs_config,
                    )
                )
            elif compute_logs_config.manager_type == ComputeLogManagerType.LOCAL:
                instance_config["compute_logs"] = {
                    "module": "dagster.core.storage.local_compute_log_manager",
                    "class": "LocalComputeLogManager",
                    "config": {
                        "base_dir": compute_logs_config.local_dir,
                    },
                }
            elif compute_logs_config.manager_type == ComputeLogManagerType.NOOP:
                instance_config["compute_logs"] = {
                    "module": "dagster.core.storage.noop_compute_log_manager",
                    "class": "NoOpComputeLogManager",
                }
            # TODO: Add Azure Blob and GCS support

        return instance_config

    @staticmethod
    def _generate_s3_compute_logs(
        platform_config: PlatformSpec,
        compute_logs_config: Any,
    ) -> dict[str, Any]:
        """Generate S3 compute log manager configuration.

        Args:
            platform_config: Platform configuration.
            compute_logs_config: Compute logs configuration.

        Returns:
            S3ComputeLogManager configuration dict.
        """
        # Resolve storage profile
        storage_ref = compute_logs_config.storage_ref or "default"
        storage_profile = platform_config.storage.get(storage_ref)

        if not storage_profile:
            raise ValueError(
                f"Storage profile '{storage_ref}' not found in platform.yaml. "
                f"Available profiles: {list(platform_config.storage.keys())}"
            )

        # Determine bucket name
        bucket = compute_logs_config.bucket
        if not bucket:
            # Default: append -compute-logs to storage bucket name
            bucket = f"{storage_profile.bucket}-compute-logs"

        # Build S3 compute log manager config
        s3_config: dict[str, Any] = {
            "module": "dagster_aws.s3.compute_log_manager",
            "class": "S3ComputeLogManager",
            "config": {
                "bucket": bucket,
                "prefix": compute_logs_config.prefix,
                "local_dir": compute_logs_config.local_dir,
                "upload_interval": compute_logs_config.upload_interval,
                "skip_empty_files": True,  # Don't upload empty logs
                "show_url_only": False,  # Show log content in UI, not just URL
            },
        }

        # Add endpoint_url for S3-compatible storage (LocalStack, MinIO)
        if storage_profile.endpoint:
            s3_config["config"]["endpoint_url"] = storage_profile.endpoint
            s3_config["config"]["use_ssl"] = not storage_profile.endpoint.startswith("http://")
            s3_config["config"]["verify"] = False  # Disable SSL verification for local dev

        # Add region
        if storage_profile.region:
            s3_config["config"]["region"] = storage_profile.region

        return s3_config
