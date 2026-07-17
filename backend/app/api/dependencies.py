"""Bağımlılık enjeksiyonu (Dependency Injection) sağlayıcıları.

FastAPI'nin `Depends` mekanizması bizim DI konteyner'ımızdır. Route'lar somut
sınıf adı yerine `AnalysisService` arayüzünü ister; burada hangi somut
uygulamanın ve hangi bağımlılık ağacının kurulacağına karar verilir.

Sprint 2: gerçek scraping pipeline'ı kurulur:
    HybridScraper(BeautifulSoupScraper, PlaywrightScraper) -> ScrapingAnalysisService
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.application.caching_analysis_service import CachingAnalysisService
from app.application.company_insight_analyzer import LLMCompanyInsightAnalyzer
from app.application.llm_analysis_service import LLMAnalysisService
from app.application.llm_outreach_writer import LLMOutreachWriter
from app.application.rule_based_scoring_engine import RuleBasedScoringEngine
from app.application.scraping_analysis_service import ScrapingAnalysisService
from app.core.config import get_settings
from app.domain.interfaces import AnalysisService, WebScraper
from app.domain.models import SellerProfile
from app.infrastructure.llm.factory import create_llm_provider
from app.infrastructure.scraping.beautifulsoup_scraper import BeautifulSoupScraper

logger = logging.getLogger(__name__)
from app.infrastructure.scraping.hybrid_scraper import HybridScraper
from app.infrastructure.scraping.playwright_scraper import PlaywrightScraper
from app.infrastructure.scraping.rate_limiter import HostRateLimiter
from app.infrastructure.scraping.robots import RobotsChecker
from app.infrastructure.scraping.url_guard import UrlGuard


@lru_cache
def get_web_scraper() -> WebScraper:
    """Aktif scraper'ı (tekil) kurar ve döndürür."""
    settings = get_settings()
    guard = UrlGuard(allow_private=settings.scraper_allow_private_urls)
    rate_limiter = HostRateLimiter(settings.scraper_min_request_interval_seconds)

    static_scraper = BeautifulSoupScraper(
        guard,
        timeout=settings.scraper_timeout_seconds,
        connect_timeout=settings.scraper_connect_timeout_seconds,
        user_agent=settings.scraper_user_agent,
        max_retries=settings.scraper_max_retries,
        retry_backoff=settings.scraper_retry_backoff_seconds,
        rate_limiter=rate_limiter,
    )
    dynamic_scraper = PlaywrightScraper(
        guard,
        timeout=settings.scraper_timeout_seconds * 2,
        user_agent=settings.scraper_user_agent,
        settle_timeout=settings.scraper_settle_timeout_seconds,
    )
    return HybridScraper(
        static_scraper,
        dynamic_scraper,
        min_words=settings.scraper_min_words_for_dynamic,
    )


@lru_cache
def get_analysis_service() -> AnalysisService:
    """Aktif `AnalysisService` uygulamasını (tekil) döndürür.

    API anahtarı varsa tam LLM pipeline'ı (Sprint 3) kurulur; yoksa zarif
    şekilde scraping-only (Sprint 2, is_stub=True) davranışına düşülür — böylece
    uygulama anahtar olmadan da çalışır.
    """
    settings = get_settings()
    robots_checker = (
        RobotsChecker(user_agent=settings.scraper_user_agent)
        if settings.scraper_respect_robots
        else None
    )

    provider = create_llm_provider(settings)
    if provider is None:
        logger.warning(
            "LLM devre dışı (sağlayıcı/anahtar yok) — scraping-only moda düşülüyor "
            "(is_stub=True). LLM_PROVIDER ve ilgili API anahtarını ayarlayın."
        )
        return ScrapingAnalysisService(get_web_scraper(), robots_checker=robots_checker)

    analyzer = LLMCompanyInsightAnalyzer(
        provider, max_input_chars=settings.llm_max_input_chars
    )
    seller = SellerProfile(
        name=settings.seller_name,
        offering=settings.seller_offering,
        rep_name=settings.seller_rep_name,
    )
    outreach_writer = LLMOutreachWriter(
        provider,
        seller,
        email_max_tokens=settings.llm_email_max_tokens,
        pitch_max_tokens=settings.llm_pitch_max_tokens,
    )
    return LLMAnalysisService(
        get_web_scraper(),
        analyzer,
        RuleBasedScoringEngine(),
        outreach_writer,
        robots_checker=robots_checker,
    )


@lru_cache
def get_cached_analysis_service() -> AnalysisService:
    """TTL önbellekli AnalysisService — yalnızca /analyze için kullanılır."""
    settings = get_settings()
    return CachingAnalysisService(
        get_analysis_service(),
        ttl=settings.cache_ttl_seconds,
        maxsize=settings.cache_maxsize,
    )
