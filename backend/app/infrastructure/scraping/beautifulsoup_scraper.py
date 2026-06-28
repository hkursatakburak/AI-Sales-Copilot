"""Statik scraper: httpx ile HTML indir, BeautifulSoup ile temizle.

JavaScript ÇALIŞTIRMAZ. İçeriği doğrudan HTML'de olan (sunucu tarafında
render edilen) sayfalar için idealdir — çok hızlı ve hafiftir. İçerik JS ile
yükleniyorsa metin boş/az gelir; bu durumu `HybridScraper` yakalayıp dinamik
yedeğe geçer.

Üretim sağlamlığı (Sprint 2 hardening):
- Gerçekçi tarayıcı başlıkları (basit bot filtrelerini geçer).
- Ayrı connect/read zaman aşımları.
- Geçici hatalarda (timeout/bağlantı) üssel backoff'lu yeniden deneme.
- Host bazlı rate limiting (nezaket).
- Tüm hatalar kullanıcı dostu, sınıflandırılmış `ScrapeError` türlerine çevrilir.

Bu sınıf KASITLI olarak bot korumalarını aşmaya çalışmaz (CAPTCHA, gelişmiş
parmak izi vb.). Engellenen siteler için anlaşılır bir mesaj döner.

Test edilebilirlik: `transport` ile httpx'e sahte taşıyıcı (MockTransport)
enjekte edilebilir; `rate_limiter=None` ve `max_retries=0` ile testler hızlı
ve ağsız kalır.
"""

from __future__ import annotations

import asyncio
import logging
import ssl

import httpx

from app.core.exceptions import (
    ConnectionFailedError,
    DnsError,
    ScrapeError,
    ScrapeTimeoutError,
    SiteBlockedError,
    SslError,
)
from app.domain.interfaces import WebScraper
from app.domain.models import ScrapedContent
from app.infrastructure.scraping.content_builder import build_scraped_content
from app.infrastructure.scraping.html_cleaner import clean_html
from app.infrastructure.scraping.http_headers import browser_headers
from app.infrastructure.scraping.rate_limiter import HostRateLimiter
from app.infrastructure.scraping.url_guard import UrlGuard

logger = logging.getLogger(__name__)

# Engelleme sayılan HTTP durum kodları (yeniden denemenin anlamı yok).
_BLOCKING_STATUSES = {401, 403, 429}


class BeautifulSoupScraper(WebScraper):
    def __init__(
        self,
        guard: UrlGuard,
        *,
        timeout: float = 15.0,
        connect_timeout: float = 5.0,
        user_agent: str = "AISalesCopilotBot/0.1",
        max_retries: int = 2,
        retry_backoff: float = 0.5,
        rate_limiter: HostRateLimiter | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        self._guard = guard
        self._timeout = httpx.Timeout(timeout, connect=connect_timeout)
        self._user_agent = user_agent
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff
        self._rate_limiter = rate_limiter
        self._transport = transport  # yalnızca testlerde doldurulur

    async def scrape(self, url: str) -> ScrapedContent:
        self._guard.validate(url)

        if self._rate_limiter is not None:
            await self._rate_limiter.acquire(url)

        response = await self._fetch_with_retries(url)
        document = clean_html(response.text)
        content = build_scraped_content(url, document, renderer="static")
        logger.info("Statik scrape tamam: %s (%d kelime)", url, content.word_count)
        return content

    async def _fetch_with_retries(self, url: str) -> httpx.Response:
        """Geçici hatalarda (timeout/bağlantı) üssel backoff ile yeniden dener.

        Kalıcı hatalar (engelleme/DNS/SSL) HEMEN fırlatılır — tekrar denemenin
        faydası yok ve gereksiz yük bindirir.
        """
        attempt = 0
        while True:
            try:
                return await self._fetch_once(url)
            except (ScrapeTimeoutError, ConnectionFailedError) as exc:
                if attempt >= self._max_retries:
                    raise
                backoff = self._retry_backoff * (2**attempt)
                attempt += 1
                logger.warning(
                    "Geçici scrape hatası (%s), %d. yeniden deneme %.1fs sonra: %s",
                    exc.code,
                    attempt,
                    backoff,
                    url,
                )
                if backoff > 0:
                    await asyncio.sleep(backoff)

    async def _fetch_once(self, url: str) -> httpx.Response:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers=browser_headers(self._user_agent),
                transport=self._transport,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response
        except httpx.HTTPStatusError as exc:
            raise self._classify_status_error(exc) from exc
        except httpx.TimeoutException as exc:
            raise ScrapeTimeoutError() from exc
        except httpx.HTTPError as exc:
            raise self._classify_transport_error(exc) from exc

    @staticmethod
    def _classify_status_error(exc: httpx.HTTPStatusError) -> ScrapeError:
        status = exc.response.status_code
        if status in _BLOCKING_STATUSES:
            return SiteBlockedError()
        if status == 404:
            return ScrapeError("Sayfa bulunamadı. Adres doğru mu?")
        if status >= 500:
            return ScrapeError(
                "Web sitesinde geçici bir sorun var. Lütfen daha sonra tekrar deneyin."
            )
        return ScrapeError("Sayfa alınamadı. Lütfen daha sonra tekrar deneyin.")

    @staticmethod
    def _classify_transport_error(exc: httpx.HTTPError) -> ScrapeError:
        """Bağlantı hatasını SSL / DNS / genel ağ olarak sınıflandırır."""
        cause = exc.__cause__ or exc.__context__
        text = f"{exc} {cause}".lower()

        if isinstance(cause, ssl.SSLError) or "ssl" in text or "certificate" in text:
            return SslError()

        import socket

        if isinstance(cause, socket.gaierror) or "name or service not known" in text or (
            "getaddrinfo" in text
        ):
            return DnsError()

        return ConnectionFailedError()
