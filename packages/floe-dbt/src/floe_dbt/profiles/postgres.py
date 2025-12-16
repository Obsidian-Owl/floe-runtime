"""PostgreSQL profile generator.

T030: [P] [US2] Implement PostgreSQLProfileGenerator
"""

from __future__ import annotations

from typing import Any

from floe_dbt.profiles.base import ProfileGeneratorConfig


class PostgreSQLProfileGenerator:
    """Generate dbt profile configuration for PostgreSQL.

    PostgreSQL is an open-source relational database. Credentials use
    env_var() template syntax for security - never hardcoded.

    Profile Fields:
        - type: "postgres"
        - host: Database hostname
        - port: Connection port (default: 5432)
        - user: Username (env_var reference)
        - password: Password (env_var reference)
        - dbname: Database name
        - schema: Default schema
        - threads: Number of parallel threads

    Example:
        >>> generator = PostgreSQLProfileGenerator()
        >>> result = generator.generate(artifacts, config)
        >>> result["dev"]["port"]
        5432
    """

    # Default PostgreSQL port
    DEFAULT_PORT = 5432

    def generate(
        self,
        artifacts: dict[str, Any],
        config: ProfileGeneratorConfig,
    ) -> dict[str, Any]:
        """Generate PostgreSQL profile configuration.

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
        # US5: Environment-prefixed secrets (e.g., POSTGRES_PROD_USER)
        profile: dict[str, Any] = {
            "type": "postgres",
            "host": properties.get("host", ""),
            "port": properties.get("port", self.DEFAULT_PORT),
            "user": config.get_secret_env_var("POSTGRES", "USER"),
            "password": config.get_secret_env_var("POSTGRES", "PASSWORD"),
            "dbname": properties.get("database", ""),
            "threads": config.threads,
        }

        # Optional schema
        if "schema" in properties:
            profile["schema"] = properties["schema"]

        # target_name is guaranteed to be set by model_validator
        assert config.target_name is not None
        return {config.target_name: profile}
