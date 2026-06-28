"""`ScrapingAnalysisService` testleri."""

from __future__ import annotations

import pytest

from app.application.scraping_analysis_service import ScrapingAnalysisService
from app.domain.models import CompanyAnalysis
from tests.factories import FakeScraper, make_scraped_content


@pytest.mark.asyncio
async def test_analyze_attaches_scraped_content() -> None:
    content = make_scraped_content(text="bir iki üç dört beş", renderer="static")
    service = ScrapingAnalysisService(FakeScraper(content))

    result = await service.analyze("https://example.com")

    assert isinstance(result, CompanyAnalysis)
    assert result.scraped is content
    assert result.scraped.word_count == 5
    assert result.meta.is_stub is True  # AI çıktıları henüz placeholder


@pytest.mark.asyncio
async def test_company_name_prefers_site_name() -> None:
    content = make_scraped_content(site_name="Acme A.Ş.", title="Acme | Anasayfa")
    service = ScrapingAnalysisService(FakeScraper(content))

    result = await service.analyze("https://acme.com")
    assert result.company_name == "Acme A.Ş."


@pytest.mark.asyncio
async def test_company_name_falls_back_to_title_prefix() -> None:
    content = make_scraped_content(site_name=None, title="Acme Corp | Anasayfa")
    service = ScrapingAnalysisService(FakeScraper(content))

    result = await service.analyze("https://acme.com")
    assert result.company_name == "Acme Corp"


@pytest.mark.asyncio
async def test_company_name_falls_back_to_domain() -> None:
    content = make_scraped_content(site_name=None, title=None)
    service = ScrapingAnalysisService(FakeScraper(content))

    result = await service.analyze("https://big-data.io/products")
    assert result.company_name == "Big Data"


@pytest.mark.asyncio
async def test_passes_url_to_scraper() -> None:
    scraper = FakeScraper(make_scraped_content())
    service = ScrapingAnalysisService(scraper)

    await service.analyze("https://example.com/about")
    assert scraper.last_url == "https://example.com/about"
