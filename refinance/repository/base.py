"""Base repository with CRUD methods, suitable for simple objects"""

from typing import Generic, Iterable, Mapping, Type, TypeVar

from fastapi import Depends
from sqlalchemy.orm import Query, Session

from refinance.db import get_db
from refinance.errors.common import NotFoundError
from refinance.models.base import BaseModel
from refinance.schemas.base import BaseFilterSchema

M = TypeVar("M", bound=BaseModel)  # model
K = TypeVar("K", int, str)  # primary key
F = TypeVar("F", bound=BaseFilterSchema)  # filters


class BaseRepository(Generic[M]):
    model: Type[M]
    db: Session

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def create(self, obj: M) -> M:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get(self, obj_id: K) -> M:
        db_obj = self.db.query(self.model).filter(self.model.id == obj_id).first()
        if not db_obj:
            raise NotFoundError(f"{self.model.__name__}.{obj_id=}")
        return db_obj

    def _apply_filters(self, query: Query, filters: F) -> Query: ...

    def get_all(self, filters: F | None = None, skip=0, limit=10) -> Iterable[M]:
        query = self.db.query(self.model)
        if filters:
            query = self._apply_filters(query, filters)
        return query.offset(skip).limit(limit).all()

    def update(self, obj_id: K, new_attrs: Mapping) -> M:
        obj = self.get(obj_id)
        for key, value in new_attrs.items():
            setattr(obj, key, value)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj_id: K) -> K:
        obj = self.get(obj_id)
        self.db.delete(obj)
        self.db.commit()
        return obj_id
