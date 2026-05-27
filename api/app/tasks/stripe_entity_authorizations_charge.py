"""Weekly Stripe charge task for entity dynamic authorizations."""

from __future__ import annotations

import datetime
import logging

from app.config import Config, get_config
from app.dependencies.services import ServiceContainer
from app.tasks import PeriodicTask

logger = logging.getLogger(__name__)


class StripeEntityAuthorizationChargeTask(PeriodicTask):
    def next_delay(self) -> float:
        config = get_config()
        return _seconds_until_next_weekly_run(
            now=datetime.datetime.now(),
            weekday=config.stripe_entity_charge_weekday,
            hour=config.stripe_entity_charge_hour,
            minute=config.stripe_entity_charge_minute,
        )

    def execute(self, container: ServiceContainer, config: Config) -> int:
        if not config.stripe_entity_charge_enabled:
            return 0
        return (
            container.stripe_authorization_service.run_weekly_entity_dynamic_charges()
        )


async def schedule_stripe_entity_authorization_charges() -> None:
    config = get_config()
    logger.info(
        "Stripe entity authorization charger started. weekday=%s time=%02d:%02d enabled=%s",
        config.stripe_entity_charge_weekday,
        config.stripe_entity_charge_hour,
        config.stripe_entity_charge_minute,
        config.stripe_entity_charge_enabled,
    )
    await StripeEntityAuthorizationChargeTask().schedule()


def _seconds_until_next_weekly_run(
    *,
    now: datetime.datetime,
    weekday: int,
    hour: int,
    minute: int,
) -> float:
    weekday = max(0, min(6, int(weekday)))
    hour = max(0, min(23, int(hour)))
    minute = max(0, min(59, int(minute)))

    days_ahead = (weekday - now.weekday()) % 7
    target = datetime.datetime.combine(
        now.date() + datetime.timedelta(days=days_ahead),
        datetime.time(hour, minute),
    )
    if target <= now:
        target += datetime.timedelta(weeks=1)
    return (target - now).total_seconds()
