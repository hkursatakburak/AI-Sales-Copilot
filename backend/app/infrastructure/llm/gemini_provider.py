"""Gemini (Google AI Studio) tabanlı `LLMProvider` implementasyonu.

`ClaudeLLMProvider` ile AYNI arayüzü (`LLMProvider`) uygular; böylece uygulamanın
geri kalanı hangi sağlayıcının kullanıldığını bilmez (Liskov / DIP). Ücretsiz
Google AI Studio API anahtarıyla çalışır.

Yapılandırılmış çıktı: Gemini'nin JSON modu (`response_mime_type="application/
json"`) kullanılır ve şema, talimat olarak prompt'a eklenir — bu yaklaşım şema
formatı uyumsuzluklarından bağımsız ve dayanıklıdır.

`google.genai` import'u tembeldir: paket/anahtar yoksa modül import'u uygulamayı
çökertmez.
"""

from __future__ import annotations

import json
import logging

from app.core.exceptions import LLMError
from app.domain.interfaces import LLMProvider

logger = logging.getLogger(__name__)


class GeminiLLMProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gemini-2.5-flash",
        max_tokens: int = 2048,
    ):
        import google.genai as genai

        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def _generate(self, *, system: str, contents: str, max_tokens: int, json_mode: bool):
        """generate_content çağrısını sarıp Gemini hatalarını `LLMError`'a çevirir."""
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
            response_mime_type="application/json" if json_mode else "text/plain",
        )
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model, contents=contents, config=config
            )
        except errors.ClientError as exc:
            code = getattr(exc, "code", None)
            if code in (401, 403) or "API key" in str(exc):
                logger.error("Gemini kimlik doğrulama hatası: %s", exc)
                raise LLMError("Analiz servisi yapılandırması hatalı (API anahtarı).") from exc
            if code == 429:
                raise LLMError(
                    "Analiz servisi şu an yoğun (kota). Lütfen birazdan tekrar deneyin."
                ) from exc
            logger.error("Gemini istemci hatası: %s", exc)
            raise LLMError() from exc
        except errors.ServerError as exc:
            raise LLMError("Analiz servisine ulaşılamadı. Lütfen tekrar deneyin.") from exc
        except errors.APIError as exc:
            logger.error("Gemini API hatası: %s", exc)
            raise LLMError() from exc

        return (response.text or "").strip()

    async def extract_structured(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict,
        tool_name: str,
        tool_description: str,
    ) -> dict:
        contents = (
            f"{prompt}\n\n"
            "YALNIZCA aşağıdaki JSON şemasına uygun, geçerli bir JSON nesnesi döndür. "
            "Açıklama, markdown veya ek metin ekleme:\n"
            f"{json.dumps(schema, ensure_ascii=False)}"
        )
        text = await self._generate(
            system=system, contents=contents, max_tokens=self._max_tokens, json_mode=True
        )
        return self._parse_json(text)

    async def generate_text(self, *, system: str, prompt: str, max_tokens: int) -> str:
        return await self._generate(
            system=system, contents=prompt, max_tokens=max_tokens, json_mode=False
        )

    @staticmethod
    def _parse_json(text: str) -> dict:
        cleaned = text.strip()
        # Olası markdown kod bloğu çitlerini temizle.
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
        try:
            data = json.loads(cleaned)
        except (ValueError, TypeError) as exc:
            logger.error("Gemini geçerli JSON döndürmedi: %.200s", text)
            raise LLMError("Analiz modeli beklenen yapılandırılmış çıktıyı döndürmedi.") from exc
        if not isinstance(data, dict):
            raise LLMError("Analiz modeli beklenen yapılandırılmış çıktıyı döndürmedi.")
        return data
