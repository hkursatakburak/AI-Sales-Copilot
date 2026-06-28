"""/analyze endpoint'inin entegrasyon testleri.

API sözleşmesini (request/response biçimi, hata davranışı) doğrularız. Gerçek
ağ KULLANILMAZ: `get_analysis_service` bağımlılığı, sahte scraper'lı bir
servisle override edilir.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_analysis_service
from app.application.scraping_analysis_service import ScrapingAnalysisService
from app.domain.interfaces import AnalysisService
from app.domain.models import (
    AnalysisMeta,
    CompanyAnalysis,
    LeadScore,
    LeadTier,
    ScoreReason,
)
from app.application.llm_analysis_service import LLMAnalysisService
from app.application.rule_based_scoring_engine import RuleBasedScoringEngine
from app.main import create_app
from tests.factories import (
    FakeAnalyzer,
    FakeOutreachWriter,
    FakeScraper,
    make_scraped_content,
)


@pytest.fixture
def client_with_fake_scraper(settings) -> TestClient:
    """Sahte scraper'lı gerçek `ScrapingAnalysisService` enjekte eder."""
    content = make_scraped_content(
        url="https://www.acme-corp.com",
        site_name="Acme Corp",
        text="Acme bulut çözümleri sunar. " * 30,
        renderer="static",
    )
    service = ScrapingAnalysisService(FakeScraper(content))  # robots_checker yok

    app = create_app(settings=settings)
    app.dependency_overrides[get_analysis_service] = lambda: service
    return TestClient(app)


def test_analyze_happy_path(client_with_fake_scraper: TestClient) -> None:
    response = client_with_fake_scraper.post(
        "/analyze", json={"url": "https://www.acme-corp.com"}
    )

    assert response.status_code == 200
    body = response.json()

    # Pydantic HttpUrl URL'yi normalize eder (sona '/' ekler).
    assert body["url"] == "https://www.acme-corp.com/"
    assert body["company_name"] == "Acme Corp"
    assert 0 <= body["lead_score"]["value"] <= 100
    assert body["lead_score"]["reasons"]

    # Sprint 2: gerçek scraping çıktısı yanıtта olmalı.
    assert body["scraped"] is not None
    assert body["scraped"]["renderer"] == "static"
    assert body["scraped"]["word_count"] > 0
    assert body["scraped"]["content_preview"]


def test_analyze_llm_pipeline_returns_real_analysis(settings) -> None:
    """Sprint 3: LLM pipeline (sahte scraper + analyzer) gerçek analiz döndürür."""
    content = make_scraped_content(site_name="Acme Corp", text="Acme bulut. " * 30)
    service = LLMAnalysisService(
        FakeScraper(content),
        FakeAnalyzer(),
        RuleBasedScoringEngine(),
        FakeOutreachWriter(),
    )

    app = create_app(settings=settings)
    app.dependency_overrides[get_analysis_service] = lambda: service
    client = TestClient(app)

    response = client.post("/analyze", json={"url": "https://www.acme-corp.com"})

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["is_stub"] is False
    assert body["company_name"] == "Acme Corp"
    assert body["summary"] == "Örnek şirket özeti."
    assert body["pain_points"]
    assert body["signals"]["sector"] == "SaaS"
    assert 0 <= body["lead_score"]["value"] <= 100
    assert body["lead_score"]["tier"] in {"hot", "warm", "cold"}
    # Sprint 4: gerçek e-posta + pitch
    assert body["cold_email"] == "Sahte soğuk e-posta"
    assert body["pitch"] == "Sahte pitch"


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
    """DI override: route'a tamamen sahte bir servis enjekte edilebilir."""

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
    assert body["scraped"] is None  # bu sahte serviste scraping yok
