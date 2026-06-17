from __future__ import annotations

from typing import Optional

from fastapi import Request

from src.app.cache.redis import AsyncCacheService


async def retrieve_cache_entry(
        raw_req: Request,
        key: str,
        limit: int,
        backend: AsyncCacheService,
        skip_cache: bool = False
) -> tuple[Optional[dict], bool]:
    """
    Попытка извлечь данные.
    Возвращает кортеж: (данные, успех).
    """
    if skip_cache:
        return (None, False)

    # Используем метод fetch, который мы определили в AsyncCacheService
    stored_data = await backend.fetch(key)

    if stored_data:
        return (stored_data, True)

    return (None, False)


async def save_cache_entry(
        key: str,
        data: dict,
        limit: int,
        backend: AsyncCacheService
):
    # Используем метод save
    await backend.save(key, data, limit)