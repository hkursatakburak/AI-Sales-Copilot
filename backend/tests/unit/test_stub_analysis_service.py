"""`StubAnalysisService` davranış testleri.

Bu testler iskeletin verdiği sözü tutar: geçerli, deterministik ve `is_stub`
işaretli bir analiz döndürmek.
"""

from __future__ import annotations

import pytest

from app.application.stub_analysis_service import StubAnalysisService
from app.domain.models import CompanyAnalysis


@pytest.fixture
def service() -> StubAnalysisService:
    return StubAnalysisService()


@pytest.mark.asyncio
async def test_analyze_returns_company_analysis(service: StubAnalysisService) -> None:
    result = await service.analyze("https://www.acme-corp.com/about")

    assert isinstance(result, CompanyAnalysis)
    assert result.url == "https://www.acme-corp.com/about"
    assert result.summary  # boş değil
    assert result.pain_points  # en az bir madde
    assert 0 <= result.lead_score.value <= 100
    assert result.lead_score.reasons  # açıklanabilirlik: en az bir gerekçe


@pytest.mark.asyncio
async def test_analyze_marks_result_as_stub(service: StubAnalysisService) -> None:
    result = await service.analyze("https://example.com")
    assert result.meta.is_stub is True


@pytest.mark.asyncio
async def test_analyze_is_deterministic(service: StubAnalysisService) -> None:
    # Aynı URL -> aynı içerik (zaman damgası hariç). Testlerin stabilitesi için.
    a = await service.analyze("https://example.com")
    b = await service.analyze("https://example.com")
    assert a.summary == b.summary
    assert a.company_name == b.company_name
    assert a.lead_score.value == b.lead_score.value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("url", "expected_name"),
    [
        ("https://www.acme-corp.com", "Acme Corp"),
        ("https://big_data.io/products", "Big Data"),
        ("https://example.com:8080/path", "Example"),
    ],
)
async def test_company_name_derived_from_url(
    service: StubAnalysisService, url: str, expected_name: str
) -> None:
    result = await service.analyze(url)
    assert result.company_name == expected_name
