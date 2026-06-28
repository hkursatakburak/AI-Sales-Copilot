"""Testlerde paylaşılan yardımcılar: sahte scraper ve içerik fabrikası."""

from __future__ import annotations

from datetime import datetime, timezone

from app.domain.interfaces import CompanyInsightAnalyzer, LLMProvider, WebScraper
from app.domain.models import (
    CompanyInsights,
    CompanySignals,
    ScrapedContent,
)


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


def make_signals(
    *,
    sector: str | None = "SaaS",
    employee_band: str | None = "51-200",
    is_hiring: bool = True,
    hiring_roles: tuple[str, ...] = ("DevOps",),
    growth_signals: tuple[str, ...] = ("yeni yatırım",),
    technologies: tuple[str, ...] = ("AWS",),
) -> CompanySignals:
    return CompanySignals(
        sector=sector,
        employee_band=employee_band,
        is_hiring=is_hiring,
        hiring_roles=hiring_roles,
        growth_signals=growth_signals,
        technologies=technologies,
    )


class FakeAnalyzer(CompanyInsightAnalyzer):
    """Sabit `CompanyInsights` döndüren analizci (LLM'siz test)."""

    def __init__(self, insights: CompanyInsights | None = None):
        self._insights = insights or CompanyInsights(
            summary="Örnek şirket özeti.",
            pain_points=("Acı noktası 1", "Acı noktası 2"),
            signals=make_signals(),
        )
        self.called = False

    async def analyze(self, content: ScrapedContent) -> CompanyInsights:
        self.called = True
        return self._insights


class FakeLLMProvider(LLMProvider):
    """Önceden belirlenmiş bir sözlük döndüren LLM sağlayıcı (ağsız test)."""

    def __init__(self, payload: dict | None = None):
        self._payload = payload if payload is not None else {
            "summary": "Test özeti",
            "pain_points": ["nokta 1"],
            "signals": {
                "sector": "SaaS",
                "employee_band": "51-200",
                "is_hiring": True,
                "hiring_roles": ["DevOps"],
                "growth_signals": ["yeni yatırım"],
                "technologies": ["AWS"],
            },
        }
        self.last_kwargs: dict | None = None

    async def extract_structured(self, **kwargs) -> dict:
        self.last_kwargs = kwargs
        return self._payload
