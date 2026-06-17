from __future__ import annotations

import re
from typing import Any, Dict, List, Union

from fastapi import HTTPException, status
from httpx import AsyncClient, HTTPStatusError, TimeoutException


class NagerImporter:
    """Адаптер для API Nager.at."""

    _API_ENDPOINT = "https://date.nager.at/api/v3/PublicHolidays"
    _REGEX_NOT_ALPHANUM = re.compile(r"[^a-z0-9]+")
    _REGEX_UNDERSCORES = re.compile(r"_+")

    def __init__(self, client: AsyncClient):
        self.client = client

    async def fetch_raw(self, year: int, country: str, request_id: str = None) -> Union[Dict, List]:
        target_url = f"{self._API_ENDPOINT}/{year}/{country}"

        try:
            resp = await self.client.get(target_url)
            resp.raise_for_status()
            return resp.json()
        except (HTTPStatusError, TimeoutException):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Nager service is unreachable"
            )

    def _generate_slug(self, text: str, limit: int = 40) -> str:
        processed = text.lower()
        processed = self._REGEX_NOT_ALPHANUM.sub("_", processed)
        processed = self._REGEX_UNDERSCORES.sub("_", processed).strip("_")

        if len(processed) > limit:
            processed = processed[:limit].rstrip("_")

        return processed if processed else "unknown"

    def _parse_entry(self, entry: Dict[str, Any], country_iso: str) -> Dict[str, Any]:
        raw_name = entry.get("localName") or entry.get("name")
        clean_title = str(raw_name).strip() if raw_name else "Holiday"
        clean_date = str(entry.get("date", ""))[:10]
        slug = self._generate_slug(clean_title)
        unique_source_id = f"nager_{country_iso}_{clean_date}_{slug}"

        return {
            "title": clean_title,
            "date": clean_date,
            "type": "holiday",
            "status": "todo",
            "source": "nager",
            "meta": {"source_id": unique_source_id},
        }

    def normalize(self, raw_data: Union[Dict, List], **kwargs) -> List[Dict[str, Any]]:
        collection = []
        items = raw_data if isinstance(raw_data, list) else [raw_data]
        for item in items:
            if not isinstance(item, dict):
                continue
            iso_code = item.get("countryCode", "XX")
            collection.append(self._parse_entry(item, iso_code))
        return collection
