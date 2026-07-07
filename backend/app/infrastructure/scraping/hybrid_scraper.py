"""Hybrid scraper: önce statik dene, gerekirse dinamiğe düş.

Rehberin önerdiği pratik kural: "Önce BeautifulSoup ile dene; içerik gelmiyorsa
(JS ile yükleniyordur) Playwright'a geç." Bu, çoğu sitede hızlı/ucuz statik
yolu kullanıp, yalnızca gereken sitelerde pahalı tarayıcıyı devreye sokar.

Strategy + Decorator karışımı: `HybridScraper` da bir `WebScraper`'dır ve
içine iki `WebScraper` alır. Üst katman farkı görmez.
"""

from __future__ import annotations

import logging

from app.core.exceptions import ScrapeError
from app.domain.interfaces import WebScraper
from app.domain.models import ScrapedContent

logger = logging.getLogger(__name__)


class HybridScraper(WebScraper):
    def __init__(
        self,
        static_scraper: WebScraper,
        dynamic_scraper: WebScraper,
        *,
        min_words: int = 120,
    ):
        self._static = static_scraper
        self._dynamic = dynamic_scraper
        self._min_words = min_words

    async def scrape(self, url: str) -> ScrapedContent:
        try:
            static_content = await self._static.scrape(url)
        except ScrapeError as static_exc:
            logger.info(
                "Statik scrape hata verdi (%s), dinamik yedeğe geçiliyor: %s",
                static_exc,
                url,
            )
            # Statik hata verdiğinde dinamiği dene. O da hata verirse fırlat.
            return await self._dynamic.scrape(url)

        if static_content.word_count >= self._min_words:
            return static_content

        logger.info(
            "Statik içerik zayıf (%d < %d kelime), dinamik yedeğe geçiliyor: %s",
            static_content.word_count,
            self._min_words,
            url,
        )

        try:
            dynamic_content = await self._dynamic.scrape(url)
        except ScrapeError as exc:
            # Dinamik başarısızsa (örn. Playwright yok) eldeki statik sonuca düş.
            logger.warning("Dinamik scrape başarısız (%s), statik sonuç dönülüyor.", exc)
            return static_content

        # Hangi yol daha çok içerik getirdiyse onu döndür.
        if dynamic_content.word_count > static_content.word_count:
            return dynamic_content
        return static_content
