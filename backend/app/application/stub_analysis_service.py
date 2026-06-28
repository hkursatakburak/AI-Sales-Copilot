"""Sprint 1 için `AnalysisService` iskelet (stub) uygulaması.

Amaç: uçtan uca akışı (eklenti -> backend -> cevap) gerçek scraping/LLM
olmadan çalıştırmak. "Önce yürüyen iskelet (walking skeleton), sonra zekâ"
felsefesi. Bu servis deterministiktir: aynı URL her zaman aynı sonucu üretir,
böylece testler stabildir ve eklenti gerçek bir cevap şekliyle çalışır.

`meta.is_stub = True` ile bu verinin placeholder olduğu açıkça işaretlenir;
böylece kimse demo'da bunu gerçek analiz sanmaz.
"""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from app import PIPELINE_VERSION
from app.domain.interfaces import AnalysisService
from app.domain.models import (
    AnalysisMeta,
    CompanyAnalysis,
    LeadScore,
    LeadTier,
    ScoreReason,
)


class StubAnalysisService(AnalysisService):
    """Gerçek bir analiz yapmadan, geçerli biçimde bir sonuç döndürür."""

    async def analyze(self, url: str) -> CompanyAnalysis:
        company_name = self._derive_company_name(url)

        lead_score = LeadScore(
            value=50,
            tier=LeadTier.WARM,
            reasons=(
                ScoreReason(
                    rule="skeleton_placeholder",
                    points=50,
                    explanation=(
                        "Bu bir iskelet (Sprint 1) puanıdır. Gerçek kural tabanlı "
                        "skorlama Sprint 3'te eklenecek."
                    ),
                ),
            ),
        )

        return CompanyAnalysis(
            url=url,
            company_name=company_name,
            summary=(
                f"[İSKELET] '{company_name}' için şirket özeti burada görünecek. "
                "Gerçek özet, scraping (Sprint 2) ve LLM (Sprint 3) eklendikten "
                "sonra üretilecek."
            ),
            pain_points=(
                "[İskelet] Acı noktası 1 — Sprint 3'te gerçek veriyle dolacak.",
                "[İskelet] Acı noktası 2 — Sprint 3'te gerçek veriyle dolacak.",
            ),
            lead_score=lead_score,
            cold_email=(
                "[İSKELET] Kişiselleştirilmiş soğuk e-posta Sprint 4'te "
                "üretilecek."
            ),
            pitch="[İSKELET] Toplantı sunum metni Sprint 4'te üretilecek.",
            meta=AnalysisMeta(
                generated_at=datetime.now(timezone.utc),
                pipeline_version=PIPELINE_VERSION,
                is_stub=True,
            ),
        )

    @staticmethod
    def _derive_company_name(url: str) -> str:
        """URL'nin alan adından kaba bir şirket adı türetir.

        Örn: 'https://www.acme-corp.com/about' -> 'Acme Corp'.
        Bu yalnızca iskelet için; gerçek isim Sprint 2'de sayfadan çekilecek.
        """
        netloc = urlparse(url).netloc or url
        host = netloc.split(":")[0]  # olası portu at
        if host.startswith("www."):
            host = host[4:]
        base = host.split(".")[0] if "." in host else host
        return base.replace("-", " ").replace("_", " ").title() or "Bilinmeyen Şirket"
