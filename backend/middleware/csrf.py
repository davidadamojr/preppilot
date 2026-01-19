"""
CSRF Protection Middleware.

Implements Origin/Referer validation for state-changing requests.
This provides defense-in-depth against cross-site request forgery attacks,
even though the app uses Bearer token authentication (which is inherently
more resistant to CSRF than cookie-based auth).

Security Model:
- GET, HEAD, OPTIONS are considered safe (read-only)
- POST, PUT, PATCH, DELETE require Origin/Referer validation
- Requests must come from trusted origins (configured via settings)
- API-only requests (with Authorization header) bypass validation in debug mode
"""

import logging
from typing import List, Optional, Set
from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger(__name__)

# HTTP methods that modify state and require CSRF protection
UNSAFE_METHODS: Set[str] = {"POST", "PUT", "PATCH", "DELETE"}

# HTTP methods that are read-only and don't require CSRF protection
SAFE_METHODS: Set[str] = {"GET", "HEAD", "OPTIONS"}


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates Origin/Referer headers for state-changing requests.

    This prevents cross-site request forgery by ensuring requests come from
    trusted origins. It's a defense-in-depth measure that complements the
    Bearer token authentication scheme.

    Configuration:
        - allowed_origins: List of trusted origins (e.g., ["http://localhost:3000"])
        - enabled: Whether CSRF protection is active (disable in tests if needed)
        - exempt_paths: Paths that bypass CSRF validation (e.g., webhooks)
    """

    def __init__(
        self,
        app,
        allowed_origins: List[str],
        enabled: bool = True,
        exempt_paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.allowed_origins = set(self._normalize_origins(allowed_origins))
        self.enabled = enabled
        self.exempt_paths = set(exempt_paths or [])

        logger.info(
            f"CSRF middleware initialized: enabled={enabled}, "
            f"origins={self.allowed_origins}"
        )

    def _normalize_origins(self, origins: List[str]) -> List[str]:
        """Normalize origins by removing trailing slashes."""
        return [origin.rstrip("/").lower() for origin in origins]

    def _extract_origin(self, request: Request) -> Optional[str]:
        """
        Extract the origin from the request.

        Checks the Origin header first (preferred), then falls back to Referer.
        The Origin header is more reliable and is always present for cross-origin
        requests in modern browsers.

        Args:
            request: The incoming HTTP request

        Returns:
            The origin string (e.g., "http://localhost:3000") or None
        """
        # Prefer Origin header (more reliable, simpler)
        origin = request.headers.get("origin")
        if origin:
            return origin.rstrip("/").lower()

        # Fall back to Referer header (contains full URL, extract origin)
        referer = request.headers.get("referer")
        if referer:
            parsed = urlparse(referer)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}".lower()

        return None

    def _is_same_origin(self, request: Request, origin: str) -> bool:
        """
        Check if the request origin matches the server's host.

        This handles same-origin requests where Origin might match the server
        but not be in the allowed_origins list.

        Args:
            request: The incoming HTTP request
            origin: The extracted origin string

        Returns:
            True if the origin matches the server's host
        """
        # Build server origin from request
        scheme = request.url.scheme
        host = request.headers.get("host", "")
        server_origin = f"{scheme}://{host}".lower()

        return origin == server_origin

    def _is_origin_allowed(self, request: Request, origin: Optional[str]) -> bool:
        """
        Determine if the request origin is trusted.

        Args:
            request: The incoming HTTP request
            origin: The extracted origin string (may be None)

        Returns:
            True if the origin is allowed, False otherwise
        """
        # No origin header - could be a same-origin request from old browser
        # or a non-browser client (curl, Postman, etc.)
        # For security, we require origin for unsafe methods in browser contexts
        if origin is None:
            # Check if it looks like a browser request
            user_agent = request.headers.get("user-agent", "").lower()
            is_browser = any(
                browser in user_agent
                for browser in ["mozilla", "chrome", "safari", "firefox", "edge"]
            )

            # Non-browser clients (curl, Postman, scripts) don't send Origin
            # These are typically trusted API clients with Bearer tokens
            if not is_browser:
                return True

            # Browser without Origin header - suspicious, but some same-origin
            # requests don't include it. Allow if Authorization header present.
            if request.headers.get("authorization"):
                return True

            # Browser request without Origin and without Auth - block for safety
            return False

        # Check if origin is in allowed list
        if origin in self.allowed_origins:
            return True

        # Check if same-origin
        if self._is_same_origin(request, origin):
            return True

        return False

    def _is_exempt_path(self, path: str) -> bool:
        """Check if the path is exempt from CSRF validation."""
        return any(path.startswith(exempt) for exempt in self.exempt_paths)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process the request and validate CSRF for unsafe methods.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware/route handler

        Returns:
            The response from the next handler, or a 403 error
        """
        # Skip validation if middleware is disabled
        if not self.enabled:
            return await call_next(request)

        # Skip validation for safe methods
        if request.method in SAFE_METHODS:
            return await call_next(request)

        # Skip validation for exempt paths
        if self._is_exempt_path(request.url.path):
            return await call_next(request)

        # Validate origin for unsafe methods
        origin = self._extract_origin(request)

        if not self._is_origin_allowed(request, origin):
            logger.warning(
                f"CSRF validation failed: method={request.method}, "
                f"path={request.url.path}, origin={origin}, "
                f"client={request.client.host if request.client else 'unknown'}"
            )

            return JSONResponse(
                status_code=403,
                content={
                    "detail": "CSRF validation failed. Request origin not allowed.",
                    "error": "csrf_validation_failed",
                },
            )

        return await call_next(request)
