"""Monthly Stripe charge task for guest static authorizations."""

from __future__ import annotations

import calendar
import datetime
import logging

from app.config import Config, get_config
from app.dependencies.services import ServiceContainer
from app.tasks import PeriodicTask

logger = logging.getLogger(__name__)


class StripeGuestMonthlyChargeTask(PeriodicTask):
    def next_delay(self) -> float:
        config = get_config()
        return _seconds_until_next_monthly_run(
            now=datetime.datetime.now(),
            day=config.stripe_guest_charge_day,
            hour=config.stripe_guest_charge_hour,
            minute=config.stripe_guest_charge_minute,
        )

    def execute(self, container: ServiceContainer, config: Config) -> int:
        if not config.stripe_guest_charge_enabled:
            return 0
        return container.stripe_authorization_service.run_monthly_guest_static_charges()


async def schedule_stripe_guest_monthly_charges() -> None:
    config = get_config()
    logger.info(
        "Stripe guest monthly charger started. day=%s time=%02d:%02d enabled=%s",
        config.stripe_guest_charge_day,
        config.stripe_guest_charge_hour,
        config.stripe_guest_charge_minute,
        config.stripe_guest_charge_enabled,
    )
    await StripeGuestMonthlyChargeTask().schedule()


def _seconds_until_next_monthly_run(
    *,
    now: datetime.datetime,
    day: int,
    hour: int,
    minute: int,
) -> float:
    day = max(1, min(31, int(day)))
    hour = max(0, min(23, int(hour)))
    minute = max(0, min(59, int(minute)))

    year = now.year
    month = now.month

    def _mk_target(y: int, m: int) -> datetime.datetime:
        last_day = calendar.monthrange(y, m)[1]
        actual_day = min(day, last_day)
        return datetime.datetime(y, m, actual_day, hour, minute)

    target = _mk_target(year, month)
    if target <= now:
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        target = _mk_target(year, month)

    return (target - now).total_seconds()
