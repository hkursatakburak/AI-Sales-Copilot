"""Ham HTML'i temizleyip yapılandırılmış metne dönüştürür.

Tek sorumluluk: HTML string -> `CleanedDocument`. Ağ veya tarayıcı bilgisi yok;
bu yüzden saf, hızlı ve kolay test edilebilir. Hem statik hem dinamik scraper
aynı temizleyiciyi kullanır (kod tekrarı yok / DRY).

Sağlamlık (Final Polish):
- Şirket adı akıllı öncelik sırasıyla bulunur: JSON-LD Organization ->
  og:site_name -> og:title -> meta[application-name] -> <title> -> <h1>.
- Gürültü etiketleri (script/style/json-ld/css...) tamamen atılır.
- Bozuk/kontrol karakterleri (encoding artıkları, U+FFFD) metinden temizlenir.
"""

from __future__ import annotations

import json
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
# Yazdırılamayan kontrol karakterleri (satır sonu/tab hariç) + U+FFFD (bozuk kodlama işareti).
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f�]")
# Şirket adı adaylarını ayraçlardan temizlemek için ("Acme | Anasayfa" -> "Acme").
_TITLE_SEPARATORS = ("|", "—", "–", "-", "·", ":", "•", "·")
_ORG_TYPES = {"organization", "corporation", "localbusiness", "onlinestore", "website"}


@dataclass(frozen=True)
class CleanedDocument:
    title: str | None
    site_name: str | None
    meta_description: str | None
    text: str
    headings: tuple[str, ...]
    company_name: str | None  # akıllı öncelikle bulunan şirket adı adayı


def _meta_content(soup: BeautifulSoup, *, name: str | None = None, prop: str | None = None) -> str | None:
    attrs = {"name": name} if name else {"property": prop}
    tag = soup.find("meta", attrs=attrs)
    if tag and tag.get("content"):
        return tag["content"].strip() or None
    return None


def _clean_control_chars(text: str) -> str:
    return _CONTROL_CHARS_RE.sub("", text)


def _split_on_separator(value: str) -> str:
    for sep in _TITLE_SEPARATORS:
        if sep in value:
            head = value.split(sep)[0].strip()
            if head:
                return head
    return value.strip()


def _extract_json_ld_org_name(soup: BeautifulSoup) -> str | None:
    """JSON-LD bloklarından Organization/WebSite adını (varsa) çıkarır."""
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = tag.string or tag.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        name = _find_org_name(data)
        if name:
            return name
    return None


def _find_org_name(node: object) -> str | None:
    """JSON-LD ağacında (dict/list/@graph) Organization 'name' değerini arar."""
    if isinstance(node, list):
        for item in node:
            if name := _find_org_name(item):
                return name
        return None
    if isinstance(node, dict):
        if "@graph" in node:
            if name := _find_org_name(node["@graph"]):
                return name
        node_type = node.get("@type", "")
        types = node_type if isinstance(node_type, list) else [node_type]
        if any(isinstance(t, str) and t.lower() in _ORG_TYPES for t in types):
            name = node.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    return None


def clean_html(html: str) -> CleanedDocument:
    soup = BeautifulSoup(html, "html.parser")

    # Meta bilgileri ve şirket adı adaylarını gürültü temizliğinden ÖNCE topla.
    json_ld_name = _extract_json_ld_org_name(soup)
    site_name = _meta_content(soup, prop="og:site_name") or _meta_content(
        soup, name="application-name"
    )
    og_title = _meta_content(soup, prop="og:title")
    meta_description = _meta_content(soup, name="description") or _meta_content(
        soup, prop="og:description"
    )

    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    headings = tuple(
        _clean_control_chars(h.get_text(strip=True))
        for h in soup.find_all(["h1", "h2", "h3"])
        if h.get_text(strip=True)
    )
    first_h1 = next(
        (h.get_text(strip=True) for h in soup.find_all("h1") if h.get_text(strip=True)),
        None,
    )

    company_name = _pick_company_name(
        json_ld_name=json_ld_name,
        site_name=site_name,
        og_title=og_title,
        title=title,
        h1=first_h1,
    )

    # Gürültü etiketlerini (script/style/json-ld dahil) DOM'dan sök.
    for tag in soup(_NOISE_TAGS):
        tag.decompose()

    raw_text = soup.get_text(separator=" ")
    text = _WHITESPACE_RE.sub(" ", _clean_control_chars(raw_text)).strip()

    return CleanedDocument(
        title=title,
        site_name=site_name,
        meta_description=meta_description,
        text=text,
        headings=headings,
        company_name=company_name,
    )


def _pick_company_name(
    *,
    json_ld_name: str | None,
    site_name: str | None,
    og_title: str | None,
    title: str | None,
    h1: str | None,
) -> str | None:
    """Öncelik sırası: JSON-LD > og:site_name/meta > og:title > title > h1."""
    if json_ld_name:
        return json_ld_name.strip()
    if site_name:
        return site_name.strip()
    if og_title:
        return _split_on_separator(og_title)
    if title:
        return _split_on_separator(title)
    if h1:
        return h1.strip()
    return None
