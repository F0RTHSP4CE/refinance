"""Stripe payments polling task."""

from __future__ import annotations

import logging

from app.config import Config, get_config
from app.dependencies.services import ServiceContainer
from app.tasks import PeriodicTask

logger = logging.getLogger(__name__)


class StripePollTask(PeriodicTask):
    def next_delay(self) -> float:
        return max(int(get_config().stripe_poll_interval_seconds or 60), 10)

    def execute(self, container: ServiceContainer, config: Config) -> int:
        return container.stripe_deposit_provider_service.poll_pending_deposits()


async def schedule_stripe_poll() -> None:
    logger.info(
        "Stripe poller started. interval=%s",
        max(int(get_config().stripe_poll_interval_seconds or 60), 10),
    )
    await StripePollTask().schedule()
