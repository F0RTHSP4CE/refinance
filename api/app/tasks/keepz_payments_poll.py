"""Keepz payments polling task."""

from __future__ import annotations

import asyncio
import logging

from app.config import get_config
from app.db import DatabaseConnection
from app.dependencies.services import ServiceContainer
from app.errors.keepz import KeepzAuthRequired
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


def run_keepz_poll() -> int:
    config = get_config()
    db_conn = DatabaseConnection(config)
    session = db_conn.get_session()
    with UnitOfWork(session) as uow:
        container = ServiceContainer(uow, config)
        service = container.keepz_deposit_provider_service
        return service.poll_pending_deposits()


async def schedule_keepz_poll() -> None:
    config = get_config()
    interval = max(int(config.keepz_poll_interval_seconds or 60), 10)
    logger.info("Keepz poller started. interval=%s", interval)
    while True:
        await asyncio.sleep(interval)
        try:
            processed = await asyncio.to_thread(run_keepz_poll)
            if processed:
                logger.info("Keepz poll completed. processed=%s", processed)
        except KeepzAuthRequired:
            logger.info("Keepz poll skipped: authentication required")
        except Exception:
            logger.exception("Keepz poll failed", exc_info=True)
