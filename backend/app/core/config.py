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

    # --- LLM (Sprint 3'ten itibaren kullanılacak) ---
    # Sprint 1'de zorunlu değil; varsayılan provider Claude olacak.
    anthropic_api_key: str | None = None

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
