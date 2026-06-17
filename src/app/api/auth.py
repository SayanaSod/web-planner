from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import DuplicateKeyError

from src.app.core.config import settings
from src.app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from src.app.db.mongo import get_users_repo
from src.app.db.repositories import UsersRepository
from src.app.models.users import TokenResponse, UserCreate, UserOut

auth_router = APIRouter()


@auth_router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
        payload: UserCreate,
        repo: UsersRepository = Depends(get_users_repo)
):
    """
    Регистрация нового пользователя.
    """
    secured_password = hash_password(payload.password)

    try:
        new_user = await repo.create(payload.email, secured_password)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )

    return UserOut(id=new_user["id"], email=new_user["email"])


@auth_router.post("/jwt/login", response_model=TokenResponse)
async def authenticate_user(
        credentials: UserCreate,
        repo: UsersRepository = Depends(get_users_repo)
):
    user_in_db = await repo.get_by_email(credentials.email)

    if not user_in_db or not verify_password(credentials.password, user_in_db["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(user_in_db["id"])
    token_data = decode_token(access_token)

    return TokenResponse(
        access_token=access_token,
        expires_in=token_data["exp"]
    )