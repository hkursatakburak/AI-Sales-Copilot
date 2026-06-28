"""robots.txt denetimi — etik/sorumlu scraping.

Bir siteyi çekmeden önce, o sitenin robots.txt kurallarının bizim
User-Agent'ımıza ilgili yolu yasaklayıp yasaklamadığını kontrol eder.
"Best-effort" çalışır: robots.txt alınamazsa (örn. yoksa veya ağ hatası)
erişime izin verilir — bu, standart davranıştır.
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)


class RobotsChecker:
    def __init__(self, *, user_agent: str, timeout: float = 5.0):
        self._user_agent = user_agent
        self._timeout = timeout

    async def is_allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(robots_url, headers={"User-Agent": self._user_agent})
        except httpx.HTTPError:
            logger.info("robots.txt alınamadı (%s), erişime izin veriliyor.", robots_url)
            return True

        if response.status_code >= 400:
            # robots.txt yok veya erişilemez -> kısıtlama yok kabul edilir.
            return True

        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        allowed = parser.can_fetch(self._user_agent, url)
        if not allowed:
            logger.warning("robots.txt erişimi reddetti: %s", url)
        return allowed
