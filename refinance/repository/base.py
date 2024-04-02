"""Base repository with CRUD methods, suitable for simple objects"""

from abc import ABC, abstractmethod
from typing import Any, Generic, Mapping, Type, TypeVar

from fastapi import Depends
from sqlalchemy.orm import Query, Session

from refinance.db import get_db
from refinance.errors.common import NotFoundError
from refinance.models.base import BaseModel
from refinance.schemas.base import BaseFilterSchema, PaginationSchema

_M = TypeVar("_M", bound=BaseModel)  # model
_K = TypeVar("_K", bound=int | str)  # primary key
_F = TypeVar("_F", bound=BaseFilterSchema)  # filters
_Q = TypeVar("_Q", bound=Query[Any])  # query


class BaseRepository(ABC, Generic[_K, _M, _F]):
    model: Type[_M]
    db: Session

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def create(self, obj: _M) -> _M:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def get(self, obj_id: _K) -> _M:
        db_obj = self.db.query(self.model).filter(self.model.id == obj_id).first()
        if not db_obj:
            raise NotFoundError(f"{self.model.__name__}.{obj_id=}")
        return db_obj

    @abstractmethod
    def _apply_filters(self, query: _Q, filters: _F) -> _Q: ...

    def get_all(self, filters: _F | None = None, skip: int = 0, limit: int = 100) -> PaginationSchema[_M]:
        query = self.db.query(self.model)
        if filters:
            query = self._apply_filters(query, filters)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return PaginationSchema[_M](items=items, total=total, skip=skip, limit=limit)

    def update(self, obj_id: _K, new_attrs: Mapping[str, Any]) -> _M:
        obj = self.get(obj_id)
        for key, value in new_attrs.items():
            setattr(obj, key, value)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj_id: _K) -> _K:
        obj = self.get(obj_id)
        self.db.delete(obj)
        self.db.commit()
        return obj_id
