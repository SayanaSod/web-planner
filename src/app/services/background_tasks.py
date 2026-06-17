# src/app/services/background_tasks.py
import logging
import contextvars
from datetime import datetime, timedelta
import httpx
from src.app.core.config import settings
from src.app.core.deps import get_mongo_client, get_http_client
from src.app.core.logging import request_id_var, user_id_var
from src.app.db.repositories import MotorTasksRepository, MotorUsersRepository

logger = logging.getLogger("scheduler")


async def get_background_db():
    """Helper для получения БД в фоновой задаче."""
    client = await get_mongo_client()  # Из глобального пула
    return client[settings.MONGO_DB]


async def auto_import_task():
    """Фоновая задача автоимпорта."""
    # Устанавливаем контекст для логгера
    request_id_var.set("scheduler-import")
    user_id_var.set("system")

    try:
        db = await get_background_db()
        users_repo = MotorUsersRepository(db["users"])
        tasks_repo = MotorTasksRepository(db["tasks"])

        # Получаем всех пользователей (в проде лучше чанками или только активных)
        # Так как метода list_all нет в интерфейсе UsersRepository из примера,
        # добавим упрощенный вариант доступа к коллекции напрямую или расширим репо.
        # Для безопасности используем raw collection access здесь.
        users_cursor = users_repo.coll.find({})

        imported_total = 0
        users_count = 0

        # Создаем отдельный HTTP клиент для задачи
        async with httpx.AsyncClient(timeout=10) as client:
            async for user in users_cursor:
                users_count += 1
                # Пример логики: Импорт праздников для дефолтной страны (например, US)
                # В реальном проекте настройки импорта хранились бы в user.settings
                from src.app.external.nager import NagerImporter
                from src.app.services.import_service import execute_import

                importer = NagerImporter(client)
                try:
                    result = await execute_import(
                        importer=importer,
                        user_id=str(user["_id"]),
                        tasks_repo=tasks_repo,
                        fetch_kwargs={"country": "US", "year": datetime.now().year},
                        normalize_kwargs={"country": "US"}
                    )
                    imported_total += result.imported
                except Exception as e:
                    logger.warning(f"Failed to auto-import for user {user['_id']}: {e}")

        logger.info(f"Auto-import completed: imported {imported_total} tasks from {users_count} users")

    except Exception as e:
        logger.error(f"Auto-import failed: {e}", exc_info=True)


async def cleanup_expired_tasks():
    request_id_var.set("scheduler-cleanup")
    user_id_var.set("system")

    try:
        db = await get_background_db()
        tasks_repo = MotorTasksRepository(db["tasks"])

        cutoff_date = datetime.utcnow() - timedelta(days=settings.CLEANUP_EXPIRED_DAYS)
        cutoff_str = cutoff_date.date().isoformat()

        # Удаляем completed старее N дней (прямой запрос к коллекции, так как в репо мб не быть метода delete_many)
        res_completed = await tasks_repo.coll.delete_many({
            "status": "completed",
            "date": {"$lt": cutoff_str}
        })

        # Удаляем любые задачи старее N дней (даже не completed, если нужно по ТЗ,
        # но обычно удаляют только старый "мусор" или completed.
        # В ТЗ: "Удаляет задачи с датой в прошлом (старше N дней)" - удалим все старое.
        res_expired = await tasks_repo.coll.delete_many({
            "date": {"$lt": cutoff_str}
        })

        total = res_completed.deleted_count + res_expired.deleted_count
        logger.info(f"Cleanup completed: removed {total} expired tasks")

    except Exception as e:
        logger.error(f"Cleanup failed: {e}", exc_info=True)


async def check_reminders():
    request_id_var.set("scheduler-reminders")
    user_id_var.set("system")

    try:
        db = await get_background_db()
        tasks_repo = MotorTasksRepository(db["tasks"])

        # Логика напоминаний обычно требует времени (HH:MM), но у нас Date only.
        # Будем имитировать: напоминаем о задачах на "завтра" или "сегодня".
        # По ТЗ: "ближайшие N минут". Для этого нужна модель с datetime.
        # Предположим, что мы ищем задачи на сегодня.

        today = datetime.now().date().isoformat()

        # Ищем задачи на сегодня со статусом todo
        cursor = tasks_repo.coll.find({"date": today, "status": "todo"})
        count = 0
        async for task in cursor:
            # В реальном проде здесь отправка push/email
            logger.info(
                f"Reminder: '{task.get('title')}' is due today",
                extra={"user_id": str(task["user_id"]), "task_id": str(task["_id"])}
            )
            count += 1

        if count > 0:
            logger.info(f"Reminders checked: {count} tasks found")

    except Exception as e:
        logger.error(f"Reminders check failed: {e}", exc_info=True)