"""Mint a JWT for an existing entity and print a ready-to-use login link.

Dev-only convenience: avoids the Telegram round-trip when working locally.

Usage (inside docker compose):
    python -m app.scripts.login --name skywinder
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import timedelta

import jwt
from app.config import get_config
from app.db import DatabaseConnection
from app.models.entity import Entity
from sqlalchemy import func


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print a dev login link for an entity")
    parser.add_argument("--name", type=str, required=True, help="Entity name")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = get_config()
    if not config.secret_key:
        print("REFINANCE_SECRET_KEY is empty — cannot sign a token", file=sys.stderr)
        sys.exit(1)

    db = DatabaseConnection(config=config)
    session = db.get_session()
    try:
        entity = (
            session.query(Entity)
            .filter(func.lower(Entity.name) == func.lower(args.name))
            .first()
        )
        if entity is None:
            print(f"Entity not found: {args.name!r}", file=sys.stderr)
            sys.exit(2)

        now = int(time.time())
        token = jwt.encode(
            {
                "sub": str(entity.id),
                "iat": now,
                "exp": now + int(timedelta(weeks=4).total_seconds()),
            },
            config.secret_key,
            algorithm="HS256",
        )
    finally:
        session.close()

    base = (config.ui_url or "").rstrip("/") or "http://localhost:9000"
    print(f"{base}/auth/token/{token}")


if __name__ == "__main__":
    main()
