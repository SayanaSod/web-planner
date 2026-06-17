from __future__ import annotations

from typing import Any, Dict, Optional

from src.app.db.repositories import TasksRepository
from src.app.external.base import ExternalImporter
from src.app.models.tasks import ImportResult, ImportTaskOut


async def run_import_process(
    provider: ExternalImporter,
    owner_id: str,
    storage: TasksRepository,
    query_params: Dict[str, Any],
    context_params: Optional[Dict[str, Any]] = None
) -> ImportResult:
    """
    Оркестратор процесса загрузки данных:
    Запрос -> Нормализация -> Сохранение -> Отчет.
    """
    ctx = context_params or {}

    # 1. Получение сырых данных от провайдера
    raw_payload = await provider.fetch_raw(**query_params)

    # 2. Приведение к единому формату
    clean_items = provider.normalize(raw_payload, **ctx)

    # 3. Сохранение в БД с дедупликацией
    success_count, saved_records = await storage.insert_many_generic(
        user_id=owner_id,
        items=clean_items
    )

    # 4. Формирование отчета
    result_details = []
    for record in saved_records:
        item_out = ImportTaskOut(
            id=record["id"],
            title=record["title"],
            date=record["date"],
            type=record["type"],
            status=record["status"],
            source=record["source"]
        )
        result_details.append(item_out)

    return ImportResult(
        imported=success_count,
        skipped=len(clean_items) - success_count,
        details=result_details,
        errors=[]
    )