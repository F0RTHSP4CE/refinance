"""Invoice auto-pay background task."""

from __future__ import annotations

import asyncio
import datetime
import logging

from app.config import get_config
from app.db import DatabaseConnection
from app.dependencies.services import ServiceContainer
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


def run_invoice_auto_pay() -> int:
    config = get_config()
    db_conn = DatabaseConnection(config)
    session = db_conn.get_session()
    with UnitOfWork(session) as uow:
        container = ServiceContainer(uow, config)
        invoice_service = container.invoice_service
        paid_count = invoice_service.auto_pay_oldest_invoices()
    return paid_count


def _seconds_until_next_noon(now: datetime.datetime) -> float:
    target = datetime.datetime.combine(now.date(), datetime.time(12, 00))
    if now >= target:
        target = target + datetime.timedelta(days=1)
    return (target - now).total_seconds()


async def schedule_invoice_auto_pay() -> None:
    while True:
        delay = _seconds_until_next_noon(datetime.datetime.now())
        await asyncio.sleep(delay)
        try:
            paid_count = await asyncio.to_thread(run_invoice_auto_pay)
            logger.info("Invoice auto-pay completed. paid=%s", paid_count)
        except Exception:
            logger.exception("Invoice auto-pay failed %s", exc_info=True)
