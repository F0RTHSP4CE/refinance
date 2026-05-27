"""Auto-balance currency exchange background task.

Runs daily at 11:55, before Stripe entity charging (12:00 Monday) and
invoice auto-pay (12:10), so balances are settled before those tasks fire.
"""

from __future__ import annotations

import datetime

from app.config import Config
from app.dependencies.services import ServiceContainer
from app.tasks import PeriodicTask


class AutoExchangeTask(PeriodicTask):
    def next_delay(self) -> float:
        now = datetime.datetime.now()
        target = datetime.datetime.combine(now.date(), datetime.time(11, 55))
        if now >= target:
            target += datetime.timedelta(days=1)
        return (target - now).total_seconds()

    def execute(self, container: ServiceContainer, config: Config) -> int:
        actor = container.entity_service.get(1)  # f0 / hackerspace entity
        result = container.currency_exchange_service.run_auto_balance_for_all(actor)
        return sum(len(r.receipts) for r in result.results)


async def schedule_auto_exchange() -> None:
    await AutoExchangeTask().schedule()
