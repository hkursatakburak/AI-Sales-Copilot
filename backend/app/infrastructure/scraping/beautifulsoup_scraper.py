"""Statik scraper: httpx ile HTML indir, BeautifulSoup ile temizle.

JavaScript ÇALIŞTIRMAZ. İçeriği doğrudan HTML'de olan (sunucu tarafında
render edilen) sayfalar için idealdir — çok hızlı ve hafiftir. İçerik JS ile
yükleniyorsa metin boş/az gelir; bu durumu `HybridScraper` yakalayıp dinamik
yedeğe geçer.

Test edilebilirlik: `transport` parametresiyle httpx'e sahte bir taşıyıcı
(MockTransport) enjekte edilebilir; böylece testler gerçek ağ kullanmaz.
"""

from __future__ import annotations

import logging

import httpx

from app.core.exceptions import ScrapeError
from app.domain.interfaces import WebScraper
from app.domain.models import ScrapedContent
from app.infrastructure.scraping.content_builder import build_scraped_content
from app.infrastructure.scraping.html_cleaner import clean_html
from app.infrastructure.scraping.url_guard import UrlGuard

logger = logging.getLogger(__name__)


class BeautifulSoupScraper(WebScraper):
    def __init__(
        self,
        guard: UrlGuard,
        *,
        timeout: float = 10.0,
        user_agent: str = "AISalesCopilotBot/0.1",
        transport: httpx.BaseTransport | None = None,
    ):
        self._guard = guard
        self._timeout = timeout
        self._user_agent = user_agent
        self._transport = transport  # yalnızca testlerde doldurulur

    async def scrape(self, url: str) -> ScrapedContent:
        self._guard.validate(url)

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers={"User-Agent": self._user_agent},
                transport=self._transport,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ScrapeError(
                f"Sayfa alınamadı (HTTP {exc.response.status_code}): {url}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ScrapeError(f"Sayfaya bağlanılamadı: {url}") from exc

        document = clean_html(response.text)
        content = build_scraped_content(url, document, renderer="static")
        logger.info("Statik scrape tamam: %s (%d kelime)", url, content.word_count)
        return content
