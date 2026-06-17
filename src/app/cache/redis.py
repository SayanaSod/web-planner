from __future__ import annotations

import hashlib
import json
from typing import Optional

from redis import asyncio as aioredis

from src.app.core.config import settings


class RedisCache:
    """
    Клиент для работы с Redis.
    """

    def __init__(self, client: aioredis.Redis):
        self.client = client

    async def connect(self):
        self.client = aioredis.from_url(url=settings.REDIS_URL, decode_responses=True)
    async def disconnect(self):
        if self.client:
            await self.client.close()

    def _make_key(self, user_id: str, method: str, path: str, query_params: dict) -> str:
        sorted_params = sorted(query_params.items())
        query_str = "&".join(f"{k}={v}" for k, v in sorted_params)
        query_hash = hashlib.sha256(query_str.encode()).hexdigest()[:16]
        return f"cache:{settings.APP_ENV}:{user_id}:{method}:{path}:{query_hash}"


    async def get(self, key: str) -> Optional[dict]:
        if self.client is None:
            return {}
        payload = await self.client.get(key)
        if not payload:
            return {}
        return json.loads(payload)

    async def set(self, key: str, value: dict, ttl: int):
        if not self.client:
            return
        json_val = json.dumps(value, ensure_ascii=False)
        await self.client.setex(name=key, time=ttl, value=json_val)

