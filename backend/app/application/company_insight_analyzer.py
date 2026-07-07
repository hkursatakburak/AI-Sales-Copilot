"""Çekilen içerikten şirket içgörüsü (özet + acı noktaları + sinyaller) üretir.

Tek bir yapılandırılmış LLM çağrısıyla üç çıktıyı birlikte alır — ayrı ayrı üç
çağrı yapmaya göre daha ucuz ve tutarlı. LLM yalnızca dil anlama/çıkarım yapar;
puanlama bu sınıfın işi DEĞİLDİR (o, kural motorunun işi).

Prompt mühendisliği ilkeleri:
- Türkçe, doğal ve spesifik çıktı iste.
- "Yalnızca verilen içeriğe dayan, uydurma" (halüsinasyonu azalt).
- Bilinmeyen alanlar için null/boş bırak.
"""

from __future__ import annotations

import logging

from app.domain.interfaces import CompanyInsightAnalyzer, LLMProvider
from app.domain.models import CompanyInsights, CompanySignals, ScrapedContent

logger = logging.getLogger(__name__)

_TOOL_NAME = "save_company_insights"
_TOOL_DESCRIPTION = (
    "Bir şirketin web sitesi içeriğinden çıkarılan satış içgörülerini kaydeder."
)

# Geçerli çalışan sayısı bantları (kural motoru bunlara göre puanlar).
_EMPLOYEE_BANDS = ["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]

_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": "Şirketin ne yaptığına dair 3-4 cümlelik, Türkçe, akıcı özet.",
        },
        "pain_points": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Şirketin muhtemel 2-4 acı noktası (Türkçe, spesifik). "
                "Örn: 'Hızlı büyüyorlar ama destek ekibi küçük görünüyor.'"
            ),
        },
        "signals": {
            "type": "object",
            "properties": {
                "sector": {
                    "type": ["string", "null"],
                    "description": "Sektör, örn. 'SaaS', 'e-ticaret', 'fintech'. Bilinmiyorsa null.",
                },
                "employee_band": {
                    "type": ["string", "null"],
                    "enum": [*_EMPLOYEE_BANDS, None],
                    "description": "Tahmini çalışan sayısı bandı. Net değilse null.",
                },
                "is_hiring": {
                    "type": "boolean",
                    "description": "Sitede açık iş ilanı / kariyer sinyali var mı.",
                },
                "hiring_roles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Açık pozisyon türleri, örn. ['DevOps', 'Satış'].",
                },
                "growth_signals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Büyüme işaretleri: yeni yatırım, yeni pazar, yeni ürün vb.",
                },
                "technologies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tespit edilen teknolojiler/araçlar.",
                },
            },
            "required": ["sector", "employee_band", "is_hiring", "hiring_roles",
                         "growth_signals", "technologies"],
        },
    },
    "required": ["summary", "pain_points", "signals"],
}

_SYSTEM_PROMPT = (
    "Sen deneyimli bir B2B satış araştırma asistanısın. Sana bir şirketin web "
    "sitesinden çekilmiş metin verilir. Görevin: satış temsilcisinin bu şirketi "
    "hızlıca anlamasını sağlayacak özet, olası acı noktaları ve yapılandırılmış "
    "sinyaller çıkarmak. KURALLAR: Yalnızca verilen içeriğe dayan, bilgi "
    "uydurma. Emin olmadığın alanları boş/null bırak. Tüm metinsel çıktılar "
    "Türkçe ve doğal olsun."
)


class LLMCompanyInsightAnalyzer(CompanyInsightAnalyzer):
    def __init__(self, provider: LLMProvider, *, max_input_chars: int = 6000):
        self._provider = provider
        self._max_input_chars = max_input_chars

    async def analyze(self, content: ScrapedContent) -> CompanyInsights:
        prompt = self._build_prompt(content)
        data = await self._provider.extract_structured(
            system=_SYSTEM_PROMPT,
            prompt=prompt,
            schema=_SCHEMA,
            tool_name=_TOOL_NAME,
            tool_description=_TOOL_DESCRIPTION,
        )
        return self._to_insights(data)

    def _build_prompt(self, content: ScrapedContent) -> str:
        text = content.text[: self._max_input_chars]
        headings = " | ".join(content.headings[:15])
        return (
            f"ŞİRKET URL: {content.url}\n"
            f"BAŞLIK: {content.title or '-'}\n"
            f"META AÇIKLAMA: {content.meta_description or '-'}\n"
            f"BÖLÜM BAŞLIKLARI: {headings or '-'}\n\n"
            f"SAYFA METNİ:\n{text}"
        )

    @staticmethod
    def _to_insights(data: dict) -> CompanyInsights:
        """LLM sözlüğünü güvenli biçimde domain modeline çevirir (eksik alanlara dayanıklı)."""
        raw_signals = data.get("signals") or {}
        signals = CompanySignals(
            sector=_clean_str(raw_signals.get("sector")),
            employee_band=_clean_str(raw_signals.get("employee_band")),
            is_hiring=bool(raw_signals.get("is_hiring", False)),
            hiring_roles=_clean_list(raw_signals.get("hiring_roles")),
            growth_signals=_clean_list(raw_signals.get("growth_signals")),
            technologies=_clean_list(raw_signals.get("technologies")),
        )
        return CompanyInsights(
            summary=(data.get("summary") or "").strip(),
            pain_points=_clean_list(data.get("pain_points")),
            signals=signals,
        )


def _clean_str(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _clean_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
