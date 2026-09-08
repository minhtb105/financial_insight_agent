"""APScheduler weekly Sunday 02:00 Asia/Ho_Chi_Minh."""

from __future__ import annotations

import os
from zoneinfo import ZoneInfo

from infrastructure.observability import get_logger

logger = get_logger("rag.scheduler")

_scheduler = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    if os.getenv("ENABLE_RAG_SCHEDULER", "false").lower() not in ("1", "true", "yes"):
        logger.info("RAG scheduler disabled (ENABLE_RAG_SCHEDULER!=true)")
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        from .pipeline import run_full_refresh

        def job():
            logger.info("RAG weekly job start (CN 02:00 Asia/Ho_Chi_Minh)")
            try:
                res = run_full_refresh(force=False)
                logger.info("RAG weekly job done: %s", res)
            except Exception as e:
                logger.exception("RAG weekly job failed: %s", e)

        sched = BackgroundScheduler(timezone=ZoneInfo("Asia/Ho_Chi_Minh"))
        sched.add_job(job, CronTrigger(day_of_week="sun", hour=2, minute=0), id="rag_weekly", replace_existing=True)
        sched.start()
        _scheduler = sched
        logger.info("RAG scheduler started — weekly CN 02:00 Asia/Ho_Chi_Minh")
    except Exception as e:
        logger.warning("Failed to start RAG scheduler: %s", e)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
        _scheduler = None
