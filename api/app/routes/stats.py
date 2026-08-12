"""Routes for stats"""

from datetime import date
from typing import List, Literal, Optional

from app.dependencies.services import get_stats_service
from app.schemas.stats import (
    DonationsByMonthSchema,
    EntityBalanceChangeByDaySchema,
    EntityMoneyFlowByDaySchema,
    EntityStatsBundleSchema,
    EntityTransactionsByDaySchema,
    FeeTransactionsByMonthSchema,
    MonthlyFeeSumByMonthSchema,
    SystemBalanceHistorySchema,
    TopEntityByMonthSchema,
    TopEntityStatSchema,
    TopTagByMonthSchema,
    TopTagStatSchema,
    TransactionsSumByTagByMonthSchema,
    TreasuryStatsBundleSchema,
)
from app.services.stats import StatsService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/stats", tags=["Stats"])


def _normalize_history_timeframe(
    stats_service: StatsService,
    months: int,
    timeframe_from: Optional[date],
    timeframe_to: Optional[date],
) -> tuple[int, date, date]:
    normalized_months = max(1, int(months))
    normalized_timeframe_to = timeframe_to or date.today()
    normalized_timeframe_from = timeframe_from
    if normalized_timeframe_from is None:
        normalized_timeframe_from = normalized_timeframe_to.replace(day=1)
        if normalized_months > 1:
            normalized_timeframe_from = stats_service._subtract_months(
                normalized_timeframe_from, normalized_months - 1
            )
    if normalized_timeframe_from > normalized_timeframe_to:
        normalized_timeframe_from = normalized_timeframe_to
    return normalized_months, normalized_timeframe_from, normalized_timeframe_to


def _get_history_stats_bundle(
    stats_service: StatsService,
    subject_type: Literal["entity", "treasury"],
    subject_id: int,
    timeframe_from: date,
    timeframe_to: date,
    *,
    cached_only: bool,
) -> dict:
    cache_args = (int(subject_id), timeframe_from, timeframe_to)
    if cached_only:
        balance_changes = StatsService._get_cached_value(
            f"get_{subject_type}_balance_history", cache_args, {}
        )
        money_flow_by_day = StatsService._get_cached_value(
            f"get_{subject_type}_money_flow_by_day", cache_args, {}
        )
        if balance_changes is None or money_flow_by_day is None:
            return {"cached": False}
    else:
        balance_changes = stats_service.get_balance_history(
            subject_type, subject_id, timeframe_from, timeframe_to
        )
        money_flow_by_day = stats_service.get_money_flow_by_day(
            subject_type, subject_id, timeframe_from, timeframe_to
        )
    return {
        "cached": True,
        "balance_changes": balance_changes,
        "money_flow_by_day": money_flow_by_day,
    }


@router.get(
    "/monthly-fee-sum-by-month", response_model=List[MonthlyFeeSumByMonthSchema]
)
def get_monthly_fee_sum_by_month(
    timeframe_from: Optional[date] = None,
    timeframe_to: Optional[date] = None,
    stats_service: StatsService = Depends(get_stats_service),
):
    return stats_service.get_monthly_fee_sum_by_month(timeframe_from, timeframe_to)


@router.get(
    "/fee-transactions-by-month", response_model=List[FeeTransactionsByMonthSchema]
)
def get_fee_transactions_by_month(
    timeframe_from: Optional[date] = None,
    timeframe_to: Optional[date] = None,
    stats_service: StatsService = Depends(get_stats_service),
):
    return stats_service.get_fee_transactions_by_month(timeframe_from, timeframe_to)


@router.get("/donations-by-month", response_model=List[DonationsByMonthSchema])
def get_donations_by_month(
    timeframe_from: Optional[date] = None,
    timeframe_to: Optional[date] = None,
    stats_service: StatsService = Depends(get_stats_service),
):
    return stats_service.get_donations_by_month(timeframe_from, timeframe_to)


@router.get("/system-balance-history", response_model=List[SystemBalanceHistorySchema])
def get_system_balance_history(
    months: int = 12,
    timeframe_from: Optional[date] = None,
    timeframe_to: Optional[date] = None,
    stats_service: StatsService = Depends(get_stats_service),
):
    _, normalized_from, normalized_to = _normalize_history_timeframe(
        stats_service, months, timeframe_from, timeframe_to
    )
    return stats_service.get_system_balance_history(normalized_from, normalized_to)


@router.get(
    "/entity/{entity_id}/balance-change-by-day",
    response_model=List[EntityBalanceChangeByDaySchema],
)
def get_entity_balance_history(
    entity_id: int,
    timeframe_from: Optional[date] = None,
    timeframe_to: Optional[date] = None,
    stats_service: StatsService = Depends(get_stats_service),
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
    stats_service: StatsService = Depends(get_stats_service),
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
    stats_service: StatsService = Depends(get_stats_service),
):
    return stats_service.get_entity_money_flow_by_day(
        entity_id, timeframe_from, timeframe_to
    )


@router.get(
    "/treasury/{treasury_id}/balance-change-by-day",
    response_model=List[EntityBalanceChangeByDaySchema],
)
def get_treasury_balance_history(
    treasury_id: int,
    timeframe_from: Optional[date] = None,
    timeframe_to: Optional[date] = None,
    stats_service: StatsService = Depends(get_stats_service),
):
    return stats_service.get_treasury_balance_history(
        treasury_id, timeframe_from, timeframe_to
    )


@router.get(
    "/treasury/{treasury_id}/money-flow-by-day/",
    response_model=List[EntityMoneyFlowByDaySchema],
)
def get_treasury_money_flow_by_day(
    treasury_id: int,
    timeframe_from: Optional[date] = None,
    timeframe_to: Optional[date] = None,
    stats_service: StatsService = Depends(get_stats_service),
):
    return stats_service.get_treasury_money_flow_by_day(
        treasury_id, timeframe_from, timeframe_to
    )


@router.get(
    "/transactions-sum-by-tag-by-month",
    response_model=List[TransactionsSumByTagByMonthSchema],
)
def get_transactions_sum_by_tag_by_month(
    tag_id: int,
    timeframe_from: Optional[date] = None,
    timeframe_to: Optional[date] = None,
    stats_service: StatsService = Depends(get_stats_service),
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
    stats_service: StatsService = Depends(get_stats_service),
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
    stats_service: StatsService = Depends(get_stats_service),
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
    stats_service: StatsService = Depends(get_stats_service),
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
    stats_service: StatsService = Depends(get_stats_service),
):
    return stats_service.get_top_outgoing_tags(
        limit=limit,
        months=months,
        timeframe_to=timeframe_to,
        entity_id=entity_id,
    )


@router.get("/outgoing-by-entity-by-month", response_model=List[TopEntityByMonthSchema])
def get_outgoing_by_entity_by_month(
    limit: int = 5,
    months: int = 6,
    timeframe_to: Optional[date] = None,
    entity_id: Optional[int] = None,
    stats_service: StatsService = Depends(get_stats_service),
):
    return stats_service.get_outgoing_by_entity_by_month(
        entity_id=entity_id,
        limit=limit,
        months=months,
        timeframe_to=timeframe_to,
    )


@router.get("/incoming-by-entity-by-month", response_model=List[TopEntityByMonthSchema])
def get_incoming_by_entity_by_month(
    limit: int = 5,
    months: int = 6,
    timeframe_to: Optional[date] = None,
    entity_id: Optional[int] = None,
    stats_service: StatsService = Depends(get_stats_service),
):
    return stats_service.get_incoming_by_entity_by_month(
        entity_id=entity_id,
        limit=limit,
        months=months,
        timeframe_to=timeframe_to,
    )


@router.get("/outgoing-by-tag-by-month", response_model=List[TopTagByMonthSchema])
def get_outgoing_by_tag_by_month(
    limit: int = 5,
    months: int = 6,
    timeframe_to: Optional[date] = None,
    entity_id: Optional[int] = None,
    stats_service: StatsService = Depends(get_stats_service),
):
    return stats_service.get_outgoing_by_tag_by_month(
        entity_id=entity_id,
        limit=limit,
        months=months,
        timeframe_to=timeframe_to,
    )


@router.get("/incoming-by-tag-by-month", response_model=List[TopTagByMonthSchema])
def get_incoming_by_tag_by_month(
    limit: int = 5,
    months: int = 6,
    timeframe_to: Optional[date] = None,
    entity_id: Optional[int] = None,
    stats_service: StatsService = Depends(get_stats_service),
):
    return stats_service.get_incoming_by_tag_by_month(
        entity_id=entity_id,
        limit=limit,
        months=months,
        timeframe_to=timeframe_to,
    )


@router.get("/treasury/{treasury_id}", response_model=TreasuryStatsBundleSchema)
def get_treasury_stats_bundle(
    treasury_id: int,
    months: int = 6,
    timeframe_from: Optional[date] = None,
    timeframe_to: Optional[date] = None,
    cached_only: bool = False,
    stats_service: StatsService = Depends(get_stats_service),
):
    """Return the two account-history graphs for a treasury."""
    _, normalized_from, normalized_to = _normalize_history_timeframe(
        stats_service, months, timeframe_from, timeframe_to
    )
    return _get_history_stats_bundle(
        stats_service,
        "treasury",
        treasury_id,
        normalized_from,
        normalized_to,
        cached_only=cached_only,
    )


@router.get("/entity/{entity_id}", response_model=EntityStatsBundleSchema)
def get_entity_stats_bundle(
    entity_id: int,
    limit: int = 6,
    months: int = 6,
    timeframe_from: Optional[date] = None,
    timeframe_to: Optional[date] = None,
    cached_only: bool = False,
    stats_service: StatsService = Depends(get_stats_service),
):
    """Return all entity stats in a single request.

    This endpoint is intended for UI usage and benefits from StatsService's in-memory caching.
    """
    normalized_months, bundle_timeframe_from, normalized_timeframe_to = (
        _normalize_history_timeframe(
            stats_service, months, timeframe_from, timeframe_to
        )
    )
    normalized_limit = max(1, int(limit))

    if cached_only:
        # Keep cache args consistent with the non-cached path below.
        tx_args = (int(entity_id), bundle_timeframe_from, normalized_timeframe_to)
        top_args = (
            int(entity_id),
            int(normalized_limit),
            int(normalized_months),
            normalized_timeframe_to,
        )

        history_stats = _get_history_stats_bundle(
            stats_service,
            "entity",
            entity_id,
            bundle_timeframe_from,
            normalized_timeframe_to,
            cached_only=True,
        )
        transactions_by_day = StatsService._get_cached_value(
            "get_entity_transactions_by_day", tx_args, {}
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
        incoming_by_entity_by_month = StatsService._get_cached_value(
            "get_incoming_by_entity_by_month", top_args, {}
        )
        outgoing_by_entity_by_month = StatsService._get_cached_value(
            "get_outgoing_by_entity_by_month", top_args, {}
        )
        incoming_by_tag_by_month = StatsService._get_cached_value(
            "get_incoming_by_tag_by_month", top_args, {}
        )
        outgoing_by_tag_by_month = StatsService._get_cached_value(
            "get_outgoing_by_tag_by_month", top_args, {}
        )

        all_present = all(
            x is not None
            for x in (
                transactions_by_day,
                top_incoming,
                top_outgoing,
                top_incoming_tags,
                top_outgoing_tags,
                incoming_by_entity_by_month,
                outgoing_by_entity_by_month,
                incoming_by_tag_by_month,
                outgoing_by_tag_by_month,
            )
        )

        if history_stats.get("cached") is False or not all_present:
            return {"cached": False}

        return {
            **history_stats,
            "transactions_by_day": transactions_by_day,
            "top_incoming": top_incoming,
            "top_outgoing": top_outgoing,
            "top_incoming_tags": top_incoming_tags,
            "top_outgoing_tags": top_outgoing_tags,
            "incoming_by_entity_by_month": incoming_by_entity_by_month,
            "outgoing_by_entity_by_month": outgoing_by_entity_by_month,
            "incoming_by_tag_by_month": incoming_by_tag_by_month,
            "outgoing_by_tag_by_month": outgoing_by_tag_by_month,
        }

    # Use the same bundle timeframe for all time-series charts.
    history_stats = _get_history_stats_bundle(
        stats_service,
        "entity",
        entity_id,
        bundle_timeframe_from,
        normalized_timeframe_to,
        cached_only=False,
    )
    transactions_by_day = stats_service.get_entity_transactions_by_day(
        entity_id,
        bundle_timeframe_from,
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
    incoming_by_entity_by_month = stats_service.get_incoming_by_entity_by_month(
        entity_id=entity_id,
        limit=normalized_limit,
        months=normalized_months,
        timeframe_to=normalized_timeframe_to,
    )
    outgoing_by_entity_by_month = stats_service.get_outgoing_by_entity_by_month(
        entity_id=entity_id,
        limit=normalized_limit,
        months=normalized_months,
        timeframe_to=normalized_timeframe_to,
    )
    incoming_by_tag_by_month = stats_service.get_incoming_by_tag_by_month(
        entity_id=entity_id,
        limit=normalized_limit,
        months=normalized_months,
        timeframe_to=normalized_timeframe_to,
    )
    outgoing_by_tag_by_month = stats_service.get_outgoing_by_tag_by_month(
        entity_id=entity_id,
        limit=normalized_limit,
        months=normalized_months,
        timeframe_to=normalized_timeframe_to,
    )

    return {
        **history_stats,
        "transactions_by_day": transactions_by_day,
        "top_incoming": top_incoming,
        "top_outgoing": top_outgoing,
        "top_incoming_tags": top_incoming_tags,
        "top_outgoing_tags": top_outgoing_tags,
        "incoming_by_entity_by_month": incoming_by_entity_by_month,
        "outgoing_by_entity_by_month": outgoing_by_entity_by_month,
        "incoming_by_tag_by_month": incoming_by_tag_by_month,
        "outgoing_by_tag_by_month": outgoing_by_tag_by_month,
    }
