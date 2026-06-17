import time
import uuid
from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.app.core.config import settings
from src.app.core.logging import request_id_var


class SystemTraceMiddleware(BaseHTTPMiddleware):
    """
    Middleware для трейсинга запросов и замера производительности.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 1. Получение или генерация ID запроса
        trace_id = request.headers.get("X-Request-ID")
        if not trace_id:
            trace_id = str(uuid.uuid4())

        request.state.request_id = trace_id

        token = request_id_var.set(trace_id)

        # 2. Логика управления кешем (исправление ошибки immutability)
        if not settings.CACHE_ENABLED and "cache-control" not in request.headers:
            header_mutator = MutableHeaders(scope=request.scope)
            header_mutator["Cache-Control"] = "no-cache"

        # 3. Замер времени выполнения
        start_ts = time.perf_counter()

        try:
            response = await call_next(request)
        finally:
            # Очистка контекста логгера после запроса
            request_id_var.reset(token)

        # 4. Подсчет времени и добавление заголовков ответа
        duration_ms = (time.perf_counter() - start_ts) * 1000

        response.headers["X-Request-ID"] = trace_id
        response.headers["X-Execution-Time"] = f"{duration_ms:.2f}"

        return response