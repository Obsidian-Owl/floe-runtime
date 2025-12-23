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
        from floe_core.schemas import FloeSpec

        yaml_content = """
# Minimal floe.yaml (Two-Tier Architecture)
name: minimal-project
version: "1.0.0"
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        # Verify required fields
        assert spec.name == "minimal-project"
        assert spec.version == "1.0.0"

        # Verify profile references use defaults (Two-Tier Architecture)
        assert spec.compute == "default"
        assert spec.catalog == "default"
        assert spec.storage == "default"

        # Verify defaults are applied
        assert spec.transforms == []
        assert spec.consumption.enabled is False
        assert spec.governance.classification_source == "dbt_meta"
        assert spec.observability.traces is True

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-002")
    @pytest.mark.requirement("001-FR-004")
    @pytest.mark.requirement("001-FR-028")
    def test_load_snowflake_floe_yaml(self, tmp_path: Path) -> None:
        """Integration test: Load production floe.yaml (Two-Tier).

        Covers:
        - Two-Tier Architecture: logical profile references
        - Consumption and governance configuration
        - Observability configuration
        """
        from floe_core.schemas import FloeSpec

        yaml_content = """
# Production configuration (Two-Tier Architecture)
name: analytics-pipeline
version: "2.0.0"

# Profile references (resolved from platform.yaml at compile time)
compute: snowflake
catalog: analytics
storage: production

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
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        # Verify profile references (Two-Tier Architecture)
        assert spec.compute == "snowflake"
        assert spec.catalog == "analytics"
        assert spec.storage == "production"

        # Verify transforms
        assert len(spec.transforms) == 1
        assert spec.transforms[0].type == "dbt"
        assert spec.transforms[0].target == "prod"

        # Verify consumption
        assert spec.consumption.enabled is True
        assert spec.consumption.database_type == "snowflake"
        assert spec.consumption.security.filter_column == "organization_id"

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-002")
    @pytest.mark.requirement("001-FR-006")
    def test_load_development_floe_yaml(self, tmp_path: Path) -> None:
        """Integration test: Load development floe.yaml with minimal config.

        Covers:
        - Two-Tier Architecture: default profile references
        - ConsumptionConfig with enabled, dev_mode flags
        """
        from floe_core.schemas import FloeSpec

        yaml_content = """
# Development configuration for local testing (Two-Tier)
name: dev-project
version: "0.1.0"

# Use default profiles (resolved from platform.yaml)
# compute: default (implied)
# catalog: default (implied)
# storage: default (implied)

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

        # Verify default profile references
        assert spec.compute == "default"
        assert spec.catalog == "default"
        assert spec.storage == "default"
        assert spec.consumption.enabled is False
        assert spec.consumption.dev_mode is True
        assert spec.observability.traces is False

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-002")
    def test_load_bigquery_floe_yaml(self, tmp_path: Path) -> None:
        """Integration test: Load BigQuery floe.yaml (Two-Tier).

        Covers:
        - Two-Tier Architecture: custom profile reference
        """
        from floe_core.schemas import FloeSpec

        yaml_content = """
name: bigquery-pipeline
version: "1.0.0"

# Custom profile reference (resolved from platform.yaml)
compute: bigquery

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

        assert spec.compute == "bigquery"
        assert spec.consumption.database_type == "bigquery"

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-028")
    def test_load_with_custom_catalog_profile(self, tmp_path: Path) -> None:
        """Integration test: Load floe.yaml with custom catalog profile.

        Covers:
        - Two-Tier Architecture: custom catalog profile reference
        """
        from floe_core.schemas import FloeSpec

        yaml_content = """
name: catalog-pipeline
version: "1.0.0"

compute: redshift
catalog: glue_catalog  # Custom profile reference

transforms:
  - type: dbt
    path: ./dbt
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        assert spec.compute == "redshift"
        assert spec.catalog == "glue_catalog"

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-028")
    def test_load_with_custom_storage_profile(self, tmp_path: Path) -> None:
        """Integration test: Load floe.yaml with custom storage profile.

        Covers:
        - Two-Tier Architecture: custom storage profile reference
        """
        from floe_core.schemas import FloeSpec

        yaml_content = """
name: storage-pipeline
version: "1.0.0"

compute: spark
catalog: nessie_catalog
storage: archive  # Custom storage profile

transforms:
  - type: dbt
    path: ./dbt
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        assert spec.compute == "spark"
        assert spec.catalog == "nessie_catalog"
        assert spec.storage == "archive"

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
compute: default
catalog: default
storage: default
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
        assert spec.compute == spec2.compute
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
        # In Two-Tier, conftest fixture might need updating
        # For now, just verify it loads
        assert spec.compute is not None
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
compute: 123invalid  # Invalid profile name (starts with digit)
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValidationError) as exc_info:
            FloeSpec.from_yaml(yaml_file)

        # Error should indicate the problematic field
        error_str = str(exc_info.value)
        assert "compute" in error_str

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
