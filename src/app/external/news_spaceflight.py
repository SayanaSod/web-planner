from __future__ import annotations

import hashlib
from datetime import date
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from httpx import AsyncClient, HTTPStatusError, TimeoutException

class NewsImporter:
    _ENDPOINT = "https://api.spaceflightnewsapi.net/v4/articles"

    def __init__(self, client: AsyncClient):
        self.client = client

    async def fetch_raw(self, q: str, from_date: Optional[date] = None, limit: int = 20, request_id: Optional[str] = None) -> Dict[str, Any]:
        query_params = {"search": q, "limit": limit, "format": "json"}
        if from_date: query_params["published_at_gte"] = from_date.isoformat()

        try:
            resp = await self.client.get(self._ENDPOINT, params=query_params)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            raise HTTPException(status_code=502, detail="News service error")

    def normalize(self, raw_data: Dict[str, Any], **kwargs) -> List[Dict[str, Any]]:
        clean_list = []
        for item in raw_data.get("results", []):
            origin_id = item.get("id")
            unique_key = f"spaceflight_{origin_id}" if origin_id else f"spaceflight_{hashlib.md5(item.get('url', '').encode()).hexdigest()[:8]}"
            clean_list.append({
                "title": item.get("title", "No Title"),
                "date": str(item.get("published_at", ""))[:10],
                "type": "news", "status": "todo", "source": "spaceflight",
                "meta": {"source_id": unique_key, "source_url": item.get("url", "")}
            })
        return clean_list
