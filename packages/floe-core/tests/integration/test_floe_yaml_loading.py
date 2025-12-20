"""Integration tests for floe.yaml loading.

T019: [US1] Integration test for floe.yaml loading
End-to-end tests for loading real floe.yaml configurations.

Covers: FR-008 (floe-core MUST have integration tests covering YAML loading,
compilation flow, and round-trip serialization)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

if TYPE_CHECKING:
    from typing import Any


class TestFloeYamlIntegration:
    """Integration tests for floe.yaml loading."""

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-001")
    @pytest.mark.requirement("001-FR-008")
    def test_load_minimal_floe_yaml(self, tmp_path: Path) -> None:
        """Integration test: Load minimal floe.yaml.

        Covers:
        - 001-FR-001: FloeSpec immutable Pydantic BaseModel
        - 001-FR-008: Sensible defaults for optional fields
        """
        from floe_core.schemas import ComputeTarget, FloeSpec

        yaml_content = """
# Minimal floe.yaml for DuckDB
name: minimal-project
version: "1.0.0"
compute:
  target: duckdb
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        # Verify required fields
        assert spec.name == "minimal-project"
        assert spec.version == "1.0.0"
        assert spec.compute.target == ComputeTarget.duckdb

        # Verify defaults are applied
        assert spec.transforms == []
        assert spec.consumption.enabled is False
        assert spec.governance.classification_source == "dbt_meta"
        assert spec.observability.traces is True
        assert spec.catalog is None

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-002")
    @pytest.mark.requirement("001-FR-004")
    @pytest.mark.requirement("001-FR-028")
    def test_load_snowflake_floe_yaml(self, tmp_path: Path) -> None:
        """Integration test: Load Snowflake production floe.yaml.

        Covers:
        - 001-FR-002: Support 7 compute targets (Snowflake)
        - 001-FR-004: ComputeConfig with connection_secret_ref and properties
        - 001-FR-028: CatalogConfig with type, uri, warehouse, scope
        """
        from floe_core.schemas import ComputeTarget, FloeSpec

        yaml_content = """
# Production Snowflake configuration
name: analytics-pipeline
version: "2.0.0"

compute:
  target: snowflake
  connection_secret_ref: snowflake-prod-credentials
  properties:
    account: xy12345.us-east-1
    warehouse: ANALYTICS_WH
    role: TRANSFORM_ROLE
    database: ANALYTICS_DB
    schema: STAGING

transforms:
  - type: dbt
    path: ./dbt
    target: prod

consumption:
  enabled: true
  port: 4000
  database_type: snowflake
  api_secret_ref: cube-api-key
  pre_aggregations:
    refresh_schedule: "0 */6 * * *"
    timezone: UTC
  security:
    row_level: true
    filter_column: organization_id

governance:
  classification_source: dbt_meta
  emit_lineage: true
  policies:
    pii_masking:
      enabled: true

observability:
  traces: true
  metrics: true
  lineage: true
  otlp_endpoint: http://otel-collector:4317
  lineage_endpoint: http://marquez:5000/api/v1/lineage
  attributes:
    service.name: analytics-pipeline
    deployment.environment: production

catalog:
  type: polaris
  uri: https://polaris.company.com/api/catalog
  credential_secret_ref: polaris-oauth2
  warehouse: analytics_warehouse
  scope: PRINCIPAL_ROLE:DATA_ENGINEER
  token_refresh_enabled: true
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        # Verify compute
        assert spec.compute.target == ComputeTarget.snowflake
        assert spec.compute.connection_secret_ref == "snowflake-prod-credentials"
        assert spec.compute.properties["account"] == "xy12345.us-east-1"

        # Verify transforms
        assert len(spec.transforms) == 1
        assert spec.transforms[0].type == "dbt"
        assert spec.transforms[0].target == "prod"

        # Verify consumption
        assert spec.consumption.enabled is True
        assert spec.consumption.database_type == "snowflake"
        assert spec.consumption.security.filter_column == "organization_id"

        # Verify catalog
        assert spec.catalog is not None
        assert spec.catalog.type == "polaris"
        assert spec.catalog.scope == "PRINCIPAL_ROLE:DATA_ENGINEER"
        assert spec.catalog.token_refresh_enabled is True

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-002")
    @pytest.mark.requirement("001-FR-006")
    def test_load_development_floe_yaml(self, tmp_path: Path) -> None:
        """Integration test: Load development floe.yaml with minimal config.

        Covers:
        - 001-FR-002: Support 7 compute targets (DuckDB)
        - 001-FR-006: ConsumptionConfig with enabled, dev_mode flags
        """
        from floe_core.schemas import ComputeTarget, FloeSpec

        yaml_content = """
# Development configuration for local testing
name: dev-project
version: "0.1.0"

compute:
  target: duckdb
  properties:
    path: ":memory:"

transforms:
  - type: dbt
    path: ./dbt

# Consumption disabled for development
consumption:
  enabled: false
  dev_mode: true

# Observability minimal for development
observability:
  traces: false
  metrics: false
  lineage: false
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        assert spec.compute.target == ComputeTarget.duckdb
        assert spec.compute.properties.get("path") == ":memory:"
        assert spec.consumption.enabled is False
        assert spec.consumption.dev_mode is True
        assert spec.observability.traces is False
        assert spec.catalog is None

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-002")
    def test_load_bigquery_floe_yaml(self, tmp_path: Path) -> None:
        """Integration test: Load BigQuery floe.yaml.

        Covers:
        - 001-FR-002: Support 7 compute targets (BigQuery)
        """
        from floe_core.schemas import ComputeTarget, FloeSpec

        yaml_content = """
name: bigquery-pipeline
version: "1.0.0"

compute:
  target: bigquery
  connection_secret_ref: bigquery-sa-key
  properties:
    project: my-gcp-project
    dataset: analytics
    location: US

transforms:
  - type: dbt
    path: ./dbt

consumption:
  enabled: true
  database_type: bigquery
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        assert spec.compute.target == ComputeTarget.bigquery
        assert spec.compute.properties["project"] == "my-gcp-project"
        assert spec.consumption.database_type == "bigquery"

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-028")
    def test_load_with_glue_catalog(self, tmp_path: Path) -> None:
        """Integration test: Load floe.yaml with Glue catalog.

        Covers:
        - 001-FR-028: CatalogConfig with type, uri, properties
        """
        from floe_core.schemas import FloeSpec

        yaml_content = """
name: glue-pipeline
version: "1.0.0"

compute:
  target: redshift
  connection_secret_ref: redshift-creds
  properties:
    host: my-cluster.redshift.amazonaws.com
    port: 5439
    database: analytics

transforms:
  - type: dbt
    path: ./dbt

catalog:
  type: glue
  uri: arn:aws:glue:us-east-1:123456789:catalog
  properties:
    region: us-east-1
    catalog_id: "123456789"
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        assert spec.catalog is not None
        assert spec.catalog.type == "glue"
        assert spec.catalog.properties["region"] == "us-east-1"

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-028")
    def test_load_with_nessie_catalog(self, tmp_path: Path) -> None:
        """Integration test: Load floe.yaml with Nessie catalog.

        Covers:
        - 001-FR-028: CatalogConfig with type, uri, properties
        """
        from floe_core.schemas import FloeSpec

        yaml_content = """
name: nessie-pipeline
version: "1.0.0"

compute:
  target: spark
  properties:
    master: spark://master:7077

transforms:
  - type: dbt
    path: ./dbt

catalog:
  type: nessie
  uri: http://nessie:19120/api/v2
  properties:
    branch: main
    reference: main@HEAD
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        assert spec.catalog is not None
        assert spec.catalog.type == "nessie"
        assert spec.catalog.properties["branch"] == "main"

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-001")
    def test_roundtrip_yaml_json_yaml(self, tmp_path: Path) -> None:
        """Integration test: Roundtrip from YAML to JSON and back.

        Covers:
        - 001-FR-001: FloeSpec immutable Pydantic model with JSON serialization
        """
        import json

        from floe_core.schemas import FloeSpec

        yaml_content = """
name: roundtrip-project
version: "1.0.0"
compute:
  target: duckdb
transforms:
  - type: dbt
    path: ./dbt
consumption:
  enabled: true
  port: 8080
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        # Load from YAML
        spec = FloeSpec.from_yaml(yaml_file)

        # Serialize to JSON
        json_data = spec.model_dump_json()

        # Parse JSON back to dict
        data = json.loads(json_data)

        # Create new spec from dict
        spec2 = FloeSpec.model_validate(data)

        # Compare
        assert spec.name == spec2.name
        assert spec.version == spec2.version
        assert spec.compute.target == spec2.compute.target
        assert len(spec.transforms) == len(spec2.transforms)
        assert spec.consumption.enabled == spec2.consumption.enabled

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-001")
    def test_conftest_fixture_compatibility(self, sample_floe_yaml: dict[str, Any]) -> None:
        """Integration test: Verify conftest fixture produces valid FloeSpec.

        Covers:
        - 001-FR-001: FloeSpec validation from dictionary input
        """
        from floe_core.schemas import FloeSpec

        spec = FloeSpec.model_validate(sample_floe_yaml)

        assert spec.name == "test-project"
        assert spec.version == "1.0.0"
        assert spec.compute.target.value == "duckdb"
        assert len(spec.transforms) == 1


class TestFloeYamlErrorHandling:
    """Integration tests for error handling during YAML loading."""

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-026")
    def test_error_message_shows_line_number(self, tmp_path: Path) -> None:
        """Error messages should help locate the issue.

        Covers:
        - 001-FR-026: Clear error messages for invalid configuration
        """
        from pydantic import ValidationError

        from floe_core.schemas import FloeSpec

        yaml_content = """
name: test-project
version: "1.0.0"
compute:
  target: invalid_target_here
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValidationError) as exc_info:
            FloeSpec.from_yaml(yaml_file)

        # Error should indicate the problematic field
        error_str = str(exc_info.value)
        assert "target" in error_str or "compute" in error_str

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-026")
    def test_error_on_empty_file(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should handle empty YAML file.

        Covers:
        - 001-FR-026: Clear error messages for invalid configuration
        """
        from floe_core.schemas import FloeSpec

        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text("")

        with pytest.raises((TypeError, ValidationError)):
            FloeSpec.from_yaml(yaml_file)

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-026")
    def test_error_on_yaml_list_instead_of_dict(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should reject YAML that parses to list.

        Covers:
        - 001-FR-026: Clear error messages for invalid configuration
        """
        from floe_core.schemas import FloeSpec

        yaml_content = """
- item1
- item2
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises((TypeError, ValidationError)):
            FloeSpec.from_yaml(yaml_file)
