"""Entity service"""

import datetime

from app.errors.entity import DuplicateEntityAuthBinding
from app.dependencies.services import get_tag_service
from app.errors.common import NotFoundError
from app.models.entity import Entity
from app.models.transaction import TransactionStatus
from app.schemas.base import PaginationSchema
from app.schemas.entity import (
    EntityCreateSchema,
    EntityFiltersSchema,
    EntityUpdateSchema,
)
from app.services.balance_queries import build_entity_balance_subqueries
from app.services.base import BaseService
from app.services.mixins.taggable_mixin import TaggableServiceMixin
from app.services.tag import TagService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import BigInteger, Text, cast
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql import func


class EntityService(TaggableServiceMixin[Entity], BaseService[Entity]):
    model = Entity

    def __init__(
        self,
        db: Session = Depends(get_uow),
        tag_service: TagService = Depends(get_tag_service),
    ):
        self.db = db
        self._tag_service = tag_service

    def delete(self, obj_id):
        """This will break the history, implement it later (maybe)"""
        raise NotImplementedError

    def _apply_filters(
        self, query: Query[Entity], filters: EntityFiltersSchema
    ) -> Query[Entity]:
        if filters.name is not None:
            query = query.filter(self.model.name.ilike(f"%{filters.name}%"))
        if filters.active is not None:
            query = query.filter(self.model.active == filters.active)
        if filters.auth_telegram_id is not None:
            query = query.filter(
                cast(func.nullif(self.model.auth.op("->>")("telegram_id"), ""), BigInteger)
                == filters.auth_telegram_id
            )
        if filters.tags_ids:
            query = self._apply_tag_filters(query, filters.tags_ids)
        return query

    def get_all(
        self, filters: EntityFiltersSchema | None = None, skip=0, limit=100
    ) -> PaginationSchema[Entity]:
        query = self.db.query(self.model)
        if filters:
            query = self._apply_base_filters(query, filters)
            query = self._apply_filters(query, filters)

            if filters.balance_currency:
                status = filters.balance_status or TransactionStatus.COMPLETED
                order = (filters.balance_order or "desc").lower()

                credit_subq, debit_subq, balance_expr = build_entity_balance_subqueries(
                    currency=filters.balance_currency,
                    status=status,
                )

                query = query.outerjoin(
                    credit_subq, credit_subq.c.entity_id == self.model.id
                ).outerjoin(debit_subq, debit_subq.c.entity_id == self.model.id)

                if order == "asc":
                    query = query.order_by(balance_expr.asc(), self.model.id.desc())
                else:
                    query = query.order_by(balance_expr.desc(), self.model.id.desc())
            else:
                query = query.order_by(self.model.id.desc())
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return PaginationSchema[Entity](
            items=items, total=total, skip=skip, limit=limit
        )

    @staticmethod
    def _normalize_auth_identifier(value: int | str | None) -> int | str | None:
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return None
            if normalized.isdigit():
                return int(normalized)
            return normalized
        return value

    def _assert_unique_auth_bindings(
        self,
        auth: dict | None,
        *,
        exclude_entity_id: int | None = None,
    ) -> None:
        normalized_auth = auth or {}
        duplicate_checks: list[tuple[str, int | str]] = []
        for key in ("telegram_id", "signal_id"):
            normalized = self._normalize_auth_identifier(normalized_auth.get(key))
            if normalized is not None:
                duplicate_checks.append((key, normalized))

        for key, normalized in duplicate_checks:
            query = self.db.query(self.model).filter(
                cast(func.nullif(self.model.auth.op("->>")(key), ""), Text) == str(normalized)
            )
            if exclude_entity_id is not None:
                query = query.filter(self.model.id != exclude_entity_id)
            if query.first() is not None:
                raise DuplicateEntityAuthBinding(f"{key}={normalized}")

    def create(self, schema: EntityCreateSchema, overrides: dict = {}):  # type: ignore[override]
        data = schema.dump()
        self._assert_unique_auth_bindings(data.get("auth"))
        return super().create(schema, overrides=overrides)

    def get_by_telegram_id(self, telegram_id: int) -> Entity:
        matches = (
            self.db.query(self.model)
            .filter(
                cast(func.nullif(self.model.auth.op("->>")("telegram_id"), ""), BigInteger) == telegram_id
            )
            .limit(2)
            .all()
        )
        if not matches:
            raise NotFoundError(f"{self.model.__name__}.auth.{telegram_id=}")
        if len(matches) > 1:
            raise DuplicateEntityAuthBinding(f"telegram_id={telegram_id}")
        return matches[0]

    def get_by_name(self, name: str) -> Entity:
        db_obj = (
            self.db.query(self.model)
            .filter(func.lower(self.model.name) == func.lower(name))
            .first()
        )
        if not db_obj:
            raise NotFoundError(f"{self.model.__name__} {name=}")
        return db_obj

    def update(self, obj_id: int, schema: EntityUpdateSchema, overrides: dict = {}):  # type: ignore[override]
        """Update entity with special handling for auth merge."""
        obj = self.get(obj_id)
        data = schema.dump()

        tag_ids = data.pop("tag_ids", None)
        data = {**data, **overrides}

        auth_update = data.pop("auth", None)

        # Set simple (non-auth) attributes
        for key, value in data.items():
            setattr(obj, key, value)

        if auth_update is not None:
            # Merge with existing auth instead of replacing wholesale
            existing_auth = obj.auth or {}
            merged_auth = {**existing_auth, **auth_update}
            self._assert_unique_auth_bindings(merged_auth, exclude_entity_id=obj.id)
            obj.auth = merged_auth

        # Handle tags if supported and provided (keep parity with BaseService)
        if tag_ids is not None and hasattr(self, "set_tags"):
            self.set_tags(obj, tag_ids)  # type: ignore

        setattr(obj, "modified_at", datetime.datetime.now())
        self.db.flush()
        self.db.refresh(obj)
        return obj
