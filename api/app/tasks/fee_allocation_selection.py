"""Daily random fallback for inactive directed fee allocation selections."""

import datetime

from app.config import Config
from app.dependencies.services import ServiceContainer
from app.tasks import PeriodicTask


class FeeAllocationSelectionTask(PeriodicTask):
    def next_delay(self) -> float:
        now = datetime.datetime.now()
        target = datetime.datetime.combine(now.date(), datetime.time(12, 30))
        if now >= target:
            target += datetime.timedelta(days=1)
        return (target - now).total_seconds()

    def execute(self, container: ServiceContainer, config: Config) -> int:
        return container.fee_allocation_service.auto_select_expired_allocations()


async def schedule_fee_allocation_selection() -> None:
    await FeeAllocationSelectionTask().schedule()
