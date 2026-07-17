"""JWT doğrulama bağımlılığı — korunan route'larda kullanılır.

`get_current_user`: Authorization: Bearer <token> başlığını okur,
JWT'yi doğrular, kullanıcıyı veritabanından çeker ve döndürür.
Geçersiz/eksik token durumunda 401 fırlatır.
"""

from __future__ import annotations

import logging

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth_service import decode_access_token
from app.core.config import Settings, get_settings
from app.infrastructure.db.database import get_db
from app.infrastructure.db.user_model import UserORM

logger = logging.getLogger(__name__)

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Geçersiz veya süresi dolmuş oturum. Lütfen tekrar giriş yapın.",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserORM:
    if not authorization or not authorization.startswith("Bearer "):
        raise _CREDENTIALS_EXCEPTION

    token = authorization.removeprefix("Bearer ").strip()
    try:
        email = decode_access_token(token, settings)
    except jwt.InvalidTokenError:
        logger.warning("Geçersiz JWT token.")
        raise _CREDENTIALS_EXCEPTION

    user = await db.scalar(select(UserORM).where(UserORM.email == email))
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXCEPTION

    return user
