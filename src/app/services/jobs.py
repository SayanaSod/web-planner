from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from src.app.core.config import settings
from src.app.core.deps import get_mongo_client

job_logger = logging.getLogger("background_jobs")


async def auto_import_task():
    try:
        client = await get_mongo_client()
        db = client[settings.MONGO_DB]
        users_collection = db["users"]

        active_users = await users_collection.find({}).to_list(length=None)

        if not active_users:
            return

        job_logger.info(f"Auto-import processed {len(active_users)} users")

    except Exception as err:
        job_logger.error(f"Error in auto_import: {err}")


async def cleanup_expired_tasks():
    try:
        client = await get_mongo_client()
        tasks = client[settings.MONGO_DB]["tasks"]
        threshold = datetime.now(timezone.utc) - timedelta(days=settings.CLEANUP_EXPIRED_DAYS)
        await tasks.delete_many({"status": "done", "date": {"$lt": threshold.date().isoformat()}})
    except Exception:
        pass


async def check_reminders():
    try:
        client = await get_mongo_client()
        tasks = client[settings.MONGO_DB]["tasks"]
        today = datetime.now(timezone.utc).date().isoformat()
        await tasks.find({"date": today, "status": "todo", "type": {"$in": ["meeting", "deadline"]}}).to_list(
            length=100)
    except Exception:
        pass
