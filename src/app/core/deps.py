from __future__ import annotations
from typing import Annotated, Any, Callable, Awaitable, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import redis.asyncio as aioredis
import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.app.core.config import settings
from src.app.core.logging import request_id_var
from src.app.db.repositories import TasksRepository, UsersRepository, MotorTasksRepository, MotorUsersRepository
from src.app.cache.redis import RedisCache
from src.app.external.nager import NagerImporter
from src.app.external.weather_open_meteo import WeatherImporter
from src.app.external.news_spaceflight import NewsImporter
from src.app.external.base import ExternalImporter
from src.app.models.tasks import ImportResult, ImportTaskOut
from src.app.core.security import decode_token

_mongo_client: AsyncIOMotorClient | None = None
_redis_pool: aioredis.ConnectionPool | None = None
bearer_scheme = HTTPBearer(auto_error=False)

async def init_dependencies():
    global _mongo_client, _redis_pool
    _mongo_client = AsyncIOMotorClient(settings.MONGO_DSN, username=settings.USERNAME, password=settings.PASSWORD, maxPoolSize=settings.MONGO_POOL_SIZE)
    _redis_pool = aioredis.ConnectionPool.from_url(settings.REDIS_URL, max_connections=settings.REDIS_POOL_SIZE)

async def close_dependencies():
    global _mongo_client, _redis_pool
    if _mongo_client: _mongo_client.close()
    if _redis_pool: await _redis_pool.aclose()

async def get_mongo_client() -> AsyncIOMotorClient:
    if _mongo_client is None: raise RuntimeError("MongoDB not initialized")
    return _mongo_client

async def get_mongo_db(client: Annotated[AsyncIOMotorClient, Depends(get_mongo_client)]) -> AsyncIOMotorDatabase:
    return client[settings.MONGO_DB]

async def get_redis_client() -> aioredis.Redis:
    if _redis_pool is None: raise RuntimeError("Redis not initialized")
    return aioredis.Redis(connection_pool=_redis_pool)

async def get_http_client() -> httpx.AsyncClient:
    headers = {"Accept": "application/json"}
    rid = request_id_var.get("system")
    if rid: headers["X-Request-ID"] = rid
    return httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT, headers=headers)

async def get_tasks_repo(db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)]) -> TasksRepository:
    return MotorTasksRepository(db["tasks"])

async def get_users_repo(db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)]) -> UsersRepository:
    return MotorUsersRepository(db["users"])

async def get_cache_service(redis: Annotated[aioredis.Redis, Depends(get_redis_client)]) -> RedisCache:
    return RedisCache(redis)

async def get_import_service(tasks_repo: Annotated[TasksRepository, Depends(get_tasks_repo)]) -> Callable:
    async def execute_import(importer: ExternalImporter, user_id: str, fetch_kwargs: dict, normalize_kwargs: dict = None) -> ImportResult:
        normalize_kwargs = normalize_kwargs or {}
        raw_data = await importer.fetch_raw(**fetch_kwargs)
        normalized = importer.normalize(raw_data, **normalize_kwargs)
        inserted_count, inserted_docs = await tasks_repo.insert_many_generic(user_id=user_id, items=normalized)
        details = [ImportTaskOut(id=doc["id"], title=doc["title"], date=doc["date"], type=doc["type"], status=doc["status"], source=doc["source"]) for doc in inserted_docs]
        return ImportResult(imported=inserted_count, skipped=len(normalized) - inserted_count, details=details, errors=[])
    return execute_import

async def get_nager_importer(client: Annotated[httpx.AsyncClient, Depends(get_http_client)]) -> NagerImporter:
    return NagerImporter(client)

async def get_weather_importer(client: Annotated[httpx.AsyncClient, Depends(get_http_client)]) -> WeatherImporter:
    return WeatherImporter(client)

async def get_news_importer(client: Annotated[httpx.AsyncClient, Depends(get_http_client)]) -> NewsImporter:
    return NewsImporter(client)

async def get_current_user(credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)], users: Annotated[UsersRepository, Depends(get_users_repo)]):
    if credentials is None: raise HTTPException(status_code=401, detail="Invalid token")
    decoded = decode_token(credentials.credentials)
    if not decoded or datetime.now(timezone.utc).timestamp() > decoded["exp"]:
        raise HTTPException(status_code=401, detail="Invalid token")
    return await users.get_by_id(decoded["sub"])
