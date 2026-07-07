"""LLM sağlayıcı fabrikası — provider-agnostic seçim.

`LLM_PROVIDER` ayarına göre uygun `LLMProvider`'ı kurar. Seçili sağlayıcının
API anahtarı yoksa `None` döner (üst katman scraping-only'ye düşer).

Yeni bir sağlayıcı (örn. OpenAI) eklemek için: `LLMProvider`'ı uygulayan bir
sınıf yaz ve buraya bir dal ekle — uygulamanın geri kalanı değişmez (OCP).
"""

from __future__ import annotations

import logging

from app.core.config import Settings
from app.domain.interfaces import LLMProvider
from app.infrastructure.llm.claude_provider import ClaudeLLMProvider
from app.infrastructure.llm.gemini_provider import GeminiLLMProvider

logger = logging.getLogger(__name__)


def create_llm_provider(settings: Settings) -> LLMProvider | None:
    provider = settings.llm_provider.strip().lower()

    if provider == "claude":
        if not settings.anthropic_api_key:
            logger.warning("LLM_PROVIDER=claude ama ANTHROPIC_API_KEY yok.")
            return None
        return ClaudeLLMProvider(
            settings.anthropic_api_key,
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout_seconds,
        )

    if provider == "gemini":
        if not settings.gemini_api_key:
            logger.warning("LLM_PROVIDER=gemini ama GEMINI_API_KEY yok.")
            return None
        return GeminiLLMProvider(
            settings.gemini_api_key,
            model=settings.gemini_model,
            max_tokens=settings.llm_max_tokens,
        )

    # OpenAI ileride buraya eklenecek (OCP): mimari açık, implementasyon henüz yok.
    logger.error("Bilinmeyen LLM_PROVIDER='%s' (claude|gemini). LLM devre dışı.", provider)
    return None
