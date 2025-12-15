"""Unit tests for EnvironmentContext optional model.

T033: [US2] Unit tests for EnvironmentContext optional model

Tests the optional SaaS enrichment context model. This model is
only populated when running with Control Plane (standalone-first principle).
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError


class TestEnvironmentContextModel:
    """Tests for EnvironmentContext model structure and validation."""

    def test_environment_context_import(self) -> None:
        """Test EnvironmentContext can be imported from compiler package."""
        from floe_core.compiler import EnvironmentContext

        assert EnvironmentContext is not None

    def test_environment_context_required_fields(self) -> None:
        """Test EnvironmentContext requires all fields."""
        from floe_core.compiler import EnvironmentContext

        with pytest.raises(ValidationError) as exc_info:
            EnvironmentContext()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        field_names = {e["loc"][0] for e in errors}
        assert "tenant_id" in field_names
        assert "tenant_slug" in field_names
        assert "project_id" in field_names
        assert "project_slug" in field_names
        assert "environment_id" in field_names
        assert "environment_type" in field_names
        assert "governance_category" in field_names

    def test_environment_context_valid_creation(self) -> None:
        """Test EnvironmentContext with valid fields."""
        from floe_core.compiler import EnvironmentContext

        tenant_id = uuid4()
        project_id = uuid4()
        env_id = uuid4()

        context = EnvironmentContext(
            tenant_id=tenant_id,
            tenant_slug="acme-corp",
            project_id=project_id,
            project_slug="data-warehouse",
            environment_id=env_id,
            environment_type="production",
            governance_category="production",
        )

        assert context.tenant_id == tenant_id
        assert context.tenant_slug == "acme-corp"
        assert context.project_id == project_id
        assert context.project_slug == "data-warehouse"
        assert context.environment_id == env_id
        assert context.environment_type == "production"
        assert context.governance_category == "production"

    def test_environment_context_uuid_fields(self) -> None:
        """Test tenant_id, project_id, environment_id are UUIDs."""
        from floe_core.compiler import EnvironmentContext

        tenant_id = uuid4()
        project_id = uuid4()
        env_id = uuid4()

        context = EnvironmentContext(
            tenant_id=tenant_id,
            tenant_slug="acme",
            project_id=project_id,
            project_slug="proj",
            environment_id=env_id,
            environment_type="development",
            governance_category="non_production",
        )

        assert isinstance(context.tenant_id, UUID)
        assert isinstance(context.project_id, UUID)
        assert isinstance(context.environment_id, UUID)

    def test_environment_context_uuid_from_string(self) -> None:
        """Test UUIDs can be provided as strings."""
        from floe_core.compiler import EnvironmentContext

        uuid_str = "12345678-1234-5678-1234-567812345678"

        context = EnvironmentContext(
            tenant_id=uuid_str,
            tenant_slug="acme",
            project_id=uuid_str,
            project_slug="proj",
            environment_id=uuid_str,
            environment_type="staging",
            governance_category="non_production",
        )

        assert str(context.tenant_id) == uuid_str

    def test_environment_context_invalid_uuid(self) -> None:
        """Test invalid UUID raises ValidationError."""
        from floe_core.compiler import EnvironmentContext

        with pytest.raises(ValidationError):
            EnvironmentContext(
                tenant_id="not-a-uuid",
                tenant_slug="acme",
                project_id=uuid4(),
                project_slug="proj",
                environment_id=uuid4(),
                environment_type="development",
                governance_category="non_production",
            )

    def test_environment_type_valid_values(self) -> None:
        """Test environment_type accepts valid literals."""
        from floe_core.compiler import EnvironmentContext

        valid_types = ["development", "preview", "staging", "production"]

        for env_type in valid_types:
            context = EnvironmentContext(
                tenant_id=uuid4(),
                tenant_slug="acme",
                project_id=uuid4(),
                project_slug="proj",
                environment_id=uuid4(),
                environment_type=env_type,
                governance_category="production" if env_type == "production" else "non_production",
            )
            assert context.environment_type == env_type

    def test_environment_type_invalid_value(self) -> None:
        """Test environment_type rejects invalid values."""
        from floe_core.compiler import EnvironmentContext

        with pytest.raises(ValidationError):
            EnvironmentContext(
                tenant_id=uuid4(),
                tenant_slug="acme",
                project_id=uuid4(),
                project_slug="proj",
                environment_id=uuid4(),
                environment_type="invalid_type",
                governance_category="non_production",
            )

    def test_governance_category_valid_values(self) -> None:
        """Test governance_category accepts valid literals."""
        from floe_core.compiler import EnvironmentContext

        valid_categories = ["production", "non_production"]

        for category in valid_categories:
            context = EnvironmentContext(
                tenant_id=uuid4(),
                tenant_slug="acme",
                project_id=uuid4(),
                project_slug="proj",
                environment_id=uuid4(),
                environment_type="development",
                governance_category=category,
            )
            assert context.governance_category == category

    def test_governance_category_invalid_value(self) -> None:
        """Test governance_category rejects invalid values."""
        from floe_core.compiler import EnvironmentContext

        with pytest.raises(ValidationError):
            EnvironmentContext(
                tenant_id=uuid4(),
                tenant_slug="acme",
                project_id=uuid4(),
                project_slug="proj",
                environment_id=uuid4(),
                environment_type="production",
                governance_category="invalid_category",
            )

    def test_environment_context_immutable(self) -> None:
        """Test EnvironmentContext is immutable (frozen=True)."""
        from floe_core.compiler import EnvironmentContext

        context = EnvironmentContext(
            tenant_id=uuid4(),
            tenant_slug="acme",
            project_id=uuid4(),
            project_slug="proj",
            environment_id=uuid4(),
            environment_type="development",
            governance_category="non_production",
        )

        with pytest.raises(ValidationError):
            context.tenant_slug = "new-slug"  # type: ignore[misc]

    def test_environment_context_extra_forbid(self) -> None:
        """Test EnvironmentContext rejects unknown fields."""
        from floe_core.compiler import EnvironmentContext

        with pytest.raises(ValidationError) as exc_info:
            EnvironmentContext(
                tenant_id=uuid4(),
                tenant_slug="acme",
                project_id=uuid4(),
                project_slug="proj",
                environment_id=uuid4(),
                environment_type="development",
                governance_category="non_production",
                unknown_field="should_fail",
            )

        assert "extra_forbidden" in str(exc_info.value)

    def test_environment_context_serialization(self) -> None:
        """Test EnvironmentContext can be serialized to dict."""
        from floe_core.compiler import EnvironmentContext

        context = EnvironmentContext(
            tenant_id=uuid4(),
            tenant_slug="acme",
            project_id=uuid4(),
            project_slug="proj",
            environment_id=uuid4(),
            environment_type="production",
            governance_category="production",
        )

        data = context.model_dump()
        assert "tenant_id" in data
        assert "tenant_slug" in data
        assert "environment_type" in data
        assert "governance_category" in data

    def test_environment_context_json_serialization(self) -> None:
        """Test EnvironmentContext can be serialized to JSON."""
        from floe_core.compiler import EnvironmentContext

        context = EnvironmentContext(
            tenant_id=uuid4(),
            tenant_slug="acme",
            project_id=uuid4(),
            project_slug="proj",
            environment_id=uuid4(),
            environment_type="staging",
            governance_category="non_production",
        )

        json_str = context.model_dump_json()
        assert '"tenant_slug":"acme"' in json_str
        assert '"environment_type":"staging"' in json_str

    def test_environment_context_empty_slugs(self) -> None:
        """Test slugs cannot be empty strings."""
        from floe_core.compiler import EnvironmentContext

        with pytest.raises(ValidationError):
            EnvironmentContext(
                tenant_id=uuid4(),
                tenant_slug="",  # Empty slug
                project_id=uuid4(),
                project_slug="proj",
                environment_id=uuid4(),
                environment_type="development",
                governance_category="non_production",
            )
