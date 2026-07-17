"""Multi-page crawler: ana sayfa + öncelikli alt sayfaları çekip birleştirir.

Tek sayfalık scraping'in kör noktasını kapatır: /about, /services, /team gibi
marka sinyali taşıyan sayfalar artık LLM'e de ulaşır.

Aynı `WebScraper` arayüzünü uygular ve `HybridScraper`'ı sarmalar (decorator).
Üst katman hiçbir farkı görmez. İç scraper zaten UrlGuard + rate limiter
içerdiğinden burada ayrıca adres doğrulaması yapılmaz; aynı host, aynı kural.
"""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import urljoin, urlparse

from app.core.exceptions import ScrapeError
from app.domain.interfaces import WebScraper
from app.domain.models import ScrapedContent

logger = logging.getLogger(__name__)

_PRIORITY_PATHS: list[str] = [
    "/about",
    "/about-us",
    "/who-we-are",
    "/services",
    "/products",
    "/solutions",
    "/team",
    "/our-team",
    "/careers",
    "/jobs",
    "/contact",
    "/contact-us",
]


def _path_label(url: str) -> str:
    """URL'den okunabilir bölüm etiketi üretir (birleştirilmiş metinde kullanılır)."""
    path = urlparse(url).path.strip("/")
    return path.replace("-", " ").replace("/", " > ").title() or "Home"


class MultiPageCrawler(WebScraper):
    """Inner scraper'ı sarmalayan çok sayfalı tarayıcı.

    `scrape(url)`:
    1. Ana URL'yi inner scraper ile çeker.
    2. Baz domain üzerinde öncelikli alt sayfa adayları oluşturur.
    3. Adayları eş zamanlı çeker; başarısızlar sessizce atlanır.
    4. Tüm sonuçları tek bir zenginleştirilmiş `ScrapedContent`'te birleştirir.
    """

    def __init__(
        self,
        inner: WebScraper,
        *,
        max_subpages: int = 4,
        min_words: int = 50,
    ) -> None:
        self._inner = inner
        self._max_subpages = max_subpages
        self._min_words = min_words

    async def scrape(self, url: str) -> ScrapedContent:
        main = await self._inner.scrape(url)

        candidates = self._candidate_urls(url)
        if not candidates:
            return main

        tasks = [self._safe_scrape(c) for c in candidates]
        results: list[ScrapedContent | None] = await asyncio.gather(*tasks)

        extras = [
            r for r in results
            if r is not None and r.word_count >= self._min_words
        ]

        if not extras:
            return main

        merged = self._merge(main, extras)
        logger.info(
            "Çok sayfalı çekim tamamlandı: %d alt sayfa birleştirildi, "
            "toplam %d kelime (%s)",
            len(extras),
            merged.word_count,
            url,
        )
        return merged

    async def _safe_scrape(self, url: str) -> ScrapedContent | None:
        try:
            return await self._inner.scrape(url)
        except ScrapeError as exc:
            logger.debug("Alt sayfa atlandı (%s): %s", exc, url)
            return None

    def _candidate_urls(self, entry_url: str) -> list[str]:
        parsed = urlparse(entry_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        seen: set[str] = {entry_url.rstrip("/")}
        candidates: list[str] = []

        for path in _PRIORITY_PATHS:
            candidate = urljoin(base, path)
            key = candidate.rstrip("/")
            if key in seen:
                continue
            seen.add(key)
            candidates.append(candidate)
            if len(candidates) >= self._max_subpages:
                break

        return candidates

    def _merge(self, main: ScrapedContent, extras: list[ScrapedContent]) -> ScrapedContent:
        parts = [main.text]
        for extra in extras:
            label = _path_label(extra.url)
            parts.append(f"\n\n[{label}]\n{extra.text}")

        merged_text = "".join(parts)

        seen_headings: set[str] = set(main.headings)
        extra_headings: list[str] = []
        for extra in extras:
            for h in extra.headings:
                if h not in seen_headings:
                    seen_headings.add(h)
                    extra_headings.append(h)

        all_headings = tuple(list(main.headings) + extra_headings)[:30]

        return ScrapedContent(
            url=main.url,
            title=main.title,
            site_name=main.site_name,
            meta_description=main.meta_description,
            text=merged_text,
            headings=all_headings,
            word_count=len(merged_text.split()),
            renderer=main.renderer,
            fetched_at=main.fetched_at,
            detected_name=main.detected_name,
        )
