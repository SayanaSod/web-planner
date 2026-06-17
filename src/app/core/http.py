from typing import Optional

import httpx

from src.app.core.config import settings


def create_http_client(trace_id: Optional[str] = None) -> httpx.AsyncClient:
    """
    Фабрика для создания асинхронного HTTP-клиента.
    Использует глобальные настройки таймаутов.
    """
    # Базовые заголовки
    session_headers = {
        "Accept": "application/json",
        # Можно добавить User-Agent, чтобы отличаться от оригинала
        "User-Agent": settings.APP_NAME
    }

    # Если передан ID запроса, добавляем его в заголовки для трейсинга
    if trace_id:
        session_headers["X-Request-ID"] = trace_id

    # Настройка пула соединений
    conn_limits = httpx.Limits(
        max_connections=settings.HTTP_MAX_CONNECTIONS,
        max_keepalive_connections=5
    )

    return httpx.AsyncClient(
        timeout=settings.HTTP_TIMEOUT,
        limits=conn_limits,
        headers=session_headers
    )