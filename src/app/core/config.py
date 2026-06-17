from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Optional


def fetch_env(key: str, default: str) -> str:
    """Обертка для получения переменных окружения."""
    return os.getenv(key, default)


@dataclass(frozen=True)
class AppConfig:
    # Основные настройки приложения
    APP_NAME: str = fetch_env("APP_NAME", "studplanner")
    APP_ENV: str = fetch_env("APP_ENV", "dev")

    # Настройки путей
    ROOT_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent

    # База данных (MongoDB)
    MONGO_DSN: str = fetch_env("MONGO_DSN", "mongodb://localhost:27017")
    MONGO_DB: str = fetch_env("MONGO_DB", "planner")
    MONGO_POOL_SIZE: int = int(fetch_env("MONGO_POOL_SIZE", "10"))

    # Кеширование (Redis)
    REDIS_URL: str = fetch_env("REDIS_URL", "redis://localhost:6379/0")
    REDIS_POOL_SIZE: int = int(fetch_env("REDIS_POOL_SIZE", "10"))
    CACHE_ENABLED: bool = fetch_env("CACHE_ENABLED", "true").lower() == "true"

    # TTL настройки (в секундах)
    CACHE_TTL_SECONDS: int = int(fetch_env("CACHE_TTL_SECONDS", "900"))
    CACHE_MAX_BYTES: int = int(fetch_env("CACHE_MAX_BYTES", "1048576"))
    CACHE_TTL_PREVIEW: int = int(fetch_env("CACHE_TTL_PREVIEW", "300"))
    # Специфичный TTL для задач
    CACHE_TTL_TASKS_SECONDS: int = int(fetch_env("CACHE_TTL_TASKS_SECONDS", "900"))
    CACHE_TTL_TASKS: Optional[int] = None if not fetch_env("CACHE_TTL_TASKS", "") else int(
        fetch_env("CACHE_TTL_TASKS", "0"))

    # Безопасность и Auth
    USERNAME: str = fetch_env("USERNAME", "admin")
    PASSWORD: str = fetch_env("PASSWORD", "secret")
    JWT_SECRET: str = fetch_env("JWT_SECRET", "dev-secret-change-me-32-characters-minimum")
    JWT_ALG: str = fetch_env("JWT_ALG", "HS256")
    JWT_EXPIRE_MINUTES: int = int(fetch_env("JWT_EXPIRE_MINUTES", "60"))

    # Логирование
    LOG_LEVEL: str = fetch_env("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = fetch_env("LOG_FORMAT", "json")
    LOG_FILE_PATH: str = fetch_env("LOG_FILE_PATH", "logs/app.log")
    LOG_ROTATE_MB: int = int(fetch_env("LOG_ROTATE_MB", "10"))
    LOG_BACKUP_COUNT: int = int(fetch_env("LOG_BACKUP_COUNT", "5"))

    # HTTP клиент
    HTTP_TIMEOUT: int = int(fetch_env("HTTP_TIMEOUT", "20"))
    HTTP_MAX_CONNECTIONS: int = int(fetch_env("HTTP_MAX_CONNECTIONS", "10"))

    # Фоновые задачи и планировщик
    SCHEDULER_ENABLED: bool = fetch_env("SCHEDULER_ENABLED", "true").lower() == "true"

    AUTO_IMPORT_ENABLED: bool = fetch_env("AUTO_IMPORT_ENABLED", "true").lower() == "true"
    AUTO_IMPORT_INTERVAL_MINUTES: int = int(fetch_env("AUTO_IMPORT_INTERVAL_MINUTES", "1"))

    CLEANUP_ENABLED: bool = fetch_env("CLEANUP_ENABLED", "true").lower() == "true"
    CLEANUP_INTERVAL_HOURS: int = int(fetch_env("CLEANUP_INTERVAL_HOURS", "24"))
    CLEANUP_EXPIRED_DAYS: int = int(fetch_env("CLEANUP_EXPIRED_DAYS", "90"))

    REMINDERS_ENABLED: bool = fetch_env("REMINDERS_ENABLED", "true").lower() == "true"
    REMINDER_CHECK_INTERVAL_MINUTES: int = int(fetch_env("REMINDER_CHECK_INTERVAL_MINUTES", "15"))
    REMINDER_BEFORE_MINUTES: int = int(fetch_env("REMINDER_BEFORE_MINUTES", "30"))

    @property
    def TEMPLATES_DIR(self) -> Path:
        return self.ROOT_DIR / "src" / "app" / "templates"

    @property
    def access_token_timedelta(self) -> timedelta:
        return timedelta(minutes=self.JWT_EXPIRE_MINUTES)


settings = AppConfig()