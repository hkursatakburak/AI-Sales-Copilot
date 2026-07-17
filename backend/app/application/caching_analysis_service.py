"""TTL önbellekli AnalysisService sarmalayıcısı (Decorator deseni).

Aynı URL için tekrarlanan /analyze isteklerini önbellekten karşılar;
LLM + scraping pipeline'ını tekrar çalıştırmaz. /email endpoint'i bu
sınıfı KULLANMAZ — her "Yeniden Üret" tıklaması taze bir LLM çıktısı üretmeli.

Thundering-herd koruması: aynı URL için eş zamanlı iki istek geldiğinde,
biri pipeline'ı çalıştırır; diğeri Lock üzerinde bekler ve sonucu önbellekten alır.
"""

from __future__ import annotations

import asyncio
import logging

from cachetools import TTLCache

from app.domain.interfaces import AnalysisService
from app.domain.models import CompanyAnalysis

logger = logging.getLogger(__name__)


class CachingAnalysisService(AnalysisService):
    def __init__(self, inner: AnalysisService, ttl: int, maxsize: int) -> None:
        self._inner = inner
        self._cache: TTLCache[str, CompanyAnalysis] = TTLCache(maxsize=maxsize, ttl=ttl)
        self._locks: dict[str, asyncio.Lock] = {}

    async def analyze(self, url: str) -> CompanyAnalysis:
        if url in self._cache:
            logger.debug("Önbellekten döndürülüyor: %s", url)
            return self._cache[url]

        lock = self._locks.setdefault(url, asyncio.Lock())
        async with lock:
            if url in self._cache:  # başka coroutine pipeline'ı bitirmiş olabilir
                return self._cache[url]
            result = await self._inner.analyze(url)
            self._cache[url] = result
            logger.debug("Önbelleğe alındı: %s", url)
            return result
