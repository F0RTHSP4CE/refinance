"""API routes for currency exchange"""

from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.currency_exchange import (
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
    currency_exchange_service: CurrencyExchangeService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),  # auth
):
    return currency_exchange_service.exchange(exchange, actor_entity)


@currency_exchange_router.post(
    "/preview", response_model=CurrencyExchangePreviewResponseSchema
)
def preview(
    preview: CurrencyExchangePreviewRequestSchema,
    currency_exchange_service: CurrencyExchangeService = Depends(),
    _: Entity = Depends(get_entity_from_token),  # auth
):
    return currency_exchange_service.preview(preview)


@currency_exchange_router.get("/rates")
def rates(
    currency_exchange_service: CurrencyExchangeService = Depends(),
    _: Entity = Depends(get_entity_from_token),  # auth
):
    # maybe someday i'll make a fancy list of rates, but for now it is what it is
    return currency_exchange_service._raw_rates
