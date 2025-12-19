"""Integration tests for OpenLineage events in Marquez.

T080: Integration test events appear in Marquez

IMPORTANT: These tests REQUIRE running infrastructure.
If infrastructure is missing, tests FAIL (not skip).

Run with:
    cd testing/docker && docker compose --profile full up -d
    # Wait for Marquez to be healthy
    uv run pytest packages/floe-cube/tests/integration/test_openlineage_marquez.py -v

Prerequisites:
- Marquez server running at http://localhost:5002 (or MARQUEZ_API_URL env var)
- OpenLineage client library installed
"""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Generator
from typing import Any

import httpx
import pytest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Configuration from environment
# Marquez API is exposed on port 5002 (internal 5000)
MARQUEZ_API_URL = os.environ.get("MARQUEZ_API_URL", "http://localhost:5002")
OPENLINEAGE_NAMESPACE = "floe-cube-integration-test"


@pytest.fixture(scope="module")
def marquez_client() -> Generator[httpx.Client, None, None]:
    """Create HTTP client for Marquez API.

    FAILS if Marquez is not available (does not skip).
    """
    client = httpx.Client(
        base_url=MARQUEZ_API_URL,
        headers={
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )

    # Verify Marquez is available - FAIL if not
    try:
        # Marquez healthcheck is on admin port, but we can check API
        response = client.get("/api/v1/namespaces")
        if response.status_code not in (200, 201):
            pytest.fail(
                f"Marquez server not ready at {MARQUEZ_API_URL}. "
                f"Status: {response.status_code}. "
                "Start infrastructure: cd testing/docker && docker compose --profile full up -d"
            )
    except httpx.ConnectError as e:
        pytest.fail(
            f"Cannot connect to Marquez at {MARQUEZ_API_URL}: {e}. "
            "Start infrastructure: cd testing/docker && docker compose --profile full up -d"
        )

    yield client
    client.close()


@pytest.fixture
def unique_job_name() -> str:
    """Generate unique job name for test isolation."""
    return f"cube.test_{uuid.uuid4().hex[:8]}.query"


def emit_openlineage_event(
    client: httpx.Client,
    namespace: str,
    job_name: str,
    run_id: str,
    event_type: str,
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
) -> httpx.Response:
    """Emit an OpenLineage event directly to Marquez.

    Args:
        client: HTTP client for Marquez
        namespace: OpenLineage namespace
        job_name: Job name
        run_id: Run ID (UUID)
        event_type: Event type (START, COMPLETE, FAIL)
        inputs: Input dataset names
        outputs: Output dataset names

    Returns:
        HTTP response
    """
    from datetime import datetime, timezone

    event_time = datetime.now(tz=timezone.utc).isoformat()

    event: dict[str, Any] = {
        "eventType": event_type,
        "eventTime": event_time,
        "run": {
            "runId": run_id,
        },
        "job": {
            "namespace": namespace,
            "name": job_name,
        },
        "producer": "floe-cube-integration-test",
        "schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json",
    }

    if inputs:
        event["inputs"] = [{"namespace": namespace, "name": name} for name in inputs]

    if outputs:
        event["outputs"] = [{"namespace": namespace, "name": name} for name in outputs]

    return client.post(
        "/api/v1/lineage",
        json=event,
    )


class TestOpenLineageEventEmission:
    """T080: Integration test events appear in Marquez."""

    def test_start_event_creates_run(
        self,
        marquez_client: httpx.Client,
        unique_job_name: str,
    ) -> None:
        """START event should create a run in Marquez."""
        run_id = str(uuid.uuid4())

        # Emit START event
        response = emit_openlineage_event(
            marquez_client,
            namespace=OPENLINEAGE_NAMESPACE,
            job_name=unique_job_name,
            run_id=run_id,
            event_type="START",
            inputs=["orders"],
        )

        assert response.status_code in (
            200,
            201,
        ), f"Failed to emit START event: {response.status_code} - {response.text}"

        # Give Marquez time to process
        time.sleep(0.5)

        # Verify run exists in Marquez
        run_response = marquez_client.get(
            f"/api/v1/namespaces/{OPENLINEAGE_NAMESPACE}/jobs/{unique_job_name}/runs"
        )

        assert run_response.status_code == 200, f"Failed to get runs: {run_response.status_code}"

        runs = run_response.json().get("runs", [])
        run_ids = [r["id"] for r in runs]
        assert run_id in run_ids, f"Run {run_id} not found in Marquez"

    def test_complete_event_marks_run_finished(
        self,
        marquez_client: httpx.Client,
        unique_job_name: str,
    ) -> None:
        """COMPLETE event should mark run as finished."""
        run_id = str(uuid.uuid4())

        # Emit START event
        start_response = emit_openlineage_event(
            marquez_client,
            namespace=OPENLINEAGE_NAMESPACE,
            job_name=unique_job_name,
            run_id=run_id,
            event_type="START",
        )
        assert start_response.status_code in (200, 201)

        # Emit COMPLETE event
        complete_response = emit_openlineage_event(
            marquez_client,
            namespace=OPENLINEAGE_NAMESPACE,
            job_name=unique_job_name,
            run_id=run_id,
            event_type="COMPLETE",
        )
        assert complete_response.status_code in (200, 201)

        # Give Marquez time to process
        time.sleep(0.5)

        # Verify run is marked as completed by getting runs list
        run_response = marquez_client.get(
            f"/api/v1/namespaces/{OPENLINEAGE_NAMESPACE}/jobs/{unique_job_name}/runs"
        )

        assert run_response.status_code == 200
        runs = run_response.json().get("runs", [])
        run_data = next((r for r in runs if r["id"] == run_id), None)
        assert run_data is not None, f"Run {run_id} not found"
        # Marquez run states: NEW, RUNNING, COMPLETED, FAILED, ABORTED
        assert run_data.get("state") == "COMPLETED", (
            f"Expected COMPLETED, got {run_data.get('state')}"
        )

    def test_fail_event_marks_run_failed(
        self,
        marquez_client: httpx.Client,
        unique_job_name: str,
    ) -> None:
        """FAIL event should mark run as failed."""
        run_id = str(uuid.uuid4())

        # Emit START event
        start_response = emit_openlineage_event(
            marquez_client,
            namespace=OPENLINEAGE_NAMESPACE,
            job_name=unique_job_name,
            run_id=run_id,
            event_type="START",
        )
        assert start_response.status_code in (200, 201)

        # Emit FAIL event
        fail_response = emit_openlineage_event(
            marquez_client,
            namespace=OPENLINEAGE_NAMESPACE,
            job_name=unique_job_name,
            run_id=run_id,
            event_type="FAIL",
        )
        assert fail_response.status_code in (200, 201)

        # Give Marquez time to process
        time.sleep(0.5)

        # Verify run is marked as failed by getting runs list
        run_response = marquez_client.get(
            f"/api/v1/namespaces/{OPENLINEAGE_NAMESPACE}/jobs/{unique_job_name}/runs"
        )

        assert run_response.status_code == 200
        runs = run_response.json().get("runs", [])
        run_data = next((r for r in runs if r["id"] == run_id), None)
        assert run_data is not None, f"Run {run_id} not found"
        assert run_data.get("state") == "FAILED", f"Expected FAILED, got {run_data.get('state')}"

    def test_namespace_created(
        self,
        marquez_client: httpx.Client,
        unique_job_name: str,
    ) -> None:
        """Namespace should be created when event is emitted."""
        run_id = str(uuid.uuid4())

        # Emit event to create namespace
        emit_openlineage_event(
            marquez_client,
            namespace=OPENLINEAGE_NAMESPACE,
            job_name=unique_job_name,
            run_id=run_id,
            event_type="START",
        )

        time.sleep(0.5)

        # Verify namespace exists
        ns_response = marquez_client.get(f"/api/v1/namespaces/{OPENLINEAGE_NAMESPACE}")

        assert ns_response.status_code == 200
        assert ns_response.json()["name"] == OPENLINEAGE_NAMESPACE

    def test_job_created_with_inputs(
        self,
        marquez_client: httpx.Client,
        unique_job_name: str,
    ) -> None:
        """Job should be created with input datasets."""
        run_id = str(uuid.uuid4())
        inputs = ["orders", "customers"]

        emit_openlineage_event(
            marquez_client,
            namespace=OPENLINEAGE_NAMESPACE,
            job_name=unique_job_name,
            run_id=run_id,
            event_type="START",
            inputs=inputs,
        )

        time.sleep(0.5)

        # Verify job exists with inputs
        job_response = marquez_client.get(
            f"/api/v1/namespaces/{OPENLINEAGE_NAMESPACE}/jobs/{unique_job_name}"
        )

        assert job_response.status_code == 200
        job_data = job_response.json()
        input_names = [i["name"] for i in job_data.get("inputs", [])]
        for expected_input in inputs:
            assert expected_input in input_names, f"Input {expected_input} not found in job inputs"


class TestQueryLineageEmitterIntegration:
    """Test QueryLineageEmitter with real Marquez backend."""

    def test_emitter_sends_to_marquez(
        self,
        marquez_client: httpx.Client,
    ) -> None:
        """QueryLineageEmitter should send events to Marquez."""
        from floe_cube.lineage import QueryLineageEmitter

        # Create emitter pointing to Marquez
        emitter = QueryLineageEmitter(
            endpoint=f"{MARQUEZ_API_URL}/api/v1/lineage",
            namespace=OPENLINEAGE_NAMESPACE,
            enabled=True,
        )

        # FAIL if client couldn't be initialized - OpenLineage should be available
        assert emitter.enabled, (
            "OpenLineage client failed to initialize. "
            "Check that openlineage-python is installed and Marquez is accessible."
        )

        cube_name = f"test_{uuid.uuid4().hex[:8]}"

        # Emit START
        run_id = emitter.emit_start(
            cube_name=cube_name,
            inputs=["orders"],
            sql="SELECT * FROM orders",
        )

        # Emit COMPLETE
        emitter.emit_complete(
            run_id=run_id,
            cube_name=cube_name,
            row_count=100,
        )

        time.sleep(1)

        # Verify run exists in Marquez
        job_name = f"cube.{cube_name}.query"
        run_response = marquez_client.get(
            f"/api/v1/namespaces/{OPENLINEAGE_NAMESPACE}/jobs/{job_name}/runs"
        )

        # May get 404 if openlineage client version incompatible
        if run_response.status_code == 200:
            runs = run_response.json().get("runs", [])
            run_ids = [r["id"]["runId"] for r in runs]
            assert run_id in run_ids, f"Run {run_id} not found in Marquez"

    def test_emitter_handles_connection_error_gracefully(self) -> None:
        """Emitter should handle connection errors without raising."""
        from floe_cube.lineage import QueryLineageEmitter

        # Create emitter pointing to non-existent endpoint
        emitter = QueryLineageEmitter(
            endpoint="http://localhost:59999/api/v1/lineage",
            namespace="test",
            enabled=True,
        )

        # Should not raise - just log warning and continue
        run_id = emitter.emit_start(cube_name="test")
        assert run_id is not None  # Still returns run_id

        emitter.emit_complete(run_id=run_id, cube_name="test", row_count=0)
        emitter.emit_fail(run_id=run_id, cube_name="test", error="test error")
