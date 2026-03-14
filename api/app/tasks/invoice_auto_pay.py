"""Invoice auto-pay background task."""

from __future__ import annotations

import datetime

from app.config import Config
from app.dependencies.services import ServiceContainer
from app.tasks import PeriodicTask


class InvoiceAutoPayTask(PeriodicTask):
    def next_delay(self) -> float:
        now = datetime.datetime.now()
        target = datetime.datetime.combine(now.date(), datetime.time(12, 0))
        if now >= target:
            target += datetime.timedelta(days=1)
        return (target - now).total_seconds()

    def execute(self, container: ServiceContainer, config: Config) -> int:
        return container.invoice_service.auto_pay_oldest_invoices()


async def schedule_invoice_auto_pay() -> None:
    await InvoiceAutoPayTask().schedule()
