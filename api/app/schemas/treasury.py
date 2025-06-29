"""DTO for Treasury"""

from typing import Optional

from app.schemas.balance import BalanceSchema
from app.schemas.base import (
    BaseFilterSchema,
    BaseReadSchema,
    BaseUpdateSchema,
    PaginationSchema,
)


class TreasurySchema(BaseReadSchema):
    name: str
    active: bool
    balances: BalanceSchema | None = None


class TreasuryCreateSchema(BaseUpdateSchema):
    name: str
    active: bool | None = True


class TreasuryUpdateSchema(BaseUpdateSchema):
    name: str | None = None
    active: bool | None = None


class TreasuryFiltersSchema(BaseFilterSchema):
    name: str | None = None
    active: bool | None = None
