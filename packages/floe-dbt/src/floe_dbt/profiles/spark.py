"""Spark profile generator.

T031: [P] [US2] Implement SparkProfileGenerator with thrift/odbc/session/http methods
"""

from __future__ import annotations

from typing import Any

from floe_dbt.profiles.base import ProfileGeneratorConfig


class SparkProfileGenerator:
    """Generate dbt profile configuration for Apache Spark.

    Spark supports multiple connection methods:
    - thrift: HiveServer2 Thrift protocol
    - http: HTTP endpoint
    - odbc: ODBC driver connection
    - session: Local Spark session

    Profile Fields:
        - type: "spark"
        - method: Connection method (thrift, http, odbc, session)
        - host: Spark server hostname
        - port: Connection port (default: 10000 for thrift)
        - schema: Default schema
        - threads: Number of parallel threads

    Example:
        >>> generator = SparkProfileGenerator()
        >>> result = generator.generate(artifacts, config)
        >>> result["dev"]["method"]
        "thrift"
    """

    # Default Spark Thrift port
    DEFAULT_PORT = 10000

    def generate(
        self,
        artifacts: dict[str, Any],
        config: ProfileGeneratorConfig,
    ) -> dict[str, Any]:
        """Generate Spark profile configuration.

        Args:
            artifacts: CompiledArtifacts containing compute configuration.
            config: Profile generator configuration.

        Returns:
            Dictionary with target configuration for profiles.yml.
        """
        compute = artifacts.get("compute", {})
        properties = compute.get("properties", {})

        method = properties.get("method", "thrift")

        # Build profile configuration
        profile: dict[str, Any] = {
            "type": "spark",
            "method": method,
            "threads": config.threads,
        }

        # Host and port for network methods
        if method in ("thrift", "http", "odbc"):
            profile["host"] = properties.get("host", "")
            profile["port"] = properties.get("port", self.DEFAULT_PORT)

        # Optional schema
        if "schema" in properties:
            profile["schema"] = properties["schema"]

        # Optional cluster configuration
        if "cluster" in properties:
            profile["cluster"] = properties["cluster"]

        # ODBC-specific: driver path
        if method == "odbc" and "driver" in properties:
            profile["driver"] = properties["driver"]

        return {config.target_name: profile}
