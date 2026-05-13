"""Security headers middleware (WAF-style hardening at the app layer)."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(self), camera=()",
    }

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Relax CSP in development to allow cross-origin API/WS calls
        from config.settings import settings
        headers = self.HEADERS.copy()
        if settings.app_env == "development":
            headers["Content-Security-Policy"] = "default-src 'self' *; img-src * data:; style-src 'self' 'unsafe-inline' *; script-src 'self' 'unsafe-inline' *; connect-src * ws: wss:; frame-ancestors 'none'"
        
        for k, v in headers.items():
            response.headers[k] = v
        return response
