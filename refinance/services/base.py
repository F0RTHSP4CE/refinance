"""Base service that incorporates business logic and CRUD operations."""

from typing import Generic, Type, TypeVar

from fastapi import Depends
from sqlalchemy.orm import Query, Session

from refinance.db import get_db
from refinance.errors.common import NotFoundError
from refinance.models.base import BaseModel
from refinance.schemas.base import BaseFilterSchema, PaginationSchema

M = TypeVar("M", bound=BaseModel)  # model
K = TypeVar("K", int, str)  # primary key


class BaseService(Generic[M]):
    model: Type[M]
    db: Session

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def create(self, schema) -> M:
        new_obj = self.model(**schema.dump())
        self.db.add(new_obj)
        self.db.commit()
        self.db.refresh(new_obj)
        return new_obj

    def get(self, obj_id: K) -> M:
        db_obj = self.db.query(self.model).filter(self.model.id == obj_id).first()
        if not db_obj:
            raise NotFoundError(f"{self.model.__name__}.{obj_id=}")
        return db_obj

    def _apply_base_filters(self, query: Query, filters: BaseFilterSchema) -> Query:
        if filters.comment is not None:
            query = query.filter(self.model.comment.ilike(f"%{filters.comment}%"))
        if filters.created_after is not None:
            query = query.filter(self.model.created_at >= filters.created_after)
        if filters.created_before is not None:
            query = query.filter(self.model.created_at <= filters.created_before)
        return query

    def _apply_filters(self, query: Query, filters: object) -> Query: ...

    def get_all(
        self, filters: BaseFilterSchema | None = None, skip=0, limit=100
    ) -> PaginationSchema[M]:
        query = self.db.query(self.model)
        if filters:
            query = self._apply_base_filters(query, filters)
            query = self._apply_filters(query, filters)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return PaginationSchema[M](items=items, total=total, skip=skip, limit=limit)

    def update(self, obj_id: K, update_schema) -> M:
        obj = self.get(obj_id)
        for key, value in update_schema.dump().items():
            setattr(obj, key, value)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj_id: K) -> K:
        obj = self.get(obj_id)
        self.db.delete(obj)
        self.db.commit()
        return obj_id
