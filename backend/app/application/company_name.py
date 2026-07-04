"""Çekilen içerikten şirket adı türetme (paylaşılan yardımcı).

Akıllı çıkarımın (JSON-LD > og:site_name > og:title > title > h1) çoğu
`html_cleaner` içinde yapılır ve `ScrapedContent.detected_name` olarak taşınır.
Burada yalnızca son adım kalır: tespit edilen ad yoksa alan adına (domain) düş.
"""

from __future__ import annotations

from urllib.parse import urlparse

from app.domain.models import ScrapedContent


def derive_company_name(content: ScrapedContent, url: str) -> str:
    if content.detected_name:
        return content.detected_name.strip()
    return _derive_from_url(url)


def _derive_from_url(url: str) -> str:
    host = (urlparse(url).hostname or url).removeprefix("www.")
    base = host.split(".")[0] if "." in host else host
    return base.replace("-", " ").replace("_", " ").title() or "Bilinmeyen Şirket"
