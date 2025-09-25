"""Routes for stats"""

from datetime import date
from typing import List, Optional

from app.schemas.stats import (
    EntityBalanceChangeByDaySchema,
    EntityTransactionsByDaySchema,
    ResidentFeeSumByMonthSchema,
    TopEntityStatSchema,
    TopTagStatSchema,
    TransactionsSumByTagByMonthSchema,
    TransactionsSumByWeekSchema,
)
from app.services.stats import StatsService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get(
    "/resident-fee-sum-by-month", response_model=List[ResidentFeeSumByMonthSchema]
)
def get_resident_fee_sum_by_month(
    timeframe_from: Optional[date] = None,
    timeframe_to: Optional[date] = None,
    stats_service: StatsService = Depends(),
):
    return stats_service.get_resident_fee_sum_by_month(timeframe_from, timeframe_to)


@router.get(
    "/transactions-sum-by-week", response_model=List[TransactionsSumByWeekSchema]
)
def get_transactions_sum_by_week(
    timeframe_from: Optional[date] = None,
    timeframe_to: Optional[date] = None,
    stats_service: StatsService = Depends(),
):
    return stats_service.get_transactions_sum_by_week(timeframe_from, timeframe_to)


@router.get(
    "/entity/{entity_id}/balance-change-by-day",
    response_model=List[EntityBalanceChangeByDaySchema],
)
def get_entity_balance_history(
    entity_id: int,
    timeframe_from: Optional[date] = None,
    timeframe_to: Optional[date] = None,
    stats_service: StatsService = Depends(),
):
    return stats_service.get_entity_balance_history(
        entity_id, timeframe_from, timeframe_to
    )


@router.get(
    "/entity/{entity_id}/transactions-by-day/",
    response_model=List[EntityTransactionsByDaySchema],
)
def get_entity_transactions_by_day(
    entity_id: int,
    timeframe_from: Optional[date] = None,
    timeframe_to: Optional[date] = None,
    stats_service: StatsService = Depends(),
):
    return stats_service.get_entity_transactions_by_day(
        entity_id, timeframe_from, timeframe_to
    )


@router.get(
    "/transactions-sum-by-tag-by-month",
    response_model=List[TransactionsSumByTagByMonthSchema],
)
def get_transactions_sum_by_tag_by_month(
    tag_id: int,
    timeframe_from: Optional[date] = None,
    timeframe_to: Optional[date] = None,
    stats_service: StatsService = Depends(),
):
    return stats_service.get_transactions_sum_by_tag_by_month(
        tag_id, timeframe_from, timeframe_to
    )


@router.get("/top-incoming-entities", response_model=List[TopEntityStatSchema])
def get_top_incoming_entities(
    limit: int = 5,
    months: int = 3,
    timeframe_to: Optional[date] = None,
    entity_id: Optional[int] = None,
    stats_service: StatsService = Depends(),
):
    return stats_service.get_top_incoming_entities(
        limit=limit,
        months=months,
        timeframe_to=timeframe_to,
        entity_id=entity_id,
    )


@router.get("/top-outgoing-entities", response_model=List[TopEntityStatSchema])
def get_top_outgoing_entities(
    limit: int = 5,
    months: int = 3,
    timeframe_to: Optional[date] = None,
    entity_id: Optional[int] = None,
    stats_service: StatsService = Depends(),
):
    return stats_service.get_top_outgoing_entities(
        limit=limit,
        months=months,
        timeframe_to=timeframe_to,
        entity_id=entity_id,
    )


@router.get("/top-incoming-tags", response_model=List[TopTagStatSchema])
def get_top_incoming_tags(
    limit: int = 5,
    months: int = 3,
    timeframe_to: Optional[date] = None,
    entity_id: Optional[int] = None,
    stats_service: StatsService = Depends(),
):
    return stats_service.get_top_incoming_tags(
        limit=limit,
        months=months,
        timeframe_to=timeframe_to,
        entity_id=entity_id,
    )


@router.get("/top-outgoing-tags", response_model=List[TopTagStatSchema])
def get_top_outgoing_tags(
    limit: int = 5,
    months: int = 3,
    timeframe_to: Optional[date] = None,
    entity_id: Optional[int] = None,
    stats_service: StatsService = Depends(),
):
    return stats_service.get_top_outgoing_tags(
        limit=limit,
        months=months,
        timeframe_to=timeframe_to,
        entity_id=entity_id,
    )
