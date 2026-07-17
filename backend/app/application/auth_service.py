"""Kimlik doğrulama uygulama servisi.

Sorumluluklar:
- Kullanıcı kaydı (register): e-posta benzersizliği + şifre hashleme
- Kullanıcı kimlik doğrulama (authenticate): e-posta araması + bcrypt doğrulama
- JWT üretimi ve doğrulaması
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.infrastructure.db.user_model import UserORM

logger = logging.getLogger(__name__)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


async def register_user(email: str, plain_password: str, db: AsyncSession) -> UserORM:
    """Yeni kullanıcı oluşturur. E-posta zaten kayıtlıysa ValueError fırlatır."""
    existing = await db.scalar(select(UserORM).where(UserORM.email == email))
    if existing is not None:
        raise ValueError(f"E-posta zaten kayıtlı: {email}")

    user = UserORM(email=email, hashed_password=hash_password(plain_password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("Yeni kullanıcı kaydedildi: %s", email)
    return user


async def authenticate_user(
    email: str, plain_password: str, db: AsyncSession
) -> UserORM | None:
    """Kimlik bilgilerini doğrular. Geçersizse None döner."""
    user = await db.scalar(select(UserORM).where(UserORM.email == email))
    if user is None or not user.is_active:
        return None
    if not verify_password(plain_password, user.hashed_password):
        return None
    return user


def create_access_token(email: str, settings: Settings) -> str:
    """HS256 imzalı JWT üretir."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": email, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> str:
    """Token'ı doğrular ve e-postayı (sub) döndürür.

    Süresi dolmuş veya geçersiz token → jwt.InvalidTokenError fırlatır.
    """
    data = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    sub: str | None = data.get("sub")
    if not sub:
        raise jwt.InvalidTokenError("Token 'sub' alanı eksik.")
    return sub
