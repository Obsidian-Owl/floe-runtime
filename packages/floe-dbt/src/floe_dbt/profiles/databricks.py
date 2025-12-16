"""Databricks profile generator.

T029: [P] [US2] Implement DatabricksProfileGenerator with Unity Catalog support
"""

from __future__ import annotations

from typing import Any

from floe_dbt.profiles.base import ProfileGeneratorConfig


class DatabricksProfileGenerator:
    """Generate dbt profile configuration for Databricks.

    Databricks supports Unity Catalog for unified data governance.
    Personal access tokens are referenced via env_var() for security.

    Profile Fields:
        - type: "databricks"
        - host: Workspace hostname
        - http_path: SQL warehouse HTTP path
        - token: Personal access token (env_var reference)
        - catalog: Unity Catalog name
        - schema: Default schema
        - threads: Number of parallel threads

    Example:
        >>> generator = DatabricksProfileGenerator()
        >>> result = generator.generate(artifacts, config)
        >>> result["dev"]["token"]
        "{{ env_var('DATABRICKS_TOKEN') }}"
    """

    def generate(
        self,
        artifacts: dict[str, Any],
        config: ProfileGeneratorConfig,
    ) -> dict[str, Any]:
        """Generate Databricks profile configuration.

        Token always uses env_var() reference per FR-003.

        Args:
            artifacts: CompiledArtifacts containing compute configuration.
            config: Profile generator configuration.

        Returns:
            Dictionary with target configuration for profiles.yml.
        """
        compute = artifacts.get("compute", {})
        properties = compute.get("properties", {})

        # Build profile configuration
        # CRITICAL: Token uses env_var template - NEVER hardcode (FR-003)
        # US5: Environment-prefixed secrets (e.g., DATABRICKS_PROD_TOKEN)
        profile: dict[str, Any] = {
            "type": "databricks",
            "host": properties.get("host", ""),
            "http_path": properties.get("http_path", ""),
            "token": config.get_secret_env_var("DATABRICKS", "TOKEN"),
            "threads": config.threads,
        }

        # Unity Catalog support
        if "catalog" in properties:
            profile["catalog"] = properties["catalog"]
        if "schema" in properties:
            profile["schema"] = properties["schema"]

        # target_name is guaranteed to be set by model_validator
        assert config.target_name is not None
        return {config.target_name: profile}
