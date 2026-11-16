"""运维可观测性回归：健康检查、就绪检查、请求 ID、安全头、Prometheus 指标。"""


def test_health_liveness(client):
    body = client.get("/api/health").json()
    assert body["code"] == 200
    assert body["data"]["status"] == "ok"
    assert body["data"]["env"] in {"dev", "test", "prod"}


def test_ready_checks_database(client):
    resp = client.get("/api/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["database"] is True


def test_request_id_generated_and_echoed(client):
    first = client.get("/api/health")
    assert len(first.headers["x-request-id"]) >= 8

    # 合法的上游请求 ID 会被透传，方便和 Nginx / 网关日志对齐
    second = client.get("/api/health", headers={"X-Request-ID": "trace-abc-123"})
    assert second.headers["x-request-id"] == "trace-abc-123"


def test_security_headers_present(client):
    resp = client.get("/api/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "no-referrer"


def test_metrics_endpoint(client):
    client.get("/api/health")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "http_requests_total" in resp.text
    assert 'path="/api/health"' in resp.text
