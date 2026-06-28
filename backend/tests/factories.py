"""Testlerde paylaşılan yardımcılar: sahte scraper ve içerik fabrikası."""

from __future__ import annotations

from datetime import datetime, timezone

from app.domain.interfaces import WebScraper
from app.domain.models import ScrapedContent


def make_scraped_content(
    *,
    url: str = "https://example.com",
    title: str | None = "Örnek Başlık",
    site_name: str | None = None,
    meta_description: str | None = "açıklama",
    text: str = "örnek metin içeriği",
    word_count: int | None = None,
    renderer: str = "static",
) -> ScrapedContent:
    return ScrapedContent(
        url=url,
        title=title,
        site_name=site_name,
        meta_description=meta_description,
        text=text,
        headings=(),
        word_count=word_count if word_count is not None else len(text.split()),
        renderer=renderer,
        fetched_at=datetime.now(timezone.utc),
    )


class FakeScraper(WebScraper):
    """Ağ kullanmadan önceden belirlenmiş içerik (veya hata) döndüren scraper."""

    def __init__(self, content: ScrapedContent | None = None, error: Exception | None = None):
        self._content = content if content is not None else make_scraped_content()
        self._error = error
        self.called = False
        self.last_url: str | None = None

    async def scrape(self, url: str) -> ScrapedContent:
        self.called = True
        self.last_url = url
        if self._error:
            raise self._error
        return self._content
