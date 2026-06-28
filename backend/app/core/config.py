"""Uygulama yapılandırması.

Tüm ayarlar tek bir `Settings` nesnesinde toplanır ve ortam değişkenlerinden
(veya `.env` dosyasından) okunur. Bu, "12-Factor App" prensibine uyar:
yapılandırma koddan ayrılır, böylece aynı kod farklı ortamlarda
(geliştirme/test/üretim) değişiklik yapmadan çalışır.

ÖNEMLİ (güvenlik): API anahtarları ASLA koda veya Chrome eklentisine gömülmez.
Yalnızca burada, backend ortamında okunur.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ortam değişkenlerinden yüklenen uygulama ayarları.

    Tüm değişkenler `COPILOT_` ön ekiyle okunur. Örn: `COPILOT_LOG_LEVEL=DEBUG`.
    """

    model_config = SettingsConfigDict(
        env_prefix="COPILOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Genel ---
    app_name: str = "AI Sales Copilot"
    environment: str = "development"  # development | staging | production
    log_level: str = "INFO"

    # --- CORS ---
    # Chrome eklentisi backend'e farklı bir origin'den (chrome-extension://...)
    # istek attığı için CORS izni gerekir. Geliştirmede esnek; üretimde
    # `COPILOT_CORS_ALLOW_ORIGINS=["https://..."]` ile daraltılmalıdır.
    cors_allow_origins: list[str] = ["*"]

    # --- Scraping (Sprint 2) ---
    # Toplam (read) zaman aşımı ve ayrı bağlantı (connect) zaman aşımı.
    scraper_timeout_seconds: float = 15.0
    scraper_connect_timeout_seconds: float = 5.0
    # Gerçekçi, güncel bir tarayıcı User-Agent'ı (standart davranış; basit bot
    # filtrelerini geçmeye yardımcı olur — gelişmiş korumaları AŞMAYA çalışmaz).
    scraper_user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    # Statik çekimden sonra metin bu kelime sayısının altındaysa, içeriğin JS ile
    # yüklendiği varsayılır ve Playwright (dinamik) yedeğe geçilir.
    scraper_min_words_for_dynamic: int = 120
    # Geçici hatalarda (timeout/bağlantı) yeniden deneme sayısı ve backoff.
    scraper_max_retries: int = 2
    scraper_retry_backoff_seconds: float = 0.5
    # Nezaket için aynı siteye ardışık isteklerde minimum bekleme (rate limiting).
    scraper_min_request_interval_seconds: float = 1.0
    # Güvenlik: özel/iç ağ adreslerine (localhost, 10.x, 192.168.x, bulut
    # metadata IP'leri) istek atmayı engeller (SSRF koruması). Yalnızca yerel
    # geliştirmede True yapın.
    scraper_allow_private_urls: bool = False
    # robots.txt'e saygı göster (etik scraping).
    scraper_respect_robots: bool = True

    # --- LLM (Sprint 3) ---
    # Anahtar yoksa sistem zarif şekilde Sprint 2 davranışına (scraping-only,
    # is_stub=True) düşer; uygulama yine çalışır.
    anthropic_api_key: str | None = None
    # Varsayılan model: en yetenekli Opus. Maliyet için Sonnet'e geçmek isterseniz:
    #   COPILOT_LLM_MODEL=claude-sonnet-4-6   (~%40 daha ucuz, bu görevlere uygun)
    llm_model: str = "claude-opus-4-8"
    llm_max_tokens: int = 2048
    llm_timeout_seconds: float = 60.0
    # LLM'e gönderilen metin bu karakter sayısında kırpılır (context-stuffing /
    # RAG-lite; token maliyetini sınırlar). Tek sayfa için fazlasıyla yeterli.
    llm_max_input_chars: int = 6000
    llm_email_max_tokens: int = 700
    llm_pitch_max_tokens: int = 700

    # --- Satıcı profili (Sprint 4) ---
    # Soğuk e-posta/pitch'in "ne sattığımızı" bilmesi için. Kendi ürününüze göre
    # COPILOT_SELLER_* ile değiştirin.
    seller_name: str = "AI Sales Copilot"
    seller_offering: str = (
        "Satış ekiplerinin potansiyel müşteri araştırmasını ve kişiselleştirilmiş "
        "ulaşım metni yazımını saniyeler içinde yapan bir yapay zekâ asistanı."
    )
    seller_rep_name: str = "Elif"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Ayarları tekil (singleton) olarak döndürür.

    `lru_cache` sayesinde ayarlar süreç boyunca yalnızca bir kez okunur.
    Testlerde `get_settings.cache_clear()` ile sıfırlanabilir.
    """
    return Settings()
