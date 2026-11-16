"""HTTP 横切关注点：请求 ID、访问日志、安全响应头、Prometheus 指标。"""
from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.log_config import request_id_ctx
from app.core.metrics import HTTP_DURATION, HTTP_IN_PROGRESS, HTTP_REQUESTS

access_logger = logging.getLogger("app.access")

_MAX_REQUEST_ID_LEN = 64

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


def _request_id_from_header(request: Request) -> str:
    incoming = (request.headers.get("x-request-id") or "").strip()
    if 8 <= len(incoming) <= _MAX_REQUEST_ID_LEN and all(c.isalnum() or c in "-_." for c in incoming):
        return incoming
    return uuid.uuid4().hex


def _route_label(request: Request) -> str:
    """用路由模板做指标 label，避免 /api/users/123 把时间序列撑爆。"""
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return path or "unmatched"


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = _request_id_from_header(request)
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        HTTP_IN_PROGRESS.inc()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            _apply_headers(response, request, request_id)
            return response
        finally:
            duration = time.perf_counter() - started
            HTTP_IN_PROGRESS.dec()
            route = _route_label(request)
            HTTP_REQUESTS.labels(request.method, route, str(status)).inc()
            HTTP_DURATION.labels(request.method, route).observe(duration)

            if request.url.path != "/metrics":
                extra = {
                    "method": request.method,
                    "path": request.url.path,
                    "status": status,
                    "duration_ms": round(duration * 1000, 1),
                    "client_ip": request.client.host if request.client else "",
                }
                if status >= 500:
                    access_logger.error("request_failed", extra=extra)
                elif duration > 1:
                    access_logger.warning("request_slow", extra=extra)
                else:
                    access_logger.info("request", extra=extra)

            request_id_ctx.reset(token)


def _apply_headers(response: Response, request: Request, request_id: str) -> None:
    headers = response.headers
    headers["X-Request-ID"] = request_id
    for key, value in _SECURITY_HEADERS.items():
        headers.setdefault(key, value)
    if settings.is_prod:
        headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
    if request.url.scheme == "https":
        headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
