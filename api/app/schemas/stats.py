"""Schemas for stats"""

from datetime import date

from pydantic import BaseModel


class ResidentFeeSumByMonthSchema(BaseModel):
    year: int
    month: int
    amounts: dict[str, float]
    total_usd: float


class EntityTransactionsByDaySchema(BaseModel):
    day: date
    transaction_count: int


class TransactionsSumByWeekSchema(BaseModel):
    year: int
    week: int
    amounts: dict[str, float]
    total_usd: float


class EntityBalanceChangeByDaySchema(BaseModel):
    day: date
    balance_changes: dict[str, float]
    total_usd: float


class TransactionsSumByTagByMonthSchema(BaseModel):
    year: int
    month: int
    amounts: dict[str, float]
    total_usd: float


class TopEntityStatSchema(BaseModel):
    entity_id: int
    entity_name: str
    amounts: dict[str, float]
    total_usd: float
