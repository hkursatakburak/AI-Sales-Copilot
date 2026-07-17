"""/email endpoint'inin entegrasyon testleri."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_analysis_service, get_cached_analysis_service
from app.application.llm_analysis_service import LLMAnalysisService
from app.application.rule_based_scoring_engine import RuleBasedScoringEngine
from app.main import create_app
from tests.conftest import make_test_app
from tests.factories import (
    FakeAnalyzer,
    FakeOutreachWriter,
    FakeScraper,
    make_scraped_content,
)


@pytest.fixture
def client_with_llm(settings) -> TestClient:
    service = LLMAnalysisService(
        FakeScraper(make_scraped_content(site_name="Acme Corp")),
        FakeAnalyzer(),
        RuleBasedScoringEngine(),
        FakeOutreachWriter(email="Merhaba, kısa bir görüşme?", pitch="- Madde 1"),
    )
    app = make_test_app(settings)
    app.dependency_overrides[get_analysis_service] = lambda: service
    app.dependency_overrides[get_cached_analysis_service] = lambda: service
    return TestClient(app)


def test_email_returns_cold_email_and_pitch(client_with_llm: TestClient) -> None:
    response = client_with_llm.post("/email", json={"url": "https://www.acme-corp.com"})

    assert response.status_code == 200
    body = response.json()
    assert body["company_name"] == "Acme Corp"
    assert body["cold_email"] == "Merhaba, kısa bir görüşme?"
    assert body["pitch"] == "- Madde 1"
    assert body["is_stub"] is False


def test_email_rejects_invalid_url(client: TestClient) -> None:
    response = client.post("/email", json={"url": "bad"})
    assert response.status_code == 422
