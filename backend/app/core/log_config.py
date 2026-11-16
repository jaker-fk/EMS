"""日志与请求上下文。

- `request_id_ctx`：整条请求链路共享的 request id（响应头也会返回），便于串联 Nginx / 应用 / 慢查询日志；
- `setup_logging()`：按 `LOG_FORMAT` 输出文本或 JSON，容器里建议 JSON；
- 访问日志由 `RequestContextMiddleware` 输出，字段包含 method / path / status / duration_ms / client_ip。
"""
from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

from app.core.config import settings

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

_EXTRA_FIELDS = ("method", "path", "status", "duration_ms", "client_ip", "user_id", "attempt")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        for field in _EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = f"{self.formatTime(record, '%Y-%m-%d %H:%M:%S')} {record.levelname} [{getattr(record, 'request_id', '-')}] {record.name}: {record.getMessage()}"
        extras = [
            f"{field}={getattr(record, field)}"
            for field in _EXTRA_FIELDS
            if getattr(record, field, None) is not None
        ]
        if extras:
            base += " " + " ".join(extras)
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


def setup_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if settings.LOG_FORMAT == "json" else TextFormatter())
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # uvicorn 的默认 handler 会绕过我们的格式，清掉并交给 root 统一输出；
    # 访问日志由 ObservabilityMiddleware 统一输出（含 request_id/耗时），这里关闭 uvicorn 自带的一份避免重复
    for name in ("uvicorn", "uvicorn.error"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers = []
        uv_logger.propagate = True
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers = []
    uvicorn_access.propagate = False
    uvicorn_access.disabled = True
