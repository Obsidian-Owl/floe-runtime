"""Redshift profile generator.

T028: [P] [US2] Implement RedshiftProfileGenerator
"""

from __future__ import annotations

from typing import Any

from floe_dbt.profiles.base import ProfileGeneratorConfig


class RedshiftProfileGenerator:
    """Generate dbt profile configuration for Amazon Redshift.

    Redshift is AWS's cloud data warehouse. Credentials use env_var()
    template syntax for security - never hardcoded.

    Profile Fields:
        - type: "redshift"
        - host: Cluster endpoint hostname
        - port: Connection port (default: 5439)
        - user: Username (env_var reference)
        - password: Password (env_var reference)
        - dbname: Database name
        - schema: Default schema
        - threads: Number of parallel threads

    Example:
        >>> generator = RedshiftProfileGenerator()
        >>> result = generator.generate(artifacts, config)
        >>> result["dev"]["port"]
        5439
    """

    # Default Redshift port
    DEFAULT_PORT = 5439

    def generate(
        self,
        artifacts: dict[str, Any],
        config: ProfileGeneratorConfig,
    ) -> dict[str, Any]:
        """Generate Redshift profile configuration.

        Credentials always use env_var() references per FR-003.

        Args:
            artifacts: CompiledArtifacts containing compute configuration.
            config: Profile generator configuration.

        Returns:
            Dictionary with target configuration for profiles.yml.
        """
        compute = artifacts.get("compute", {})
        properties = compute.get("properties", {})

        # Build profile configuration
        # CRITICAL: Credentials use env_var template - NEVER hardcode (FR-003)
        # US5: Environment-prefixed secrets (e.g., REDSHIFT_PROD_USER)
        profile: dict[str, Any] = {
            "type": "redshift",
            "host": properties.get("host", ""),
            "port": properties.get("port", self.DEFAULT_PORT),
            "user": config.get_secret_env_var("REDSHIFT", "USER"),
            "password": config.get_secret_env_var("REDSHIFT", "PASSWORD"),
            "dbname": properties.get("database", ""),
            "threads": config.threads,
        }

        # Optional schema
        if "schema" in properties:
            profile["schema"] = properties["schema"]

        # target_name is guaranteed to be set by model_validator
        assert config.target_name is not None
        return {config.target_name: profile}
