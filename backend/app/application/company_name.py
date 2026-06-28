"""Çekilen içerikten şirket adı türetme (paylaşılan yardımcı).

Hem Sprint 2 (scraping-only) hem Sprint 3 (LLM) servisleri aynı kuralı kullanır.
"""

from __future__ import annotations

from urllib.parse import urlparse

from app.domain.models import ScrapedContent

_TITLE_SEPARATORS = ("|", "—", "–", "-", "·", ":", "•")


def derive_company_name(content: ScrapedContent, url: str) -> str:
    if content.site_name:
        return content.site_name.strip()

    if content.title:
        for sep in _TITLE_SEPARATORS:
            if sep in content.title:
                candidate = content.title.split(sep)[0].strip()
                if candidate:
                    return candidate
        return content.title.strip()

    return _derive_from_url(url)


def _derive_from_url(url: str) -> str:
    host = (urlparse(url).hostname or url).removeprefix("www.")
    base = host.split(".")[0] if "." in host else host
    return base.replace("-", " ").replace("_", " ").title() or "Bilinmeyen Şirket"
