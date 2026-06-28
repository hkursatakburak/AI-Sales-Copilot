"""Sprint 3 `AnalysisService`: scraping + LLM içgörü + kural tabanlı skorlama.

Pipeline (düz, sıralı orkestrasyon — rehberin önerdiği gibi LangGraph YOK):
    robots kontrolü -> scrape -> LLM içgörü (özet+pain point+sinyaller) ->
    kural tabanlı skor -> CompanyAnalysis

Artık `is_stub=False`: özet, acı noktaları ve lead skoru GERÇEK. Yalnızca
soğuk e-posta ve pitch placeholder kalır (Sprint 4).

Tüm bağımlılıklar arayüz üzerinden enjekte edilir (DIP) → her parça ayrı ayrı
test edilebilir, LLM mock'lanabilir.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app import PIPELINE_VERSION
from app.application.company_name import derive_company_name
from app.core.exceptions import RobotsDisallowedError
from app.domain.interfaces import (
    AnalysisService,
    CompanyInsightAnalyzer,
    OutreachWriter,
    ScoringEngine,
    WebScraper,
)
from app.domain.models import AnalysisMeta, CompanyAnalysis
from app.infrastructure.scraping.robots import RobotsChecker

logger = logging.getLogger(__name__)


class LLMAnalysisService(AnalysisService):
    def __init__(
        self,
        scraper: WebScraper,
        analyzer: CompanyInsightAnalyzer,
        scoring_engine: ScoringEngine,
        outreach_writer: OutreachWriter,
        robots_checker: RobotsChecker | None = None,
    ):
        self._scraper = scraper
        self._analyzer = analyzer
        self._scoring_engine = scoring_engine
        self._outreach_writer = outreach_writer
        self._robots_checker = robots_checker

    async def analyze(self, url: str) -> CompanyAnalysis:
        if self._robots_checker is not None and not await self._robots_checker.is_allowed(url):
            raise RobotsDisallowedError()

        content = await self._scraper.scrape(url)
        company_name = derive_company_name(content, url)

        insights = await self._analyzer.analyze(content)
        lead_score = self._scoring_engine.score(insights.signals)

        # E-posta ve pitch birbirinden bağımsız → eşzamanlı üret (daha hızlı).
        cold_email, pitch = await asyncio.gather(
            self._outreach_writer.write_cold_email(company_name, insights),
            self._outreach_writer.write_pitch(company_name, insights),
        )

        logger.info(
            "Analiz tamam: %s | skor=%d (%s) | %d acı noktası",
            company_name,
            lead_score.value,
            lead_score.tier.value,
            len(insights.pain_points),
        )

        return CompanyAnalysis(
            url=url,
            company_name=company_name,
            summary=insights.summary,
            pain_points=insights.pain_points,
            lead_score=lead_score,
            cold_email=cold_email,
            pitch=pitch,
            meta=AnalysisMeta(
                generated_at=datetime.now(timezone.utc),
                pipeline_version=PIPELINE_VERSION,
                is_stub=False,
            ),
            scraped=content,
            signals=insights.signals,
        )
