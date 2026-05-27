"""Stripe payments polling task."""

from __future__ import annotations

import asyncio
import logging

from app.config import Config, get_config
from app.dependencies.services import ServiceContainer
from app.tasks import PeriodicTask

logger = logging.getLogger(__name__)


class StripePollTask(PeriodicTask):
    def next_delay(self) -> float:
        raise NotImplementedError  # schedule() is fully overridden

    def execute(self, container: ServiceContainer, config: Config) -> int:
        return container.stripe_deposit_provider_service.poll_pending_deposits()

    async def schedule(self) -> None:
        config = get_config()
        interval = max(int(config.stripe_poll_interval_seconds or 60), 10)
        logger.info("Stripe poller started. interval=%s", interval)
        while True:
            await asyncio.sleep(interval)
            try:
                processed = await asyncio.to_thread(self.run)
                if processed:
                    logger.info("Stripe poll completed. processed=%s", processed)
            except Exception:
                logger.exception("Stripe poll failed")


async def schedule_stripe_poll() -> None:
    await StripePollTask().schedule()
