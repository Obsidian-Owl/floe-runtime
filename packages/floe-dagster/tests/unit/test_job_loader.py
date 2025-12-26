"""Unit tests for job loader.

T023: [010-orchestration-auto-discovery] job loader tests
Covers: 010-FR-011 through 010-FR-012

Tests the load_jobs function that converts JobDefinition to Dagster jobs.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from dagster import JobDefinition
from dagster._core.definitions.unresolved_asset_job_definition import UnresolvedAssetJobDefinition
import pytest

from floe_core.schemas.job_definition import BatchJob, OpsJob


class TestLoadJobs:
    """Tests for load_jobs function."""

    def test_load_jobs_with_empty_dict(self) -> None:
        """load_jobs should return empty list for empty input."""
        from floe_dagster.loaders.job_loader import load_jobs

        result = load_jobs({})

        assert result == []

    def test_load_jobs_with_batch_job(self) -> None:
        """load_jobs should create Dagster batch job from BatchJob."""
        from floe_dagster.loaders.job_loader import load_jobs

        jobs = {
            "bronze_refresh": BatchJob(
                type="batch",
                selection=["*"],
                description="Refresh bronze layer",
                tags={"layer": "bronze"},
            )
        }

        result = load_jobs(jobs)

        assert len(result) == 1
        assert isinstance(result[0], (JobDefinition, UnresolvedAssetJobDefinition))
        assert result[0].name == "bronze_refresh"

    def test_load_jobs_with_ops_job(self) -> None:
        """load_jobs should create Dagster ops job from OpsJob."""
        from floe_dagster.loaders.job_loader import load_jobs

        jobs = {
            "maintenance": OpsJob(
                type="ops",
                target_function="demo.ops.maintenance.vacuum_tables",
                args={"retention_days": 30},
                description="Vacuum old tables",
            )
        }

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_op_func = MagicMock()
            mock_module.vacuum_tables = mock_op_func
            mock_import.return_value = mock_module

            result = load_jobs(jobs)

            assert len(result) == 1
            assert isinstance(result[0], JobDefinition)
            assert result[0].name == "maintenance"

    def test_load_jobs_with_multiple_jobs(self) -> None:
        """load_jobs should handle multiple jobs."""
        from floe_dagster.loaders.job_loader import load_jobs

        jobs = {
            "bronze_job": BatchJob(
                type="batch",
                selection=["*"],
            ),
            "gold_job": BatchJob(
                type="batch",
                selection=["*"],
            ),
        }

        result = load_jobs(jobs)

        assert len(result) == 2
        job_names = [job.name for job in result]
        assert "bronze_job" in job_names
        assert "gold_job" in job_names

    def test_load_jobs_raises_on_unknown_job_type(self) -> None:
        """load_jobs should raise ValueError for unknown job type."""
        from floe_dagster.loaders.job_loader import load_jobs

        jobs = {"invalid": MagicMock(type="unknown_type")}

        with pytest.raises(ValueError) as exc_info:
            load_jobs(jobs)

        assert "Unknown job type" in str(exc_info.value)


class TestCreateBatchJob:
    """Tests for _create_batch_job helper."""

    def test_create_batch_job_with_minimal_config(self) -> None:
        """_create_batch_job should work with minimal config."""
        from floe_dagster.loaders.job_loader import _create_batch_job

        job_def = BatchJob(
            type="batch",
            selection=["*"],
        )

        result = _create_batch_job("test_job", job_def)

        assert isinstance(result, (JobDefinition, UnresolvedAssetJobDefinition))
        assert result.name == "test_job"

    def test_create_batch_job_with_multiple_selections(self) -> None:
        """_create_batch_job should combine multiple selections with *."""
        from floe_dagster.loaders.job_loader import _create_batch_job

        job_def = BatchJob(
            type="batch",
            selection=["*"],
        )

        result = _create_batch_job("multi_job", job_def)

        assert result.name == "multi_job"

    def test_create_batch_job_with_description(self) -> None:
        """_create_batch_job should include description."""
        from floe_dagster.loaders.job_loader import _create_batch_job

        job_def = BatchJob(
            type="batch",
            selection=["*"],
            description="Process bronze layer assets",
        )

        result = _create_batch_job("described_job", job_def)

        assert result.name == "described_job"
        assert result.description == "Process bronze layer assets"

    def test_create_batch_job_with_tags(self) -> None:
        """_create_batch_job should include tags."""
        from floe_dagster.loaders.job_loader import _create_batch_job

        job_def = BatchJob(
            type="batch",
            selection=["*"],
            tags={"layer": "bronze", "priority": "high"},
        )

        result = _create_batch_job("tagged_job", job_def)

        assert result.name == "tagged_job"


class TestCreateOpsJob:
    """Tests for _create_ops_job helper."""

    def test_create_ops_job_with_args(self) -> None:
        """_create_ops_job should pass args to op function."""
        from floe_dagster.loaders.job_loader import _create_ops_job

        job_def = OpsJob(
            type="ops",
            target_function="demo.ops.test.test_op",
            args={"param1": "value1"},
        )

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_op = MagicMock()
            mock_module.test_op = mock_op
            mock_import.return_value = mock_module

            result = _create_ops_job("ops_job", job_def)

            assert isinstance(result, JobDefinition)
            assert result.name == "ops_job"

    def test_create_ops_job_without_args(self) -> None:
        """_create_ops_job should work without args."""
        from floe_dagster.loaders.job_loader import _create_ops_job

        job_def = OpsJob(
            type="ops",
            target_function="demo.ops.test.no_args_op",
        )

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_op = MagicMock()
            mock_module.no_args_op = mock_op
            mock_import.return_value = mock_module

            result = _create_ops_job("no_args_job", job_def)

            assert result.name == "no_args_job"

    def test_create_ops_job_raises_on_import_error(self) -> None:
        """_create_ops_job should raise ImportError if target cannot be imported."""
        from floe_dagster.loaders.job_loader import _create_ops_job

        job_def = OpsJob(
            type="ops",
            target_function="nonexistent.module.function",
        )

        with patch("importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("No module named 'nonexistent'")

            with pytest.raises(ImportError) as exc_info:
                _create_ops_job("failing_job", job_def)

            assert "Cannot import nonexistent.module.function" in str(exc_info.value)

    def test_create_ops_job_raises_on_missing_function(self) -> None:
        """_create_ops_job should raise ImportError if function doesn't exist."""
        from floe_dagster.loaders.job_loader import _create_ops_job

        job_def = OpsJob(
            type="ops",
            target_function="demo.ops.test.missing_function",
        )

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            del mock_module.missing_function
            mock_import.return_value = mock_module

            with pytest.raises(ImportError) as exc_info:
                _create_ops_job("missing_func_job", job_def)

            assert "Cannot import demo.ops.test.missing_function" in str(exc_info.value)
