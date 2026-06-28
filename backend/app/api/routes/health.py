"""Sağlık kontrolü (health check) endpoint'i.

Servisin ayakta olup olmadığını ucuzca kontrol etmek için kullanılır
(load balancer'lar, uptime izleme, CI/CD smoke testleri). Hiçbir bağımlılığa
dokunmaz; yalnızca sürecin yanıt verdiğini doğrular.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app import __version__
from app.api.schemas import HealthResponse
from app.core.config import Settings, get_settings

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=__version__,
        environment=settings.environment,
    )
