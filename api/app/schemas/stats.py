"""Schemas for stats"""

from datetime import date

from pydantic import BaseModel


class ResidentFeeSumByMonthSchema(BaseModel):
    year: int
    month: int
    amounts: dict[str, float]


class EntityTransactionsByDaySchema(BaseModel):
    day: date
    transaction_count: int


class TransactionsSumByWeekSchema(BaseModel):
    year: int
    week: int
    amounts: dict[str, float]


class EntityBalanceChangeByDaySchema(BaseModel):
    day: date
    balance_changes: dict[str, float]
