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
    # Akıllı öncelikle bulunan şirket adı adayı (JSON-LD/og/title/h1). Yoksa None.
    detected_name: str | None = None


@dataclass(frozen=True, slots=True)
class CompanySignals:
    """LLM tarafından çekilen metinden çıkarılan yapılandırılmış iş sinyalleri.

    Bu, lead scoring'in girdisidir. ÖNEMLİ: LLM yalnızca bu sinyalleri ÇIKARIR
    (özellik mühendisliği); puanı LLM vermez — deterministik kural motoru verir.
    Bu, "LLM-assisted scoring" yaklaşımıdır: esnek metin anlama (LLM) + şeffaf,
    açıklanabilir karar (kurallar). ML modeli eğitilmez.
    """

    sector: str | None  # örn. "SaaS", "e-ticaret", "fintech"
    employee_band: str | None  # örn. "11-50", "51-200" (siteden tahmin, çoğu kez None)
    is_hiring: bool  # açık iş ilanı sinyali var mı
    hiring_roles: tuple[str, ...]  # örn. ("DevOps", "Satış")
    growth_signals: tuple[str, ...]  # örn. ("yeni yatırım", "yeni pazar")
    technologies: tuple[str, ...]  # tespit edilen teknolojiler


@dataclass(frozen=True, slots=True)
class CompanyInsights:
    """LLM analiz çıktısı: özet + acı noktaları + sinyaller (tek çağrıdan)."""

    summary: str
    pain_points: tuple[str, ...]
    signals: CompanySignals


@dataclass(frozen=True, slots=True)
class SellerProfile:
    """Soğuk e-posta ve pitch'i kişiselleştirmek için SATICININ (bizim) profili.

    E-posta anlamlı olsun diye modelin 'ne sattığımızı' bilmesi şarttır; aksi
    halde genel/uydurma çıktı üretir. Yapılandırmadan (config) gelir.
    """

    name: str  # satıcı şirket/ürün adı
    offering: str  # ne sattığımız / değer önerisi
    rep_name: str  # e-postayı imzalayan temsilci


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
    # Sprint 3'ten itibaren: LLM'in çıkardığı, skorlamayı besleyen sinyaller.
    signals: CompanySignals | None = None
