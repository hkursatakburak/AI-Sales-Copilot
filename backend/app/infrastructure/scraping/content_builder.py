"""`CleanedDocument` -> `ScrapedContent` dönüşümü (tek yerde, DRY).

Hem statik hem dinamik scraper aynı kurala göre `ScrapedContent` üretir.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.domain.models import ScrapedContent
from app.infrastructure.scraping.html_cleaner import CleanedDocument


def build_scraped_content(url: str, doc: CleanedDocument, renderer: str) -> ScrapedContent:
    return ScrapedContent(
        url=url,
        title=doc.title,
        site_name=doc.site_name,
        meta_description=doc.meta_description,
        text=doc.text,
        headings=doc.headings,
        word_count=len(doc.text.split()),
        renderer=renderer,
        fetched_at=datetime.now(timezone.utc),
        detected_name=doc.company_name,
    )
