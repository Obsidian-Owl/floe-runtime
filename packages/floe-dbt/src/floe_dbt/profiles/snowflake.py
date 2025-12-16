"""Snowflake profile generator.

T026: [P] [US2] Implement SnowflakeProfileGenerator with env_var templating
T081: [US5] Add environment-specific secret references
"""

from __future__ import annotations

from typing import Any

from floe_dbt.profiles.base import ProfileGeneratorConfig


class SnowflakeProfileGenerator:
    """Generate dbt profile configuration for Snowflake.

    Snowflake is a cloud data warehouse. Credentials are NEVER hardcoded -
    all sensitive values use dbt's env_var() template syntax for security.
    Supports multi-environment deployments with environment-prefixed secrets.

    Profile Fields:
        - type: "snowflake"
        - account: Snowflake account identifier
        - user: Username (env_var reference with environment prefix)
        - password: Password (env_var reference with environment prefix)
        - role: Snowflake role
        - warehouse: Virtual warehouse name
        - database: Database name
        - schema: Default schema
        - threads: Number of parallel threads

    Example:
        >>> generator = SnowflakeProfileGenerator()
        >>> config = ProfileGeneratorConfig(environment="prod")
        >>> result = generator.generate(artifacts, config)
        >>> result["prod"]["password"]
        "{{ env_var('SNOWFLAKE_PROD_PASSWORD') }}"
    """

    def generate(
        self,
        artifacts: dict[str, Any],
        config: ProfileGeneratorConfig,
    ) -> dict[str, Any]:
        """Generate Snowflake profile configuration.

        Credentials always use env_var() references per FR-003.
        Environment prefix is included for multi-environment support.

        Args:
            artifacts: CompiledArtifacts containing compute configuration.
            config: Profile generator configuration with environment.

        Returns:
            Dictionary with target configuration for profiles.yml.
        """
        compute = artifacts.get("compute", {})
        properties = compute.get("properties", {})

        # Build profile configuration
        # CRITICAL: Credentials use env_var template - NEVER hardcode (FR-003)
        # Environment prefix enables multi-environment secret management
        profile: dict[str, Any] = {
            "type": "snowflake",
            "account": properties.get("account", ""),
            "user": config.get_secret_env_var("SNOWFLAKE", "USER"),
            "password": config.get_secret_env_var("SNOWFLAKE", "PASSWORD"),
            "threads": config.threads,
        }

        # Optional fields from properties
        if "role" in properties:
            profile["role"] = properties["role"]
        if "warehouse" in properties:
            profile["warehouse"] = properties["warehouse"]
        if "database" in properties:
            profile["database"] = properties["database"]
        if "schema" in properties:
            profile["schema"] = properties["schema"]

        # target_name is guaranteed to be set by model_validator
        assert config.target_name is not None
        return {config.target_name: profile}
