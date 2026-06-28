"""/health endpoint'inin entegrasyon testi (gerçek HTTP katmanı dahil)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    assert "version" in body


def test_health_sets_request_id_header(client: TestClient) -> None:
    response = client.get("/health")
    # Middleware her yanıta izleme için X-Request-ID eklemeli.
    assert response.headers.get("X-Request-ID")
