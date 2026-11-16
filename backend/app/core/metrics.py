"""Prometheus 指标（/metrics 暴露）。

只保留低基数、排障必要的指标：
- http_requests_total{method,path,status}
- http_request_duration_seconds{method,path}
- http_requests_in_progress
- db_up / redis_up（由 /api/ready 刷新）
"""
from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS = Counter(
    "http_requests_total", "HTTP 请求总数", ["method", "path", "status"]
)
HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP 请求耗时（秒）",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
HTTP_IN_PROGRESS = Gauge("http_requests_in_progress", "当前处理中的请求数")
DB_UP = Gauge("database_up", "数据库是否可用（1/0）")
REDIS_UP = Gauge("redis_up", "Redis 是否可用（1/0）")
