"""Helper CLI to add or update an Entity for authentication tests.

Usage examples (inside docker compose):
    python -m app.scripts.add_entity --name skywinder --telegram-id 123456789
    python -m app.scripts.add_entity --id 205 --name alice --telegram-id 111222333

This will upsert an entity by id or name and set auth.telegram_id if provided.
"""

from __future__ import annotations

import argparse
import json
import logging
from typing import Any, Dict, Optional

from app.config import get_config
from app.db import DatabaseConnection
from app.models.entity import Entity
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upsert an Entity for auth")
    parser.add_argument("--id", type=int, required=False, help="Entity id (optional)")
    parser.add_argument("--name", type=str, required=True, help="Entity name")
    parser.add_argument(
        "--telegram-id",
        type=int,
        required=False,
        help="Telegram numeric id to receive login links",
    )
    parser.add_argument(
        "--active",
        action="store_true",
        help="Mark entity as active (default: active)",
    )
    return parser.parse_args()


def upsert_entity(
    session: Session, *, entity_id: Optional[int], name: str, telegram_id: Optional[int]
) -> Entity:
    existing: Optional[Entity] = None
    if entity_id is not None:
        existing = session.query(Entity).filter_by(id=entity_id).first()
    if existing is None:
        existing = session.query(Entity).filter(Entity.name.ilike(name)).first()

    auth_payload: Optional[Dict[str, Any]] = None
    if telegram_id is not None:
        auth_payload = {"telegram_id": int(telegram_id)}

    if existing is None:
        new_entity = Entity(name=name)
        if entity_id is not None:
            # Assign explicit id only if provided
            new_entity.id = entity_id
        if auth_payload is not None:
            new_entity.auth = auth_payload
        session.add(new_entity)
        session.commit()
        session.refresh(new_entity)
        logger.info(
            "Created entity id=%s name=%s auth=%s",
            new_entity.id,
            new_entity.name,
            json.dumps(new_entity.auth) if isinstance(new_entity.auth, dict) else None,
        )
        return new_entity

    # Update existing
    existing.name = name
    if auth_payload is not None:
        existing.auth = auth_payload
    session.add(existing)
    session.commit()
    session.refresh(existing)
    logger.info(
        "Updated entity id=%s name=%s auth=%s",
        existing.id,
        existing.name,
        json.dumps(existing.auth) if isinstance(existing.auth, dict) else None,
    )
    return existing


def main() -> None:
    args = parse_args()
    # Create config explicitly for CLI usage (bypass FastAPI Depends)
    config = get_config()
    db = DatabaseConnection(config=config)  # creates tables/seed if not exists
    session = db.get_session()
    try:
        upsert_entity(
            session,
            entity_id=args.id,
            name=args.name,
            telegram_id=args.telegram_id,
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
