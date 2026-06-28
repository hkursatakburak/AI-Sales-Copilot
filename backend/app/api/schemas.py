"""API şemaları (DTO'lar) — dış dünyayla konuşulan veri biçimi.

Neden domain modellerinden AYRI?
Domain modelleri (dataclass) iş kurallarını temsil eder ve framework'ten
bağımsızdır. API şemaları (Pydantic) ise HTTP/JSON sınırındaki sözleşmedir:
gelen veriyi doğrular, giden veriyi serileştirir ve otomatik Swagger
dokümantasyonu üretir. Bu ayrım, API biçimini değiştirmeden iç modeli
değiştirebilmemizi (veya tersini) sağlar (Clean Architecture).

`from_domain` metotları domain -> DTO dönüşümünü tek bir yerde toplar.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from pydantic import BaseModel, Field, HttpUrl

from app.domain.models import (
    CompanyAnalysis,
    CompanySignals,
    LeadScore,
    ScrapedContent,
)


class AnalyzeRequest(BaseModel):
    """/analyze isteğinin gövdesi."""

    # HttpUrl, geçersiz URL'leri (örn. "abc", "ftp://...") otomatik reddeder
    # ve 422 döndürür. Girdi doğrulama bedavaya gelir.
    url: HttpUrl = Field(..., examples=["https://www.example.com"])


class ScoreReasonSchema(BaseModel):
    rule: str
    points: int
    explanation: str


class LeadScoreSchema(BaseModel):
    value: int = Field(..., ge=0, le=100)
    tier: str
    reasons: list[ScoreReasonSchema]

    @classmethod
    def from_domain(cls, score: LeadScore) -> "LeadScoreSchema":
        return cls(
            value=score.value,
            tier=score.tier.value,
            reasons=[
                ScoreReasonSchema(rule=r.rule, points=r.points, explanation=r.explanation)
                for r in score.reasons
            ],
        )


class AnalysisMetaSchema(BaseModel):
    generated_at: datetime
    pipeline_version: str
    is_stub: bool


class ScrapedContentSchema(BaseModel):
    """Çekilen ham içeriğin özeti (panelde 'gerçekten ne çekildi' göstergesi)."""

    title: str | None
    site_name: str | None
    meta_description: str | None
    word_count: int
    renderer: str
    content_preview: str  # tam metnin ilk kısmı (panelde önizleme)
    fetched_at: datetime

    # Önizlemeyi makul bir uzunlukta tutarız; tam metin yanıtı şişirmesin.
    # ClassVar: bu bir model alanı değil, sabittir.
    PREVIEW_CHARS: ClassVar[int] = 320

    @classmethod
    def from_domain(cls, content: ScrapedContent) -> "ScrapedContentSchema":
        preview = content.text[: cls.PREVIEW_CHARS]
        if len(content.text) > cls.PREVIEW_CHARS:
            preview += "…"
        return cls(
            title=content.title,
            site_name=content.site_name,
            meta_description=content.meta_description,
            word_count=content.word_count,
            renderer=content.renderer,
            content_preview=preview,
            fetched_at=content.fetched_at,
        )


class SignalsSchema(BaseModel):
    """LLM'in çıkardığı, skorlamayı besleyen sinyaller (şeffaflık için sunulur)."""

    sector: str | None
    employee_band: str | None
    is_hiring: bool
    hiring_roles: list[str]
    growth_signals: list[str]
    technologies: list[str]

    @classmethod
    def from_domain(cls, signals: CompanySignals) -> "SignalsSchema":
        return cls(
            sector=signals.sector,
            employee_band=signals.employee_band,
            is_hiring=signals.is_hiring,
            hiring_roles=list(signals.hiring_roles),
            growth_signals=list(signals.growth_signals),
            technologies=list(signals.technologies),
        )


class AnalyzeResponse(BaseModel):
    """/analyze yanıtının gövdesi — eklentinin gösterdiği tüm alanlar."""

    url: str
    company_name: str | None
    summary: str
    pain_points: list[str]
    lead_score: LeadScoreSchema
    cold_email: str
    pitch: str
    meta: AnalysisMetaSchema
    scraped: ScrapedContentSchema | None = None
    signals: SignalsSchema | None = None

    @classmethod
    def from_domain(cls, analysis: CompanyAnalysis) -> "AnalyzeResponse":
        return cls(
            url=analysis.url,
            company_name=analysis.company_name,
            summary=analysis.summary,
            pain_points=list(analysis.pain_points),
            lead_score=LeadScoreSchema.from_domain(analysis.lead_score),
            cold_email=analysis.cold_email,
            pitch=analysis.pitch,
            meta=AnalysisMetaSchema(
                generated_at=analysis.meta.generated_at,
                pipeline_version=analysis.meta.pipeline_version,
                is_stub=analysis.meta.is_stub,
            ),
            scraped=(
                ScrapedContentSchema.from_domain(analysis.scraped)
                if analysis.scraped is not None
                else None
            ),
            signals=(
                SignalsSchema.from_domain(analysis.signals)
                if analysis.signals is not None
                else None
            ),
        )


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
