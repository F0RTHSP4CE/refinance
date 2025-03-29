"""Database connection and initialization"""

import logging
import os
from typing import Any, Generator, List, Type

from app.bootstrap import BOOTSTRAP
from app.config import Config, get_config
from app.models.base import BaseModel
from fastapi import Depends
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)


class DatabaseConnection:
    engine: Engine
    session_local: sessionmaker[Session]
    # Class-level flag ensures bootstrapping runs only once per process.
    _bootstrapped: bool = False

    def __init__(self, config: Config = Depends(get_config)) -> None:
        # Ensure the database folder exists.
        os.makedirs(config.database_path.parent, exist_ok=True)
        self.engine = create_engine(
            config.database_url, connect_args={"check_same_thread": False}
        )
        self.session_local = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        # Seed bootstrap data only once per process.
        if not self.__class__._bootstrapped:
            self.create_tables()
            self.seed_bootstrap_data()
            self.__class__._bootstrapped = True

    def create_tables(self) -> None:
        """Create all database tables defined in models."""
        logger.info("Creating database tables...")
        BaseModel.metadata.create_all(bind=self.engine)
        logger.info("Database tables created.")

    def drop_tables(self) -> None:
        """Drop all database tables."""
        logger.info("Dropping database tables...")
        BaseModel.metadata.drop_all(bind=self.engine)
        logger.info("Database tables dropped.")

    def get_session(self) -> Session:
        """Return a new SQLAlchemy session."""
        return self.session_local()

    def seed_bootstrap_data(self) -> None:
        """
        Seed bootstrap data for Tags and Entities, and update the autoincrement
        sequence if the current value is less than the desired start.
        This method is called once during initialization.
        """
        with self.get_session() as session:
            for model, seeds in BOOTSTRAP.items():
                try:
                    self._seed_model(
                        session=session,
                        model=model,
                        seeds=seeds,
                        sequence_start=100,
                    )
                    session.commit()
                    logger.info("Bootstrap data seeding completed successfully.")
                except SQLAlchemyError as exc:
                    session.rollback()
                    logger.exception("Error occurred during bootstrap data seeding.")
                    raise exc

    def _seed_model(
        self,
        session: Session,
        model: Type[BaseModel],
        seeds: List[BaseModel],
        sequence_start: int = 100,
    ) -> None:
        """
        Seed bootstrap data for a given model.

        For each seed instance:
          - Merge the detached instance into the session. This will add it if it does not exist
            or update the existing record.
          - Then update the autoincrement counter if its current value is lower than desired.

        This method handles both SQLite and PostgreSQL.

        Args:
            session: SQLAlchemy session.
            model: The model class to seed.
            seeds: A list of pre-instantiated model objects.
            sequence_start: Desired start value for autoincrement IDs.
        """
        table_name = model.__tablename__
        logger.info("Seeding data for table '%s'", table_name)

        for seed in seeds:
            logger.debug("Merging seed with id %s for table '%s'", seed.id, table_name)
            session.merge(seed)
        session.flush()
        logger.info("Merged %d seed(s) for table '%s'", len(seeds), table_name)

        # Determine which dialect is used (SQLite or PostgreSQL)
        db_engine = session.get_bind()
        dialect = db_engine.dialect.name.lower()
        logger.debug("Database dialect detected: %s", dialect)

        if dialect == "sqlite":
            # Check if sqlite_sequence exists.
            seq_table = session.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"
                )
            ).fetchone()
            if seq_table is not None:
                result = session.execute(
                    text("SELECT seq FROM sqlite_sequence WHERE name = :table"),
                    {"table": table_name},
                ).fetchone()
                current_seq = result[0] if result is not None else 0
                logger.info(
                    "Current sequence for table '%s': %d", table_name, current_seq
                )
                if current_seq < (sequence_start - 1):
                    logger.info(
                        "Updating sequence for table '%s' to %d",
                        table_name,
                        sequence_start - 1,
                    )
                    session.execute(
                        text(
                            "UPDATE sqlite_sequence SET seq = :seq WHERE name = :table"
                        ),
                        {"seq": sequence_start - 1, "table": table_name},
                    )
                    session.flush()
            else:
                logger.warning(
                    "sqlite_sequence table does not exist; skipping sequence update for '%s'",
                    table_name,
                )
        elif dialect == "postgresql":
            # For PostgreSQL, assume the sequence name is '{table_name}_id_seq'
            sequence_name = f"{table_name}_id_seq"
            result = session.execute(
                text(f"SELECT last_value FROM {sequence_name}")
            ).fetchone()
            current_seq = result[0] if result is not None else 0
            logger.info(
                "Current sequence for table '%s' (sequence: '%s'): %d",
                table_name,
                sequence_name,
                current_seq,
            )
            if current_seq < (sequence_start - 1):
                logger.info(
                    "Updating sequence for table '%s' (sequence: '%s') to %d",
                    table_name,
                    sequence_name,
                    sequence_start,
                )
                session.execute(
                    text(
                        f"ALTER SEQUENCE {sequence_name} RESTART WITH {sequence_start}"
                    )
                )
                session.flush()
        else:
            logger.warning(
                "Dialect '%s' not explicitly handled for sequence update on table '%s'",
                dialect,
                table_name,
            )


def get_db(db_conn: DatabaseConnection = Depends()) -> Generator[Session, Any, None]:
    """
    Dependency for providing a SQLAlchemy session to services and tests.

    Yields:
        SQLAlchemy Session.
    """
    session = db_conn.get_session()
    try:
        yield session
    finally:
        session.close()
