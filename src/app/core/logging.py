import json
import logging
import logging.handlers
import queue
import re
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.app.core.config import settings

request_id_var: ContextVar[str] = ContextVar("request_id", default="system")
user_id_var: ContextVar[str] = ContextVar("user_id", default="system")


class SecretSanitizer(logging.Filter):
    """Фильтр для скрытия чувствительных данных."""

    def init(self):
        super().init()
        self._mask = r'\1[PROTECTED]\3'
        self._patterns = [
            (r'("password":\s*")([^"]*)(")', self._mask),
            (r'("token":\s*")([^"]*)(")', self._mask),
            (r'("api_key":\s*")([^"]*)(")', self._mask),
            (r'("authorization":\s*"Bearer\s)([^"]*)(")', self._mask),
            (r'(password=)([^&\s]+)', r'\1[PROTECTED]'),
            (r'(token=)([^&\s]+)', r'\1[PROTECTED]'),
            (r'(api_key=)([^&\s]+)', r'\1[PROTECTED]'),
        ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._cleanse_text(record.msg)
        return True

    def _cleanse_text(self, content: str) -> str:
        for regex, replacement in self._patterns:
            content = re.sub(regex, replacement, content, flags=re.IGNORECASE)
        return content


class JsonLogFormatter(logging.Formatter):
    """Форматтер для вывода логов в JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = self._construct_payload(record)
        return json.dumps(payload, ensure_ascii=False)

    def _construct_payload(self, record: logging.LogRecord) -> Dict[str, Any]:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger_name": record.name,
            "message": record.getMessage(),
            "req_id": request_id_var.get(),
            "uid": user_id_var.get(),
        }

        self._inject_http_info(payload, record)

        self._inject_error_info(payload, record)

        return payload

    def _inject_http_info(self, data: Dict[str, Any], record: logging.LogRecord):
        target_attrs = ['method', 'path', 'status', 'duration_ms']
        for attr in target_attrs:
            val = getattr(record, attr, None)
            if val is not None:
                data[attr] = val

    def _inject_error_info(self, data: Dict[str, Any], record: logging.LogRecord):
        if not record.exc_info:
            return

        exc_type, _, _ = record.exc_info
        if exc_type:
            data["error_type"] = exc_type.name

        if record.levelno >= logging.ERROR:
            data["stack_trace"] = self.formatException(record.exc_info)


# Глобальные переменные для работы асинхронной очереди
_ASYNC_QUEUE: Optional[queue.Queue] = None
_LOG_LISTENER: Optional[logging.handlers.QueueListener] = None


def setup_logging_system():
    """Настройка системы логирования."""
    global _ASYNC_QUEUE, _LOG_LISTENER

    _ASYNC_QUEUE = queue.Queue(-1)

    # Настройка корневого логгера
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL.upper())

    # Очистка старых хендлеров
    while root.handlers:
        root.removeHandler(root.handlers[0])

    # QueueHandler для неблокирующей записи
    q_handler = logging.handlers.QueueHandler(_ASYNC_QUEUE)
    root.addHandler(q_handler)

    outputs = _build_handlers()
    _LOG_LISTENER = logging.handlers.QueueListener(
        _ASYNC_QUEUE,
        *outputs,
        respect_handler_level=True
    )
    _LOG_LISTENER.start()


def _build_handlers() -> List[logging.Handler]:
    log_handlers = []

    # Выбор форматтера
    if settings.LOG_FORMAT == "json":
        log_fmt = JsonLogFormatter()
    else:
        log_fmt = logging.Formatter(
            fmt='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    sanitizer = SecretSanitizer()

    # Консольный вывод
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(log_fmt)
    stdout_handler.addFilter(sanitizer)
    log_handlers.append(stdout_handler)

    # Файловый вывод
    if settings.LOG_FILE_PATH:
        file_out = logging.handlers.RotatingFileHandler(
            filename=settings.LOG_FILE_PATH,
            maxBytes=settings.LOG_ROTATE_MB * 1024 * 1024,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_out.setFormatter(log_fmt)
        file_out.addFilter(sanitizer)
        log_handlers.append(file_out)

    return log_handlers


def teardown_logging():
    """Остановка слушателя логов."""
    global _LOG_LISTENER

    if _LOG_LISTENER:
        _LOG_LISTENER.stop()
        _LOG_LISTENER = None


def fetch_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)