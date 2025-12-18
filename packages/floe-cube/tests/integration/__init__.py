"""Integration tests for floe-cube.

These tests require running infrastructure (Cube, databases, etc.)
and are marked with @pytest.mark.integration.

IMPORTANT: These tests WILL FAIL if infrastructure is not running.
This is intentional - infrastructure must be available before running tests.

Run integration tests with:
    # Recommended: use the test runner script (zero-config)
    cd testing/docker && ./scripts/run-cube-tests.sh

    # Or manually:
    cd testing/docker && docker compose --profile full up -d
    # Wait for cube-init to complete (loads test data)
    docker compose logs cube-init -f
    # Then run integration tests
    pytest -m integration packages/floe-cube/tests/integration/

Prerequisites (started by full profile):
- Cube server at http://localhost:4000
- Trino server at http://localhost:8080
- Polaris catalog at http://localhost:8181
- LocalStack S3 at http://localhost:4566
- Test data loaded via cube-init (15k+ orders rows)
"""
