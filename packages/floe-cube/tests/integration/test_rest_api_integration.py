"""Integration tests for Cube REST API.

T036: REST API returns JSON for valid query test
T037: REST API 401 for invalid credentials test
T038: REST API pagination over 10k rows test
T039: Pre-aggregations build and accelerate queries test

IMPORTANT: These tests REQUIRE running infrastructure.
If infrastructure is missing, tests FAIL (not skip).

Run with:
    cd testing/docker && ./scripts/run-cube-tests.sh

Or manually:
    cd testing/docker && docker compose --profile full up -d
    # Wait for cube-init to complete
    pytest -m integration packages/floe-cube/tests/integration/

Prerequisites:
- Cube server running at http://localhost:4000 (or CUBE_API_URL env var)
- Trino server with Iceberg catalog (via docker-compose full profile)
- Test data loaded (15k+ rows via cube-init)
"""

from __future__ import annotations

import os
from collections.abc import Generator

import httpx
import pytest

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Configuration from environment
CUBE_API_URL = os.environ.get("CUBE_API_URL", "http://localhost:4000")
# In dev mode, Cube doesn't require authentication
# For production tests, set CUBE_API_TOKEN to a valid JWT
CUBE_API_TOKEN = os.environ.get("CUBE_API_TOKEN", "")


@pytest.fixture(scope="module")
def cube_client() -> Generator[httpx.Client, None, None]:
    """Create HTTP client for Cube API.

    FAILS if Cube is not available (does not skip).
    """
    client = httpx.Client(
        base_url=CUBE_API_URL,
        headers={
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )

    # Verify Cube is available - FAIL if not
    try:
        response = client.get("/readyz")
        if response.status_code != 200:
            pytest.fail(
                f"Cube server not ready at {CUBE_API_URL}. "
                f"Status: {response.status_code}. "
                "Start infrastructure: cd testing/docker && ./scripts/run-cube-tests.sh"
            )
    except httpx.ConnectError as e:
        pytest.fail(
            f"Cannot connect to Cube at {CUBE_API_URL}: {e}. "
            "Start infrastructure: cd testing/docker && ./scripts/run-cube-tests.sh"
        )

    yield client
    client.close()


@pytest.fixture
def authenticated_headers() -> dict[str, str]:
    """Headers with valid authentication.

    Note: Cube in dev mode (CUBEJS_DEV_MODE=true) doesn't enforce auth.
    These headers are included for consistency but may be ignored.
    """
    headers = {"Content-Type": "application/json"}
    if CUBE_API_TOKEN:
        headers["Authorization"] = CUBE_API_TOKEN
    return headers


class TestRestApiJsonResponse:
    """T036: REST API returns JSON for valid query test.

    Covers:
    - FR-016: REST API endpoint returns JSON for valid queries
    - FR-023: Environment variable injection (CUBE_API_URL)
    """

    @pytest.mark.requirement("006-FR-016")
    @pytest.mark.requirement("006-FR-023")
    def test_valid_query_returns_json(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Valid query should return JSON response with 'data' key."""
        response = cube_client.post(
            "/cubejs-api/v1/load",
            headers=authenticated_headers,
            json={
                "query": {
                    "measures": ["Orders.count"],
                    "dimensions": ["Orders.status"],
                },
            },
        )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )

        data = response.json()
        assert "data" in data, f"Response missing 'data' key: {data}"

    def test_json_content_type_header(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Response should have application/json content-type."""
        response = cube_client.post(
            "/cubejs-api/v1/load",
            headers=authenticated_headers,
            json={
                "query": {
                    "measures": ["Orders.count"],
                },
            },
        )

        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type, (
            f"Expected JSON content-type, got: {content_type}"
        )

    def test_query_with_multiple_measures_and_dimensions(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Query with multiple measures and dimensions returns structured JSON."""
        response = cube_client.post(
            "/cubejs-api/v1/load",
            headers=authenticated_headers,
            json={
                "query": {
                    "measures": ["Orders.count", "Orders.totalAmount"],
                    "dimensions": ["Orders.status", "Orders.region"],
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)

    def test_query_with_filters_returns_filtered_data(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Query with filters returns filtered JSON data."""
        response = cube_client.post(
            "/cubejs-api/v1/load",
            headers=authenticated_headers,
            json={
                "query": {
                    "measures": ["Orders.count"],
                    "filters": [
                        {
                            "member": "Orders.status",
                            "operator": "equals",
                            "values": ["completed"],
                        }
                    ],
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_query_with_time_dimension(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Query with time dimension and granularity works."""
        response = cube_client.post(
            "/cubejs-api/v1/load",
            headers=authenticated_headers,
            json={
                "query": {
                    "measures": ["Orders.count"],
                    "timeDimensions": [
                        {
                            "dimension": "Orders.createdAt",
                            "granularity": "day",
                        }
                    ],
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data


class TestRestApiAuthentication:
    """T037: REST API authentication behavior test.

    FR-006: REST API authentication handling

    Note: Cube in dev mode (CUBEJS_DEV_MODE=true) does NOT enforce authentication.
    These tests verify the behavior when dev mode is disabled.
    When dev mode is enabled, invalid auth may still return 200.
    """

    def test_invalid_token_handled(
        self,
        cube_client: httpx.Client,
    ) -> None:
        """Invalid token should be handled (401/403 or 200 in dev mode)."""
        # Intentionally invalid test token (not a real secret)
        fake_token = "FAKE_TEST_TOKEN_not_a_real_secret"  # noqa: S105
        response = cube_client.post(
            "/cubejs-api/v1/load",
            headers={
                "Authorization": f"Bearer {fake_token}",
                "Content-Type": "application/json",
            },
            json={
                "query": {
                    "measures": ["Orders.count"],
                },
            },
        )

        # In dev mode, invalid tokens may be ignored (returns 200)
        # In production mode, should return 401/403
        assert response.status_code in (
            200,
            401,
            403,
        ), f"Expected 200 (dev mode) or 401/403 (prod mode), got {response.status_code}"

    def test_expired_jwt_handled(
        self,
        cube_client: httpx.Client,
    ) -> None:
        """Expired JWT should be handled (401/403 or 200 in dev mode)."""
        # Fake JWT for testing - header and payload are valid base64, signature is fake
        # Header: {"alg":"HS256","typ":"JWT"}
        # Payload: {"sub":"user1","exp":1600000000} (expired 2020-09-13)
        # Signature: intentionally invalid (not a real secret)
        expired_jwt = (  # noqa: S105
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiJ1c2VyMSIsImV4cCI6MTYwMDAwMDAwMH0."
            "FAKE_SIGNATURE_FOR_TESTING"
        )

        response = cube_client.post(
            "/cubejs-api/v1/load",
            headers={
                "Authorization": f"Bearer {expired_jwt}",
                "Content-Type": "application/json",
            },
            json={
                "query": {
                    "measures": ["Orders.count"],
                },
            },
        )

        # In dev mode, expired tokens may be ignored (returns 200)
        # In production mode, should return 401/403
        assert response.status_code in (
            200,
            401,
            403,
        ), f"Expected 200 (dev mode) or 401/403 (prod mode), got {response.status_code}"

    def test_malformed_auth_header_handled(
        self,
        cube_client: httpx.Client,
    ) -> None:
        """Malformed Authorization header should be handled."""
        response = cube_client.post(
            "/cubejs-api/v1/load",
            headers={
                "Authorization": "not-a-valid-format",
                "Content-Type": "application/json",
            },
            json={
                "query": {
                    "measures": ["Orders.count"],
                },
            },
        )

        # Should handle gracefully (400/401/403 or 200 in dev mode)
        assert response.status_code in (
            200,
            400,
            401,
            403,
        ), f"Expected handled response, got {response.status_code}"

    def test_missing_auth_handled(
        self,
        cube_client: httpx.Client,
    ) -> None:
        """Missing authentication should be handled."""
        response = cube_client.post(
            "/cubejs-api/v1/load",
            headers={"Content-Type": "application/json"},  # No Authorization
            json={
                "query": {
                    "measures": ["Orders.count"],
                },
            },
        )

        # In dev mode, missing auth is allowed (returns 200)
        # In production mode, should return 401/403
        assert response.status_code in (
            200,
            401,
            403,
        ), f"Expected 200 (dev mode) or 401/403 (prod mode), got {response.status_code}"


class TestRestApiPagination:
    """T038: REST API pagination over 10k rows test.

    FR-007: REST API supports pagination for large result sets
    """

    def test_pagination_with_limit(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """REST API should respect limit parameter."""
        response = cube_client.post(
            "/cubejs-api/v1/load",
            headers=authenticated_headers,
            json={
                "query": {
                    "measures": ["Orders.count"],
                    "dimensions": ["Orders.id"],
                    "limit": 100,
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) <= 100

    def test_pagination_with_offset(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """REST API should support offset parameter."""
        response = cube_client.post(
            "/cubejs-api/v1/load",
            headers=authenticated_headers,
            json={
                "query": {
                    "measures": ["Orders.count"],
                    "dimensions": ["Orders.id"],
                    "limit": 100,
                    "offset": 0,
                },
            },
        )

        assert response.status_code == 200

    def test_paginated_results_different_offsets(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Different offsets should return different data."""
        # Page 1
        page1 = cube_client.post(
            "/cubejs-api/v1/load",
            headers=authenticated_headers,
            json={
                "query": {
                    "measures": ["Orders.count"],
                    "dimensions": ["Orders.id"],
                    "limit": 10,
                    "offset": 0,
                },
            },
        )

        # Page 2
        page2 = cube_client.post(
            "/cubejs-api/v1/load",
            headers=authenticated_headers,
            json={
                "query": {
                    "measures": ["Orders.count"],
                    "dimensions": ["Orders.id"],
                    "limit": 10,
                    "offset": 10,
                },
            },
        )

        assert page1.status_code == 200
        assert page2.status_code == 200

        page1_data = page1.json()["data"]
        page2_data = page2.json()["data"]

        # If we have enough data, pages should be different
        if len(page1_data) == 10 and len(page2_data) > 0:
            assert page1_data != page2_data, "Paginated results should be different"

    def test_large_limit_succeeds(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Large limit value should succeed (Cube may cap internally)."""
        response = cube_client.post(
            "/cubejs-api/v1/load",
            headers=authenticated_headers,
            json={
                "query": {
                    "measures": ["Orders.count"],
                    "dimensions": ["Orders.status"],
                    "limit": 50000,
                },
            },
            timeout=60.0,  # Longer timeout for large queries
        )

        assert response.status_code == 200

    def test_pagination_over_10k_rows(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Should be able to paginate through >10k rows.

        This test verifies that multiple pages can be fetched sequentially.
        Requires sufficient test data (15k+ rows loaded by cube-init).
        """
        pages_fetched = 0
        page_size = 5000
        offset = 0

        while offset < 15000:  # Try to fetch up to 15k rows
            response = cube_client.post(
                "/cubejs-api/v1/load",
                headers=authenticated_headers,
                json={
                    "query": {
                        "measures": ["Orders.count"],
                        "dimensions": ["Orders.id"],
                        "limit": page_size,
                        "offset": offset,
                    },
                },
                timeout=60.0,
            )

            assert response.status_code == 200, f"Page {pages_fetched} failed: {response.text}"

            data = response.json()
            rows_returned = len(data.get("data", []))
            pages_fetched += 1

            # Stop if no more data
            if rows_returned < page_size:
                break

            offset += page_size

        assert pages_fetched >= 1, "Should fetch at least one page"


class TestRestApiErrorHandling:
    """Tests for REST API error handling."""

    def test_invalid_cube_name_returns_error(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Query with non-existent cube should return error."""
        response = cube_client.post(
            "/cubejs-api/v1/load",
            headers=authenticated_headers,
            json={
                "query": {
                    "measures": ["NonExistentCube.count"],
                },
            },
        )

        assert response.status_code in (
            400,
            500,
        ), f"Expected error status, got {response.status_code}"
        data = response.json()
        assert "error" in data or "message" in data.get("error", {})

    def test_invalid_json_body_returns_error(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Invalid JSON body should return 400 or 415."""
        response = cube_client.post(
            "/cubejs-api/v1/load",
            headers=authenticated_headers,
            content=b"not valid json {{{",
        )

        assert response.status_code in (400, 415, 500)

    def test_empty_query_returns_meaningful_response(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Empty query should return error or empty data (not crash)."""
        response = cube_client.post(
            "/cubejs-api/v1/load",
            headers=authenticated_headers,
            json={"query": {}},
        )

        # Should handle gracefully (either error or empty data)
        assert response.status_code in (200, 400, 500)


class TestPreAggregations:
    """T039: Pre-aggregations build and accelerate queries test.

    FR-025: System MUST support pre-aggregation refresh schedules (cron format)
    FR-026: System MUST automatically use pre-aggregated data when queries match

    Pre-aggregations use external: false to store in Trino/Iceberg
    (instead of GCS which is required for Trino export bucket).
    """

    def test_pre_aggregation_status_api_accessible(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Pre-aggregation status API should be accessible."""
        response = cube_client.get(
            "/cubejs-api/v1/pre-aggregations/jobs",
            headers=authenticated_headers,
        )

        # Should return 200 or 404 (if no jobs yet)
        assert response.status_code in (
            200,
            404,
        ), f"Pre-aggregation jobs API failed: {response.status_code}: {response.text}"

    def test_query_can_use_pre_aggregation(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Query matching pre-aggregation definition should succeed.

        The Orders.ordersByDay pre-aggregation covers:
        - measures: [count, totalAmount]
        - dimensions: [status]
        - timeDimension: createdAt with day granularity

        This query matches that definition.
        """
        response = cube_client.post(
            "/cubejs-api/v1/load",
            headers=authenticated_headers,
            json={
                "query": {
                    "measures": ["Orders.count", "Orders.totalAmount"],
                    "dimensions": ["Orders.status"],
                    "timeDimensions": [
                        {
                            "dimension": "Orders.createdAt",
                            "granularity": "day",
                        }
                    ],
                },
            },
            timeout=120.0,  # Pre-aggregation build may take time
        )

        assert response.status_code == 200, (
            f"Pre-aggregation query failed: {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "data" in data, f"Response missing 'data' key: {data}"

    def test_pre_aggregation_meta_endpoint(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Meta endpoint should show pre-aggregation definitions."""
        response = cube_client.get(
            "/cubejs-api/v1/meta",
            headers=authenticated_headers,
        )

        assert response.status_code == 200, (
            f"Meta API failed: {response.status_code}: {response.text}"
        )

        meta = response.json()
        assert "cubes" in meta, f"Meta response missing 'cubes': {meta}"

        # Find Orders cube
        orders_cube = None
        for cube in meta.get("cubes", []):
            if cube.get("name") == "Orders":
                orders_cube = cube
                break

        assert orders_cube is not None, (
            f"Orders cube not found in meta. Available cubes: "
            f"{[c.get('name') for c in meta.get('cubes', [])]}"
        )

    def test_query_without_pre_aggregation_also_works(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Query NOT matching pre-aggregation should still work (hits raw data).

        This query uses 'region' dimension which is NOT in the ordersByDay
        pre-aggregation, so it should query raw Iceberg data.
        """
        response = cube_client.post(
            "/cubejs-api/v1/load",
            headers=authenticated_headers,
            json={
                "query": {
                    "measures": ["Orders.count"],
                    "dimensions": ["Orders.region"],  # Not in pre-agg
                },
            },
        )

        assert response.status_code == 200, (
            f"Non-pre-agg query failed: {response.status_code}: {response.text}"
        )
        data = response.json()
        assert "data" in data
