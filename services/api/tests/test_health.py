def test_ping(client):
    response = client.get("/v1/health/ping")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_check_shape(client):
    """Health returns 200 or 503 depending on dep state, but shape is always the same."""
    response = client.get("/v1/health")
    assert response.status_code in (200, 503)
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    assert "database" in body["checks"]
    assert "redis" in body["checks"]
    assert "ai_provider" in body["checks"]
    assert "market_data" in body["checks"]
