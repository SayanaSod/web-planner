from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from requests.exceptions import ConnectionError

from src.app.core.deps import (
    get_current_user,
    get_import_service,
    get_nager_importer,
    get_news_importer,
    get_weather_importer,
)
from src.app.external.nager import NagerImporter
from src.app.external.news_spaceflight import NewsImporter
from src.app.external.weather_open_meteo import WeatherImporter
from src.app.models.tasks import ImportResult, NewsImportRequest, WeatherImportRequest

importers_router = APIRouter()


@importers_router.post("/nager", response_model=ImportResult)
async def sync_nager_data(
    raw_req: Request,
    iso_code: Annotated[str, Query(alias="country", min_length=2, max_length=2, description="ISO-2")],
    target_year: Annotated[int, Query(alias="year", ge=1900, le=2100)],
    client: NagerImporter = Depends(get_nager_importer),
    auth_user=Depends(get_current_user),
    worker=Depends(get_import_service),
):
    try:
        result = await worker(
            client,
            auth_user["id"],
            fetch_kwargs={
                "country": iso_code,
                "year": target_year,
                "request_id": raw_req.state.request_id,
            },
            normalize_kwargs={
                "country": iso_code
            },
        )
    except ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="External service is unavailable"
        )

    return ImportResult(
        imported=result.imported,
        skipped=result.skipped,
        details=result.details
    )


@importers_router.post("/weather", response_model=ImportResult)
async def sync_weather_data(
    raw_req: Request,
    payload: WeatherImportRequest,
    client: WeatherImporter = Depends(get_weather_importer),
    auth_user=Depends(get_current_user),
    worker=Depends(get_import_service),
):
    try:
        result = await worker(
            client,
            auth_user["id"],
            fetch_kwargs={
                "lat": payload.lat,
                "lon": payload.lon,
                "days": payload.days,
                "request_id": raw_req.state.request_id,
            },
            normalize_kwargs={
                "lat": payload.lat,
                "lon": payload.lon,
                "hot_from": payload.hot_from,
                "cold_to": payload.cold_to,
            },
        )
    except ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="External service is unavailable"
        )

    return ImportResult(
        imported=result.imported,
        skipped=result.skipped,
        details=result.details
    )


@importers_router.post("/news", response_model=ImportResult)
async def sync_news_data(
    payload: NewsImportRequest,
    client: NewsImporter = Depends(get_news_importer),
    auth_user=Depends(get_current_user),
    worker=Depends(get_import_service),
):
    try:
        result = await worker(
            client,
            auth_user["id"],
            fetch_kwargs={
                "q": payload.q,
                "from_date": payload.from_,
                "limit": payload.limit,
            },
        )
    except ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="External service is unavailable"
        )

    return ImportResult(
        imported=result.imported,
        skipped=result.skipped,
        details=result.details
    )