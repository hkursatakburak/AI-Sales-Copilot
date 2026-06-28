"""Statik scraper testleri.

httpx'in `MockTransport`'u ile gerçek ağ kullanılmadan test edilir. `UrlGuard`
`allow_private=True` ile DNS çözümü atlanır (testler offline çalışsın diye).
"""

from __future__ import annotations

import httpx
import pytest

from app.core.exceptions import ScrapeError
from app.infrastructure.scraping.beautifulsoup_scraper import BeautifulSoupScraper
from app.infrastructure.scraping.url_guard import UrlGuard

PAGE_HTML = """
<html><head><title>Test A.Ş.</title>
<meta property="og:site_name" content="Test A.Ş." /></head>
<body><h1>Başlık</h1><p>Bu bir test sayfasıdır ve birkaç kelime içerir.</p></body></html>
"""


def _scraper(handler) -> BeautifulSoupScraper:
    transport = httpx.MockTransport(handler)
    return BeautifulSoupScraper(UrlGuard(allow_private=True), transport=transport)


@pytest.mark.asyncio
async def test_scrape_returns_clean_content() -> None:
    scraper = _scraper(lambda req: httpx.Response(200, text=PAGE_HTML))

    content = await scraper.scrape("https://example.com")

    assert content.renderer == "static"
    assert content.site_name == "Test A.Ş."
    assert content.word_count > 0
    assert "test sayfasıdır" in content.text
    assert "Başlık" in content.headings


@pytest.mark.asyncio
async def test_scrape_raises_on_http_error() -> None:
    scraper = _scraper(lambda req: httpx.Response(404, text="yok"))

    with pytest.raises(ScrapeError):
        await scraper.scrape("https://example.com/missing")


@pytest.mark.asyncio
async def test_scrape_raises_on_connection_error() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("bağlanılamadı")

    scraper = _scraper(boom)
    with pytest.raises(ScrapeError):
        await scraper.scrape("https://example.com")


@pytest.mark.asyncio
async def test_scrape_validates_url_first() -> None:
    # Özel adres engellenmeli; transport'a hiç ulaşılmamalı.
    scraper = BeautifulSoupScraper(UrlGuard(allow_private=False))
    with pytest.raises(ScrapeError):
        await scraper.scrape("http://127.0.0.1/internal")
