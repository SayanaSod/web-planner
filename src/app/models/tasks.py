from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, constr, Field

AllowedType = Literal["task", "meeting", "deadline", "holiday", "news", "open-meteo", "spaceflight"]
AllowedStatus = Literal["todo", "done"]


class TaskCreate(BaseModel):
    title: constr(min_length=1, max_length=200)
    date: date
    type: AllowedType = "task"


class TaskUpdate(BaseModel):
    title: Optional[constr(min_length=1, max_length=200)] = None
    date: Optional[date] = None
    type: Optional[AllowedType] = None
    status: Optional[AllowedStatus] = None


class TaskOut(BaseModel):
    id: str
    title: str
    date: date
    type: AllowedType
    status: AllowedStatus
    source: Literal["local", "nager", "open-meteo", "spaceflight"] = "local"

class ImportTaskOut(BaseModel):
    id: str
    title: str
    date: date
    type: AllowedType
    status: AllowedStatus
    source: str

class ImportResult(BaseModel):
    imported: int
    skipped: int
    details: list[ImportTaskOut]
    errors: list[str] = []

class WeatherImportRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    days: int = Field(default=3, ge=1, le=7)
    hot_from: float = 25.0
    cold_to: float = 0.0

class NewsImportRequest(BaseModel):
    q: constr(min_length=1)
    from_: Optional[date] = Field(default=None, alias="from")
    limit: int = Field(default=20, ge=1, le=50)