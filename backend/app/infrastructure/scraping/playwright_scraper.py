"""Dinamik scraper: Playwright ile gerçek tarayıcı çalıştırıp JS'i render et.

İçeriği JavaScript ile yüklenen modern siteler (SPA'lar) için gereklidir.
Statik scraper'dan ağırdır (CPU/RAM), bu yüzden yalnızca gerekince kullanılır.

Playwright İSTEĞE BAĞLI bir bağımlılıktır: import içeride (lazy) yapılır.
Kurulu değilse net bir `ScrapeError` döner; böylece statik yol Playwright
olmadan da çalışmaya devam eder. Tarayıcı ikilisi ayrıca kurulur:
    playwright install chromium
"""

from __future__ import annotations

import logging

from app.core.exceptions import ScrapeError
from app.domain.interfaces import WebScraper
from app.domain.models import ScrapedContent
from app.infrastructure.scraping.content_builder import build_scraped_content
from app.infrastructure.scraping.html_cleaner import clean_html
from app.infrastructure.scraping.url_guard import UrlGuard

logger = logging.getLogger(__name__)


class PlaywrightScraper(WebScraper):
    def __init__(
        self,
        guard: UrlGuard,
        *,
        timeout: float = 20.0,
        user_agent: str = "AISalesCopilotBot/0.1",
    ):
        self._guard = guard
        self._timeout_ms = int(timeout * 1000)
        self._user_agent = user_agent

    async def scrape(self, url: str) -> ScrapedContent:
        self._guard.validate(url)

        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # pragma: no cover - ortama bağlı
            raise ScrapeError(
                "Playwright kurulu değil. 'pip install playwright && "
                "playwright install chromium' çalıştırın."
            ) from exc

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                try:
                    page = await browser.new_page(user_agent=self._user_agent)
                    await page.goto(url, timeout=self._timeout_ms, wait_until="networkidle")
                    html = await page.content()
                finally:
                    await browser.close()
        except ScrapeError:
            raise
        except Exception as exc:  # Playwright çeşitli hata tipleri fırlatır
            raise ScrapeError(f"Tarayıcı ile sayfa render edilemedi: {url}") from exc

        document = clean_html(html)
        content = build_scraped_content(url, document, renderer="dynamic")
        logger.info("Dinamik scrape tamam: %s (%d kelime)", url, content.word_count)
        return content
