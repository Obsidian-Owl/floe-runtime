"""Unit tests for orchestration configuration schemas.

T013: [010-orchestration-auto-discovery] OrchestrationConfig validation tests
Covers: 010-FR-040 through 010-FR-048
Tests Pydantic v2 schema validation for declarative orchestration.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from floe_core.schemas.orchestration_config import (
    IDENTIFIER_PATTERN,
    MODULE_PATH_PATTERN,
    DbtConfig,
    ObservabilityLevel,
    OrchestrationConfig,
)


class TestDbtConfig:
    """Tests for DbtConfig schema validation."""

    def test_dbt_config_minimal_valid(self) -> None:
        """DbtConfig should accept minimal valid configuration."""
        config = DbtConfig(manifest_path="target/manifest.json")

        assert config.manifest_path == "target/manifest.json"
        assert config.observability_level == ObservabilityLevel.PER_MODEL
        assert config.project_dir is None
        assert config.profiles_dir is None
        assert config.target is None

    def test_dbt_config_full_valid(self) -> None:
        """DbtConfig should accept all optional fields."""
        config = DbtConfig(
            manifest_path="target/manifest.json",
            observability_level=ObservabilityLevel.JOB_LEVEL,
            project_dir="demo/dbt",
            profiles_dir=".floe/profiles",
            target="dev",
        )

        assert config.manifest_path == "target/manifest.json"
        assert config.observability_level == ObservabilityLevel.JOB_LEVEL
        assert config.project_dir == "demo/dbt"
        assert config.profiles_dir == ".floe/profiles"
        assert config.target == "dev"

    def test_dbt_config_requires_manifest_path(self) -> None:
        """DbtConfig should require manifest_path."""
        with pytest.raises(ValidationError) as exc_info:
            DbtConfig()  # type: ignore[call-arg]

        assert "manifest_path" in str(exc_info.value)

    def test_dbt_config_target_must_be_identifier(self) -> None:
        """DbtConfig target must match identifier pattern."""
        with pytest.raises(ValidationError) as exc_info:
            DbtConfig(manifest_path="target/manifest.json", target="dev-123")

        assert "target" in str(exc_info.value)

    def test_dbt_config_is_frozen(self) -> None:
        """DbtConfig should be immutable (frozen)."""
        config = DbtConfig(manifest_path="target/manifest.json")

        with pytest.raises(ValidationError):
            config.manifest_path = "other/path"  # type: ignore[misc]

    def test_dbt_config_forbids_extra_fields(self) -> None:
        """DbtConfig should forbid extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            DbtConfig(
                manifest_path="target/manifest.json",
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "unknown_field" in str(exc_info.value)


class TestOrchestrationConfig:
    """Tests for OrchestrationConfig schema validation."""

    def test_orchestration_config_empty_valid(self) -> None:
        """OrchestrationConfig should accept empty configuration."""
        config = OrchestrationConfig()

        assert config.asset_modules == []
        assert config.dbt is None
        assert config.partitions == {}
        assert config.assets == {}
        assert config.jobs == {}
        assert config.schedules == {}
        assert config.sensors == {}
        assert config.backfills == {}

    def test_orchestration_config_with_asset_modules(self) -> None:
        """OrchestrationConfig should accept asset_modules."""
        config = OrchestrationConfig(asset_modules=["demo.assets.bronze", "demo.assets.gold"])

        assert len(config.asset_modules) == 2
        assert "demo.assets.bronze" in config.asset_modules

    def test_orchestration_config_with_dbt(self) -> None:
        """OrchestrationConfig should accept dbt configuration."""
        config = OrchestrationConfig(dbt=DbtConfig(manifest_path="target/manifest.json"))

        assert config.dbt is not None
        assert config.dbt.manifest_path == "target/manifest.json"

    def test_orchestration_config_asset_modules_must_be_valid_paths(self) -> None:
        """OrchestrationConfig asset_modules must match module path pattern."""
        with pytest.raises(ValidationError) as exc_info:
            OrchestrationConfig(asset_modules=["demo.assets.bronze", "invalid-module-name"])

        assert "asset_modules" in str(exc_info.value) or "Invalid module path" in str(
            exc_info.value
        )

    def test_orchestration_config_partition_keys_must_be_identifiers(self) -> None:
        """OrchestrationConfig partition keys must be valid identifiers."""
        from floe_core.schemas.partition_definition import StaticPartition

        with pytest.raises(ValidationError) as exc_info:
            OrchestrationConfig(
                partitions={
                    "invalid-partition": StaticPartition(type="static", partition_keys=["a", "b"])
                }
            )

        assert "invalid-partition" in str(exc_info.value) or "Invalid identifier" in str(
            exc_info.value
        )

    def test_orchestration_config_is_frozen(self) -> None:
        """OrchestrationConfig should be immutable (frozen)."""
        config = OrchestrationConfig()

        with pytest.raises(ValidationError):
            config.asset_modules = ["new.module"]  # type: ignore[misc]

    def test_orchestration_config_forbids_extra_fields(self) -> None:
        """OrchestrationConfig should forbid extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            OrchestrationConfig(unknown_field="value")  # type: ignore[call-arg]

        assert "unknown_field" in str(exc_info.value)


class TestPatternConstants:
    """Tests for validation pattern constants."""

    def test_identifier_pattern_matches_valid_identifiers(self) -> None:
        """IDENTIFIER_PATTERN should match valid Python identifiers."""
        import re

        assert re.match(IDENTIFIER_PATTERN, "my_partition")
        assert re.match(IDENTIFIER_PATTERN, "DailyPartition")
        assert re.match(IDENTIFIER_PATTERN, "partition123")
        assert not re.match(IDENTIFIER_PATTERN, "123partition")
        assert not re.match(IDENTIFIER_PATTERN, "my-partition")
        assert not re.match(IDENTIFIER_PATTERN, "my.partition")

    def test_module_path_pattern_matches_valid_modules(self) -> None:
        """MODULE_PATH_PATTERN should match valid Python module paths."""
        import re

        assert re.match(MODULE_PATH_PATTERN, "demo")
        assert re.match(MODULE_PATH_PATTERN, "demo.assets")
        assert re.match(MODULE_PATH_PATTERN, "demo.assets.bronze")
        assert not re.match(MODULE_PATH_PATTERN, "123demo")
        assert not re.match(MODULE_PATH_PATTERN, "demo-assets")
        assert not re.match(MODULE_PATH_PATTERN, "demo..assets")
