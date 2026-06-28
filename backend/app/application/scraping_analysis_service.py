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
from urllib.parse import urlparse

from app import PIPELINE_VERSION
from app.core.exceptions import RobotsDisallowedError
from app.domain.interfaces import AnalysisService, WebScraper
from app.domain.models import (
    AnalysisMeta,
    CompanyAnalysis,
    LeadScore,
    LeadTier,
    ScrapedContent,
    ScoreReason,
)
from app.infrastructure.scraping.robots import RobotsChecker

logger = logging.getLogger(__name__)

# Başlıkları şirket adına indirgerken kullanılan ayraçlar ("Acme | Anasayfa").
_TITLE_SEPARATORS = ("|", "—", "–", "-", "·", ":", "•")


class ScrapingAnalysisService(AnalysisService):
    def __init__(self, scraper: WebScraper, robots_checker: RobotsChecker | None = None):
        self._scraper = scraper
        self._robots_checker = robots_checker

    async def analyze(self, url: str) -> CompanyAnalysis:
        if self._robots_checker is not None and not await self._robots_checker.is_allowed(url):
            raise RobotsDisallowedError()

        content = await self._scraper.scrape(url)
        company_name = self._company_name(content, url)
        logger.info("Analiz için içerik hazır: %s (%d kelime)", company_name, content.word_count)

        return CompanyAnalysis(
            url=url,
            company_name=company_name,
            summary=(
                "[İSKELET] LLM tarafından üretilen şirket özeti Sprint 3'te gelecek. "
                f"Şu an {content.word_count} kelimelik gerçek içerik çekildi "
                f"({content.renderer} render)."
            ),
            pain_points=(
                "[İskelet] Acı noktaları Sprint 3'te LLM ile çıkarılacak.",
            ),
            lead_score=self._placeholder_score(),
            cold_email="[İSKELET] Soğuk e-posta Sprint 4'te üretilecek.",
            pitch="[İSKELET] Toplantı sunumu Sprint 4'te üretilecek.",
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
                    rule="skeleton_placeholder",
                    points=50,
                    explanation="Kural tabanlı skorlama Sprint 3'te eklenecek.",
                ),
            ),
        )

    @classmethod
    def _company_name(cls, content: ScrapedContent, url: str) -> str:
        if content.site_name:
            return content.site_name.strip()

        if content.title:
            for sep in _TITLE_SEPARATORS:
                if sep in content.title:
                    candidate = content.title.split(sep)[0].strip()
                    if candidate:
                        return candidate
            return content.title.strip()

        return cls._derive_from_url(url)

    @staticmethod
    def _derive_from_url(url: str) -> str:
        host = (urlparse(url).hostname or url).removeprefix("www.")
        base = host.split(".")[0] if "." in host else host
        return base.replace("-", " ").replace("_", " ").title() or "Bilinmeyen Şirket"
