"""Seed bootstrap data (system entities, tags) into the configured database.

Usage (inside docker compose):
    python -m app.scripts.seed

Idempotent: uses session.merge under the hood, safe to run on every API start.
"""

from __future__ import annotations

import logging

from app.config import get_config
from app.db import DatabaseConnection

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main() -> None:
    db = DatabaseConnection(config=get_config())
    db.seed_bootstrap_data()


if __name__ == "__main__":
    main()
