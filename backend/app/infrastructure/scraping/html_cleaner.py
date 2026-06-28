"""Ham HTML'i temizleyip yapılandırılmış metne dönüştürür.

Tek sorumluluk: HTML string -> `CleanedDocument`. Ağ veya tarayıcı bilgisi yok;
bu yüzden saf, hızlı ve kolay test edilebilir. Hem statik hem dinamik scraper
aynı temizleyiciyi kullanır (kod tekrarı yok / DRY).

Strateji:
- Gürültü etiketlerini (script, style, nav, footer, header, aside, form...) at.
- Başlık (title / og:title) ve şirket adı (og:site_name) ipuçlarını topla.
- Meta açıklamasını (description / og:description) al.
- h1-h3 başlıklarını topla (sayfa yapısının iskeleti).
- Görünür metni boşlukları sadeleştirerek çıkar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

# Anlamsız/gürültü kabul edilen ve atılan etiketler.
_NOISE_TAGS = [
    "script",
    "style",
    "noscript",
    "template",
    "svg",
    "nav",
    "footer",
    "header",
    "aside",
    "form",
    "iframe",
]

_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class CleanedDocument:
    title: str | None
    site_name: str | None
    meta_description: str | None
    text: str
    headings: tuple[str, ...]


def _meta_content(soup: BeautifulSoup, *, name: str | None = None, prop: str | None = None) -> str | None:
    attrs = {"name": name} if name else {"property": prop}
    tag = soup.find("meta", attrs=attrs)
    if tag and tag.get("content"):
        return tag["content"].strip() or None
    return None


def clean_html(html: str) -> CleanedDocument:
    soup = BeautifulSoup(html, "html.parser")

    # Meta bilgileri DOM temizlenmeden önce topla (head içindeler).
    site_name = _meta_content(soup, prop="og:site_name")
    og_title = _meta_content(soup, prop="og:title")
    meta_description = _meta_content(soup, name="description") or _meta_content(
        soup, prop="og:description"
    )

    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    title = title or og_title

    # Başlıkları (h1-h3) gürültü temizliğinden önce yakala.
    headings = tuple(
        h.get_text(strip=True)
        for h in soup.find_all(["h1", "h2", "h3"])
        if h.get_text(strip=True)
    )

    # Gürültü etiketlerini DOM'dan sök.
    for tag in soup(_NOISE_TAGS):
        tag.decompose()

    raw_text = soup.get_text(separator=" ")
    text = _WHITESPACE_RE.sub(" ", raw_text).strip()

    return CleanedDocument(
        title=title,
        site_name=site_name,
        meta_description=meta_description,
        text=text,
        headings=headings,
    )
