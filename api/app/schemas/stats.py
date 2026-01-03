"""Schemas for stats"""

from datetime import date

from pydantic import BaseModel, Field


class ResidentFeeSumByMonthSchema(BaseModel):
    year: int
    month: int
    amounts: dict[str, float]
    total_usd: float


class EntityTransactionsByDaySchema(BaseModel):
    day: date
    transaction_count: int


class EntityMoneyFlowByDaySchema(BaseModel):
    day: date
    incoming_total_usd: float
    outgoing_total_usd: float


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


class TopTagStatSchema(BaseModel):
    tag_id: int
    tag_name: str
    amounts: dict[str, float]
    total_usd: float


class EntityStatsBundleSchema(BaseModel):
    cached: bool = True
    balance_changes: list[EntityBalanceChangeByDaySchema] = Field(default_factory=list)
    transactions_by_day: list[EntityTransactionsByDaySchema] = Field(
        default_factory=list
    )
    money_flow_by_day: list[EntityMoneyFlowByDaySchema] = Field(default_factory=list)
    top_incoming: list[TopEntityStatSchema] = Field(default_factory=list)
    top_outgoing: list[TopEntityStatSchema] = Field(default_factory=list)
    top_incoming_tags: list[TopTagStatSchema] = Field(default_factory=list)
    top_outgoing_tags: list[TopTagStatSchema] = Field(default_factory=list)
