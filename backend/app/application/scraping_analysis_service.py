"""Sprint 2 `AnalysisService`: gerçek scraping yapan analiz servisi.

`StubAnalysisService`'in yerini alır. Artık `company_name` ve `scraped` alanları
GERÇEK veriyle dolar. Özet/acı noktaları/e-posta/pitch/lead skoru hâlâ
placeholder'dır (LLM Sprint 3, e-posta+pitch Sprint 4) — bu yüzden
`meta.is_stub` hâlâ True'dur. Yani: "scraping gerçek, AI çıktısı henüz değil".

Bağımlılıklar arayüz üzerinden enjekte edilir (DIP): servis, hangi somut
scraper'ın geldiğini bilmez.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app import PIPELINE_VERSION
from app.application.company_name import derive_company_name
from app.core.exceptions import RobotsDisallowedError
from app.domain.interfaces import AnalysisService, WebScraper
from app.domain.models import (
    AnalysisMeta,
    CompanyAnalysis,
    LeadScore,
    LeadTier,
    ScoreReason,
)
from app.infrastructure.scraping.robots import RobotsChecker

logger = logging.getLogger(__name__)


class ScrapingAnalysisService(AnalysisService):
    def __init__(self, scraper: WebScraper, robots_checker: RobotsChecker | None = None):
        self._scraper = scraper
        self._robots_checker = robots_checker

    async def analyze(self, url: str) -> CompanyAnalysis:
        if self._robots_checker is not None and not await self._robots_checker.is_allowed(url):
            raise RobotsDisallowedError()

        content = await self._scraper.scrape(url)
        company_name = derive_company_name(content, url)
        logger.info("Analiz için içerik hazır: %s (%d kelime)", company_name, content.word_count)

        return CompanyAnalysis(
            url=url,
            company_name=company_name,
            summary=(
                "[LLM KAPALI] Şirket özeti için API anahtarı gerekir. "
                f"Şu an {content.word_count} kelimelik gerçek içerik çekildi "
                f"({content.renderer} render)."
            ),
            pain_points=(
                "[LLM KAPALI] Acı noktaları için API anahtarı (COPILOT_ANTHROPIC_API_KEY) ekleyin.",
            ),
            lead_score=self._placeholder_score(),
            cold_email="[LLM KAPALI] Soğuk e-posta için API anahtarı ekleyin.",
            pitch="[LLM KAPALI] Toplantı sunumu için API anahtarı ekleyin.",
            meta=AnalysisMeta(
                generated_at=datetime.now(timezone.utc),
                pipeline_version=PIPELINE_VERSION,
                is_stub=True,
            ),
            scraped=content,
        )

    @staticmethod
    def _placeholder_score() -> LeadScore:
        return LeadScore(
            value=50,
            tier=LeadTier.WARM,
            reasons=(
                ScoreReason(
                    rule="llm_disabled",
                    points=50,
                    explanation="Gerçek skor için API anahtarı (LLM) gerekir.",
                ),
            ),
        )
