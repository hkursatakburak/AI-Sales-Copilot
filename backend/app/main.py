"""FastAPI uygulama fabrikası (application factory) ve giriş noktası.

`create_app()` deseni kullanılır: uygulama bir fonksiyon içinde kurulur.
Faydası — testler her seferinde temiz bir uygulama örneği oluşturabilir;
global durum (state) kaçaklarından kaçınılır.

Çalıştırma (geliştirme):
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import analyze, health
from app.api.routes import auth as auth_routes
from app.core.auth import get_current_user
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Yapılandırılmış bir FastAPI uygulaması oluşturur ve döndürür."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        from app.infrastructure.db.database import init_db
        await init_db(settings.database_url)
        yield

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Satış temsilcileri için şirket analizi üreten AI Sales Copilot backend'i.",
        lifespan=lifespan,
    )

    # Bu uygulama örneğine özgü ayarları DI'a bağla: route'lar `Depends(get_settings)`
    # ile global tekil yerine buradaki `settings`'i alır. Testlerin kendi ayarlarını
    # enjekte edebilmesinin anahtarı budur.
    app.dependency_overrides[get_settings] = lambda: settings

    # --- CORS ---
    # Chrome eklentisi (chrome-extension://...) farklı origin olduğu için gerekli.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- İstek bağlamı / loglama middleware'i ---
    app.add_middleware(RequestContextMiddleware)

    # --- Hata işleyiciler ---
    register_exception_handlers(app)

    # --- Route'lar ---
    app.include_router(health.router)
    app.include_router(auth_routes.router)  # /auth/register, /auth/login — token gerektirmez
    app.include_router(
        analyze.router,
        dependencies=[Depends(get_current_user)],  # /analyze, /email — JWT zorunlu
    )

    logger.info("Uygulama oluşturuldu (ortam=%s, sürüm=%s)", settings.environment, __version__)
    return app


# Uvicorn'un içe aktardığı modül seviyesi uygulama nesnesi.
app = create_app()
