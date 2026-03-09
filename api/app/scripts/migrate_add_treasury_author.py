"""One-off idempotent migration: add treasuries.author_entity_id.

Usage:
    python -m app.scripts.migrate_add_treasury_author
"""

from __future__ import annotations

import logging

from app.config import get_config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _build_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite"):
        return create_engine(database_url, connect_args={"check_same_thread": False})
    return create_engine(database_url)


def _migrate_postgresql(engine: Engine) -> None:
    with engine.begin() as conn:
        column_exists = conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'treasuries'
                  AND column_name = 'author_entity_id'
                """
            )
        ).first()

        if not column_exists:
            logger.info("Adding column treasuries.author_entity_id")
            conn.execute(
                text(
                    """
                    ALTER TABLE treasuries
                    ADD COLUMN author_entity_id INTEGER NULL
                    """
                )
            )
        else:
            logger.info("Column treasuries.author_entity_id already exists")

        fk_exists = conn.execute(
            text(
                """
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'treasuries_author_entity_id_fkey'
                  AND conrelid = 'treasuries'::regclass
                """
            )
        ).first()

        if not fk_exists:
            logger.info("Adding FK constraint treasuries_author_entity_id_fkey")
            conn.execute(
                text(
                    """
                    ALTER TABLE treasuries
                    ADD CONSTRAINT treasuries_author_entity_id_fkey
                    FOREIGN KEY (author_entity_id)
                    REFERENCES entities(id)
                    """
                )
            )
        else:
            logger.info("FK constraint treasuries_author_entity_id_fkey already exists")


def _migrate_sqlite(engine: Engine) -> None:
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(treasuries)")).fetchall()
        columns = {row[1] for row in rows}

        if "author_entity_id" not in columns:
            logger.info("Adding column treasuries.author_entity_id (sqlite)")
            conn.execute(
                text(
                    """
                    ALTER TABLE treasuries
                    ADD COLUMN author_entity_id INTEGER NULL
                    """
                )
            )
        else:
            logger.info("Column treasuries.author_entity_id already exists")


def main() -> None:
    config = get_config()
    engine = _build_engine(config.database_url)
    dialect = engine.dialect.name.lower()

    try:
        if dialect == "postgresql":
            _migrate_postgresql(engine)
        elif dialect == "sqlite":
            _migrate_sqlite(engine)
        else:
            raise RuntimeError(f"Unsupported dialect for migration: {dialect}")
    finally:
        engine.dispose()

    logger.info("Migration completed successfully")


if __name__ == "__main__":
    main()
