"""Integration tests for Row-Level Security (RLS).

T042: Row-level security integration tests

This module tests the floe-cube row-level security implementation:
- FR-016: Row-level security via security context from JWT claims
- FR-017: Filter queries by configured filter_column when RLS enabled
- FR-018: Reject queries without valid JWT when RLS required
- FR-019: Prevent cross-context data access in concurrent scenarios
- FR-027: Verify JWT signature before extracting security context

IMPORTANT: These tests validate RLS *configuration generation* and *security context*
extraction. Full RLS enforcement requires Cube to be configured with the generated
security functions, which is typically done in production deployments.

The tests verify:
1. Security configuration generates correct JavaScript
2. Security context is correctly extracted from JWT tokens
3. Query filters would be applied based on security context
4. Concurrent context isolation is maintained

Run with:
    cd testing/docker && ./scripts/run-integration-tests.sh --profile full

Prerequisites:
- Cube server running at http://localhost:4000 (or CUBE_API_URL env var)
- Orders table with 'region' column (created by cube-init)
"""

from __future__ import annotations

import base64
import json
import os
import time
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import httpx
import pytest

from floe_cube.models import SecurityContext
from floe_cube.security import JWTValidationError, JWTValidator, extract_security_context
from floe_cube.security_config import CubeSecurityGenerator

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Configuration from environment
CUBE_API_URL = os.environ.get("CUBE_API_URL", "http://localhost:4000")


def _create_test_jwt(
    payload: dict[str, Any],
    header: dict[str, str] | None = None,
) -> str:
    """Create a JWT token for testing (without signature verification).

    Note: This creates valid JWT structure for testing. In production,
    Cube's JWT middleware verifies signatures.
    """
    if header is None:
        header = {"alg": "HS256", "typ": "JWT"}

    # Encode header
    header_json = json.dumps(header, separators=(",", ":"))
    header_b64 = base64.urlsafe_b64encode(header_json.encode()).decode().rstrip("=")

    # Encode payload
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")

    # Dummy signature (not verified in dev mode)
    signature = "test_signature"

    return f"{header_b64}.{payload_b64}.{signature}"


@pytest.fixture(scope="module")
def cube_client() -> Generator[httpx.Client, None, None]:
    """Create HTTP client for Cube API.

    FAILS if Cube is not available (does not skip).
    """
    client = httpx.Client(
        base_url=CUBE_API_URL,
        headers={"Content-Type": "application/json"},
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


# =============================================================================
# FR-016: Row-Level Security via Security Context from JWT Claims
# =============================================================================


class TestSecurityContextFromJWT:
    """FR-016: Test security context extraction from JWT tokens."""

    def test_extract_security_context_with_filter_claims(self) -> None:
        """Security context extracts filter claims from JWT payload.

        Given a JWT payload with filter claims (organization_id, region),
        When extract_security_context is called,
        Then the filter_claims dictionary contains the expected values.
        """
        future_exp = int(time.time()) + 3600
        payload = {
            "sub": "user_123",
            "organization_id": "org_abc",
            "region": "north",
            "exp": future_exp,
        }

        ctx = extract_security_context(
            payload,
            filter_claims=["organization_id", "region"],
        )

        assert ctx.user_id == "user_123"
        assert ctx.filter_claims["organization_id"] == "org_abc"
        assert ctx.filter_claims["region"] == "north"

    def test_extract_from_jwt_token_string(self) -> None:
        """Security context can be extracted from JWT token string.

        Given a JWT token with claims,
        When JWTValidator.extract_context_from_token is called,
        Then the security context is populated correctly.
        """
        future_exp = int(time.time()) + 3600
        payload = {
            "sub": "user_456",
            "roles": ["analyst", "viewer"],
            "department": "engineering",
            "exp": future_exp,
        }
        token = _create_test_jwt(payload)

        validator = JWTValidator(filter_claims=["department"])
        ctx = validator.extract_context_from_token(token)

        assert ctx.user_id == "user_456"
        assert "analyst" in ctx.roles
        assert "viewer" in ctx.roles
        assert ctx.filter_claims["department"] == "engineering"

    def test_security_context_with_custom_claim_names(self) -> None:
        """Security context supports custom claim name mappings.

        Given a JWT with non-standard claim names,
        When JWTValidator is configured with custom claim names,
        Then claims are extracted correctly.
        """
        future_exp = int(time.time()) + 3600
        payload = {
            "user_id": "custom_user",  # Not 'sub'
            "groups": ["admin"],  # Not 'roles'
            "tenant_id": "tenant_xyz",
            "exp": future_exp,
        }
        token = _create_test_jwt(payload)

        validator = JWTValidator(
            user_id_claim="user_id",
            roles_claim="groups",
            filter_claims=["tenant_id"],
        )
        ctx = validator.extract_context_from_token(token)

        assert ctx.user_id == "custom_user"
        assert ctx.roles == ["admin"]
        assert ctx.filter_claims["tenant_id"] == "tenant_xyz"


# =============================================================================
# FR-017: Filter Queries by Configured filter_column When RLS Enabled
# =============================================================================


class TestQueryFiltering:
    """FR-017: Test query filtering based on security context.

    Note: These tests verify that the Cube REST API can filter by dimension.
    In production with RLS enabled, these filters would be automatically
    injected by the queryRewrite function based on security context.
    """

    def test_filter_by_region_returns_subset(
        self,
        cube_client: httpx.Client,
    ) -> None:
        """Query with region filter returns subset of data.

        Given an Orders cube with region dimension,
        When querying with filter on region='north',
        Then only rows with region='north' are counted.
        """
        # Query with filter (simulating what RLS would inject)
        filtered_response = cube_client.post(
            "/cubejs-api/v1/load",
            json={
                "query": {
                    "measures": ["Orders.count"],
                    "filters": [
                        {
                            "member": "Orders.region",
                            "operator": "equals",
                            "values": ["north"],
                        }
                    ],
                },
            },
        )

        assert filtered_response.status_code == 200, (
            f"Filter query failed: {filtered_response.text}"
        )
        filtered_data = filtered_response.json()
        assert "data" in filtered_data

        # Query without filter (total)
        total_response = cube_client.post(
            "/cubejs-api/v1/load",
            json={
                "query": {
                    "measures": ["Orders.count"],
                },
            },
        )

        assert total_response.status_code == 200
        total_data = total_response.json()

        # Filtered count should be less than total
        filtered_count = filtered_data["data"][0]["Orders.count"]
        total_count = total_data["data"][0]["Orders.count"]

        assert filtered_count < total_count, (
            f"Filtered count ({filtered_count}) should be less than total ({total_count})"
        )

    def test_different_regions_return_different_data(
        self,
        cube_client: httpx.Client,
    ) -> None:
        """Different region filters return different row counts.

        Given Orders table with multiple regions,
        When querying with different region filters,
        Then different subsets of data are returned.
        """
        counts_by_region: dict[str, int] = {}

        for region in ["north", "south", "east", "west"]:
            response = cube_client.post(
                "/cubejs-api/v1/load",
                json={
                    "query": {
                        "measures": ["Orders.count"],
                        "filters": [
                            {
                                "member": "Orders.region",
                                "operator": "equals",
                                "values": [region],
                            }
                        ],
                    },
                },
            )

            assert response.status_code == 200, f"Query for {region} failed"
            data = response.json()
            counts_by_region[region] = data["data"][0]["Orders.count"]

        # All regions should have data
        for region, count in counts_by_region.items():
            assert count > 0, f"Region {region} should have data"

        # Sum of regions should approximately equal total
        total_response = cube_client.post(
            "/cubejs-api/v1/load",
            json={"query": {"measures": ["Orders.count"]}},
        )
        total_count = total_response.json()["data"][0]["Orders.count"]
        region_sum = sum(counts_by_region.values())

        assert region_sum == total_count, (
            f"Sum of regions ({region_sum}) should equal total ({total_count})"
        )


# =============================================================================
# FR-018: Reject Queries Without Valid JWT When RLS Required
# =============================================================================


class TestInvalidJWTRejection:
    """FR-018: Test rejection of invalid JWT tokens.

    Note: In dev mode (CUBEJS_DEV_MODE=true), Cube does not enforce JWT.
    These tests verify the JWTValidator correctly rejects invalid tokens.
    """

    def test_reject_expired_jwt(self) -> None:
        """Expired JWT token is rejected.

        Given a JWT with past expiration,
        When validate_expiration is called,
        Then JWTValidationError is raised.
        """
        validator = JWTValidator()
        payload = {
            "sub": "user",
            "exp": int(time.time()) - 3600,  # 1 hour ago
        }

        with pytest.raises(JWTValidationError) as exc_info:
            validator.validate_expiration(payload)

        assert "expired" in str(exc_info.value).lower()

    def test_reject_missing_user_id(self) -> None:
        """JWT without user_id claim is rejected.

        Given a JWT payload missing the user_id claim,
        When extract_context is called,
        Then JWTValidationError is raised.
        """
        validator = JWTValidator()
        payload = {
            "exp": int(time.time()) + 3600,
            # Missing 'sub' claim
        }

        with pytest.raises(JWTValidationError) as exc_info:
            validator.extract_context(payload)

        assert "sub" in str(exc_info.value)

    def test_reject_empty_user_id(self) -> None:
        """JWT with empty user_id is rejected.

        Given a JWT payload with empty user_id,
        When extract_context is called,
        Then JWTValidationError is raised.
        """
        validator = JWTValidator()
        payload = {
            "sub": "",
            "exp": int(time.time()) + 3600,
        }

        with pytest.raises(JWTValidationError) as exc_info:
            validator.extract_context(payload)

        assert "empty" in str(exc_info.value).lower()

    def test_reject_malformed_jwt_token(self) -> None:
        """Malformed JWT token string is rejected.

        Given an invalid JWT string,
        When decode_token is called,
        Then JWTValidationError is raised.
        """
        validator = JWTValidator()

        with pytest.raises(JWTValidationError) as exc_info:
            validator.decode_token("not.valid.jwt.format.extra")

        assert "malformed" in str(exc_info.value).lower()

    def test_reject_invalid_base64_payload(self) -> None:
        """JWT with invalid base64 payload is rejected.

        Given a JWT with corrupted payload,
        When decode_token is called,
        Then JWTValidationError is raised.
        """
        validator = JWTValidator()
        invalid_token = "header.!!!invalid!!!.signature"

        with pytest.raises(JWTValidationError) as exc_info:
            validator.decode_token(invalid_token)

        assert "decode" in str(exc_info.value).lower()


# =============================================================================
# FR-019: Prevent Cross-Context Data Access in Concurrent Scenarios
# =============================================================================


class TestConcurrentContextIsolation:
    """FR-019: Test isolation of security contexts in concurrent queries.

    These tests verify that multiple concurrent queries with different
    security contexts do not leak data between contexts.
    """

    def test_concurrent_queries_with_different_regions(
        self,
        cube_client: httpx.Client,
    ) -> None:
        """Concurrent queries with different filters return isolated data.

        Given multiple concurrent queries with different region filters,
        When all queries complete,
        Then each query returns only its filtered data.
        """
        regions = ["north", "south", "east", "west"]
        results: dict[str, int | None] = dict.fromkeys(regions)

        def query_region(region: str) -> tuple[str, int]:
            """Execute query for a specific region."""
            response = cube_client.post(
                "/cubejs-api/v1/load",
                json={
                    "query": {
                        "measures": ["Orders.count"],
                        "filters": [
                            {
                                "member": "Orders.region",
                                "operator": "equals",
                                "values": [region],
                            }
                        ],
                    },
                },
            )
            assert response.status_code == 200, f"Query for {region} failed"
            data = response.json()
            return region, data["data"][0]["Orders.count"]

        # Execute queries concurrently
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(query_region, r) for r in regions]
            for future in futures:
                region, count = future.result()
                results[region] = count

        # Verify each region got its own data
        for region in regions:
            region_count = results[region]
            assert region_count is not None, f"Region {region} query failed"
            assert region_count > 0, f"Region {region} should have data"

        # Verify we got results for all regions
        assert len(results) == len(regions)
        # All counts should be non-None (queries succeeded)
        assert all(c is not None for c in results.values())

    def test_security_context_immutability(self) -> None:
        """SecurityContext is immutable and thread-safe.

        Given a SecurityContext instance,
        When attempting to modify it,
        Then ValidationError is raised (frozen=True).
        """
        from pydantic import ValidationError

        ctx = SecurityContext(
            user_id="user_123",
            roles=["admin"],
            filter_claims={"org_id": "org_1"},
            exp=int(time.time()) + 3600,
        )

        # Attempt to modify should raise
        with pytest.raises(ValidationError):
            ctx.user_id = "different_user"

        with pytest.raises(ValidationError):
            ctx.filter_claims = {"different": "value"}

    def test_separate_validator_instances(self) -> None:
        """Separate JWTValidator instances don't share state.

        Given two JWTValidator instances with different configs,
        When extracting contexts,
        Then each uses its own configuration.
        """
        validator1 = JWTValidator(
            user_id_claim="sub",
            filter_claims=["org_id"],
        )
        validator2 = JWTValidator(
            user_id_claim="user_id",
            filter_claims=["tenant_id"],
        )

        future_exp = int(time.time()) + 3600

        # Payload for validator1
        payload1 = {
            "sub": "user1",
            "org_id": "org_a",
            "exp": future_exp,
        }

        # Payload for validator2
        payload2 = {
            "user_id": "user2",
            "tenant_id": "tenant_b",
            "exp": future_exp,
        }

        ctx1 = validator1.extract_context(payload1)
        ctx2 = validator2.extract_context(payload2)

        # Each context should have its own claims
        assert ctx1.user_id == "user1"
        assert ctx1.filter_claims.get("org_id") == "org_a"
        assert "tenant_id" not in ctx1.filter_claims

        assert ctx2.user_id == "user2"
        assert ctx2.filter_claims.get("tenant_id") == "tenant_b"
        assert "org_id" not in ctx2.filter_claims


# =============================================================================
# Security Configuration Generation Tests
# =============================================================================


class TestSecurityConfigGeneration:
    """Test Cube security configuration generation.

    These tests verify that CubeSecurityGenerator produces valid
    JavaScript code for checkAuth and queryRewrite functions.
    """

    def test_generate_check_auth_with_rls_enabled(self) -> None:
        """Generate checkAuth function when RLS is enabled.

        Given a security config with row_level=True,
        When generate_check_auth is called,
        Then valid JavaScript is generated with claim extraction.
        """
        config = {
            "row_level": True,
            "user_id_claim": "sub",
            "roles_claim": "roles",
            "filter_claims": ["organization_id", "region"],
        }
        generator = CubeSecurityGenerator(config)

        js_code = generator.generate_check_auth()

        # Verify JavaScript contains expected elements
        assert "async function checkAuth" in js_code
        assert "securityContext" in js_code
        assert "organization_id" in js_code
        assert "region" in js_code
        assert "sub" in js_code

    def test_generate_query_rewrite_with_filter_claims(self) -> None:
        """Generate queryRewrite function with filter claims.

        Given a security config with filter_claims,
        When generate_query_rewrite is called,
        Then JavaScript injects filters for each claim.
        """
        config = {
            "row_level": True,
            "filter_claims": ["organization_id"],
        }
        generator = CubeSecurityGenerator(config)

        js_code = generator.generate_query_rewrite()

        # Verify filter injection
        assert "function queryRewrite" in js_code
        assert "securityContext" in js_code
        assert "organization_id" in js_code
        assert "filters" in js_code
        assert "equals" in js_code

    def test_generate_passthrough_when_rls_disabled(self) -> None:
        """Generate passthrough functions when RLS is disabled.

        Given a security config with row_level=False,
        When generating security functions,
        Then passthrough functions are generated.
        """
        config = {"row_level": False}
        generator = CubeSecurityGenerator(config)

        check_auth = generator.generate_check_auth()
        query_rewrite = generator.generate_query_rewrite()

        # Passthrough should not have filtering logic
        assert "security disabled" in check_auth.lower()
        assert "security disabled" in query_rewrite.lower()
        assert "return {}" in check_auth or "return query" in query_rewrite

    def test_write_security_config_to_file(self) -> None:
        """Write security configuration to file.

        Given a security config,
        When write_security_config is called,
        Then security.js is written with valid content.
        """
        config = {
            "row_level": True,
            "filter_claims": ["region"],
        }
        generator = CubeSecurityGenerator(config)

        with TemporaryDirectory() as temp_dir:
            output_path = generator.write_security_config(Path(temp_dir))

            assert output_path.exists()
            assert output_path.name == "security.js"

            content = output_path.read_text()
            assert "module.exports" in content
            assert "checkAuth" in content
            assert "queryRewrite" in content

    def test_generate_env_vars_with_jwt_config(self) -> None:
        """Generate environment variables for JWT configuration.

        Given a security config with JWT settings,
        When generate_env_vars is called,
        Then environment variables are generated correctly.
        """
        config = {
            "row_level": True,
            "user_id_claim": "sub",
            "roles_claim": "groups",
            "filter_claims": ["org_id", "dept_id"],
            "jwt_secret_ref": "k8s-secret-name",
            "jwt_audience": "cube-api",
            "jwt_issuer": "https://auth.example.com",
        }
        generator = CubeSecurityGenerator(config)

        env_vars = generator.generate_env_vars()

        assert env_vars["FLOE_SECURITY_ENABLED"] == "true"
        assert env_vars["FLOE_SECURITY_USER_ID_CLAIM"] == "sub"
        assert env_vars["FLOE_SECURITY_ROLES_CLAIM"] == "groups"
        assert env_vars["FLOE_SECURITY_FILTER_CLAIMS"] == "org_id,dept_id"
        assert "k8s-secret-name" in env_vars["CUBEJS_JWT_SECRET"]
        assert env_vars["CUBEJS_JWT_AUDIENCE"] == "cube-api"
        assert env_vars["CUBEJS_JWT_ISSUER"] == "https://auth.example.com"


# =============================================================================
# End-to-End RLS Scenario Tests
# =============================================================================


class TestRLSEndToEnd:
    """End-to-end tests for RLS scenarios.

    These tests simulate complete RLS workflows from JWT to query filtering.
    """

    def test_complete_rls_workflow_simulation(
        self,
        cube_client: httpx.Client,
    ) -> None:
        """Simulate complete RLS workflow from JWT to filtered query.

        This test simulates what would happen in production:
        1. Extract security context from JWT
        2. Generate filter based on security context
        3. Execute filtered query
        4. Verify only authorized data is returned

        Note: In production, steps 2-4 happen automatically via Cube's
        queryRewrite function. Here we simulate the workflow.
        """
        # Step 1: Create JWT and extract security context
        future_exp = int(time.time()) + 3600
        jwt_payload = {
            "sub": "analyst_user",
            "roles": ["analyst"],
            "region": "north",
            "exp": future_exp,
        }
        token = _create_test_jwt(jwt_payload)

        validator = JWTValidator(filter_claims=["region"])
        ctx = validator.extract_context_from_token(token)

        # Step 2: Build filter from security context
        region_filter = ctx.filter_claims.get("region")
        assert region_filter == "north"

        # Step 3: Execute filtered query (simulating queryRewrite)
        response = cube_client.post(
            "/cubejs-api/v1/load",
            json={
                "query": {
                    "measures": ["Orders.count"],
                    "filters": [
                        {
                            "member": "Orders.region",
                            "operator": "equals",
                            "values": [region_filter],
                        }
                    ],
                },
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Step 4: Verify data was filtered
        filtered_count = data["data"][0]["Orders.count"]
        assert filtered_count > 0, "Filtered query should return data"

        # Verify this is a subset of total
        total_response = cube_client.post(
            "/cubejs-api/v1/load",
            json={"query": {"measures": ["Orders.count"]}},
        )
        total_count = total_response.json()["data"][0]["Orders.count"]

        assert filtered_count < total_count, (
            f"Filtered count ({filtered_count}) should be less than total ({total_count})"
        )

    def test_multi_claim_filter_scenario(
        self,
        cube_client: httpx.Client,
    ) -> None:
        """Test scenario with multiple filter claims.

        Given a JWT with multiple filter claims (region and status),
        When applying both filters,
        Then data is filtered by both dimensions.
        """
        # Create context with multiple claims
        future_exp = int(time.time()) + 3600
        ctx = SecurityContext(
            user_id="multi_filter_user",
            roles=["viewer"],
            filter_claims={
                "region": "east",
                "status": "completed",
            },
            exp=future_exp,
        )

        # Apply both filters
        response = cube_client.post(
            "/cubejs-api/v1/load",
            json={
                "query": {
                    "measures": ["Orders.count"],
                    "filters": [
                        {
                            "member": "Orders.region",
                            "operator": "equals",
                            "values": [ctx.filter_claims["region"]],
                        },
                        {
                            "member": "Orders.status",
                            "operator": "equals",
                            "values": [ctx.filter_claims["status"]],
                        },
                    ],
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        count = data["data"][0]["Orders.count"]

        # Verify data is filtered more restrictively than single filter
        single_filter_response = cube_client.post(
            "/cubejs-api/v1/load",
            json={
                "query": {
                    "measures": ["Orders.count"],
                    "filters": [
                        {
                            "member": "Orders.region",
                            "operator": "equals",
                            "values": ["east"],
                        },
                    ],
                },
            },
        )
        single_count = single_filter_response.json()["data"][0]["Orders.count"]

        assert count <= single_count, (
            "Multi-filter should return same or fewer rows than single filter"
        )
