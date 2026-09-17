"""Keepz payments polling task."""

from __future__ import annotations

import logging

from app.config import Config
from app.dependencies.services import ServiceContainer
from app.tasks import DepositPollTask

logger = logging.getLogger(__name__)


class KeepzPollTask(DepositPollTask):
    provider = "keepz"

    def execute(self, container: ServiceContainer, config: Config) -> int:
        return container.keepz_deposit_provider_service.poll_pending_deposits()


async def schedule_keepz_poll() -> None:
    logger.info("Keepz poller started with deposit-aware backoff")
    await KeepzPollTask().schedule()
