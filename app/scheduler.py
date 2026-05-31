"""APScheduler 로 주기적으로 모니터링 엔진을 실행한다.

BackgroundScheduler(스레드 기반)를 써서 동기 SQLAlchemy 코드와 자연스럽게 맞춘다.
잡 실행마다 새 DB 세션을 연다.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import SessionLocal
from app.services.monitor import check_all_active_watches

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _job() -> None:
    db = SessionLocal()
    try:
        check_all_active_watches(db)
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _job,
        trigger="interval",
        minutes=settings.check_interval_minutes,
        id="price_check",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("스케줄러 시작 (주기: %d분)", settings.check_interval_minutes)
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("스케줄러 종료")
    _scheduler = None
