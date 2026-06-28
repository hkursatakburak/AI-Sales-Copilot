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

from pydantic import BaseModel, Field, HttpUrl

from app.domain.models import CompanyAnalysis, LeadScore


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
        )


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
