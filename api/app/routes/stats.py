"""Routes for stats"""

from datetime import date, timedelta
from typing import List, Optional

from app.schemas.stats import (
    EntityBalanceChangeByDaySchema,
    EntityMoneyFlowByDaySchema,
    EntityStatsBundleSchema,
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
    "/entity/{entity_id}/money-flow-by-day/",
    response_model=List[EntityMoneyFlowByDaySchema],
)
def get_entity_money_flow_by_day(
    entity_id: int,
    timeframe_from: Optional[date] = None,
    timeframe_to: Optional[date] = None,
    stats_service: StatsService = Depends(),
):
    return stats_service.get_entity_money_flow_by_day(
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


@router.get("/entity/{entity_id}", response_model=EntityStatsBundleSchema)
def get_entity_stats_bundle(
    entity_id: int,
    limit: int = 6,
    months: int = 6,
    timeframe_from: Optional[date] = None,
    timeframe_to: Optional[date] = None,
    cached_only: bool = False,
    stats_service: StatsService = Depends(),
):
    """Return all entity stats in a single request.

    This endpoint is intended for UI usage and benefits from StatsService's in-memory caching.
    """

    if cached_only:
        # Compute the same normalized cache args as the underlying service methods,
        # but do not call them (to avoid doing DB work on cache misses).
        normalized_timeframe_to = timeframe_to or date.today()

        # get_entity_balance_history normalizes timeframe_from -> start_day, clamps to [three_months_ago, timeframe_to]
        three_months_ago = stats_service._subtract_months(normalized_timeframe_to, 3)
        start_day = timeframe_from if timeframe_from is not None else three_months_ago
        if start_day < three_months_ago:
            start_day = three_months_ago
        if start_day > normalized_timeframe_to:
            start_day = normalized_timeframe_to

        balance_args = (int(entity_id), start_day, normalized_timeframe_to)

        # get_entity_transactions_by_day defaults timeframe_from to last 365 days.
        normalized_timeframe_from = (
            timeframe_from
            if timeframe_from is not None
            else normalized_timeframe_to - timedelta(days=365)
        )
        tx_args = (int(entity_id), normalized_timeframe_from, normalized_timeframe_to)

        # money flow chart uses the selected "months" window, aligned to month boundaries
        flow_start_month = normalized_timeframe_to.replace(day=1)
        if months > 1:
            flow_start_month = stats_service._subtract_months(
                flow_start_month, months - 1
            )
        flow_args = (int(entity_id), flow_start_month, normalized_timeframe_to)

        top_args = (int(entity_id), int(limit), int(months), normalized_timeframe_to)

        balance_changes = StatsService._get_cached_value(
            "get_entity_balance_history", balance_args, {}
        )
        transactions_by_day = StatsService._get_cached_value(
            "get_entity_transactions_by_day", tx_args, {}
        )
        money_flow_by_day = StatsService._get_cached_value(
            "get_entity_money_flow_by_day", flow_args, {}
        )
        top_incoming = StatsService._get_cached_value(
            "get_top_incoming_entities", top_args, {}
        )
        top_outgoing = StatsService._get_cached_value(
            "get_top_outgoing_entities", top_args, {}
        )
        top_incoming_tags = StatsService._get_cached_value(
            "get_top_incoming_tags", top_args, {}
        )
        top_outgoing_tags = StatsService._get_cached_value(
            "get_top_outgoing_tags", top_args, {}
        )

        all_present = all(
            x is not None
            for x in (
                balance_changes,
                transactions_by_day,
                money_flow_by_day,
                top_incoming,
                top_outgoing,
                top_incoming_tags,
                top_outgoing_tags,
            )
        )

        if not all_present:
            return {"cached": False}

        return {
            "cached": True,
            "balance_changes": balance_changes,
            "transactions_by_day": transactions_by_day,
            "money_flow_by_day": money_flow_by_day,
            "top_incoming": top_incoming,
            "top_outgoing": top_outgoing,
            "top_incoming_tags": top_incoming_tags,
            "top_outgoing_tags": top_outgoing_tags,
        }

    balance_changes = stats_service.get_entity_balance_history(
        entity_id, timeframe_from, timeframe_to
    )
    transactions_by_day = stats_service.get_entity_transactions_by_day(
        entity_id, timeframe_from, timeframe_to
    )

    normalized_timeframe_to = timeframe_to or date.today()
    flow_timeframe_from = timeframe_from
    if flow_timeframe_from is None:
        flow_timeframe_from = normalized_timeframe_to.replace(day=1)
        if months > 1:
            flow_timeframe_from = stats_service._subtract_months(
                flow_timeframe_from, months - 1
            )

    money_flow_by_day = stats_service.get_entity_money_flow_by_day(
        entity_id,
        flow_timeframe_from,
        normalized_timeframe_to,
    )
    top_incoming = stats_service.get_top_incoming_entities(
        limit=limit, months=months, timeframe_to=timeframe_to, entity_id=entity_id
    )
    top_outgoing = stats_service.get_top_outgoing_entities(
        limit=limit, months=months, timeframe_to=timeframe_to, entity_id=entity_id
    )
    top_incoming_tags = stats_service.get_top_incoming_tags(
        limit=limit, months=months, timeframe_to=timeframe_to, entity_id=entity_id
    )
    top_outgoing_tags = stats_service.get_top_outgoing_tags(
        limit=limit, months=months, timeframe_to=timeframe_to, entity_id=entity_id
    )

    return {
        "cached": True,
        "balance_changes": balance_changes,
        "transactions_by_day": transactions_by_day,
        "money_flow_by_day": money_flow_by_day,
        "top_incoming": top_incoming,
        "top_outgoing": top_outgoing,
        "top_incoming_tags": top_incoming_tags,
        "top_outgoing_tags": top_outgoing_tags,
    }
