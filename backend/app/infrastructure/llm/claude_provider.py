"""Claude (Anthropic) tabanlı `LLMProvider` implementasyonu.

Yapılandırılmış çıktı için **zorunlu araç kullanımı (forced tool use)** tercih
edildi: modele bir "araç" (JSON şeması) verip `tool_choice` ile o aracı
çağırmaya zorlarız. Model, çıktıyı şemaya uygun bir `tool_use` bloğu olarak
döndürür — serbest metin ayrıştırmaya göre çok daha güvenilir ve SDK
sürümlerinden bağımsızdır.

`anthropic` import'u tembeldir (lazy): paket kurulu değilse veya API anahtarı
yoksa modülün import edilmesi uygulamayı çökertmez (scraping-only'ye zarif düşüş).
"""

from __future__ import annotations

import logging

from app.core.exceptions import LLMError
from app.domain.interfaces import LLMProvider

logger = logging.getLogger(__name__)


class ClaudeLLMProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        *,
        model: str = "claude-opus-4-8",
        max_tokens: int = 2048,
        timeout: float = 60.0,
    ):
        # Tembel import: anthropic yalnızca gerçekten kullanılınca gerekir.
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=api_key, timeout=timeout)
        self._model = model
        self._max_tokens = max_tokens

    async def _create(self, **kwargs):
        """messages.create çağrısını sarıp Anthropic hatalarını kullanıcı dostu
        `LLMError`'a çevirir (tek yerde — DRY)."""
        import anthropic

        try:
            return await self._client.messages.create(model=self._model, **kwargs)
        except anthropic.AuthenticationError as exc:
            logger.error("Claude kimlik doğrulama hatası: %s", exc)
            raise LLMError("Analiz servisi yapılandırması hatalı (API anahtarı).") from exc
        except anthropic.RateLimitError as exc:
            raise LLMError(
                "Analiz servisi şu an yoğun. Lütfen birazdan tekrar deneyin."
            ) from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("Analiz servisine bağlanılamadı.") from exc
        except anthropic.APIError as exc:
            logger.error("Claude API hatası: %s", exc)
            raise LLMError() from exc

    async def extract_structured(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict,
        tool_name: str,
        tool_description: str,
    ) -> dict:
        message = await self._create(
            max_tokens=self._max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {"name": tool_name, "description": tool_description, "input_schema": schema}
            ],
            tool_choice={"type": "tool", "name": tool_name},
        )
        for block in message.content:
            if block.type == "tool_use":
                # block.input zaten şemaya göre ayrıştırılmış bir sözlüktür.
                return dict(block.input)
        raise LLMError("Analiz modeli beklenen yapılandırılmış çıktıyı döndürmedi.")

    async def generate_text(self, *, system: str, prompt: str, max_tokens: int) -> str:
        message = await self._create(
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in message.content if b.type == "text").strip()
