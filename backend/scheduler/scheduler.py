"""
Scheduler — APScheduler wired into FastAPI's lifespan.

Design:
  - One scheduler instance, started on app startup, stopped on shutdown.
  - Jobs are stored in PostgreSQL (not in memory) so restarts don't lose schedules.
  - Each active source gets a job added automatically on startup.
  - The /api/v1/scrape endpoint can also trigger jobs manually.

APScheduler job store uses SQLAlchemy (sync) — it has its own connection separate
from the async session factory used by the API routes.
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

logger = logging.getLogger(__name__)


def create_scheduler() -> AsyncIOScheduler:
    jobstores = {
        "default": SQLAlchemyJobStore(
            url="sqlite:///scheduler_jobs.db",
            tablename="apscheduler_jobs",
        ),
    }
    executors = {
        "default": AsyncIOExecutor(),
    }
    job_defaults = {
        "coalesce": True,
        "max_instances": 1,
        "misfire_grace_time": 60 * 10,
    }

    scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
    )

    def on_job_executed(event):
        logger.info(f"Job '{event.job_id}' completed at {datetime.now().isoformat()}")

    def on_job_error(event):
        logger.error(f"Job '{event.job_id}' raised {event.exception!r}")

    scheduler.add_listener(on_job_executed, EVENT_JOB_EXECUTED)
    scheduler.add_listener(on_job_error, EVENT_JOB_ERROR)

    return scheduler


scheduler = create_scheduler()