"""Abstract base class for ProfileGenerator adapter tests.

Following the dbt adapter testing pattern, this provides a standardized
test suite that all adapter implementations must pass.

Usage:
    class TestMyAdapter(BaseProfileGeneratorTests):
        @pytest.fixture
        def generator(self):
            from my_plugin import MyAdapter
            return MyAdapter()

        @property
        def target_type(self) -> str:
            return "my_adapter"

        @property
        def required_fields(self) -> set[str]:
            return {"type", "host", "threads"}

        def get_minimal_artifacts(self) -> dict[str, Any]:
            return {"compute": {"target": "my_adapter", "properties": {}}, ...}
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pytest

from floe_dbt.profiles.base import ProfileGenerator, ProfileGeneratorConfig


class BaseProfileGeneratorTests(ABC):
    """Abstract test suite for ProfileGenerator implementations.

    Concrete test classes inherit from this and implement abstract methods
    to specify adapter-specific behavior. All tests defined here are
    automatically inherited and run for each adapter.

    This pattern follows dbt's adapter testing approach where base classes
    define the contract and concrete classes inherit the test suite.

    Abstract Methods (must implement):
        generator: pytest fixture returning the ProfileGenerator instance
        target_type: Property returning the dbt adapter type (e.g., "duckdb")
        required_fields: Property returning required profile output fields
        get_minimal_artifacts: Method returning minimal CompiledArtifacts for testing

    Inherited Tests (run automatically):
        test_implements_protocol: Verifies Protocol compliance
        test_generate_returns_dict: Verifies return type
        test_generate_includes_target_name: Verifies output structure
        test_generate_has_correct_type: Verifies adapter type field
        test_generate_has_required_fields: Verifies all required fields present
        test_generate_uses_config_threads: Verifies thread configuration
        test_generate_custom_target_name: Verifies custom target name support
    """

    # =========================================================================
    # Abstract methods - must be implemented by concrete test classes
    # =========================================================================

    @pytest.fixture
    @abstractmethod
    def generator(self) -> ProfileGenerator:
        """Return an instance of the ProfileGenerator being tested.

        Example:
            @pytest.fixture
            def generator(self) -> ProfileGenerator:
                from floe_dbt.profiles.duckdb import DuckDBProfileGenerator
                return DuckDBProfileGenerator()
        """
        ...

    @property
    @abstractmethod
    def target_type(self) -> str:
        """Return the dbt adapter type (e.g., 'duckdb', 'snowflake').

        This must match the 'type' field in the generated profile.
        """
        ...

    @property
    @abstractmethod
    def required_fields(self) -> set[str]:
        """Return the required fields in the generated profile output.

        Example:
            @property
            def required_fields(self) -> set[str]:
                return {"type", "path", "threads"}  # DuckDB
        """
        ...

    @abstractmethod
    def get_minimal_artifacts(self) -> dict[str, Any]:
        """Return minimal CompiledArtifacts for this adapter.

        Should include only the required fields to generate a valid profile.

        Example:
            def get_minimal_artifacts(self) -> dict[str, Any]:
                return {
                    "version": "1.0.0",
                    "compute": {"target": "duckdb", "properties": {"path": ":memory:"}},
                    "transforms": [],
                }
        """
        ...

    # =========================================================================
    # Shared fixtures
    # =========================================================================

    @pytest.fixture
    def config(self) -> ProfileGeneratorConfig:
        """Standard profile generator config for testing."""
        return ProfileGeneratorConfig(
            profile_name="floe",
            target_name="dev",
            threads=4,
        )

    # =========================================================================
    # Shared test methods - inherited by all adapter test classes
    # =========================================================================

    def test_implements_protocol(self, generator: ProfileGenerator) -> None:
        """Test that generator implements ProfileGenerator protocol.

        This verifies the generator is runtime-checkable and compatible
        with the ProfileGenerator Protocol.
        """
        assert isinstance(generator, ProfileGenerator), (
            f"{type(generator).__name__} does not implement ProfileGenerator protocol"
        )

    def test_generate_returns_dict(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that generate returns a dictionary."""
        artifacts = self.get_minimal_artifacts()
        result = generator.generate(artifacts, config)
        assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"

    def test_generate_includes_target_name(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that output includes the target name as key."""
        artifacts = self.get_minimal_artifacts()
        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        assert config.target_name in result, (
            f"Expected target_name '{config.target_name}' in result keys: {list(result.keys())}"
        )

    def test_generate_has_correct_type(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that profile has correct adapter type."""
        artifacts = self.get_minimal_artifacts()
        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        profile = result[config.target_name]
        assert profile["type"] == self.target_type, (
            f"Expected type '{self.target_type}', got '{profile.get('type')}'"
        )

    def test_generate_has_required_fields(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that all required fields are present in the profile."""
        artifacts = self.get_minimal_artifacts()
        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        profile = result[config.target_name]

        missing_fields = self.required_fields - set(profile.keys())
        assert not missing_fields, (
            f"Missing required fields: {missing_fields}. Profile has: {set(profile.keys())}"
        )

    def test_generate_uses_config_threads(
        self,
        generator: ProfileGenerator,
    ) -> None:
        """Test that thread count from config is used."""
        config = ProfileGeneratorConfig(
            profile_name="floe",
            target_name="dev",
            threads=8,
        )
        artifacts = self.get_minimal_artifacts()
        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        profile = result[config.target_name]
        assert profile["threads"] == 8, f"Expected threads=8, got threads={profile.get('threads')}"

    def test_generate_custom_target_name(
        self,
        generator: ProfileGenerator,
    ) -> None:
        """Test generation with custom target name."""
        config = ProfileGeneratorConfig(
            profile_name="floe",
            target_name="custom_target",
            threads=4,
        )
        artifacts = self.get_minimal_artifacts()
        result = generator.generate(artifacts, config)

        assert "custom_target" in result, (
            f"Expected 'custom_target' in result, got: {list(result.keys())}"
        )
        assert "dev" not in result, "Default 'dev' target should not be present"

    def test_generate_with_different_environments(
        self,
        generator: ProfileGenerator,
    ) -> None:
        """Test generation with different environment configurations."""
        for env in ["dev", "staging", "prod"]:
            config = ProfileGeneratorConfig(
                profile_name="floe",
                target_name=env,
                environment=env,
                threads=4,
            )
            artifacts = self.get_minimal_artifacts()
            result = generator.generate(artifacts, config)

            assert env in result, f"Expected '{env}' in result for environment {env}"
            profile = result[env]
            assert profile["type"] == self.target_type


class BaseCredentialProfileGeneratorTests(BaseProfileGeneratorTests):
    """Extended base class for adapters that require credentials.

    Use this for adapters like Snowflake, Redshift, Databricks, PostgreSQL
    that need user/password or token authentication.

    Additional Tests:
        test_credentials_use_env_var_template: Verifies credentials use env_var()
        test_never_hardcodes_credentials: Verifies no plaintext credentials
    """

    @property
    @abstractmethod
    def credential_fields(self) -> set[str]:
        """Return the fields that should use env_var() template.

        Example:
            @property
            def credential_fields(self) -> set[str]:
                return {"user", "password"}  # Snowflake
        """
        ...

    def test_credentials_use_env_var_template(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that credentials use env_var() template syntax (FR-003)."""
        artifacts = self.get_minimal_artifacts()
        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        profile = result[config.target_name]

        for field in self.credential_fields:
            if field in profile:
                value = str(profile[field])
                assert "env_var" in value or field.upper() in value, (
                    f"Credential field '{field}' should use env_var() template. Got: {value}"
                )

    def test_never_hardcodes_credentials(
        self,
        generator: ProfileGenerator,
        config: ProfileGeneratorConfig,
    ) -> None:
        """Test that credentials are never hardcoded, even if provided."""
        artifacts = self.get_minimal_artifacts()

        # Add fake credentials to properties (should be ignored)
        compute = artifacts.get("compute", {})
        properties = compute.get("properties", {})
        properties["password"] = "secret123"
        properties["user"] = "admin"
        compute["properties"] = properties
        artifacts["compute"] = compute

        result = generator.generate(artifacts, config)
        assert config.target_name is not None
        profile = result[config.target_name]

        # Check that plaintext values are not used
        for field in self.credential_fields:
            if field in profile:
                value = str(profile[field])
                assert "secret123" not in value, (
                    f"Credential field '{field}' contains hardcoded password"
                )
                assert "env_var" in value or field.upper() in value, (
                    f"Credential field '{field}' should use env_var() template"
                )
