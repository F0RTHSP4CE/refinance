"""Auto-balance currency exchange background task.

Runs before invoice auto-pay (at 11:58) and exchanges available positive-balance
currencies to cover negative-balance currencies for all eligible entities
(residents, members, ex-residents).
"""

from __future__ import annotations

import asyncio
import datetime
import logging

from app.config import get_config
from app.db import DatabaseConnection
from app.dependencies.services import ServiceContainer
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


def run_auto_exchange() -> int:
    """Execute auto-balance for all eligible entities. Returns the number of exchanges made."""
    config = get_config()
    db_conn = DatabaseConnection(config)
    session = db_conn.get_session()
    with UnitOfWork(session) as uow:
        container = ServiceContainer(uow, config)
        actor = container.entity_service.get(1)  # f0 / hackerspace entity
        result = container.currency_exchange_service.run_auto_balance_for_all(actor)
    total = sum(len(r.receipts) for r in result.results)
    return total


def _seconds_until_next_1158(now: datetime.datetime) -> float:
    target = datetime.datetime.combine(now.date(), datetime.time(11, 58))
    if now >= target:
        target = target + datetime.timedelta(days=1)
    return (target - now).total_seconds()


async def schedule_auto_exchange() -> None:
    while True:
        delay = _seconds_until_next_1158(datetime.datetime.now())
        await asyncio.sleep(delay)
        try:
            exchange_count = await asyncio.to_thread(run_auto_exchange)
            logger.info("Auto-exchange completed. exchanges=%s", exchange_count)
        except Exception:
            logger.exception("Auto-exchange failed", exc_info=True)
