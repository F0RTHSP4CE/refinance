"""Background tasks."""

from __future__ import annotations

import asyncio
import datetime
import logging
from abc import ABC, abstractmethod

from app.config import Config, get_config
from app.db import DatabaseConnection
from app.dependencies.services import ServiceContainer
from app.models.deposit import Deposit
from app.uow import UnitOfWork

logger = logging.getLogger(__name__)


class PeriodicTask(ABC):
    @abstractmethod
    def next_delay(self) -> float: ...

    @abstractmethod
    def execute(self, container: ServiceContainer, config: Config) -> int: ...

    def run(self) -> int:
        config = get_config()
        with UnitOfWork(DatabaseConnection(config).get_session()) as uow:
            return self.execute(ServiceContainer(uow.db, config), config)

    def run_if_due(self) -> int | None:
        return self.run()

    async def schedule(self) -> None:
        while True:
            await asyncio.sleep(self.next_delay())
            try:
                result = await asyncio.to_thread(self.run_if_due)
                if result is not None:
                    logger.info("%s completed. result=%s", type(self).__name__, result)
            except Exception:
                logger.exception("%s failed", type(self).__name__)


class DepositPollTask(PeriodicTask):
    """Poll a provider at 30s, 1m, 3m, 10m, then hourly."""

    provider: str

    def __init__(self) -> None:
        self._last_slot: tuple[int | None, int] | None = None

    def next_delay(self) -> float:
        return 30

    def run_if_due(self) -> int | None:
        config = get_config()
        with UnitOfWork(DatabaseConnection(config).get_session()) as uow:
            latest = (
                uow.db.query(Deposit.id, Deposit.created_at)
                .filter(Deposit.provider == self.provider)
                .order_by(Deposit.created_at.desc(), Deposit.id.desc())
                .first()
            )
            slot = deposit_poll_slot(latest.created_at if latest else None)
            marker = (latest.id if latest else None, slot)
            if slot < 0 or marker == self._last_slot:
                return None
            self._last_slot = marker
            return self.execute(ServiceContainer(uow.db, config), config)


def deposit_poll_slot(
    created_at: datetime.datetime | None, now: datetime.datetime | None = None
) -> int:
    now = now or datetime.datetime.now()
    if created_at is None:
        return int(now.timestamp() // 3600)

    elapsed = (now - created_at).total_seconds() - 30
    if elapsed < 0:
        return -1
    slot = 0
    for delay in (60, 180, 600):
        if elapsed < delay:
            return slot
        elapsed -= delay
        slot += 1
    return slot + int(elapsed // 3600)
