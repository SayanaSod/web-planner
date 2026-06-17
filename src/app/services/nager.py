from __future__ import annotations

import re
from typing import Any, Dict, List

import httpx

# Изменили константу
SERVICE_ENDPOINT = "https://date.nager.at/api/v3/PublicHolidays"

# Переименовали скомпилированные регулярки
_INVALID_CHARS = re.compile(r"[^a-z0-9]+")
_REPEATING_UNDERSCORES = re.compile(r"_+")


async def retrieve_holidays_data(target_year: int, iso_code: str) -> List[Dict[str, Any]]:
    """
    Получение данных о праздниках (Async).
    """
    request_url = f"{SERVICE_ENDPOINT}/{target_year}/{iso_code}"

    # Используем контекстный менеджер для корректного закрытия соединения
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(request_url)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            # Заменили requests.exceptions на стандартный Exception или логирование
            raise ConnectionError(f"Nager API unavailable for {iso_code}")


def generate_safe_slug(text: str, char_limit: int = 40) -> str:
    """Очистка строки для использования в ID."""
    processed = text.lower()
    processed = _INVALID_CHARS.sub("_", processed)
    processed = _REPEATING_UNDERSCORES.sub("_", processed).strip("_")

    if len(processed) > char_limit:
        processed = processed[:char_limit].rstrip("_")

    return processed if processed else "item"


def map_api_response_to_task(
        record: Dict[str, Any],
        country_code: str
) -> Dict[str, Any]:
    """Нормализация одной записи праздника."""
    # Приоритет локального названия над международным
    raw_name = record.get("localName") or record.get("name")
    clean_title = str(raw_name).strip() if raw_name else "Holiday"

    # Дата в формате YYYY-MM-DD
    event_date = str(record.get("date", ""))[:10]

    # Уникальный идентификатор
    slug_part = generate_safe_slug(clean_title)
    unique_id = f"nager_{country_code}_{event_date}_{slug_part}"

    return {
        "title": clean_title,
        "date": event_date,
        "type": "holiday",
        "status": "todo",
        "source": "nager",
        "meta": {
            "source_id": unique_id
        },
    }