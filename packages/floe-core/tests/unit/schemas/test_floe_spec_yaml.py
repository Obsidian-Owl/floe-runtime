"""Unit tests for FloeSpec YAML loading.

T018: [US1] Unit tests for FloeSpec.from_yaml() loading
Tests FloeSpec YAML parsing and loading functionality.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import yaml
from pydantic import ValidationError

if TYPE_CHECKING:
    from typing import Any


class TestFloeSpecFromYaml:
    """Tests for FloeSpec.from_yaml() class method."""

    def test_from_yaml_minimal_config(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should load minimal configuration."""
        from floe_core.schemas import ComputeTarget, FloeSpec

        yaml_content = """
name: test-project
version: "1.0.0"
compute:
  target: duckdb
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        assert spec.name == "test-project"
        assert spec.version == "1.0.0"
        assert spec.compute.target == ComputeTarget.duckdb

    def test_from_yaml_full_config(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should load full configuration."""
        from floe_core.schemas import FloeSpec

        yaml_content = """
name: full-project
version: "2.0.0"
compute:
  target: snowflake
  connection_secret_ref: snowflake-secret
  properties:
    account: xy12345.us-east-1
    warehouse: COMPUTE_WH
transforms:
  - type: dbt
    path: ./dbt
    target: prod
consumption:
  enabled: true
  port: 8080
  database_type: snowflake
governance:
  classification_source: external
  emit_lineage: false
observability:
  traces: true
  metrics: true
  otlp_endpoint: http://otel:4317
catalog:
  type: polaris
  uri: http://polaris:8181/api/catalog
  warehouse: my_warehouse
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        assert spec.name == "full-project"
        assert spec.version == "2.0.0"
        assert spec.compute.properties["account"] == "xy12345.us-east-1"
        assert len(spec.transforms) == 1
        assert spec.consumption.enabled is True
        assert spec.governance.classification_source == "external"
        assert spec.observability.otlp_endpoint == "http://otel:4317"
        assert spec.catalog is not None
        assert spec.catalog.type == "polaris"

    def test_from_yaml_with_string_path(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should accept string path."""
        from floe_core.schemas import FloeSpec

        yaml_content = """
name: test-project
version: "1.0.0"
compute:
  target: duckdb
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(str(yaml_file))

        assert spec.name == "test-project"

    def test_from_yaml_file_not_found(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should raise FileNotFoundError."""
        from floe_core.schemas import FloeSpec

        non_existent = tmp_path / "non_existent.yaml"

        with pytest.raises(FileNotFoundError):
            FloeSpec.from_yaml(non_existent)

    def test_from_yaml_invalid_yaml_syntax(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should raise error on invalid YAML."""
        from floe_core.schemas import FloeSpec

        yaml_content = """
name: test-project
version: "1.0.0"
compute:
  target: duckdb
  invalid: [unclosed bracket
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises((yaml.YAMLError, ValidationError)):
            FloeSpec.from_yaml(yaml_file)

    def test_from_yaml_missing_required_field(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should raise ValidationError for missing fields."""
        from pydantic import ValidationError

        from floe_core.schemas import FloeSpec

        yaml_content = """
name: test-project
# version is missing
compute:
  target: duckdb
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValidationError) as exc_info:
            FloeSpec.from_yaml(yaml_file)

        assert "version" in str(exc_info.value)

    def test_from_yaml_invalid_compute_target(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should raise error for invalid target."""
        from pydantic import ValidationError

        from floe_core.schemas import FloeSpec

        yaml_content = """
name: test-project
version: "1.0.0"
compute:
  target: invalid_target
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValidationError) as exc_info:
            FloeSpec.from_yaml(yaml_file)

        assert "target" in str(exc_info.value)

    def test_from_yaml_extra_fields_rejected(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should reject extra fields."""
        from pydantic import ValidationError

        from floe_core.schemas import FloeSpec

        yaml_content = """
name: test-project
version: "1.0.0"
compute:
  target: duckdb
unknown_field: some_value
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValidationError) as exc_info:
            FloeSpec.from_yaml(yaml_file)

        assert "extra" in str(exc_info.value).lower()

    def test_from_yaml_multiple_transforms(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should load multiple transforms."""
        from floe_core.schemas import FloeSpec

        yaml_content = """
name: test-project
version: "1.0.0"
compute:
  target: duckdb
transforms:
  - type: dbt
    path: ./dbt/staging
  - type: dbt
    path: ./dbt/marts
    target: prod
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        assert len(spec.transforms) == 2
        assert spec.transforms[0].path == "./dbt/staging"
        assert spec.transforms[1].path == "./dbt/marts"
        assert spec.transforms[1].target == "prod"

    def test_from_yaml_empty_transforms(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should handle empty transforms list."""
        from floe_core.schemas import FloeSpec

        yaml_content = """
name: test-project
version: "1.0.0"
compute:
  target: duckdb
transforms: []
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        assert spec.transforms == []

    def test_from_yaml_consumption_partial(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should handle partial consumption config."""
        from floe_core.schemas import FloeSpec

        yaml_content = """
name: test-project
version: "1.0.0"
compute:
  target: duckdb
consumption:
  enabled: true
  port: 9000
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        assert spec.consumption.enabled is True
        assert spec.consumption.port == 9000
        # Other fields should have defaults
        assert spec.consumption.dev_mode is False


class TestFloeSpecFromDict:
    """Tests for FloeSpec.from_dict() or direct dict parsing."""

    def test_from_dict_minimal(self) -> None:
        """FloeSpec should be constructible from dict."""
        from floe_core.schemas import ComputeTarget, FloeSpec

        data: dict[str, Any] = {
            "name": "test-project",
            "version": "1.0.0",
            "compute": {"target": "duckdb"},
        }

        spec = FloeSpec.model_validate(data)

        assert spec.name == "test-project"
        assert spec.compute.target == ComputeTarget.duckdb

    def test_from_dict_nested_configs(self) -> None:
        """FloeSpec should parse nested configuration dicts."""
        from floe_core.schemas import FloeSpec

        data: dict[str, Any] = {
            "name": "test-project",
            "version": "1.0.0",
            "compute": {
                "target": "snowflake",
                "properties": {"account": "test.us-east-1"},
            },
            "consumption": {
                "enabled": True,
                "pre_aggregations": {"refresh_schedule": "0 * * * *"},
            },
        }

        spec = FloeSpec.model_validate(data)

        assert spec.compute.properties["account"] == "test.us-east-1"
        assert spec.consumption.pre_aggregations.refresh_schedule == "0 * * * *"
