"""DuckDB profile generator.

T025: [P] [US2] Implement DuckDBProfileGenerator
"""

from __future__ import annotations

from typing import Any

from floe_dbt.profiles.base import ProfileGeneratorConfig


class DuckDBProfileGenerator:
    """Generate dbt profile configuration for DuckDB.

    DuckDB is an in-process analytical database, ideal for local development
    and testing. It supports both in-memory and file-based databases.

    Profile Fields:
        - type: "duckdb"
        - path: Database file path or ":memory:"
        - threads: Number of parallel threads
        - extensions: Optional list of DuckDB extensions to load

    Example:
        >>> generator = DuckDBProfileGenerator()
        >>> result = generator.generate(artifacts, config)
        >>> result
        {
            "dev": {
                "type": "duckdb",
                "path": ":memory:",
                "threads": 4
            }
        }
    """

    def generate(
        self,
        artifacts: dict[str, Any],
        config: ProfileGeneratorConfig,
    ) -> dict[str, Any]:
        """Generate DuckDB profile configuration.

        Args:
            artifacts: CompiledArtifacts containing compute configuration.
            config: Profile generator configuration.

        Returns:
            Dictionary with target configuration for profiles.yml.
        """
        compute = artifacts.get("compute", {})
        properties = compute.get("properties", {})

        # Build profile configuration
        profile: dict[str, Any] = {
            "type": "duckdb",
            "path": properties.get("path", ":memory:"),
            "threads": config.threads,
        }

        # Optional extensions
        if "extensions" in properties:
            profile["extensions"] = properties["extensions"]

        # target_name is guaranteed to be set by model_validator
        assert config.target_name is not None
        return {config.target_name: profile}
