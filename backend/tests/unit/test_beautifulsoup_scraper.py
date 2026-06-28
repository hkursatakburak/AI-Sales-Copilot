"""Statik scraper testleri.

httpx'in `MockTransport`'u ile gerçek ağ kullanılmadan test edilir. `UrlGuard`
`allow_private=True` ile DNS çözümü atlanır (testler offline çalışsın diye).
"""

from __future__ import annotations

import httpx
import pytest

from app.core.exceptions import (
    ConnectionFailedError,
    DnsError,
    ScrapeError,
    ScrapeTimeoutError,
    SiteBlockedError,
    SslError,
)
from app.infrastructure.scraping.beautifulsoup_scraper import BeautifulSoupScraper
from app.infrastructure.scraping.url_guard import UrlGuard

PAGE_HTML = """
<html><head><title>Test A.Ş.</title>
<meta property="og:site_name" content="Test A.Ş." /></head>
<body><h1>Başlık</h1><p>Bu bir test sayfasıdır ve birkaç kelime içerir.</p></body></html>
"""


def _scraper(handler, *, max_retries: int = 0) -> BeautifulSoupScraper:
    transport = httpx.MockTransport(handler)
    return BeautifulSoupScraper(
        UrlGuard(allow_private=True),
        max_retries=max_retries,
        retry_backoff=0.0,  # testlerde uyuma
        rate_limiter=None,
        transport=transport,
    )


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
async def test_scrape_validates_url_first() -> None:
    # Özel adres engellenmeli; transport'a hiç ulaşılmamalı.
    scraper = BeautifulSoupScraper(UrlGuard(allow_private=False))
    with pytest.raises(ScrapeError):
        await scraper.scrape("http://127.0.0.1/internal")


# --- Hata sınıflandırması (kullanıcı dostu mesajlar) ---


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403, 429])
async def test_blocking_status_maps_to_site_blocked(status: int) -> None:
    scraper = _scraper(lambda req: httpx.Response(status, text="blocked"))
    with pytest.raises(SiteBlockedError) as exc:
        await scraper.scrape("https://example.com")
    assert "güvenlik" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_404_is_not_treated_as_block() -> None:
    scraper = _scraper(lambda req: httpx.Response(404, text="yok"))
    with pytest.raises(ScrapeError) as exc:
        await scraper.scrape("https://example.com/missing")
    assert not isinstance(exc.value, SiteBlockedError)


@pytest.mark.asyncio
async def test_timeout_maps_to_scrape_timeout() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("çok yavaş", request=request)

    scraper = _scraper(boom)
    with pytest.raises(ScrapeTimeoutError):
        await scraper.scrape("https://example.com")


@pytest.mark.asyncio
async def test_ssl_error_maps_to_ssl_error() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("certificate verify failed", request=request)

    scraper = _scraper(boom)
    with pytest.raises(SslError):
        await scraper.scrape("https://example.com")


@pytest.mark.asyncio
async def test_dns_error_maps_to_dns_error() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("getaddrinfo failed", request=request)

    scraper = _scraper(boom)
    with pytest.raises(DnsError):
        await scraper.scrape("https://example.com")


@pytest.mark.asyncio
async def test_generic_connection_error_maps_to_connection_failed() -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    scraper = _scraper(boom)
    with pytest.raises(ConnectionFailedError):
        await scraper.scrape("https://example.com")


# --- Retry mekanizması ---


@pytest.mark.asyncio
async def test_retries_transient_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            raise httpx.ReadTimeout("yavaş", request=request)
        return httpx.Response(200, text=PAGE_HTML)

    scraper = _scraper(handler, max_retries=2)
    content = await scraper.scrape("https://example.com")

    assert content.word_count > 0
    assert calls["n"] == 3  # 1 ilk + 2 yeniden deneme


@pytest.mark.asyncio
async def test_does_not_retry_blocking_status() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(403, text="blocked")

    scraper = _scraper(handler, max_retries=3)
    with pytest.raises(SiteBlockedError):
        await scraper.scrape("https://example.com")
    assert calls["n"] == 1  # engelleme yeniden denenmez
