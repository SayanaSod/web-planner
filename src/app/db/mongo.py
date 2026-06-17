from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.app.core.config import settings
from src.app.db.repositories import (
    MotorTasksRepository,
    MotorUsersRepository,
    TasksRepository,
    UsersRepository,
)

_STATE_DB_ATTR = "mongo_db_ref"


def _access_app_database() -> AsyncIOMotorDatabase:
    from src.app.main import app

    database = getattr(app.state, _STATE_DB_ATTR, None)

    if not database:
        mongo_conn = AsyncIOMotorClient(
            settings.MONGO_DSN,
            username=settings.USERNAME,
            password=settings.PASSWORD
        )
        database = mongo_conn[settings.MONGO_DB]
        setattr(main_app.state, _STATE_DB_ATTR, database)

    return database


async def get_users_repo() -> UsersRepository:
    active_db = _access_app_database()
    return MotorUsersRepository(active_db["users"])


async def get_tasks_repo() -> TasksRepository:
    active_db = _access_app_database()
    return MotorTasksRepository(active_db["tasks"])