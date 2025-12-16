"""BigQuery profile generator.

T027: [P] [US2] Implement BigQueryProfileGenerator with service-account/oauth support
"""

from __future__ import annotations

from typing import Any

from floe_dbt.profiles.base import ProfileGeneratorConfig


class BigQueryProfileGenerator:
    """Generate dbt profile configuration for BigQuery.

    BigQuery supports two authentication methods:
    - oauth: Uses default application credentials (gcloud auth)
    - service-account: Uses service account JSON key file

    Profile Fields:
        - type: "bigquery"
        - method: "oauth" or "service-account"
        - project: GCP project ID
        - dataset: Default dataset
        - location: BigQuery location (US, EU, etc.)
        - keyfile: Path to service account key (for service-account method)
        - threads: Number of parallel threads

    Example:
        >>> generator = BigQueryProfileGenerator()
        >>> result = generator.generate(artifacts, config)
        >>> result["dev"]["method"]
        "oauth"
    """

    def generate(
        self,
        artifacts: dict[str, Any],
        config: ProfileGeneratorConfig,
    ) -> dict[str, Any]:
        """Generate BigQuery profile configuration.

        Args:
            artifacts: CompiledArtifacts containing compute configuration.
            config: Profile generator configuration.

        Returns:
            Dictionary with target configuration for profiles.yml.
        """
        compute = artifacts.get("compute", {})
        properties = compute.get("properties", {})

        method = properties.get("method", "oauth")

        # Build profile configuration
        profile: dict[str, Any] = {
            "type": "bigquery",
            "method": method,
            "project": properties.get("project", ""),
            "threads": config.threads,
        }

        # Add dataset if specified
        if "dataset" in properties:
            profile["dataset"] = properties["dataset"]

        # Add location if specified
        if "location" in properties:
            profile["location"] = properties["location"]

        # For service-account, reference keyfile via env_var (FR-003)
        # US5: Environment-prefixed secrets (e.g., BIGQUERY_PROD_KEYFILE)
        if method == "service-account":
            profile["keyfile"] = config.get_secret_env_var("BIGQUERY", "KEYFILE")

        return {config.target_name: profile}
