"""DTO for Treasury"""

from app.schemas.balance import BalanceSchema
from app.schemas.base import (
    BaseFilterSchema,
    BaseReadSchema,
    BaseUpdateSchema,
    PaginationSchema,
)
from app.schemas.entity import EntitySchema


class TreasurySchema(BaseReadSchema):
    name: str
    active: bool
    author_entity_id: int | None = None
    author_entity: EntitySchema | None = None
    balances: BalanceSchema | None = None


class TreasuryCreateSchema(BaseUpdateSchema):
    name: str
    active: bool | None = True
    author_entity_id: int | None = None


class TreasuryUpdateSchema(BaseUpdateSchema):
    name: str | None = None
    active: bool | None = None
    author_entity_id: int | None = None


class TreasuryFiltersSchema(BaseFilterSchema):
    name: str | None = None
    active: bool | None = None
