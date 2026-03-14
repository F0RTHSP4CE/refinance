"""Keepz payments polling task."""

from __future__ import annotations

import asyncio
import logging

from app.config import Config, get_config
from app.dependencies.services import ServiceContainer
from app.errors.keepz import KeepzAuthRequired
from app.tasks import PeriodicTask

logger = logging.getLogger(__name__)


class KeepzPollTask(PeriodicTask):
    def next_delay(self) -> float:
        raise NotImplementedError  # schedule() is fully overridden

    def execute(self, container: ServiceContainer, config: Config) -> int:
        return container.keepz_deposit_provider_service.poll_pending_deposits()

    async def schedule(self) -> None:
        config = get_config()
        interval = max(int(config.keepz_poll_interval_seconds or 60), 10)
        logger.info("Keepz poller started. interval=%s", interval)
        while True:
            await asyncio.sleep(interval)
            try:
                processed = await asyncio.to_thread(self.run)
                if processed:
                    logger.info("Keepz poll completed. processed=%s", processed)
            except KeepzAuthRequired:
                logger.info("Keepz poll skipped: authentication required")
            except Exception:
                logger.exception("Keepz poll failed")


async def schedule_keepz_poll() -> None:
    await KeepzPollTask().schedule()
