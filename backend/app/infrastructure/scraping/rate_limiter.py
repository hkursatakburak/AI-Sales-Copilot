"""Host bazlı basit rate limiter (nezaket kuralı).

Aynı siteye art arda çok hızlı istek atmak hem kabadır hem de engellenmeye
(IP ban) yol açar. Bu sınıf, aynı host'a yapılan ardışık isteklerin arasında
en az `min_interval` saniye olmasını sağlar. Farklı host'lar birbirini
beklemez (her host kendi zaman damgasını tutar).
"""

from __future__ import annotations

import asyncio
import time
from urllib.parse import urlparse


class HostRateLimiter:
    def __init__(self, min_interval: float):
        self._min_interval = min_interval
        self._last_request: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_for(self, host: str) -> asyncio.Lock:
        # Her host için ayrı kilit: A sitesini beklerken B sitesi bloke olmasın.
        if host not in self._locks:
            self._locks[host] = asyncio.Lock()
        return self._locks[host]

    async def acquire(self, url: str) -> None:
        if self._min_interval <= 0:
            return

        host = urlparse(url).netloc or url
        async with self._lock_for(host):
            last = self._last_request.get(host)
            now = time.monotonic()
            if last is not None:
                wait = self._min_interval - (now - last)
                if wait > 0:
                    await asyncio.sleep(wait)
                    now = time.monotonic()
            self._last_request[host] = now
