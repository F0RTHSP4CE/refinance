"""Background tasks."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

from app.config import Config, get_config
from app.db import DatabaseConnection
from app.dependencies.services import ServiceContainer
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

    async def schedule(self) -> None:
        while True:
            await asyncio.sleep(self.next_delay())
            try:
                result = await asyncio.to_thread(self.run)
                logger.info("%s completed. result=%s", type(self).__name__, result)
            except Exception:
                logger.exception("%s failed", type(self).__name__)
