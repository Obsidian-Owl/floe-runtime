"""Unit tests for GovernanceConfig model.

T014: [US1] Unit tests for GovernanceConfig defaults
Tests GovernanceConfig with classification_source and policies.
"""

from __future__ import annotations

from typing import Literal

import pytest
from pydantic import ValidationError


class TestGovernanceConfig:
    """Tests for GovernanceConfig model."""

    def test_governance_config_default_values(self) -> None:
        """GovernanceConfig should have correct defaults."""
        from floe_core.schemas import GovernanceConfig

        config = GovernanceConfig()
        assert config.classification_source == "dbt_meta"
        assert config.policies == {}
        assert config.emit_lineage is True

    def test_governance_config_classification_source_dbt_meta(self) -> None:
        """GovernanceConfig should accept 'dbt_meta' classification_source."""
        from floe_core.schemas import GovernanceConfig

        config = GovernanceConfig(classification_source="dbt_meta")
        source: Literal["dbt_meta", "external"] = config.classification_source
        assert source == "dbt_meta"

    def test_governance_config_classification_source_external(self) -> None:
        """GovernanceConfig should accept 'external' classification_source."""
        from floe_core.schemas import GovernanceConfig

        config = GovernanceConfig(classification_source="external")
        assert config.classification_source == "external"

    def test_governance_config_invalid_classification_source(self) -> None:
        """GovernanceConfig should reject invalid classification_source."""
        from floe_core.schemas import GovernanceConfig

        with pytest.raises(ValidationError) as exc_info:
            GovernanceConfig(classification_source="invalid")  # type: ignore[arg-type]

        assert "classification_source" in str(exc_info.value)

    def test_governance_config_policies_empty_default(self) -> None:
        """GovernanceConfig.policies should default to empty dict."""
        from floe_core.schemas import GovernanceConfig

        config = GovernanceConfig()
        assert config.policies == {}
        assert isinstance(config.policies, dict)

    def test_governance_config_policies_with_values(self) -> None:
        """GovernanceConfig should accept custom policies."""
        from floe_core.schemas import GovernanceConfig

        config = GovernanceConfig(
            policies={
                "pii_masking": {"enabled": True, "columns": ["email", "phone"]},
                "retention": {"days": 90},
            }
        )
        assert config.policies["pii_masking"]["enabled"] is True
        assert config.policies["retention"]["days"] == 90

    def test_governance_config_emit_lineage_default(self) -> None:
        """GovernanceConfig.emit_lineage should default to True."""
        from floe_core.schemas import GovernanceConfig

        config = GovernanceConfig()
        assert config.emit_lineage is True

    def test_governance_config_emit_lineage_disabled(self) -> None:
        """GovernanceConfig should accept emit_lineage=False."""
        from floe_core.schemas import GovernanceConfig

        config = GovernanceConfig(emit_lineage=False)
        assert config.emit_lineage is False

    def test_governance_config_is_frozen(self) -> None:
        """GovernanceConfig should be immutable."""
        from floe_core.schemas import GovernanceConfig

        config = GovernanceConfig()

        with pytest.raises(ValidationError):
            config.emit_lineage = False  # type: ignore[misc]

    def test_governance_config_rejects_extra_fields(self) -> None:
        """GovernanceConfig should reject unknown fields."""
        from floe_core.schemas import GovernanceConfig

        with pytest.raises(ValidationError) as exc_info:
            GovernanceConfig(unknown_field="value")  # type: ignore[call-arg]

        assert "extra" in str(exc_info.value).lower()

    def test_governance_config_default_factory_isolation(self) -> None:
        """GovernanceConfig defaults should be isolated (no shared state)."""
        from floe_core.schemas import GovernanceConfig

        config1 = GovernanceConfig()
        config2 = GovernanceConfig()

        # Verify they are independent objects
        assert config1 is not config2
        assert config1.policies is not config2.policies
