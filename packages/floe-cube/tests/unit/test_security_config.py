"""Unit tests for Cube security function generator.

T057: Unit test checkAuth function generation
T058: Unit test queryRewrite function generation
T059: Unit test environment variable generation
"""

from __future__ import annotations

from pathlib import Path

from floe_cube.security_config import CubeSecurityGenerator


class TestCheckAuthGeneration:
    """T057: Generate cube.js checkAuth function."""

    def test_check_auth_disabled_when_row_level_false(self) -> None:
        """When row_level is False, checkAuth should be passthrough."""
        generator = CubeSecurityGenerator({"row_level": False})
        code = generator.generate_check_auth()

        assert "async function checkAuth" in code
        assert "security disabled" in code
        assert "return {}" in code

    def test_check_auth_enabled_extracts_user_id(self) -> None:
        """When enabled, checkAuth should extract user ID from claim."""
        generator = CubeSecurityGenerator(
            {
                "row_level": True,
                "user_id_claim": "sub",
            }
        )
        code = generator.generate_check_auth()

        assert "async function checkAuth" in code
        assert "claims['sub']" in code
        assert "missing user identifier" in code

    def test_check_auth_uses_custom_user_id_claim(self) -> None:
        """checkAuth should use configured user_id_claim."""
        generator = CubeSecurityGenerator(
            {
                "row_level": True,
                "user_id_claim": "user_id",
            }
        )
        code = generator.generate_check_auth()

        assert "claims['user_id']" in code
        assert "claims['sub']" not in code

    def test_check_auth_extracts_roles(self) -> None:
        """checkAuth should extract roles from configured claim."""
        generator = CubeSecurityGenerator(
            {
                "row_level": True,
                "roles_claim": "groups",
            }
        )
        code = generator.generate_check_auth()

        assert "claims['groups']" in code
        assert "|| []" in code  # Default to empty array

    def test_check_auth_extracts_filter_claims(self) -> None:
        """checkAuth should extract all configured filter claims."""
        generator = CubeSecurityGenerator(
            {
                "row_level": True,
                "filter_claims": ["organization_id", "department"],
            }
        )
        code = generator.generate_check_auth()

        assert "claims['organization_id']" in code
        assert "claims['department']" in code
        assert "organization_id:" in code
        assert "department:" in code

    def test_check_auth_returns_security_context(self) -> None:
        """checkAuth should return securityContext object."""
        generator = CubeSecurityGenerator({"row_level": True})
        code = generator.generate_check_auth()

        assert "return {" in code
        assert "securityContext:" in code
        assert "user_id:" in code
        assert "roles:" in code


class TestQueryRewriteGeneration:
    """T058: Generate cube.js queryRewrite function."""

    def test_query_rewrite_disabled_when_row_level_false(self) -> None:
        """When row_level is False, queryRewrite should pass through."""
        generator = CubeSecurityGenerator({"row_level": False})
        code = generator.generate_query_rewrite()

        assert "function queryRewrite" in code
        assert "security disabled" in code
        assert "return query" in code

    def test_query_rewrite_requires_security_context(self) -> None:
        """When enabled, queryRewrite should require securityContext."""
        generator = CubeSecurityGenerator({"row_level": True})
        code = generator.generate_query_rewrite()

        assert "function queryRewrite" in code
        assert "if (!securityContext)" in code
        assert "no security context" in code

    def test_query_rewrite_adds_filter_for_each_claim(self) -> None:
        """queryRewrite should add filter for each configured claim."""
        generator = CubeSecurityGenerator(
            {
                "row_level": True,
                "filter_claims": ["organization_id", "department"],
            }
        )
        code = generator.generate_query_rewrite()

        assert "securityContext.organization_id" in code
        assert "securityContext.department" in code
        assert "member:" in code
        assert "operator: 'equals'" in code

    def test_query_rewrite_merges_with_existing_filters(self) -> None:
        """queryRewrite should preserve existing query filters."""
        generator = CubeSecurityGenerator(
            {
                "row_level": True,
                "filter_claims": ["organization_id"],
            }
        )
        code = generator.generate_query_rewrite()

        assert "...query" in code
        assert "...(query.filters || [])" in code
        assert "...filters" in code

    def test_query_rewrite_uses_cube_member_syntax(self) -> None:
        """queryRewrite should use ${query.cube}.column syntax."""
        generator = CubeSecurityGenerator(
            {
                "row_level": True,
                "filter_claims": ["organization_id"],
            }
        )
        code = generator.generate_query_rewrite()

        assert "${query.cube}.organization_id" in code


class TestEnvVarGeneration:
    """T059: Add filter configuration environment variables."""

    def test_env_vars_disabled_when_row_level_false(self) -> None:
        """When row_level is False, only disabled flag is set."""
        generator = CubeSecurityGenerator({"row_level": False})
        env_vars = generator.generate_env_vars()

        assert env_vars["FLOE_SECURITY_ENABLED"] == "false"
        assert len(env_vars) == 1

    def test_env_vars_includes_user_id_claim(self) -> None:
        """Env vars should include user_id_claim."""
        generator = CubeSecurityGenerator(
            {
                "row_level": True,
                "user_id_claim": "user_id",
            }
        )
        env_vars = generator.generate_env_vars()

        assert env_vars["FLOE_SECURITY_USER_ID_CLAIM"] == "user_id"

    def test_env_vars_includes_roles_claim(self) -> None:
        """Env vars should include roles_claim."""
        generator = CubeSecurityGenerator(
            {
                "row_level": True,
                "roles_claim": "groups",
            }
        )
        env_vars = generator.generate_env_vars()

        assert env_vars["FLOE_SECURITY_ROLES_CLAIM"] == "groups"

    def test_env_vars_includes_filter_claims_as_csv(self) -> None:
        """Filter claims should be comma-separated."""
        generator = CubeSecurityGenerator(
            {
                "row_level": True,
                "filter_claims": ["organization_id", "department"],
            }
        )
        env_vars = generator.generate_env_vars()

        assert env_vars["FLOE_SECURITY_FILTER_CLAIMS"] == "organization_id,department"

    def test_env_vars_includes_jwt_secret_ref(self) -> None:
        """JWT secret should use K8s secret reference syntax."""
        generator = CubeSecurityGenerator(
            {
                "row_level": True,
                "jwt_secret_ref": "cube-jwt-secret",
            }
        )
        env_vars = generator.generate_env_vars()

        assert env_vars["CUBEJS_JWT_SECRET"] == "${cube-jwt-secret}"

    def test_env_vars_includes_jwt_audience(self) -> None:
        """JWT audience should be included if configured."""
        generator = CubeSecurityGenerator(
            {
                "row_level": True,
                "jwt_audience": "my-api",
            }
        )
        env_vars = generator.generate_env_vars()

        assert env_vars["CUBEJS_JWT_AUDIENCE"] == "my-api"

    def test_env_vars_includes_jwt_issuer(self) -> None:
        """JWT issuer should be included if configured."""
        generator = CubeSecurityGenerator(
            {
                "row_level": True,
                "jwt_issuer": "https://auth.example.com",
            }
        )
        env_vars = generator.generate_env_vars()

        assert env_vars["CUBEJS_JWT_ISSUER"] == "https://auth.example.com"


class TestFullConfigGeneration:
    """Test complete security.js generation."""

    def test_full_config_includes_module_exports(self) -> None:
        """Full config should export checkAuth and queryRewrite."""
        generator = CubeSecurityGenerator({"row_level": True})
        config = generator.generate_full_config()

        assert "module.exports = {" in config
        assert "checkAuth," in config
        assert "queryRewrite," in config

    def test_full_config_includes_generation_header(self) -> None:
        """Full config should have auto-generated header."""
        generator = CubeSecurityGenerator({"row_level": True})
        config = generator.generate_full_config()

        assert "generated by floe-cube" in config
        assert "DO NOT EDIT" in config

    def test_write_security_config_creates_file(self, tmp_path: Path) -> None:
        """write_security_config should create security.js file."""
        generator = CubeSecurityGenerator({"row_level": True})
        path = generator.write_security_config(tmp_path)

        assert path.exists()
        assert path.name == "security.js"
        content = path.read_text()
        assert "module.exports" in content


class TestSanitizeJsName:
    """Test JavaScript name sanitization."""

    def test_sanitizes_hyphens(self) -> None:
        """Hyphens should be converted to underscores."""
        generator = CubeSecurityGenerator({})
        result = generator._sanitize_js_name("my-claim")

        assert result == "my_claim"

    def test_sanitizes_leading_digits(self) -> None:
        """Leading digits should be prefixed with underscore."""
        generator = CubeSecurityGenerator({})
        result = generator._sanitize_js_name("123claim")

        assert result == "_123claim"

    def test_sanitizes_special_characters(self) -> None:
        """Special characters should be replaced."""
        generator = CubeSecurityGenerator({})
        result = generator._sanitize_js_name("my.claim@org")

        assert result == "my_claim_org"
