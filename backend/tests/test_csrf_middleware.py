"""
Tests for CSRF protection middleware.

Tests the Origin/Referer validation logic for state-changing requests.
"""

import pytest
from unittest.mock import MagicMock
from starlette.testclient import TestClient
from starlette.requests import Request

from backend.middleware.csrf import CSRFMiddleware, SAFE_METHODS, UNSAFE_METHODS


class TestCSRFMiddlewareConstants:
    """Test the method classification constants."""

    def test_safe_methods_are_correct(self):
        """Safe methods should be GET, HEAD, OPTIONS."""
        assert SAFE_METHODS == {"GET", "HEAD", "OPTIONS"}

    def test_unsafe_methods_are_correct(self):
        """Unsafe methods should be POST, PUT, PATCH, DELETE."""
        assert UNSAFE_METHODS == {"POST", "PUT", "PATCH", "DELETE"}


class TestCSRFMiddlewareOriginExtraction:
    """Test origin extraction from headers."""

    @pytest.fixture
    def middleware(self):
        """Create a CSRF middleware instance for testing."""
        app = MagicMock()
        return CSRFMiddleware(
            app,
            allowed_origins=["http://localhost:3000", "http://localhost:8000"],
            enabled=True,
        )

    def test_extract_origin_from_origin_header(self, middleware):
        """Should extract origin from Origin header."""
        request = MagicMock(spec=Request)
        request.headers = {"origin": "http://localhost:3000"}

        origin = middleware._extract_origin(request)
        assert origin == "http://localhost:3000"

    def test_extract_origin_normalizes_case(self, middleware):
        """Should normalize origin to lowercase."""
        request = MagicMock(spec=Request)
        request.headers = {"origin": "HTTP://LOCALHOST:3000"}

        origin = middleware._extract_origin(request)
        assert origin == "http://localhost:3000"

    def test_extract_origin_removes_trailing_slash(self, middleware):
        """Should remove trailing slash from origin."""
        request = MagicMock(spec=Request)
        request.headers = {"origin": "http://localhost:3000/"}

        origin = middleware._extract_origin(request)
        assert origin == "http://localhost:3000"

    def test_extract_origin_from_referer_header(self, middleware):
        """Should extract origin from Referer header when Origin is absent."""
        request = MagicMock(spec=Request)
        request.headers = {"referer": "http://localhost:3000/dashboard/plans"}

        origin = middleware._extract_origin(request)
        assert origin == "http://localhost:3000"

    def test_extract_origin_prefers_origin_over_referer(self, middleware):
        """Should prefer Origin header over Referer."""
        request = MagicMock(spec=Request)
        request.headers = {
            "origin": "http://localhost:3000",
            "referer": "http://malicious.com/attack",
        }

        origin = middleware._extract_origin(request)
        assert origin == "http://localhost:3000"

    def test_extract_origin_returns_none_when_missing(self, middleware):
        """Should return None when neither Origin nor Referer is present."""
        request = MagicMock(spec=Request)
        request.headers = {}

        origin = middleware._extract_origin(request)
        assert origin is None


class TestCSRFMiddlewareOriginValidation:
    """Test origin validation logic."""

    @pytest.fixture
    def middleware(self):
        """Create a CSRF middleware instance for testing."""
        app = MagicMock()
        return CSRFMiddleware(
            app,
            allowed_origins=["http://localhost:3000", "http://localhost:8000"],
            enabled=True,
        )

    def test_allowed_origin_passes(self, middleware):
        """Origin in allowed list should pass validation."""
        request = MagicMock(spec=Request)
        request.headers = {"origin": "http://localhost:3000"}
        request.url = MagicMock()
        request.url.scheme = "http"

        assert middleware._is_origin_allowed(request, "http://localhost:3000") is True

    def test_disallowed_origin_fails(self, middleware):
        """Origin not in allowed list should fail validation."""
        request = MagicMock(spec=Request)
        request.headers = {"user-agent": "Mozilla/5.0"}
        request.url = MagicMock()
        request.url.scheme = "http"

        assert middleware._is_origin_allowed(request, "http://malicious.com") is False

    def test_same_origin_passes(self, middleware):
        """Same-origin request should pass validation."""
        request = MagicMock(spec=Request)
        request.headers = {"host": "api.example.com"}
        request.url = MagicMock()
        request.url.scheme = "https"

        assert middleware._is_origin_allowed(request, "https://api.example.com") is True

    def test_non_browser_client_without_origin_passes(self, middleware):
        """Non-browser clients (curl, Postman) without Origin should pass."""
        request = MagicMock(spec=Request)
        request.headers = {"user-agent": "curl/7.64.1"}

        assert middleware._is_origin_allowed(request, None) is True

    def test_browser_with_auth_but_no_origin_passes(self, middleware):
        """Browser request with Authorization header but no Origin should pass."""
        request = MagicMock(spec=Request)
        request.headers = {
            "user-agent": "Mozilla/5.0 Chrome",
            "authorization": "Bearer token123",
        }

        assert middleware._is_origin_allowed(request, None) is True

    def test_browser_without_auth_or_origin_fails(self, middleware):
        """Browser request without Authorization and without Origin should fail."""
        request = MagicMock(spec=Request)
        request.headers = {"user-agent": "Mozilla/5.0 Chrome"}

        assert middleware._is_origin_allowed(request, None) is False


class TestCSRFMiddlewareIntegration:
    """Integration tests using FastAPI TestClient."""

    @pytest.fixture
    def csrf_enabled_client(self):
        """Create a test client with CSRF protection enabled."""
        from fastapi import FastAPI

        # Create a minimal app with CSRF middleware
        test_app = FastAPI()

        @test_app.post("/test")
        async def test_post():
            return {"status": "ok"}

        @test_app.delete("/test")
        async def test_delete():
            return {"status": "deleted"}

        @test_app.get("/test")
        async def test_get():
            return {"status": "ok"}

        # Add CSRF middleware (enabled)
        test_app.add_middleware(
            CSRFMiddleware,
            allowed_origins=["http://localhost:3000", "http://testserver"],
            enabled=True,
            exempt_paths=[],
        )

        return TestClient(test_app)

    def test_get_request_succeeds_without_origin(self, csrf_enabled_client):
        """GET requests should succeed without Origin header."""
        response = csrf_enabled_client.get("/test")
        assert response.status_code == 200

    def test_post_with_testserver_origin_succeeds(self, csrf_enabled_client):
        """POST with testserver origin should succeed."""
        # TestClient uses http://testserver as default
        response = csrf_enabled_client.post(
            "/test",
            headers={"Origin": "http://testserver"},
        )
        assert response.status_code == 200

    def test_post_with_allowed_origin_succeeds(self, csrf_enabled_client):
        """POST with allowed origin should succeed."""
        response = csrf_enabled_client.post(
            "/test",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200

    def test_post_with_disallowed_origin_fails(self, csrf_enabled_client):
        """POST with disallowed origin should fail with 403."""
        response = csrf_enabled_client.post(
            "/test",
            headers={
                "Origin": "http://evil.com",
                "User-Agent": "Mozilla/5.0",
            },
        )
        assert response.status_code == 403
        assert "csrf" in response.json()["error"].lower()

    def test_delete_with_disallowed_origin_fails(self, csrf_enabled_client):
        """DELETE with disallowed origin should fail with 403."""
        response = csrf_enabled_client.delete(
            "/test",
            headers={
                "Origin": "http://attacker.site",
                "User-Agent": "Mozilla/5.0",
            },
        )
        assert response.status_code == 403

    def test_post_with_authorization_header_and_no_origin_succeeds(
        self, csrf_enabled_client
    ):
        """POST from browser with Authorization but no Origin should succeed."""
        response = csrf_enabled_client.post(
            "/test",
            headers={
                "User-Agent": "Mozilla/5.0 Chrome",
                "Authorization": "Bearer token123",
            },
        )
        assert response.status_code == 200

    def test_post_from_non_browser_without_origin_succeeds(self, csrf_enabled_client):
        """POST from non-browser client (curl) without Origin should succeed."""
        response = csrf_enabled_client.post(
            "/test",
            headers={"User-Agent": "curl/7.64.1"},
        )
        assert response.status_code == 200


class TestCSRFMiddlewareConfiguration:
    """Test middleware configuration options."""

    def test_normalize_origins_removes_trailing_slashes(self):
        """Allowed origins should have trailing slashes removed."""
        middleware = CSRFMiddleware(
            MagicMock(),
            allowed_origins=[
                "http://localhost:3000/",
                "http://localhost:8000//",
            ],
            enabled=True,
        )

        assert "http://localhost:3000" in middleware.allowed_origins
        assert "http://localhost:8000" in middleware.allowed_origins

    def test_normalize_origins_lowercases(self):
        """Allowed origins should be lowercased."""
        middleware = CSRFMiddleware(
            MagicMock(),
            allowed_origins=["HTTP://LOCALHOST:3000"],
            enabled=True,
        )

        assert "http://localhost:3000" in middleware.allowed_origins

    def test_exempt_paths_are_stored(self):
        """Exempt paths should be stored correctly."""
        middleware = CSRFMiddleware(
            MagicMock(),
            allowed_origins=["http://localhost:3000"],
            enabled=True,
            exempt_paths=["/health", "/webhook/stripe"],
        )

        assert "/health" in middleware.exempt_paths
        assert "/webhook/stripe" in middleware.exempt_paths

    def test_is_exempt_path_with_prefix_match(self):
        """Exempt path matching should use prefix matching."""
        middleware = CSRFMiddleware(
            MagicMock(),
            allowed_origins=["http://localhost:3000"],
            enabled=True,
            exempt_paths=["/webhook/"],  # Trailing slash for exact prefix
        )

        # Prefix matches (with trailing slash in exempt path)
        assert middleware._is_exempt_path("/webhook/") is True
        assert middleware._is_exempt_path("/webhook/stripe") is True
        assert middleware._is_exempt_path("/webhook/paypal/notify") is True

        # Non-matches (different prefix)
        assert middleware._is_exempt_path("/webhook") is False  # Missing trailing slash
        assert middleware._is_exempt_path("/api/webhook") is False

    def test_is_exempt_path_exact_match(self):
        """Exempt path can match exactly without trailing slash."""
        middleware = CSRFMiddleware(
            MagicMock(),
            allowed_origins=["http://localhost:3000"],
            enabled=True,
            exempt_paths=["/health"],
        )

        # Exact match
        assert middleware._is_exempt_path("/health") is True
        # Prefix also matches (inherent behavior of startswith)
        assert middleware._is_exempt_path("/health/check") is True
        # Non-matches
        assert middleware._is_exempt_path("/healthz") is True  # Note: startswith matches
        assert middleware._is_exempt_path("/api/health") is False
