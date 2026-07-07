"""`ScrapingAnalysisService` testleri."""

from __future__ import annotations

import pytest

from app.application.scraping_analysis_service import ScrapingAnalysisService
from app.core.exceptions import RobotsDisallowedError
from app.domain.models import CompanyAnalysis
from tests.factories import FakeScraper, make_scraped_content


class _FakeRobots:
    def __init__(self, allowed: bool):
        self._allowed = allowed
        self.checked = False

    async def is_allowed(self, url: str) -> bool:
        self.checked = True
        return self._allowed


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
async def test_uses_detected_name_when_present() -> None:
    # Akıllı ad çıkarımı html_cleaner'da yapılır; servis detected_name'i kullanır.
    content = make_scraped_content(detected_name="Acme A.Ş.")
    service = ScrapingAnalysisService(FakeScraper(content))

    result = await service.analyze("https://acme.com")
    assert result.company_name == "Acme A.Ş."


@pytest.mark.asyncio
async def test_company_name_falls_back_to_domain() -> None:
    content = make_scraped_content(detected_name=None)
    service = ScrapingAnalysisService(FakeScraper(content))

    result = await service.analyze("https://big-data.io/products")
    assert result.company_name == "Big Data"


@pytest.mark.asyncio
async def test_passes_url_to_scraper() -> None:
    scraper = FakeScraper(make_scraped_content())
    service = ScrapingAnalysisService(scraper)

    await service.analyze("https://example.com/about")
    assert scraper.last_url == "https://example.com/about"


@pytest.mark.asyncio
async def test_robots_disallowed_raises_before_scraping() -> None:
    scraper = FakeScraper(make_scraped_content())
    robots = _FakeRobots(allowed=False)
    service = ScrapingAnalysisService(scraper, robots_checker=robots)

    with pytest.raises(RobotsDisallowedError):
        await service.analyze("https://example.com")

    assert robots.checked is True
    assert scraper.called is False  # robots reddedince scrape edilmez


@pytest.mark.asyncio
async def test_robots_allowed_proceeds_to_scrape() -> None:
    scraper = FakeScraper(make_scraped_content())
    robots = _FakeRobots(allowed=True)
    service = ScrapingAnalysisService(scraper, robots_checker=robots)

    result = await service.analyze("https://example.com")
    assert result.scraped is not None
    assert scraper.called is True
