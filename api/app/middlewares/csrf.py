"""CSRF protection middleware.

Validates X-CSRF-Token header for state-changing requests.
Sets csrf_token cookie on responses when missing (so client can send it back).
Excludes /tokens and /deposit-callbacks (pre-auth and webhook endpoints).
Disabled when REFINANCE_CSRF_DISABLED=1 (e.g. for tests).
"""

import secrets

from app.config import get_config
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
EXCLUDED_PREFIXES = ("/tokens", "/deposit-callbacks")
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _get_cookie(request: Request, name: str) -> str | None:
    """Extract cookie value from request."""
    cookie_header = request.headers.get("cookie")
    if not cookie_header:
        return None
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith(f"{name}="):
            return part[len(name) + 1 :].strip()
    return None


def _path_matches_exclusion(path: str) -> bool:
    """Check if path should be excluded from CSRF validation."""
    # Strip query string for prefix check
    base_path = path.split("?")[0] if "?" in path else path
    return any(base_path.rstrip("/").startswith(p.rstrip("/")) for p in EXCLUDED_PREFIXES)


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if get_config().csrf_disabled:
            return await call_next(request)

        method = request.method.upper()

        # For safe methods, skip validation
        if method in SAFE_METHODS:
            response = await call_next(request)
            return self._maybe_set_cookie(request, response)

        # Excluded paths (tokens, webhooks)
        if _path_matches_exclusion(request.url.path):
            response = await call_next(request)
            return self._maybe_set_cookie(request, response)

        # Validate CSRF for state-changing requests
        cookie_token = _get_cookie(request, CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)

        if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF validation failed"},
            )

        response = await call_next(request)
        return self._maybe_set_cookie(request, response)

    def _maybe_set_cookie(self, request: Request, response):
        """Add Set-Cookie for csrf_token if request had none."""
        if _get_cookie(request, CSRF_COOKIE_NAME) is not None:
            return response

        token = secrets.token_urlsafe(32)
        # SameSite=Lax allows cookie on top-level navigations (e.g. login link)
        # Not HttpOnly: client JS must read cookie to send X-CSRF-Token header
        cookie_value = f"{CSRF_COOKIE_NAME}={token}; Path=/; SameSite=Lax"
        response.headers.append("Set-Cookie", cookie_value)
        response.headers.append(CSRF_HEADER_NAME, token)
        return response
