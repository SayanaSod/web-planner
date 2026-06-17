from __future__ import annotations

from typing import Any, Dict, List, Set
from fastapi import HTTPException, status
from httpx import AsyncClient, HTTPStatusError, TimeoutException

class WeatherImporter:
    _API_URL = "https://api.open-meteo.com/v1/forecast"
    _BAD_WEATHER_CODES: Set[int] = {51, 52, 53, 54, 55, 56, 57, 61, 62, 63, 64, 65, 66, 67, 80, 81, 82}

    def __init__(self, client: AsyncClient):
        self.client = client

    async def fetch_raw(self, lat: float, lon: float, days: int = 3, request_id: str = None) -> Dict[str, Any]:
        query_params = {
            "latitude": lat, "longitude": lon, "forecast_days": days,
            "daily": "weathercode,temperature_2m_max,temperature_2m_min",
            "timezone": "auto"
        }
        try:
            resp = await self.client.get(self._API_URL, params=query_params)
            resp.raise_for_status()
            return resp.json()
        except (HTTPStatusError, TimeoutException):
            raise HTTPException(status_code=502, detail="Weather service unavailable")

    def normalize(self, raw: Dict[str, Any], lat: float, lon: float, hot_from: float = 25.0, cold_to: float = 0.0, **kwargs) -> List[Dict[str, Any]]:
        result_tasks = []
        daily_data = raw.get("daily", {})
        if not daily_data: return []

        iterator = zip(daily_data.get("time", []), daily_data.get("weathercode", []), daily_data.get("temperature_2m_max", []), daily_data.get("temperature_2m_min", []))

        for date_iso, code, max_temp, min_temp in iterator:
            if code in self._BAD_WEATHER_CODES:
                result_tasks.append(self._make_task("Взять зонт", date_iso, f"openmeteo_{lat}_{lon}_{date_iso}_rain"))
            if max_temp >= hot_from:
                result_tasks.append(self._make_task("Пить больше воды", date_iso, f"openmeteo_{lat}_{lon}_{date_iso}_hot"))
            if min_temp <= cold_to:
                result_tasks.append(self._make_task("Тёплая одежда", date_iso, f"openmeteo_{lat}_{lon}_{date_iso}_cold"))
        return result_tasks

    def _make_task(self, title: str, date: str, source_id: str) -> dict:
        return {"title": title, "date": date, "type": "task", "status": "todo", "source": "open-meteo", "meta": {"source_id": source_id}}
