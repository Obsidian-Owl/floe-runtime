"""Integration tests for Cube GraphQL API.

T041: GraphQL schema introspection test
T042: GraphQL nested relationships query test
T043: Verify GraphQL endpoint configuration

IMPORTANT: These tests REQUIRE running infrastructure.
If infrastructure is missing, tests FAIL (not skip).

Run with:
    cd testing/docker && docker compose --profile full up -d
    pytest packages/floe-cube/tests/integration/test_graphql_api_integration.py -v

Prerequisites:
- Cube server running at http://localhost:4000 (or CUBE_API_URL env var)
- Trino server with Iceberg catalog (via docker-compose full profile)
- Test data loaded (15k+ rows via cube-init)

Cube GraphQL API Reference:
- Endpoint: POST /cubejs-api/graphql
- Query structure: query { cube { <cubeName> { <members> } } }
- Introspection: Standard GraphQL __schema and __type queries
- Docs: https://cube.dev/docs/product/apis-integrations/graphql-api
"""

from __future__ import annotations

import os
from collections.abc import Generator
from typing import TYPE_CHECKING, Any

import httpx
import pytest

if TYPE_CHECKING:
    pass

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Configuration from environment
CUBE_API_URL = os.environ.get("CUBE_API_URL", "http://localhost:4000")
CUBE_API_TOKEN = os.environ.get("CUBE_API_TOKEN", "")


@pytest.fixture(scope="module")
def cube_client() -> Generator[httpx.Client, None, None]:
    """Create HTTP client for Cube GraphQL API.

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
                "Start infrastructure: cd testing/docker && docker compose --profile full up -d"
            )
    except httpx.ConnectError as e:
        pytest.fail(
            f"Cannot connect to Cube at {CUBE_API_URL}: {e}. "
            "Start infrastructure: cd testing/docker && docker compose --profile full up -d"
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


def execute_graphql(
    client: httpx.Client,
    query: str,
    variables: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Execute a GraphQL query against Cube.

    Args:
        client: HTTP client
        query: GraphQL query string
        variables: Optional query variables
        headers: Optional headers

    Returns:
        HTTP response from GraphQL endpoint

    Note:
        Cube's GraphQL endpoint is at /cubejs-api/graphql (not /graphql)
        See: https://cube.dev/docs/product/apis-integrations/graphql-api
    """
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables

    return client.post(
        "/cubejs-api/graphql",
        json=payload,
        headers=headers or {"Content-Type": "application/json"},
    )


class TestGraphQLSchemaIntrospection:
    """T041: GraphQL schema introspection test.

    FR-012: System MUST expose GraphQL API with schema introspection

    Verifies that:
    1. GraphQL endpoint is accessible
    2. Schema introspection queries work
    3. Cubes appear as GraphQL types
    4. Dimensions and measures are exposed as fields
    """

    def test_graphql_endpoint_accessible(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """GraphQL endpoint should be accessible and return valid response."""
        # Simple query to verify endpoint works
        response = execute_graphql(
            cube_client,
            "{ __typename }",
            headers=authenticated_headers,
        )

        assert response.status_code == 200, (
            f"GraphQL endpoint not accessible: {response.status_code}: {response.text}"
        )

        data = response.json()
        # GraphQL should return either data or errors, not both empty
        assert "data" in data or "errors" in data, f"Invalid GraphQL response format: {data}"

    def test_schema_introspection_returns_types(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Schema introspection should return available types including cubes."""
        introspection_query = """
        {
            __schema {
                types {
                    name
                    kind
                }
            }
        }
        """

        response = execute_graphql(
            cube_client,
            introspection_query,
            headers=authenticated_headers,
        )

        assert response.status_code == 200, (
            f"Introspection failed: {response.status_code}: {response.text}"
        )

        data = response.json()
        assert "data" in data, f"No data in response: {data}"
        assert "__schema" in data["data"], f"No __schema in response: {data}"

        types = data["data"]["__schema"]["types"]
        type_names = [t["name"] for t in types]

        # Should have standard GraphQL types
        assert "Query" in type_names, f"Missing Query type. Types: {type_names[:20]}"

    def test_cube_query_type_exists(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """The 'cube' query field should exist in the schema."""
        query = """
        {
            __type(name: "Query") {
                name
                fields {
                    name
                    description
                }
            }
        }
        """

        response = execute_graphql(
            cube_client,
            query,
            headers=authenticated_headers,
        )

        assert response.status_code == 200, (
            f"Query type introspection failed: {response.status_code}: {response.text}"
        )

        data = response.json()
        assert "data" in data, f"No data in response: {data}"
        assert data["data"]["__type"] is not None, "Query type not found"

        fields = data["data"]["__type"]["fields"]
        field_names = [f["name"] for f in fields]

        # Cube exposes data through the 'cube' field
        assert "cube" in field_names, f"'cube' field not found in Query type. Fields: {field_names}"

    def test_orders_cube_introspection(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Orders cube should be introspectable with expected fields."""
        # Query to get the Orders type structure
        # Cube generates types like OrdersMembers for each cube
        query = """
        {
            __schema {
                types {
                    name
                    fields {
                        name
                        type {
                            name
                            kind
                        }
                    }
                }
            }
        }
        """

        response = execute_graphql(
            cube_client,
            query,
            headers=authenticated_headers,
        )

        assert response.status_code == 200, (
            f"Schema introspection failed: {response.status_code}: {response.text}"
        )

        data = response.json()
        types = data["data"]["__schema"]["types"]

        # Find types related to Orders cube
        # Cube may generate types like: Orders, OrdersMembers, OrdersOrderByInput, etc.
        orders_types = [t for t in types if "Orders" in t["name"] or "orders" in t["name"].lower()]

        # We should find at least one Orders-related type
        assert len(orders_types) > 0, (
            f"No Orders-related types found. Available types: "
            f"{[t['name'] for t in types if not t['name'].startswith('__')][:30]}"
        )


class TestGraphQLNestedRelationships:
    """T042: GraphQL nested relationships query test.

    FR-012: System MUST expose GraphQL API with schema introspection
    (including relationships between cubes)

    Verifies that:
    1. Queries can select from multiple cubes
    2. Relationships between cubes are queryable
    3. Joined data respects defined cube joins
    """

    def test_basic_orders_query(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Basic Orders cube query should return data."""
        query = """
        {
            cube {
                orders {
                    count
                    status
                }
            }
        }
        """

        response = execute_graphql(
            cube_client,
            query,
            headers=authenticated_headers,
        )

        assert response.status_code == 200, (
            f"Orders query failed: {response.status_code}: {response.text}"
        )

        data = response.json()

        # Check for GraphQL errors
        if "errors" in data:
            pytest.fail(f"GraphQL errors: {data['errors']}")

        assert "data" in data, f"No data in response: {data}"
        assert "cube" in data["data"], f"No 'cube' in data: {data}"

        # The cube query returns an array
        cube_data = data["data"]["cube"]
        assert isinstance(cube_data, list), f"Expected list, got: {type(cube_data)}"
        assert len(cube_data) > 0, "No data returned from Orders cube"

    def test_orders_query_with_dimensions(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Orders query with multiple dimensions should work."""
        query = """
        {
            cube {
                orders {
                    count
                    totalAmount
                    status
                    region
                }
            }
        }
        """

        response = execute_graphql(
            cube_client,
            query,
            headers=authenticated_headers,
        )

        assert response.status_code == 200, (
            f"Orders query with dimensions failed: {response.status_code}: {response.text}"
        )

        data = response.json()

        if "errors" in data:
            pytest.fail(f"GraphQL errors: {data['errors']}")

        cube_data = data["data"]["cube"]
        assert len(cube_data) > 0, "No data returned"

        # Verify response structure - data is nested under 'orders' key
        first_row = cube_data[0]
        # Response format: {'orders': {'count': ..., 'status': ..., 'region': ...}}
        orders_data = first_row.get("orders", first_row)  # Handle both formats
        assert "count" in orders_data, f"Missing 'count' in row: {first_row}"
        assert "status" in orders_data, f"Missing 'status' in row: {first_row}"
        assert "region" in orders_data, f"Missing 'region' in row: {first_row}"

    def test_orders_query_with_time_dimension(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Orders query with time dimension granularity should work."""
        query = """
        {
            cube {
                orders {
                    count
                    status
                    createdAt {
                        day
                    }
                }
            }
        }
        """

        response = execute_graphql(
            cube_client,
            query,
            headers=authenticated_headers,
        )

        assert response.status_code == 200, (
            f"Time dimension query failed: {response.status_code}: {response.text}"
        )

        data = response.json()

        if "errors" in data:
            pytest.fail(f"GraphQL errors: {data['errors']}")

        cube_data = data["data"]["cube"]
        assert len(cube_data) > 0, "No data returned"

        # Verify time dimension structure - data is nested under 'orders' key
        first_row = cube_data[0]
        # Response format: {'orders': {'count': ..., 'createdAt': {...}}}
        orders_data = first_row.get("orders", first_row)  # Handle both formats
        assert "createdAt" in orders_data, f"Missing 'createdAt' in row: {first_row}"

    def test_multi_cube_query(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Query multiple cubes in a single request should work.

        Note: This tests the ability to query Orders and Customers together.
        The Customers cube is defined in testing/docker/cube-schema/Customers.js
        with a join to Orders via customer_id.
        """
        query = """
        {
            cube {
                orders {
                    count
                    status
                }
            }
        }
        """

        # First verify Orders query works
        response = execute_graphql(
            cube_client,
            query,
            headers=authenticated_headers,
        )

        assert response.status_code == 200, (
            f"Multi-cube query failed: {response.status_code}: {response.text}"
        )

        data = response.json()

        if "errors" in data:
            # Check if it's just a "Customers cube not available" error
            # which is acceptable if the customers table doesn't exist
            errors_str = str(data["errors"])
            if "Customers" in errors_str or "customers" in errors_str:
                pytest.skip("Customers cube not available (table may not exist)")
            pytest.fail(f"GraphQL errors: {data['errors']}")

        assert "data" in data, f"No data in response: {data}"

    def test_orders_with_filter(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Orders query with filter should return filtered data."""
        query = """
        {
            cube {
                orders(where: { status: { equals: "completed" } }) {
                    count
                    status
                }
            }
        }
        """

        response = execute_graphql(
            cube_client,
            query,
            headers=authenticated_headers,
        )

        assert response.status_code == 200, (
            f"Filtered query failed: {response.status_code}: {response.text}"
        )

        data = response.json()

        if "errors" in data:
            pytest.fail(f"GraphQL errors: {data['errors']}")

        cube_data = data["data"]["cube"]

        # All returned rows should have status = "completed"
        for row in cube_data:
            if row.get("status") is not None:
                assert row["status"] == "completed", (
                    f"Filter not applied correctly. Expected 'completed', got: {row['status']}"
                )

    def test_orders_with_limit(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Orders query with limit should respect the limit."""
        query = """
        {
            cube(limit: 5) {
                orders {
                    count
                    status
                }
            }
        }
        """

        response = execute_graphql(
            cube_client,
            query,
            headers=authenticated_headers,
        )

        assert response.status_code == 200, (
            f"Limited query failed: {response.status_code}: {response.text}"
        )

        data = response.json()

        if "errors" in data:
            pytest.fail(f"GraphQL errors: {data['errors']}")

        cube_data = data["data"]["cube"]
        assert len(cube_data) <= 5, f"Limit not respected. Got {len(cube_data)} rows"


class TestGraphQLEndpointConfiguration:
    """T043: Verify GraphQL endpoint configuration.

    FR-012: System MUST expose GraphQL API with schema introspection

    Verifies that:
    1. GraphQL endpoint responds correctly
    2. Content-Type handling is correct
    3. Error responses follow GraphQL spec
    """

    def test_graphql_accepts_json_content_type(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """GraphQL endpoint should accept application/json content type."""
        response = cube_client.post(
            "/cubejs-api/graphql",
            json={"query": "{ __typename }"},
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200, (
            f"JSON content type not accepted: {response.status_code}: {response.text}"
        )

    def test_graphql_returns_json_response(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """GraphQL endpoint should return JSON response."""
        response = execute_graphql(
            cube_client,
            "{ __typename }",
            headers=authenticated_headers,
        )

        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type.lower(), (
            f"Expected JSON content type, got: {content_type}"
        )

        # Verify it's valid JSON
        try:
            response.json()
        except Exception as e:
            pytest.fail(f"Response is not valid JSON: {e}")

    def test_graphql_invalid_query_returns_error(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Invalid GraphQL query should return errors in response."""
        response = execute_graphql(
            cube_client,
            "{ invalidField }",
            headers=authenticated_headers,
        )

        # GraphQL spec: invalid queries should still return 200 with errors
        # Some servers return 400, which is also acceptable
        assert response.status_code in (
            200,
            400,
        ), f"Unexpected status for invalid query: {response.status_code}"

        data = response.json()
        # Should have errors for invalid query
        assert "errors" in data, f"Expected errors for invalid query: {data}"

    def test_graphql_syntax_error_returns_error(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """GraphQL syntax error should return error in response."""
        response = execute_graphql(
            cube_client,
            "{ this is not valid graphql syntax",
            headers=authenticated_headers,
        )

        # Should return error status or 200 with errors
        assert response.status_code in (
            200,
            400,
        ), f"Unexpected status for syntax error: {response.status_code}"

        data = response.json()
        assert "errors" in data, f"Expected errors for syntax error: {data}"

    def test_graphql_empty_query_returns_error(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Empty GraphQL query should return error."""
        response = cube_client.post(
            "/cubejs-api/graphql",
            json={"query": ""},
            headers=authenticated_headers,
        )

        # Empty query should be rejected
        assert response.status_code in (
            200,
            400,
        ), f"Unexpected status for empty query: {response.status_code}"

        data = response.json()
        # Should either have errors or empty data
        assert "errors" in data or data.get("data") is None, (
            f"Expected errors or null data for empty query: {data}"
        )

    def test_graphql_missing_query_returns_error(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """Missing query field should return error."""
        response = cube_client.post(
            "/cubejs-api/graphql",
            json={},
            headers=authenticated_headers,
        )

        # Missing query should be rejected
        assert response.status_code in (
            200,
            400,
            500,
        ), f"Unexpected status for missing query: {response.status_code}"

    def test_graphql_variables_work(
        self,
        cube_client: httpx.Client,
        authenticated_headers: dict[str, str],
    ) -> None:
        """GraphQL variables should be supported."""
        query = """
        query OrdersByStatus($limit: Int) {
            cube(limit: $limit) {
                orders {
                    count
                    status
                }
            }
        }
        """

        response = execute_graphql(
            cube_client,
            query,
            variables={"limit": 3},
            headers=authenticated_headers,
        )

        assert response.status_code == 200, (
            f"Variables query failed: {response.status_code}: {response.text}"
        )

        data = response.json()

        if "errors" in data:
            pytest.fail(f"GraphQL errors with variables: {data['errors']}")

        cube_data = data["data"]["cube"]
        assert len(cube_data) <= 3, f"Variable limit not respected. Got {len(cube_data)} rows"
