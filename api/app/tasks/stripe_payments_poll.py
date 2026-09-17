"""Stripe payments polling task."""

from __future__ import annotations

import logging

from app.config import Config
from app.dependencies.services import ServiceContainer
from app.tasks import DepositPollTask

logger = logging.getLogger(__name__)


class StripePollTask(DepositPollTask):
    provider = "stripe"

    def execute(self, container: ServiceContainer, config: Config) -> int:
        n = container.stripe_deposit_provider_service.poll_pending_deposits()
        n += container.stripe_authorization_service.poll_subscription_invoice_deposits()
        return n


async def schedule_stripe_poll() -> None:
    logger.info("Stripe poller started with deposit-aware backoff")
    await StripePollTask().schedule()
