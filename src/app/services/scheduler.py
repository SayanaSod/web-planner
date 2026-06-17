from __future__ import annotations

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from src.app.core.config import settings
from src.app.services.jobs import auto_import_task, cleanup_expired_tasks, check_reminders

logger = logging.getLogger("scheduler")

class TaskScheduler:
    """Планировщик фоновых задач."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def setup_tasks(self):
        if settings.AUTO_IMPORT_ENABLED:
            self.scheduler.add_job(auto_import_task, IntervalTrigger(seconds=5), id="auto_import", replace_existing=True)
        if settings.CLEANUP_ENABLED:
            self.scheduler.add_job(cleanup_expired_tasks, IntervalTrigger(hours=settings.CLEANUP_INTERVAL_HOURS), id="cleanup", replace_existing=True)
        if settings.REMINDERS_ENABLED:
            self.scheduler.add_job(check_reminders, IntervalTrigger(minutes=settings.REMINDER_CHECK_INTERVAL_MINUTES), id="reminders", replace_existing=True)

    def start(self):
        if settings.SCHEDULER_ENABLED:
            self.setup_tasks()
            self.scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

scheduler = TaskScheduler()
