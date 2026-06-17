from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.app.core.config import settings

_BCRYPT_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Генерация хеша пароля."""
    return _BCRYPT_CONTEXT.hash(plain_password)


def verify_password(plain_secret: str, hashed_secret: str) -> bool:
    """Проверка совпадения пароля и хеша."""
    return _BCRYPT_CONTEXT.verify(plain_secret, hashed_secret)


def create_access_token(subject: str) -> str:
    """Создание JWT токена."""
    current_time = datetime.now(tz=timezone.utc)
    expiration_time = current_time + settings.access_token_timedelta

    token_data: Dict[str, Any] = {
        "sub": subject,
        "exp": int(expiration_time.timestamp())
    }

    encoded_jwt = jwt.encode(
        token_data,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALG
    )
    return encoded_jwt


def decode_token(raw_token: str) -> Optional[Dict[str, Any]]:
    """Декодирование и валидация токена."""
    try:
        decoded_data = jwt.decode(
            raw_token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALG]
        )
        return decoded_data
    except JWTError:
        # Логирование ошибки можно добавить здесь при необходимости
        return None