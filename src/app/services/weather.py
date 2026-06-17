from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException, status

FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"


async def get_forecast_data(
        lat: float,
        lon: float,
        period_days: int = 3,
        trace_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Запрос прогноза погоды (Open-Meteo).
    """
    query_params = {
        "latitude": lat,
        "longitude": lon,
        "forecast_days": period_days,
        "daily": "weathercode,temperature_2m_max,temperature_2m_min",
        "timezone": "auto"
    }

    headers = {}
    if trace_id:
        headers["X-Request-ID"] = trace_id

    async with httpx.AsyncClient(headers=headers) as session:
        try:
            resp = await session.get(FORECAST_API_URL, params=query_params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Weather provider is unavailable"
            )


_CLEAN_REGEX = re.compile(r"[^a-z0-9]+")


def _make_slug(text: str) -> str:
    return _CLEAN_REGEX.sub("_", text.lower()).strip("_")


def parse_weather_response(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Преобразование ответа OpenMeteo в список задач.
    Логика полностью переписана, так как исходный код был скопирован из Nager (праздники).
    """
    tasks = []

    # OpenMeteo возвращает структуру { "daily": { "time": [...], "weathercode": [...] } }
    daily_block = data.get("daily", {})

    dates = daily_block.get("time", [])
    codes = daily_block.get("weathercode", [])

    if not dates or not codes:
        return []

    for date_str, w_code in zip(dates, codes):
        # Если код погоды значимый (например, дождь/снег/гроза обычно > 50)
        if w_code is not None:
            slug = _make_slug(f"code_{w_code}")
            unique_id = f"openmeteo_{date_str}_{slug}"

            tasks.append({
                "title": f"Weather Condition: {w_code}",
                "date": date_str,
                "type": "task",  # Тип должен совпадать с AllowedType из models/tasks.py
                "status": "todo",
                "source": "open-meteo",
                "meta": {
                    "source_id": unique_id,
                    "weather_code": w_code
                },
            })

    return tasks