"""Unit tests for FloeSpec YAML loading.

T018: [US1] Unit tests for FloeSpec.from_yaml() loading
T035: [US2] Updated for Two-Tier Architecture

Tests FloeSpec YAML parsing and loading functionality.
In Two-Tier Architecture, FloeSpec uses profile references (strings)
for storage, catalog, and compute instead of inline configurations.
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
    """Tests for FloeSpec.from_yaml() class method (Two-Tier Architecture)."""

    def test_from_yaml_minimal_config(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should load minimal configuration."""
        from floe_core.schemas import FloeSpec

        yaml_content = """
name: test-project
version: "1.0.0"
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        assert spec.name == "test-project"
        assert spec.version == "1.0.0"
        # Two-Tier: Defaults to "default" profile reference
        assert spec.compute == "default"
        assert spec.catalog == "default"
        assert spec.storage == "default"

    def test_from_yaml_with_profile_references(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should load profile reference configuration."""
        from floe_core.schemas import FloeSpec

        yaml_content = """
name: test-project
version: "1.0.0"
storage: production
catalog: analytics
compute: snowflake
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        assert spec.name == "test-project"
        assert spec.version == "1.0.0"
        assert spec.storage == "production"
        assert spec.catalog == "analytics"
        assert spec.compute == "snowflake"

    def test_from_yaml_full_config(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should load full configuration."""
        from floe_core.schemas import FloeSpec

        yaml_content = """
name: full-project
version: "2.0.0"
storage: data-lake
catalog: prod-catalog
compute: production
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
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        assert spec.name == "full-project"
        assert spec.version == "2.0.0"
        assert spec.storage == "data-lake"
        assert spec.catalog == "prod-catalog"
        assert spec.compute == "production"
        assert len(spec.transforms) == 1
        assert spec.consumption.enabled is True
        assert spec.governance.classification_source == "external"
        assert spec.observability.otlp_endpoint == "http://otel:4317"

    def test_from_yaml_with_string_path(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should accept string path."""
        from floe_core.schemas import FloeSpec

        yaml_content = """
name: test-project
version: "1.0.0"
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
compute: default
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
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValidationError) as exc_info:
            FloeSpec.from_yaml(yaml_file)

        assert "version" in str(exc_info.value)

    def test_from_yaml_invalid_profile_name(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should raise error for invalid profile name."""
        from pydantic import ValidationError

        from floe_core.schemas import FloeSpec

        yaml_content = """
name: test-project
version: "1.0.0"
compute: 123-invalid  # Invalid: starts with number
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        with pytest.raises(ValidationError) as exc_info:
            FloeSpec.from_yaml(yaml_file)

        assert "compute" in str(exc_info.value)

    def test_from_yaml_extra_fields_rejected(self, tmp_path: Path) -> None:
        """FloeSpec.from_yaml() should reject extra fields."""
        from pydantic import ValidationError

        from floe_core.schemas import FloeSpec

        yaml_content = """
name: test-project
version: "1.0.0"
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
    """Tests for FloeSpec from dict parsing (Two-Tier Architecture)."""

    def test_from_dict_minimal(self) -> None:
        """FloeSpec should be constructible from minimal dict."""
        from floe_core.schemas import FloeSpec

        data: dict[str, Any] = {
            "name": "test-project",
            "version": "1.0.0",
        }

        spec = FloeSpec.model_validate(data)

        assert spec.name == "test-project"
        # Two-Tier: Defaults to "default" profile reference
        assert spec.compute == "default"
        assert spec.catalog == "default"
        assert spec.storage == "default"

    def test_from_dict_with_profile_references(self) -> None:
        """FloeSpec should parse profile reference strings."""
        from floe_core.schemas import FloeSpec

        data: dict[str, Any] = {
            "name": "test-project",
            "version": "1.0.0",
            "storage": "production",
            "catalog": "analytics",
            "compute": "snowflake",
        }

        spec = FloeSpec.model_validate(data)

        assert spec.storage == "production"
        assert spec.catalog == "analytics"
        assert spec.compute == "snowflake"

    def test_from_dict_nested_configs(self) -> None:
        """FloeSpec should parse nested configuration dicts."""
        from floe_core.schemas import FloeSpec

        data: dict[str, Any] = {
            "name": "test-project",
            "version": "1.0.0",
            "consumption": {
                "enabled": True,
                "pre_aggregations": {"refresh_schedule": "0 * * * *"},
            },
        }

        spec = FloeSpec.model_validate(data)

        assert spec.consumption.enabled is True
        assert spec.consumption.pre_aggregations.refresh_schedule == "0 * * * *"


class TestFloeSpecTwoTierArchitecture:
    """Tests for Two-Tier Configuration Architecture compliance."""

    def test_zero_secrets_in_floe_spec(self, tmp_path: Path) -> None:
        """FloeSpec should contain zero infrastructure secrets."""
        from floe_core.schemas import FloeSpec

        # This is a valid floe.yaml with NO infrastructure details
        yaml_content = """
name: secure-pipeline
version: "1.0.0"
storage: production
catalog: analytics
compute: snowflake
transforms:
  - type: dbt
    path: ./dbt
governance:
  emit_lineage: true
"""
        yaml_file = tmp_path / "floe.yaml"
        yaml_file.write_text(yaml_content)

        spec = FloeSpec.from_yaml(yaml_file)

        # Verify no credentials, URIs, or endpoints in FloeSpec
        assert spec.storage == "production"  # Just a name, not config
        assert spec.catalog == "analytics"  # Just a name, not config
        assert spec.compute == "snowflake"  # Just a name, not config

    def test_same_floe_yaml_different_environments(self) -> None:
        """Same floe.yaml can be used across environments."""
        from floe_core.schemas import FloeSpec

        # This exact config works in dev, staging, and production
        # Platform engineers configure platform.yaml differently per environment
        data: dict[str, Any] = {
            "name": "multi-env-pipeline",
            "version": "1.0.0",
            "storage": "default",
            "catalog": "default",
            "compute": "default",
            "transforms": [{"type": "dbt", "path": "./dbt"}],
        }

        spec = FloeSpec.model_validate(data)

        # The same spec object is valid regardless of environment
        # Resolution happens at compile time with PlatformSpec
        assert spec.storage == "default"
        assert spec.catalog == "default"
        assert spec.compute == "default"

    def test_profile_references_are_strings(self) -> None:
        """Profile references in FloeSpec are simple strings."""
        from floe_core.schemas import FloeSpec

        spec = FloeSpec(
            name="test",
            version="1.0.0",
            storage="my-storage",
            catalog="my-catalog",
            compute="my-compute",
        )

        assert isinstance(spec.storage, str)
        assert isinstance(spec.catalog, str)
        assert isinstance(spec.compute, str)
