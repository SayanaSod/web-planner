from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """
    Модель данных для регистрации и аутентификации.
    """
    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        description="Секретный ключ (минимум 8 символов)"
    )


class UserOut(BaseModel):
    """
    Публичная схема пользователя для ответов API.
    """
    id: str
    email: EmailStr


class TokenResponse(BaseModel):
    """
    Контейнер для JWT токена.
    """
    access_token: str
    token_type: str = Field(default="bearer")
    expires_in: int