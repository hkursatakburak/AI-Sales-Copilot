"""Uygulamaya özel hata tipleri ve tutarlı hata yanıtı üretimi.

Tüm bilinen hatalar tek bir taban sınıftan (`AppError`) türer ve istemciye
her zaman aynı JSON zarfıyla döner:

    {"error": {"code": "...", "message": "...", "request_id": "..."}}

Böylece Chrome eklentisi (ve gelecekteki istemciler) hataları tek bir
biçimde işleyebilir. İleride eklenecek scraping/LLM hataları da bu hiyerarşiye
oturacak (Sprint 2-3).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_request_id

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Uygulama hatalarının ortak taban sınıfı."""

    code: str = "internal_error"
    status_code: int = 500

    def __init__(self, message: str = "Beklenmeyen bir hata oluştu."):
        super().__init__(message)
        self.message = message


class ScrapeError(AppError):
    """Web scraping sırasında oluşan hata (Sprint 2'de kullanılacak)."""

    code = "scrape_error"
    status_code = 502


class LLMError(AppError):
    """LLM çağrısı sırasında oluşan hata (Sprint 3'te kullanılacak)."""

    code = "llm_error"
    status_code = 502


def _error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message, "request_id": get_request_id()}}


def register_exception_handlers(app: FastAPI) -> None:
    """Tüm hata işleyicilerini FastAPI uygulamasına bağlar."""

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        logger.warning("İşlenen uygulama hatası: %s - %s", exc.code, exc.message)
        return JSONResponse(status_code=exc.status_code, content=_error_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Geçersiz girdi (örn. bozuk URL) -> 422 ile açıklayıcı mesaj.
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Gönderilen veri geçersiz.",
                    "request_id": get_request_id(),
                    "details": exc.errors(),
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        # Beklenmeyen her hata loglanır ama istemciye iç detay sızdırılmaz.
        logger.exception("Beklenmeyen hata: %s", exc)
        return JSONResponse(
            status_code=500,
            content=_error_body("internal_error", "Beklenmeyen bir hata oluştu."),
        )
