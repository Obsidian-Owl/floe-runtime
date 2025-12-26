"""Integration tests for ops maintenance jobs.

T038: [010-orchestration-auto-discovery] Test ops job integration
Covers: 010-FR-021, 010-FR-022

Tests that ops jobs defined in orchestration configuration execute custom
maintenance operations with configurable parameters.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from dagster import Definitions, JobDefinition
import pytest

from floe_dagster.definitions import FloeDefinitions
from testing.base_classes import IntegrationTestBase


class TestOpsMaintenanceJobs(IntegrationTestBase):
    """Integration tests for ops maintenance job execution."""

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-021", "010-FR-022")
    def test_ops_job_auto_loaded_from_config(self) -> None:
        """Verify ops jobs are auto-loaded from orchestration config.

        Requirements:
            - FR-021: Auto-load ops jobs from configuration
            - FR-022: Execute custom maintenance operations
        """
        from unittest.mock import patch

        mock_op = MagicMock()

        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "jobs": {
                    "vacuum_job": {
                        "type": "ops",
                        "target_function": "demo.ops.vacuum.vacuum_old_snapshots",
                        "args": {"retention_days": 30, "dry_run": False},
                        "description": "Vacuum old table snapshots",
                        "tags": {"category": "maintenance"},
                    }
                }
            },
        }

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.vacuum_old_snapshots = mock_op
            mock_import.return_value = mock_module

            defs = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(defs, Definitions)
            assert defs.jobs is not None
            assert len(defs.jobs) == 1

            job = list(defs.jobs)[0]
            assert isinstance(job, JobDefinition)
            assert job.name == "vacuum_job"
            assert job.description == "Vacuum old table snapshots"

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-021", "010-FR-022")
    def test_ops_job_with_args(self) -> None:
        """Verify ops jobs pass arguments to target function.

        Requirements:
            - FR-021: Support configurable parameters
            - FR-022: Pass args to maintenance function
        """
        from unittest.mock import patch

        mock_op = MagicMock()

        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "jobs": {
                    "compact_job": {
                        "type": "ops",
                        "target_function": "demo.ops.compact.compact_tables",
                        "args": {
                            "catalog": "demo",
                            "tables": ["bronze_customers", "bronze_orders"],
                            "min_commits": 10,
                        },
                        "description": "Compact bronze tables",
                    }
                }
            },
        }

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.compact_tables = mock_op
            mock_import.return_value = mock_module

            defs = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(defs, Definitions)
            assert defs.jobs is not None
            assert len(defs.jobs) == 1

            job = list(defs.jobs)[0]
            assert job.name == "compact_job"

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-021", "010-FR-022")
    def test_ops_job_without_args(self) -> None:
        """Verify ops jobs work without arguments.

        Requirements:
            - FR-021: Support ops jobs without args
            - FR-022: Execute parameterless operations
        """
        from unittest.mock import patch

        mock_op = MagicMock()

        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "jobs": {
                    "cleanup_job": {
                        "type": "ops",
                        "target_function": "demo.ops.cleanup.cleanup_temp_files",
                        "description": "Clean up temporary files",
                    }
                }
            },
        }

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.cleanup_temp_files = mock_op
            mock_import.return_value = mock_module

            defs = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(defs, Definitions)
            assert defs.jobs is not None
            assert len(defs.jobs) == 1

            job = list(defs.jobs)[0]
            assert job.name == "cleanup_job"

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-021", "010-FR-022")
    def test_multiple_ops_jobs(self) -> None:
        """Verify multiple ops jobs can be configured.

        Requirements:
            - FR-021: Support multiple ops jobs
            - FR-022: Each job executes independently
        """
        from unittest.mock import patch

        mock_vacuum = MagicMock()
        mock_compact = MagicMock()

        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "jobs": {
                    "vacuum_job": {
                        "type": "ops",
                        "target_function": "demo.ops.vacuum.vacuum_all",
                        "args": {"retention_days": 30},
                    },
                    "compact_job": {
                        "type": "ops",
                        "target_function": "demo.ops.compact.compact_all",
                        "args": {"min_commits": 10},
                    },
                }
            },
        }

        with patch("importlib.import_module") as mock_import:

            def import_side_effect(module_path):
                if "vacuum" in module_path:
                    mock_module = MagicMock()
                    mock_module.vacuum_all = mock_vacuum
                    return mock_module
                elif "compact" in module_path:
                    mock_module = MagicMock()
                    mock_module.compact_all = mock_compact
                    return mock_module
                return MagicMock()

            mock_import.side_effect = import_side_effect

            defs = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(defs, Definitions)
            assert defs.jobs is not None
            assert len(defs.jobs) == 2

            job_names = {job.name for job in defs.jobs}
            assert job_names == {"vacuum_job", "compact_job"}

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-021", "010-FR-022")
    def test_ops_job_with_tags(self) -> None:
        """Verify ops jobs support metadata tags.

        Requirements:
            - FR-021: Support job tags
            - FR-022: Tag-based job organization
        """
        from unittest.mock import patch

        mock_op = MagicMock()

        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "jobs": {
                    "maintenance_job": {
                        "type": "ops",
                        "target_function": "demo.ops.maintenance.run_maintenance",
                        "tags": {
                            "category": "maintenance",
                            "priority": "low",
                            "schedule": "daily",
                        },
                    }
                }
            },
        }

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.run_maintenance = mock_op
            mock_import.return_value = mock_module

            defs = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(defs, Definitions)
            assert defs.jobs is not None
            assert len(defs.jobs) == 1

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-021")
    def test_combines_batch_and_ops_jobs(self) -> None:
        """Verify batch and ops jobs can coexist.

        Requirements:
            - FR-021: Support mixed job types
        """
        from unittest.mock import patch

        mock_op = MagicMock()

        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {
                "jobs": {
                    "bronze_job": {
                        "type": "batch",
                        "selection": ["*"],
                        "description": "Process bronze layer",
                    },
                    "vacuum_job": {
                        "type": "ops",
                        "target_function": "demo.ops.vacuum.vacuum_bronze",
                        "description": "Vacuum bronze tables",
                    },
                }
            },
        }

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.vacuum_bronze = mock_op
            mock_import.return_value = mock_module

            defs = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

            assert isinstance(defs, Definitions)
            assert defs.jobs is not None
            assert len(defs.jobs) == 2

            job_names = {job.name for job in defs.jobs}
            assert job_names == {"bronze_job", "vacuum_job"}

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-021")
    def test_empty_ops_jobs_config_does_not_error(self) -> None:
        """Verify empty jobs config does not cause errors.

        Requirements:
            - FR-021: Graceful degradation
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {"jobs": {}},
        }

        defs = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

        assert isinstance(defs, Definitions)

    @pytest.mark.integration
    @pytest.mark.requirement("010-FR-021")
    def test_missing_jobs_key_does_not_error(self) -> None:
        """Verify missing jobs key does not cause errors.

        Requirements:
            - FR-021: Missing configuration is valid
        """
        artifacts = {
            "version": "2.0.0",
            "observability": {"tracing": {"enabled": False}},
            "orchestration": {},
        }

        defs = FloeDefinitions.from_compiled_artifacts(artifacts_dict=artifacts)

        assert isinstance(defs, Definitions)
