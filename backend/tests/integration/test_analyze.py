"""/analyze endpoint'inin entegrasyon testleri.

Burada API sözleşmesini (request/response biçimi, hata davranışı) doğrularız.
DI override örneği de gösterilir: route'un servisi nasıl sahteyle değiştirilir.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.dependencies import get_analysis_service
from app.domain.interfaces import AnalysisService
from app.domain.models import (
    AnalysisMeta,
    CompanyAnalysis,
    LeadScore,
    LeadTier,
    ScoreReason,
)
from app.main import create_app


def test_analyze_happy_path(client: TestClient) -> None:
    response = client.post("/analyze", json={"url": "https://www.acme-corp.com"})

    assert response.status_code == 200
    body = response.json()

    # Sözleşmedeki tüm alanlar mevcut mu?
    assert body["url"] == "https://www.acme-corp.com/"
    assert body["company_name"] == "Acme Corp"
    assert isinstance(body["pain_points"], list) and body["pain_points"]
    assert 0 <= body["lead_score"]["value"] <= 100
    assert body["lead_score"]["reasons"]  # açıklanabilirlik
    assert body["meta"]["is_stub"] is True


def test_analyze_rejects_invalid_url(client: TestClient) -> None:
    response = client.post("/analyze", json={"url": "not-a-valid-url"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["request_id"]


def test_analyze_requires_url_field(client: TestClient) -> None:
    response = client.post("/analyze", json={})
    assert response.status_code == 422


def test_analyze_uses_injected_service(settings) -> None:
    """DI override: route'a sahte bir servis enjekte edilebildiğini kanıtlar."""

    class FakeService(AnalysisService):
        async def analyze(self, url: str) -> CompanyAnalysis:
            return CompanyAnalysis(
                url=url,
                company_name="Sahte A.Ş.",
                summary="sahte özet",
                pain_points=("sahte acı noktası",),
                lead_score=LeadScore(
                    value=95,
                    tier=LeadTier.HOT,
                    reasons=(ScoreReason(rule="test", points=95, explanation="test"),),
                ),
                cold_email="sahte email",
                pitch="sahte pitch",
                meta=AnalysisMeta(
                    generated_at=datetime.now(timezone.utc),
                    pipeline_version="test",
                    is_stub=False,
                ),
            )

    app = create_app(settings=settings)
    app.dependency_overrides[get_analysis_service] = lambda: FakeService()
    client = TestClient(app)

    response = client.post("/analyze", json={"url": "https://example.com"})

    assert response.status_code == 200
    body = response.json()
    assert body["company_name"] == "Sahte A.Ş."
    assert body["lead_score"]["value"] == 95
    assert body["meta"]["is_stub"] is False
