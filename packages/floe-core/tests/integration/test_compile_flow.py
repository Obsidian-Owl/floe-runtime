"""Integration test for full compile flow.

T038: [US2] Integration test for full compile flow

Tests the complete compilation pipeline from floe.yaml to CompiledArtifacts.

Covers:
- FR-008: floe-core MUST have integration tests covering YAML loading,
  compilation flow, and round-trip serialization
- FR-022: Integration tests MUST validate that CompiledArtifacts generated in
  Docker environments work correctly with production-like configurations
- FR-031: Integration tests MUST verify CompiledArtifacts without optional
  EnvironmentContext fields still execute correctly (standalone mode)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


class TestFullCompileFlow:
    """Integration tests for the complete compile workflow."""

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-016")
    @pytest.mark.requirement("001-FR-009")
    @pytest.mark.requirement("001-FR-010")
    def test_end_to_end_compile_minimal(self, tmp_path: Path) -> None:
        """Test end-to-end compilation with minimal configuration.

        Covers:
        - 001-FR-016: Compiler accepts FloeSpec, returns CompiledArtifacts
        - 001-FR-009: CompiledArtifacts is immutable Pydantic model
        - 001-FR-010: Metadata section includes compiled_at, source_hash
        """
        from floe_core.compiler import CompiledArtifacts, Compiler

        # Create minimal floe.yaml
        project_dir = tmp_path / "minimal-project"
        project_dir.mkdir()

        # Create platform.yaml
        platform_config = {
            "version": "1.0.0",
            "storage": {"default": {"bucket": "test-bucket"}},
            "catalogs": {
                "default": {
                    "uri": "http://polaris:8181/api/catalog",
                    "warehouse": "test-warehouse",
                }
            },
            "compute": {"default": {"type": "duckdb"}},
        }

        (project_dir / "platform.yaml").write_text(yaml.dump(platform_config))

        floe_config = {
            "name": "minimal-project",
            "version": "1.0.0",
            "compute": "default",
            "transforms": [{"type": "dbt", "path": "./dbt"}],
        }

        (project_dir / "floe.yaml").write_text(yaml.dump(floe_config))

        # Compile
        compiler = Compiler()
        artifacts = compiler.compile(project_dir / "floe.yaml")

        # Verify output
        assert isinstance(artifacts, CompiledArtifacts)
        assert artifacts.version == "1.0.0"
        assert artifacts.resolved_profiles is not None
        assert artifacts.resolved_profiles.compute.type.value == "duckdb"
        assert len(artifacts.transforms) == 1
        assert artifacts.transforms[0].type == "dbt"

        # Verify metadata
        assert artifacts.metadata.compiled_at is not None
        assert artifacts.metadata.floe_core_version is not None
        assert artifacts.metadata.source_hash is not None

        # Verify defaults
        assert artifacts.consumption.enabled is False
        assert artifacts.governance.classification_source == "dbt_meta"
        assert artifacts.observability.traces is True

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("006-FR-022")
    @pytest.mark.requirement("001-FR-016")
    @pytest.mark.requirement("001-FR-011")
    @pytest.mark.requirement("001-FR-028")
    def test_end_to_end_compile_full(self, tmp_path: Path) -> None:
        """Test end-to-end compilation with full configuration.

        Covers:
        - 006-FR-008: Integration test for compilation flow
        - 006-FR-022: CompiledArtifacts with production-like configurations
        - 001-FR-016: Compiler accepts FloeSpec, returns CompiledArtifacts
        - 001-FR-011: CompiledArtifacts sections (compute, consumption, governance, observability)
        - 001-FR-028: CatalogConfig includes type, uri, warehouse, scope
        """
        from floe_core.compiler import Compiler

        # Create full floe.yaml
        project_dir = tmp_path / "full-project"
        project_dir.mkdir()

        # Create platform.yaml with snowflake profile
        # Note: scope is inside credentials, not at catalog level
        platform_config = {
            "version": "1.0.0",
            "storage": {"default": {"bucket": "test-bucket"}},
            "catalogs": {
                "default": {
                    "type": "polaris",
                    "uri": "https://polaris.example.com/api/catalog",
                    "warehouse": "my_warehouse",
                    "credentials": {
                        "mode": "oauth2",
                        "client_id": "test-client",
                        "client_secret": {"secret_ref": "polaris-secret"},
                        "scope": "PRINCIPAL_ROLE:ALL",
                    },
                }
            },
            "compute": {
                "snowflake": {
                    "type": "snowflake",
                    "properties": {
                        "account": "xy12345.us-east-1",
                        "warehouse": "COMPUTE_WH",
                    },
                    "credentials": {
                        "mode": "static",
                        "secret_ref": "snowflake-creds",
                    },
                }
            },
        }

        (project_dir / "platform.yaml").write_text(yaml.dump(platform_config))

        floe_config = {
            "name": "full-project",
            "version": "2.0.0",
            "compute": "snowflake",
            "transforms": [
                {"type": "dbt", "path": "./dbt", "target": "prod"},
            ],
            "consumption": {
                "enabled": True,
                "database_type": "snowflake",
                "port": 8080,
                "pre_aggregations": {"refresh_schedule": "0 * * * *"},
                "security": {"row_level": True, "filter_column": "org_id"},
            },
            "governance": {
                "classification_source": "dbt_meta",
                "emit_lineage": True,
            },
            "observability": {
                "traces": True,
                "metrics": True,
                "lineage": True,
                "otlp_endpoint": "http://otel-collector:4317",
            },
        }

        (project_dir / "floe.yaml").write_text(yaml.dump(floe_config))

        # Compile
        compiler = Compiler()
        artifacts = compiler.compile(project_dir / "floe.yaml")

        # Verify all sections
        assert artifacts.resolved_profiles is not None
        assert artifacts.resolved_profiles.compute.type.value == "snowflake"
        assert artifacts.resolved_profiles.compute.credentials.secret_ref == "snowflake-creds"
        assert artifacts.consumption.enabled is True
        assert artifacts.consumption.database_type == "snowflake"
        assert artifacts.governance.emit_lineage is True
        assert artifacts.observability.otlp_endpoint == "http://otel-collector:4317"
        assert artifacts.resolved_profiles.catalog is not None
        assert artifacts.resolved_profiles.catalog.type.value == "polaris"
        # Scope is now inside credentials
        assert artifacts.resolved_profiles.catalog.credentials.scope == "PRINCIPAL_ROLE:ALL"

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-018")
    def test_end_to_end_with_dbt_classifications(self, tmp_path: Path) -> None:
        """Test end-to-end compilation with dbt classification extraction.

        Covers:
        - 006-FR-008: Compilation flow with classification extraction
        - 001-FR-018: Extract column classifications from dbt manifest meta tags
        """
        from floe_core.compiler import Compiler

        # Create project
        project_dir = tmp_path / "classified-project"
        project_dir.mkdir()

        # Create platform.yaml
        platform_config = {
            "version": "1.0.0",
            "storage": {"default": {"bucket": "test-bucket"}},
            "catalogs": {
                "default": {
                    "uri": "http://polaris:8181/api/catalog",
                    "warehouse": "test-warehouse",
                }
            },
            "compute": {"default": {"type": "duckdb"}},
        }

        (project_dir / "platform.yaml").write_text(yaml.dump(platform_config))

        floe_config = {
            "name": "classified-project",
            "version": "1.0.0",
            "compute": "default",
            "transforms": [{"type": "dbt", "path": "./dbt"}],
            "governance": {"classification_source": "dbt_meta"},
        }

        (project_dir / "floe.yaml").write_text(yaml.dump(floe_config))

        # Create dbt project with manifest
        dbt_dir = project_dir / "dbt"
        dbt_dir.mkdir()
        (dbt_dir / "dbt_project.yml").write_text("name: test_dbt\nversion: 1.0.0")

        target_dir = dbt_dir / "target"
        target_dir.mkdir()

        manifest = {
            "nodes": {
                "model.test.customers": {
                    "name": "customers",
                    "resource_type": "model",
                    "columns": {
                        "email": {
                            "name": "email",
                            "meta": {
                                "floe": {
                                    "classification": "pii",
                                    "pii_type": "email",
                                    "sensitivity": "high",
                                }
                            },
                        },
                        "phone": {
                            "name": "phone",
                            "meta": {
                                "floe": {
                                    "classification": "pii",
                                    "pii_type": "phone",
                                    "sensitivity": "high",
                                }
                            },
                        },
                        "revenue": {
                            "name": "revenue",
                            "meta": {
                                "floe": {
                                    "classification": "financial",
                                    "sensitivity": "medium",
                                }
                            },
                        },
                    },
                },
                "model.test.orders": {
                    "name": "orders",
                    "resource_type": "model",
                    "columns": {
                        "order_id": {
                            "name": "order_id",
                            "meta": {
                                "floe": {
                                    "classification": "identifier",
                                }
                            },
                        },
                    },
                },
            },
            "sources": {},
        }

        (target_dir / "manifest.json").write_text(json.dumps(manifest))

        # Compile
        compiler = Compiler()
        artifacts = compiler.compile(project_dir / "floe.yaml")

        # Verify classifications extracted
        assert artifacts.column_classifications is not None
        assert "customers" in artifacts.column_classifications
        assert "orders" in artifacts.column_classifications

        # Verify customer classifications
        customer_cols = artifacts.column_classifications["customers"]
        assert "email" in customer_cols
        assert customer_cols["email"].classification == "pii"
        assert customer_cols["email"].pii_type == "email"
        assert customer_cols["email"].sensitivity == "high"

        assert "phone" in customer_cols
        assert customer_cols["phone"].pii_type == "phone"

        assert "revenue" in customer_cols
        assert customer_cols["revenue"].classification == "financial"

        # Verify order classifications
        order_cols = artifacts.column_classifications["orders"]
        assert "order_id" in order_cols
        assert order_cols["order_id"].classification == "identifier"

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-009")
    def test_compile_then_serialize_round_trip(self, tmp_path: Path) -> None:
        """Test compile output can be serialized and deserialized.

        Covers:
        - 006-FR-008: Round-trip serialization
        - 001-FR-009: CompiledArtifacts is immutable and JSON-serializable
        """
        from floe_core.compiler import CompiledArtifacts, Compiler

        # Create project
        project_dir = tmp_path / "serialize-project"
        project_dir.mkdir()

        # Create platform.yaml
        platform_config = {
            "version": "1.0.0",
            "storage": {"default": {"bucket": "test-bucket"}},
            "catalogs": {
                "default": {
                    "uri": "http://polaris:8181/api/catalog",
                    "warehouse": "test-warehouse",
                }
            },
            "compute": {"default": {"type": "bigquery"}},
        }

        (project_dir / "platform.yaml").write_text(yaml.dump(platform_config))

        floe_config = {
            "name": "serialize-project",
            "version": "1.0.0",
            "compute": "default",
            "transforms": [{"type": "dbt", "path": "./dbt"}],
        }

        (project_dir / "floe.yaml").write_text(yaml.dump(floe_config))

        # Compile
        compiler = Compiler()
        original = compiler.compile(project_dir / "floe.yaml")

        # Serialize to JSON
        json_str = original.model_dump_json()

        # Write to file and read back
        output_file = tmp_path / "artifacts.json"
        output_file.write_text(json_str)
        loaded_json = output_file.read_text()

        # Deserialize
        loaded = CompiledArtifacts.model_validate_json(loaded_json)

        # Verify round-trip
        assert loaded.version == original.version
        assert loaded.resolved_profiles is not None
        assert original.resolved_profiles is not None
        assert loaded.resolved_profiles.compute.type == original.resolved_profiles.compute.type
        assert loaded.metadata.source_hash == original.metadata.source_hash

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("001-FR-005")
    def test_compile_multiple_transforms(self, tmp_path: Path) -> None:
        """Test compilation with multiple transform configurations.

        Covers:
        - 006-FR-008: Compilation flow with multiple transforms
        - 001-FR-005: TransformConfig for each dbt project reference
        """
        from floe_core.compiler import Compiler

        project_dir = tmp_path / "multi-transform"
        project_dir.mkdir()

        # Create platform.yaml
        platform_config = {
            "version": "1.0.0",
            "storage": {"default": {"bucket": "test-bucket"}},
            "catalogs": {
                "default": {
                    "uri": "http://polaris:8181/api/catalog",
                    "warehouse": "test-warehouse",
                }
            },
            "compute": {"default": {"type": "duckdb"}},
        }

        (project_dir / "platform.yaml").write_text(yaml.dump(platform_config))

        floe_config = {
            "name": "multi-transform",
            "version": "1.0.0",
            "compute": "default",
            "transforms": [
                {"type": "dbt", "path": "./dbt/staging"},
                {"type": "dbt", "path": "./dbt/marts", "target": "prod"},
            ],
        }

        (project_dir / "floe.yaml").write_text(yaml.dump(floe_config))

        compiler = Compiler()
        artifacts = compiler.compile(project_dir / "floe.yaml")

        assert len(artifacts.transforms) == 2
        assert artifacts.transforms[0].path == "./dbt/staging"
        assert artifacts.transforms[0].target is None
        assert artifacts.transforms[1].path == "./dbt/marts"
        assert artifacts.transforms[1].target == "prod"

    @pytest.mark.requirement("006-FR-008")
    @pytest.mark.requirement("006-FR-022")
    @pytest.mark.requirement("001-FR-002")
    @pytest.mark.requirement("001-FR-003")
    def test_compile_all_compute_targets(self, tmp_path: Path) -> None:
        """Test compilation works for all compute targets.

        Covers:
        - 006-FR-008: Integration test for compilation flow
        - 006-FR-022: CompiledArtifacts with production-like configurations
        - 001-FR-002: Support 7 compute targets (Snowflake, BigQuery, Redshift, etc.)
        - 001-FR-003: ComputeTarget enum with target values
        """
        from floe_core.compiler import Compiler
        from floe_core.schemas import ComputeTarget

        targets = list(ComputeTarget)

        for target in targets:
            project_dir = tmp_path / f"project-{target.value}"
            project_dir.mkdir()

            # Create platform.yaml with profile for each target
            platform_config = {
                "version": "1.0.0",
                "storage": {"default": {"bucket": "test-bucket"}},
                "catalogs": {
                    "default": {
                        "uri": "http://polaris:8181/api/catalog",
                        "warehouse": "test-warehouse",
                    }
                },
                "compute": {"default": {"type": target.value}},
            }

            (project_dir / "platform.yaml").write_text(yaml.dump(platform_config))

            floe_config = {
                "name": f"project-{target.value}",
                "version": "1.0.0",
                "compute": "default",
                "transforms": [{"type": "dbt", "path": "./dbt"}],
            }

            (project_dir / "floe.yaml").write_text(yaml.dump(floe_config))

            compiler = Compiler()
            artifacts = compiler.compile(project_dir / "floe.yaml")

            assert artifacts.resolved_profiles is not None
            assert artifacts.resolved_profiles.compute.type == target


class TestCompileFlowGracefulDegradation:
    """Tests for graceful degradation in compile flow."""

    @pytest.mark.requirement("006-FR-031")
    @pytest.mark.requirement("001-FR-025")
    def test_compile_without_dbt_manifest(self, tmp_path: Path) -> None:
        """Test compilation continues without dbt manifest.

        Covers:
        - 006-FR-031: CompiledArtifacts without optional fields execute correctly
        - 001-FR-025: Graceful degradation when dbt manifest missing
        """
        from floe_core.compiler import Compiler

        project_dir = tmp_path / "no-manifest"
        project_dir.mkdir()

        # Create platform.yaml
        platform_config = {
            "version": "1.0.0",
            "storage": {"default": {"bucket": "test-bucket"}},
            "catalogs": {
                "default": {
                    "uri": "http://polaris:8181/api/catalog",
                    "warehouse": "test-warehouse",
                }
            },
            "compute": {"default": {"type": "duckdb"}},
        }

        (project_dir / "platform.yaml").write_text(yaml.dump(platform_config))

        floe_config = {
            "name": "no-manifest",
            "version": "1.0.0",
            "compute": "default",
            "transforms": [{"type": "dbt", "path": "./dbt"}],
        }

        (project_dir / "floe.yaml").write_text(yaml.dump(floe_config))

        # Create dbt project without manifest
        dbt_dir = project_dir / "dbt"
        dbt_dir.mkdir()
        (dbt_dir / "dbt_project.yml").write_text("name: test\nversion: 1.0.0")

        compiler = Compiler()
        artifacts = compiler.compile(project_dir / "floe.yaml")

        # Should succeed without classifications
        assert artifacts is not None
        assert artifacts.column_classifications is None

    @pytest.mark.requirement("006-FR-031")
    @pytest.mark.requirement("001-FR-025")
    def test_compile_with_empty_manifest(self, tmp_path: Path) -> None:
        """Test compilation handles empty manifest.

        Covers:
        - 006-FR-031: Graceful degradation with empty manifest
        - 001-FR-025: Graceful degradation when manifest has no classifications
        """
        from floe_core.compiler import Compiler

        project_dir = tmp_path / "empty-manifest"
        project_dir.mkdir()

        # Create platform.yaml
        platform_config = {
            "version": "1.0.0",
            "storage": {"default": {"bucket": "test-bucket"}},
            "catalogs": {
                "default": {
                    "uri": "http://polaris:8181/api/catalog",
                    "warehouse": "test-warehouse",
                }
            },
            "compute": {"default": {"type": "duckdb"}},
        }

        (project_dir / "platform.yaml").write_text(yaml.dump(platform_config))

        floe_config = {
            "name": "empty-manifest",
            "version": "1.0.0",
            "compute": "default",
            "transforms": [{"type": "dbt", "path": "./dbt"}],
        }

        (project_dir / "floe.yaml").write_text(yaml.dump(floe_config))

        # Create dbt project with empty manifest
        dbt_dir = project_dir / "dbt"
        dbt_dir.mkdir()
        (dbt_dir / "dbt_project.yml").write_text("name: test\nversion: 1.0.0")

        target_dir = dbt_dir / "target"
        target_dir.mkdir()
        (target_dir / "manifest.json").write_text(json.dumps({"nodes": {}, "sources": {}}))

        compiler = Compiler()
        artifacts = compiler.compile(project_dir / "floe.yaml")

        # Should succeed with no classifications
        assert artifacts is not None
        assert artifacts.column_classifications is None or artifacts.column_classifications == {}

    @pytest.mark.requirement("006-FR-031")
    @pytest.mark.requirement("001-FR-020")
    def test_compile_standalone_first(self, tmp_path: Path) -> None:
        """Test compile works completely standalone (no SaaS dependencies).

        Covers:
        - 006-FR-031: CompiledArtifacts without optional EnvironmentContext
          fields still execute correctly in standalone mode
        - 001-FR-020: Standalone execution without SaaS context
        """
        from floe_core.compiler import Compiler

        project_dir = tmp_path / "standalone"
        project_dir.mkdir()

        # Create platform.yaml
        platform_config = {
            "version": "1.0.0",
            "storage": {"default": {"bucket": "test-bucket"}},
            "catalogs": {
                "default": {
                    "uri": "http://polaris:8181/api/catalog",
                    "warehouse": "test-warehouse",
                }
            },
            "compute": {"default": {"type": "duckdb"}},
        }

        (project_dir / "platform.yaml").write_text(yaml.dump(platform_config))

        # Minimal standalone config
        floe_config = {
            "name": "standalone",
            "version": "1.0.0",
            "compute": "default",
            "transforms": [{"type": "dbt", "path": "./dbt"}],
        }

        (project_dir / "floe.yaml").write_text(yaml.dump(floe_config))

        compiler = Compiler()
        artifacts = compiler.compile(project_dir / "floe.yaml")

        # Verify standalone operation
        assert artifacts is not None
        assert artifacts.environment_context is None  # No SaaS context
        assert artifacts.lineage_namespace is None  # No SaaS namespace

        # All core functionality works
        assert artifacts.resolved_profiles is not None
        assert artifacts.resolved_profiles.compute.type.value == "duckdb"
        assert artifacts.governance.classification_source == "dbt_meta"
        assert artifacts.observability.traces is True
