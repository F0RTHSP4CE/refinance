"""API routes for currency exchange"""

from app.dependencies.services import get_currency_exchange_service
from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.currency_exchange import (
    AutoBalancePreviewSchema,
    AutoBalanceRunResultSchema,
    CurrencyExchangePreviewRequestSchema,
    CurrencyExchangePreviewResponseSchema,
    CurrencyExchangeReceiptSchema,
    CurrencyExchangeRequestSchema,
)
from app.services.currency_exchange import CurrencyExchangeService
from fastapi import APIRouter, Depends

currency_exchange_router = APIRouter(
    prefix="/currency_exchange", tags=["CurrencyExchange"]
)


@currency_exchange_router.post(
    "/exchange", response_model=CurrencyExchangeReceiptSchema
)
def exchange(
    exchange: CurrencyExchangeRequestSchema,
    currency_exchange_service: CurrencyExchangeService = Depends(
        get_currency_exchange_service
    ),
    actor_entity: Entity = Depends(get_entity_from_token),  # auth
):
    return currency_exchange_service.exchange(exchange, actor_entity)


@currency_exchange_router.post(
    "/preview", response_model=CurrencyExchangePreviewResponseSchema
)
def preview(
    preview: CurrencyExchangePreviewRequestSchema,
    currency_exchange_service: CurrencyExchangeService = Depends(
        get_currency_exchange_service
    ),
    _: Entity = Depends(get_entity_from_token),  # auth
):
    return currency_exchange_service.preview(preview)


@currency_exchange_router.get("/rates")
def rates(
    currency_exchange_service: CurrencyExchangeService = Depends(
        get_currency_exchange_service
    ),
    _: Entity = Depends(get_entity_from_token),  # auth
):
    # maybe someday i'll make a fancy list of rates, but for now it is what it is
    return currency_exchange_service._raw_rates


@currency_exchange_router.get(
    "/auto_balance/preview", response_model=AutoBalancePreviewSchema
)
def auto_balance_preview(
    currency_exchange_service: CurrencyExchangeService = Depends(
        get_currency_exchange_service
    ),
    _: Entity = Depends(get_entity_from_token),  # auth
):
    """Preview the exchanges that would be performed by auto-balance for all eligible entities."""
    return currency_exchange_service.compute_auto_balance_plan_for_all()


@currency_exchange_router.post(
    "/auto_balance/run", response_model=AutoBalanceRunResultSchema
)
def auto_balance_run(
    currency_exchange_service: CurrencyExchangeService = Depends(
        get_currency_exchange_service
    ),
    actor_entity: Entity = Depends(get_entity_from_token),  # auth
):
    """Execute auto-balance exchanges for all eligible entities."""
    return currency_exchange_service.run_auto_balance_for_all(actor_entity)
