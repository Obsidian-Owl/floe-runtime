"""Cube configuration generator from ConsumptionConfig.

This module generates Cube configuration files from floe-core ConsumptionConfig,
enabling deployment of the Cube semantic layer.

T016: Implement database driver template selection
T017: Implement cube.js configuration generator from ConsumptionConfig
T018: Implement K8s secret reference handling
T019: Implement config file writer
T020: Add validation for unsupported database_type

Functional Requirements:
- FR-001: Generate Cube configuration from ConsumptionConfig
- FR-002: Support all database_type values
- FR-003: Reference Kubernetes secrets (never embed secrets)
- FR-004: Generate valid cube.js configuration file format
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)

# T016: Database driver template mapping
# Maps floe database_type to Cube's CUBEJS_DB_TYPE values
DATABASE_DRIVER_MAP: dict[str, str] = {
    "postgres": "postgres",
    "snowflake": "snowflake",
    "bigquery": "bigquery",
    "databricks": "databricks-jdbc",
    "trino": "trino",
    "duckdb": "duckdb",
}

# Supported database types for validation
SUPPORTED_DATABASE_TYPES = frozenset(DATABASE_DRIVER_MAP.keys())


def get_cube_driver_type(database_type: str) -> str:
    """Get the Cube driver type for a given database type.

    Args:
        database_type: The database type from ConsumptionConfig

    Returns:
        The corresponding Cube driver type

    Raises:
        ValueError: If the database type is not supported

    Example:
        >>> get_cube_driver_type("postgres")
        'postgres'
        >>> get_cube_driver_type("databricks")
        'databricks-jdbc'
    """
    if database_type not in DATABASE_DRIVER_MAP:
        supported = ", ".join(sorted(SUPPORTED_DATABASE_TYPES))
        msg = (
            f"Unsupported database_type: '{database_type}'. "
            f"Supported types: {supported}"
        )
        raise ValueError(msg)

    return DATABASE_DRIVER_MAP[database_type]


class CubeConfigGenerator:
    """Generator for Cube configuration from ConsumptionConfig.

    This class takes a ConsumptionConfig dictionary and generates
    the corresponding Cube configuration environment variables.

    Attributes:
        config: The ConsumptionConfig dictionary

    Example:
        >>> config = {"enabled": True, "database_type": "postgres", "port": 4000}
        >>> generator = CubeConfigGenerator(config)
        >>> cube_config = generator.generate()
        >>> cube_config["CUBEJS_DB_TYPE"]
        'postgres'
    """

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize the generator with ConsumptionConfig.

        Args:
            config: ConsumptionConfig dictionary from CompiledArtifacts
        """
        self.config = config
        self._log = logger.bind(
            database_type=config.get("database_type"),
            port=config.get("port"),
        )

    @classmethod
    def from_compiled_artifacts(
        cls,
        artifacts: Any,
    ) -> CubeConfigGenerator:
        """Create generator from CompiledArtifacts.

        Args:
            artifacts: CompiledArtifacts instance from floe-core

        Returns:
            CubeConfigGenerator instance

        Example:
            >>> from floe_core.compiler import CompiledArtifacts
            >>> artifacts = CompiledArtifacts.from_file("compiled.json")
            >>> generator = CubeConfigGenerator.from_compiled_artifacts(artifacts)
        """
        # Handle both dict and Pydantic model
        if hasattr(artifacts, "consumption"):
            consumption = artifacts.consumption
            if hasattr(consumption, "model_dump"):
                config = consumption.model_dump()
            else:
                config = dict(consumption)
        elif isinstance(artifacts, dict):
            config = artifacts.get("consumption", {})
        else:
            msg = "artifacts must be CompiledArtifacts or dict"
            raise TypeError(msg)

        return cls(config)

    def generate(self) -> dict[str, str]:
        """Generate Cube configuration environment variables.

        Returns:
            Dictionary of CUBEJS_* environment variables

        Raises:
            ValueError: If database_type is not supported

        Example:
            >>> generator = CubeConfigGenerator({"database_type": "postgres", "port": 4000})
            >>> config = generator.generate()
            >>> config["CUBEJS_DB_TYPE"]
            'postgres'
        """
        self._log.info("generating_cube_config")

        # T016: Database driver selection
        database_type = self.config.get("database_type", "postgres")
        cube_driver = get_cube_driver_type(database_type)

        # Build configuration
        config: dict[str, str] = {
            "CUBEJS_DB_TYPE": cube_driver,
            "CUBEJS_API_PORT": str(self.config.get("port", 4000)),
        }

        # T017: Add optional configuration
        self._add_dev_mode(config)
        self._add_pre_aggregation_config(config)
        self._add_security_config(config)

        # T018: Add secret references
        self._add_secret_refs(config)

        self._log.info(
            "cube_config_generated",
            driver=cube_driver,
            port=config["CUBEJS_API_PORT"],
        )

        return config

    def _add_dev_mode(self, config: dict[str, str]) -> None:
        """Add dev mode configuration if enabled.

        Args:
            config: Configuration dict to update
        """
        dev_mode = self.config.get("dev_mode", False)
        if dev_mode:
            config["CUBEJS_DEV_MODE"] = "true"

    def _add_pre_aggregation_config(self, config: dict[str, str]) -> None:
        """Add pre-aggregation configuration.

        Args:
            config: Configuration dict to update
        """
        pre_agg = self.config.get("pre_aggregations", {})
        if pre_agg:
            # Enable scheduled refresh for pre-aggregations
            config["CUBEJS_SCHEDULED_REFRESH_DEFAULT"] = "true"

            timezone = pre_agg.get("timezone", "UTC")
            config["CUBEJS_SCHEDULED_REFRESH_TIMEZONE"] = timezone

    def _add_security_config(self, config: dict[str, str]) -> None:
        """Add security configuration.

        Args:
            config: Configuration dict to update
        """
        security = self.config.get("security", {})
        if security.get("row_level", False):
            # Row-level security is configured via checkAuth in cube.js
            # We just set a marker that security is enabled
            config["CUBEJS_SECURITY_ENABLED"] = "true"

    def _add_secret_refs(self, config: dict[str, str]) -> None:
        """Add Kubernetes secret references (T018).

        CRITICAL: Never embed actual secret values.
        Always reference secrets via environment variable syntax.

        Args:
            config: Configuration dict to update
        """
        api_secret_ref = self.config.get("api_secret_ref")
        if api_secret_ref:
            # Reference the secret via env var syntax
            # K8s will inject the actual value at runtime
            config["CUBEJS_API_SECRET"] = f"${{{api_secret_ref}}}"
            self._log.debug("secret_ref_configured", secret_name=api_secret_ref)

    def generate_file_content(self) -> str:
        """Generate cube.js file content as JavaScript module.

        Returns:
            JavaScript module content for cube.js

        Example:
            >>> generator = CubeConfigGenerator(config)
            >>> content = generator.generate_file_content()
            >>> "module.exports" in content
            True
        """
        config = self.generate()

        lines = [
            "// Cube configuration generated by floe-cube",
            "// DO NOT EDIT - this file is auto-generated",
            "",
            "module.exports = {",
        ]

        # Add each config value
        for key, value in sorted(config.items()):
            # Use process.env for secret references
            if value.startswith("${"):
                # Extract env var name from ${NAME}
                env_var = value[2:-1]
                lines.append(f"  {key}: process.env.{env_var},")
            else:
                # Escape quotes in values
                escaped_value = value.replace("'", "\\'")
                lines.append(f"  {key}: '{escaped_value}',")

        lines.append("};")
        lines.append("")

        return "\n".join(lines)

    def write_config(self, output_dir: Path) -> Path:
        """Write Cube configuration to file (T019).

        Args:
            output_dir: Directory to write cube.js to

        Returns:
            Path to the written file

        Example:
            >>> generator = CubeConfigGenerator(config)
            >>> path = generator.write_config(Path(".floe/cube"))
            >>> path.exists()
            True
        """
        # Create directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        config_file = output_dir / "cube.js"
        content = self.generate_file_content()
        config_file.write_text(content)

        self._log.info("cube_config_written", path=str(config_file))

        return config_file


def validate_database_type(database_type: str) -> None:
    """Validate that a database type is supported (T020).

    Args:
        database_type: The database type to validate

    Raises:
        ValueError: If the database type is not supported with clear error message

    Example:
        >>> validate_database_type("postgres")  # OK
        >>> validate_database_type("oracle")  # Raises ValueError
    """
    if database_type not in SUPPORTED_DATABASE_TYPES:
        supported = ", ".join(sorted(SUPPORTED_DATABASE_TYPES))
        msg = (
            f"Unsupported database type: '{database_type}'. "
            f"floe-cube supports the following database types: {supported}. "
            f"Please update your floe.yaml consumption.database_type setting."
        )
        raise ValueError(msg)
