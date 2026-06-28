"""Dinamik scraper: Playwright ile gerçek tarayıcı çalıştırıp JS'i render et.

İçeriği JavaScript ile yüklenen modern siteler (SPA'lar) için gereklidir.
Statik scraper'dan ağırdır (CPU/RAM), bu yüzden yalnızca gerekince kullanılır.

Playwright İSTEĞE BAĞLI bir bağımlılıktır: import içeride (lazy) yapılır.
Kurulu değilse net bir `ScrapeError` döner; böylece statik yol Playwright
olmadan da çalışmaya devam eder. Tarayıcı ikilisi ayrıca kurulur:
    playwright install chromium

Hata yönetimi: zaman aşımı kullanıcı dostu `ScrapeTimeoutError`'a, diğer
render hataları sade `ScrapeError`'a çevrilir.
"""

from __future__ import annotations

import logging

from app.core.exceptions import ScrapeError, ScrapeTimeoutError
from app.domain.interfaces import WebScraper
from app.domain.models import ScrapedContent
from app.infrastructure.scraping.content_builder import build_scraped_content
from app.infrastructure.scraping.html_cleaner import clean_html
from app.infrastructure.scraping.http_headers import browser_headers
from app.infrastructure.scraping.url_guard import UrlGuard

logger = logging.getLogger(__name__)


class PlaywrightScraper(WebScraper):
    def __init__(
        self,
        guard: UrlGuard,
        *,
        timeout: float = 25.0,
        user_agent: str = "AISalesCopilotBot/0.1",
    ):
        self._guard = guard
        self._timeout_ms = int(timeout * 1000)
        self._user_agent = user_agent

    async def scrape(self, url: str) -> ScrapedContent:
        self._guard.validate(url)

        try:
            from playwright.async_api import (
                Error as PlaywrightError,
                TimeoutError as PlaywrightTimeoutError,
                async_playwright,
            )
        except ImportError as exc:  # pragma: no cover - ortama bağlı
            raise ScrapeError(
                "Dinamik içerik okuyucusu kullanılamıyor (Playwright kurulu değil)."
            ) from exc

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                try:
                    context = await browser.new_context(
                        user_agent=self._user_agent,
                        extra_http_headers=_extra_headers(self._user_agent),
                    )
                    page = await context.new_page()
                    await page.goto(
                        url, timeout=self._timeout_ms, wait_until="domcontentloaded"
                    )
                    html = await page.content()
                finally:
                    await browser.close()
        except PlaywrightTimeoutError as exc:
            raise ScrapeTimeoutError() from exc
        except PlaywrightError as exc:
            raise ScrapeError(
                "Sayfa tarayıcıyla açılamadı. Lütfen daha sonra tekrar deneyin."
            ) from exc

        document = clean_html(html)
        content = build_scraped_content(url, document, renderer="dynamic")
        logger.info("Dinamik scrape tamam: %s (%d kelime)", url, content.word_count)
        return content


def _extra_headers(user_agent: str) -> dict[str, str]:
    # User-Agent context'te ayrıca verildiği için burada onu tekrar etmeyiz.
    headers = browser_headers(user_agent)
    headers.pop("User-Agent", None)
    return headers
