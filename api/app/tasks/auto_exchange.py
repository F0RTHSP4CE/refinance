"""Auto-balance currency exchange background task.

Runs before invoice auto-pay (at 11:58) and exchanges available positive-balance
currencies to cover negative-balance currencies for all eligible entities
(residents, members, ex-residents).
"""

from __future__ import annotations

import datetime

from app.config import Config
from app.dependencies.services import ServiceContainer
from app.tasks import PeriodicTask


class AutoExchangeTask(PeriodicTask):
    def next_delay(self) -> float:
        now = datetime.datetime.now()
        target = datetime.datetime.combine(now.date(), datetime.time(11, 58))
        if now >= target:
            target += datetime.timedelta(days=1)
        return (target - now).total_seconds()

    def execute(self, container: ServiceContainer, config: Config) -> int:
        actor = container.entity_service.get(1)  # f0 / hackerspace entity
        result = container.currency_exchange_service.run_auto_balance_for_all(actor)
        return sum(len(r.receipts) for r in result.results)


async def schedule_auto_exchange() -> None:
    await AutoExchangeTask().schedule()
