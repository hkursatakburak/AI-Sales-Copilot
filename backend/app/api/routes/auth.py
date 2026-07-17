"""Kimlik doğrulama endpoint'leri.

POST /auth/register  — yeni kullanıcı kaydı
POST /auth/login     — kullanıcı adı/şifre ile JWT alma
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.application import auth_service
from app.core.config import Settings, get_settings
from app.infrastructure.db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


class AuthRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


@router.post("/auth/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: AuthRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    try:
        await auth_service.register_user(payload.email, payload.password, db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return MessageResponse(message="Kayıt başarılı.")


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    payload: AuthRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    user = await auth_service.authenticate_user(payload.email, payload.password, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya şifre hatalı.",
        )
    token = auth_service.create_access_token(user.email, settings)
    return TokenResponse(access_token=token)
