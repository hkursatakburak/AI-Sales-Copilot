"""Alan (domain) modelleri — projenin saf iş varlıkları.

Clean Architecture'ın kalbi: bu dosya HİÇBİR framework'e (FastAPI, Pydantic,
HTTP) bağımlı değildir. Yalnızca standart kütüphane kullanır. Böylece iş
kuralları teknolojiden bağımsızdır; yarın FastAPI'yi atıp yerine başka bir şey
koysak bu modeller aynen kalır.

Modeller `frozen=True` (değişmez/immutable) olarak tanımlanır: bir analiz
nesnesi üretildikten sonra değiştirilemez. Bu, öngörülebilirlik ve thread
güvenliği sağlar.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class LeadTier(str, Enum):
    """Lead skorunun insan-okunur kategorisi."""

    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


@dataclass(frozen=True, slots=True)
class ScoreReason:
    """Lead skoruna katkı yapan TEK bir kuralın açıklaması.

    Açıklanabilir Yapay Zekâ (Explainable AI) mantığının temeli: her puanın
    nereden geldiği şeffaftır. "Neden 80 puan?" sorusuna bu liste cevap verir.
    """

    rule: str  # Kuralın makine-okunur kimliği, örn. "company_size"
    points: int  # Bu kuralın kattığı puan (+ veya -)
    explanation: str  # İnsan-okunur gerekçe


@dataclass(frozen=True, slots=True)
class LeadScore:
    """Bir müşteri adayının toplam değerlendirmesi."""

    value: int  # 0-100 arası nihai puan
    tier: LeadTier
    reasons: tuple[ScoreReason, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.value <= 100:
            raise ValueError(f"Lead skoru 0-100 arasında olmalı, alınan: {self.value}")


@dataclass(frozen=True, slots=True)
class AnalysisMeta:
    """Analizle ilgili teknik üst veri (metadata)."""

    generated_at: datetime
    pipeline_version: str
    is_stub: bool  # True ise sonuç gerçek değil, iskelet/placeholder verisidir


@dataclass(frozen=True, slots=True)
class ScrapedContent:
    """Bir web sayfasından çekilip temizlenmiş ham içerik.

    Bu, LLM ve lead scoring'in (Sprint 3) üzerinde çalışacağı "hammaddedir".
    `renderer` alanı, içeriğin nasıl elde edildiğini söyler: statik HTTP ile mi
    ("static") yoksa tarayıcı render'ı ile mi ("dynamic"). Bu, hem hata ayıklama
    hem de demo'da hangi yolun kullanıldığını göstermek için değerlidir.
    """

    url: str
    title: str | None
    site_name: str | None
    meta_description: str | None
    text: str  # temizlenmiş, düz metin (reklam/menü/script atılmış)
    headings: tuple[str, ...]
    word_count: int
    renderer: str  # "static" | "dynamic"
    fetched_at: datetime


@dataclass(frozen=True, slots=True)
class CompanyAnalysis:
    """Bir şirket için üretilen eksiksiz analiz sonucu.

    Bu, /analyze endpoint'inin döndürdüğü ana iş nesnesidir. Sprint 1'de
    alanlar `StubAnalysisService` tarafından deterministik placeholder'larla
    doldurulur; Sprint 2-4'te gerçek scraping + LLM çıktılarıyla dolacak.
    """

    url: str
    company_name: str | None
    summary: str
    pain_points: tuple[str, ...]
    lead_score: LeadScore
    cold_email: str
    pitch: str
    meta: AnalysisMeta
    # Sprint 2'den itibaren doldurulan gerçek scraping çıktısı.
    scraped: ScrapedContent | None = None
