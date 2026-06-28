"""/analyze endpoint'i — projenin ana giriş noktası.

Chrome eklentisi aktif sekmenin URL'sini buraya POST eder; backend bir
`CompanyAnalysis` üretip JSON olarak döndürür. Endpoint "ince" tutulur:
iş mantığını kendi yapmaz, yalnızca enjekte edilen `AnalysisService`'e devreder
(Tek Sorumluluk İlkesi / SRP).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.api.dependencies import get_analysis_service
from app.api.schemas import AnalyzeRequest, AnalyzeResponse, EmailResponse
from app.domain.interfaces import AnalysisService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    payload: AnalyzeRequest,
    service: AnalysisService = Depends(get_analysis_service),
) -> AnalyzeResponse:
    url = str(payload.url)
    logger.info("Analiz isteği alındı: %s", url)

    analysis = await service.analyze(url)

    return AnalyzeResponse.from_domain(analysis)


@router.post("/email", response_model=EmailResponse)
async def regenerate_email(
    payload: AnalyzeRequest,
    service: AnalysisService = Depends(get_analysis_service),
) -> EmailResponse:
    """Soğuk e-posta + pitch'i yeniden üretir.

    Aynı pipeline'ı çalıştırır; LLM doğası gereği her çağrı farklı (taze) bir
    e-posta üretir — kullanıcı tonu beğenmezse 'yeniden üret' için idealdir.
    """
    url = str(payload.url)
    logger.info("E-posta yeniden üretim isteği: %s", url)

    analysis = await service.analyze(url)

    return EmailResponse.from_domain(analysis)
