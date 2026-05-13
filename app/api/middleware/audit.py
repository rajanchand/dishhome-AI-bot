"""Audit-log middleware: records all POST/PUT/PATCH/DELETE to the audit_logs table."""

import asyncio
import json
from typing import Any
from uuid import UUID

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.models import AsyncSessionLocal, AuditLog


SENSITIVE_KEYS = {
    "password", "current_password", "new_password",
    "secret", "token", "refresh_token", "access_token",
    "otp_code", "mfa_secret", "credit_card", "card_number", "cvv",
}


def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: ("***REDACTED***" if k.lower() in SENSITIVE_KEYS else _redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact(x) for x in obj]
    return obj


class AuditMiddleware(BaseHTTPMiddleware):
    AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    EXCLUDE_PREFIXES = (
        "/api/health", "/api/ping", "/metrics", "/ws/", "/api/auth/refresh",
    )

    async def dispatch(self, request: Request, call_next):
        body_bytes = b""
        if request.method in self.AUDITED_METHODS:
            body_bytes = await request.body()

            async def receive():
                return {"type": "http.request", "body": body_bytes, "more_body": False}
            request = Request(request.scope, receive)

        response = await call_next(request)

        if (
            request.method in self.AUDITED_METHODS
            and not any(str(request.url.path).startswith(p) for p in self.EXCLUDE_PREFIXES)
        ):
            asyncio.create_task(self._write_log(request, response, body_bytes))

        return response

    async def _write_log(self, request: Request, response: Response, body_bytes: bytes):
        try:
            body_json = None
            if body_bytes:
                try:
                    body_json = _redact(json.loads(body_bytes.decode("utf-8")))
                except Exception:
                    body_json = None

            user_id = None
            if hasattr(request.state, "user_id") and request.state.user_id:
                try:
                    user_id = UUID(str(request.state.user_id))
                except Exception:
                    user_id = None

            ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            action = f"{request.method.lower()}.{request.url.path}"

            async with AsyncSessionLocal() as db:
                entry = AuditLog(
                    user_id=user_id,
                    action=action[:100],
                    request_method=request.method,
                    request_path=str(request.url.path),
                    request_body=body_json,
                    response_status=response.status_code,
                    ip_address=ip,
                    user_agent=user_agent,
                )
                db.add(entry)
                await db.commit()
        except Exception as e:
            logger.warning(f"Audit log write failed: {e}")
