"""Bağımlılık enjeksiyonu (Dependency Injection) sağlayıcıları.

FastAPI'nin `Depends` mekanizması bizim DI konteyner'ımızdır. Route'lar somut
sınıf adı yerine `AnalysisService` arayüzünü ister; burada hangi somut
uygulamanın ve hangi bağımlılık ağacının kurulacağına karar verilir.

Sprint 2: gerçek scraping pipeline'ı kurulur:
    HybridScraper(BeautifulSoupScraper, PlaywrightScraper) -> ScrapingAnalysisService
"""

from __future__ import annotations

from functools import lru_cache

from app.application.scraping_analysis_service import ScrapingAnalysisService
from app.core.config import get_settings
from app.domain.interfaces import AnalysisService, WebScraper
from app.infrastructure.scraping.beautifulsoup_scraper import BeautifulSoupScraper
from app.infrastructure.scraping.hybrid_scraper import HybridScraper
from app.infrastructure.scraping.playwright_scraper import PlaywrightScraper
from app.infrastructure.scraping.robots import RobotsChecker
from app.infrastructure.scraping.url_guard import UrlGuard


@lru_cache
def get_web_scraper() -> WebScraper:
    """Aktif scraper'ı (tekil) kurar ve döndürür."""
    settings = get_settings()
    guard = UrlGuard(allow_private=settings.scraper_allow_private_urls)

    static_scraper = BeautifulSoupScraper(
        guard,
        timeout=settings.scraper_timeout_seconds,
        user_agent=settings.scraper_user_agent,
    )
    dynamic_scraper = PlaywrightScraper(
        guard,
        timeout=settings.scraper_timeout_seconds * 2,
        user_agent=settings.scraper_user_agent,
    )
    return HybridScraper(
        static_scraper,
        dynamic_scraper,
        min_words=settings.scraper_min_words_for_dynamic,
    )


@lru_cache
def get_analysis_service() -> AnalysisService:
    """Aktif `AnalysisService` uygulamasını (tekil) döndürür."""
    settings = get_settings()
    robots_checker = (
        RobotsChecker(user_agent=settings.scraper_user_agent)
        if settings.scraper_respect_robots
        else None
    )
    return ScrapingAnalysisService(get_web_scraper(), robots_checker=robots_checker)
