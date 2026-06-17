from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime
from typing import Annotated, Optional

from bson.errors import InvalidId
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pymongo.errors import DuplicateKeyError

from src.app.cache.redis import RedisCache
from src.app.core.config import settings
from src.app.core.deps import get_cache_service, get_current_user
from src.app.db.mongo import get_tasks_repo
from src.app.db.repositories import TasksRepository
from src.app.models.tasks import TaskCreate, TaskOut, TaskUpdate

tasks_router = APIRouter()


@tasks_router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_new_task(
        payload: TaskCreate,
        repo: TasksRepository = Depends(get_tasks_repo),
        auth_user=Depends(get_current_user),
):
    if not payload.task_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task type is required"
        )

    task_data = payload.dict(by_alias=True)
    task_data["date"] = payload.date.isoformat()

    try:
        new_task = await repo.create(auth_user["id"], task_data)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task already registered"
        )

    return TaskOut(
        id=new_task["id"],
        title=new_task["title"],
        date=new_task["date"],
        type=new_task["type"],
        status=new_task["status"],
        source=new_task["source"]
    )


@tasks_router.get("", response_model=list[TaskOut])
async def fetch_tasks_list(
        raw_req: Request,
        repo: TasksRepository = Depends(get_tasks_repo),
        cache_service: RedisCache = Depends(get_cache_service),
        auth_user=Depends(get_current_user),
        target_date: Optional[date_cls] = Query(default=None, alias="date"),
        task_type: Optional[str] = Query(default=None, alias="type"),
        search_q: Optional[str] = Query(default=None, alias="q"),
):
    filter_params = {
        "date": str(target_date) if target_date else None,
        "type": task_type,
        "q": search_q
    }

    should_use_cache = raw_req.headers.get("Cache-Control") != "no-cache"
    cache_key = ""

    if should_use_cache:
        cache_key = cache_service._make_key(
            auth_user["id"], "GET", "tasks_list", filter_params
        )
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            return cached_data

    if not task_type:
        results = await repo.list(
            user_id=auth_user["id"],
            date_eq=target_date,
            q=search_q
        )
    else:
        results = await repo.list(
            user_id=auth_user["id"],
            date_eq=target_date,
            type_eq=task_type,
            q=search_q
        )

    response_items = [
        TaskOut(
            id=item["id"],
            title=item["title"],
            date=item["date"],
            type=item["type"],
            status=item["status"],
            source=item["source"]
        ) for item in results
    ]

    if should_use_cache and response_items:
        dumped_data = [item.dict(by_alias=True) for item in response_items]
        await cache_service.set(
            cache_key,
            dumped_data,
            settings.CACHE_TTL_TASKS_SECONDS
        )

    return response_items


@tasks_router.get("/{task_id}", response_model=TaskOut)
async def retrieve_single_task(
        task_id: str,
        repo: TasksRepository = Depends(get_tasks_repo),
        auth_user=Depends(get_current_user)
):
    try:
        found_task = await repo.get(user_id=auth_user["id"], task_id=task_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    if not found_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return TaskOut(
        id=found_task["id"],
        title=found_task["title"],
        date=found_task["date"],
        type=found_task["type"],
        status=found_task["status"],
        source=found_task["source"]
    )


@tasks_router.patch("/{task_id}", response_model=TaskOut)
async def modify_existing_task(
        task_id: str,
        update_data: TaskUpdate,
        repo: TasksRepository = Depends(get_tasks_repo),
        auth_user=Depends(get_current_user),
):
    changes = update_data.dict(exclude_unset=True, by_alias=True)

    if "date" in changes and hasattr(changes["date"], "isoformat"):
        changes["date"] = changes["date"].isoformat()

    updated_task = await repo.update(
        user_id=auth_user["id"],
        task_id=task_id,
        patch=changes
    )

    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return TaskOut(
        id=updated_task["id"],
        title=updated_task["title"],
        date=updated_task["date"],
        type=updated_task["type"],
        status=updated_task["status"],
        source=updated_task["source"]
    )


@tasks_router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_task(
        task_id: str,
        repo: TasksRepository = Depends(get_tasks_repo),
        auth_user=Depends(get_current_user)
):
    is_deleted = await repo.delete(user_id=auth_user["id"], task_id=task_id)

    if not is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return None
