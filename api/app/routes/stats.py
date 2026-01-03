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

        normalized_months = max(1, int(months))
        normalized_limit = max(1, int(limit))

        # Bundle timeframe: if timeframe_from is not provided, use the selected
        # months window aligned to month boundaries (same as the UI control).
        bundle_timeframe_from = timeframe_from
        if bundle_timeframe_from is None:
            bundle_timeframe_from = normalized_timeframe_to.replace(day=1)
            if normalized_months > 1:
                bundle_timeframe_from = stats_service._subtract_months(
                    bundle_timeframe_from, normalized_months - 1
                )

        if bundle_timeframe_from > normalized_timeframe_to:
            bundle_timeframe_from = normalized_timeframe_to

        # Keep cache args consistent with the non-cached path below.
        balance_args = (int(entity_id), bundle_timeframe_from, normalized_timeframe_to)
        tx_args = (int(entity_id), bundle_timeframe_from, normalized_timeframe_to)
        flow_args = (int(entity_id), bundle_timeframe_from, normalized_timeframe_to)
        top_args = (
            int(entity_id),
            int(normalized_limit),
            int(normalized_months),
            normalized_timeframe_to,
        )

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

    normalized_timeframe_to = timeframe_to or date.today()

    normalized_months = max(1, int(months))
    normalized_limit = max(1, int(limit))
    bundle_timeframe_from = timeframe_from
    if bundle_timeframe_from is None:
        bundle_timeframe_from = normalized_timeframe_to.replace(day=1)
        if normalized_months > 1:
            bundle_timeframe_from = stats_service._subtract_months(
                bundle_timeframe_from, normalized_months - 1
            )
    if bundle_timeframe_from > normalized_timeframe_to:
        bundle_timeframe_from = normalized_timeframe_to

    # Use the same bundle timeframe for all time-series charts.
    balance_changes = stats_service.get_entity_balance_history(
        entity_id,
        bundle_timeframe_from,
        normalized_timeframe_to,
    )
    transactions_by_day = stats_service.get_entity_transactions_by_day(
        entity_id,
        bundle_timeframe_from,
        normalized_timeframe_to,
    )

    flow_timeframe_from = bundle_timeframe_from

    money_flow_by_day = stats_service.get_entity_money_flow_by_day(
        entity_id,
        flow_timeframe_from,
        normalized_timeframe_to,
    )
    top_incoming = stats_service.get_top_incoming_entities(
        limit=normalized_limit,
        months=normalized_months,
        timeframe_to=normalized_timeframe_to,
        entity_id=entity_id,
    )
    top_outgoing = stats_service.get_top_outgoing_entities(
        limit=normalized_limit,
        months=normalized_months,
        timeframe_to=normalized_timeframe_to,
        entity_id=entity_id,
    )
    top_incoming_tags = stats_service.get_top_incoming_tags(
        limit=normalized_limit,
        months=normalized_months,
        timeframe_to=normalized_timeframe_to,
        entity_id=entity_id,
    )
    top_outgoing_tags = stats_service.get_top_outgoing_tags(
        limit=normalized_limit,
        months=normalized_months,
        timeframe_to=normalized_timeframe_to,
        entity_id=entity_id,
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
