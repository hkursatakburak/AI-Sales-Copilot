"""Bağımlılık enjeksiyonu (Dependency Injection) sağlayıcıları.

FastAPI'nin `Depends` mekanizması bizim DI konteyner'ımızdır. Route'lar somut
sınıf adı yerine `AnalysisService` arayüzünü ister; burada hangi somut
uygulamanın bağlanacağına karar verilir.

Faydası:
- Route kodu test edilirken `app.dependency_overrides` ile bu sağlayıcı kolayca
  sahte (mock) bir servisle değiştirilebilir.
- Sprint 4'te `StubAnalysisService` yerine gerçek pipeline'ı döndürmek için
  yalnızca burayı değiştirmek yeterli olacak.
"""

from __future__ import annotations

from functools import lru_cache

from app.application.stub_analysis_service import StubAnalysisService
from app.domain.interfaces import AnalysisService


@lru_cache
def get_analysis_service() -> AnalysisService:
    """Aktif `AnalysisService` uygulamasını (tekil) döndürür.

    Sprint 1: iskelet servis. İleriki sprintlerde burada gerçek pipeline
    kurulup döndürülecek.
    """
    return StubAnalysisService()
