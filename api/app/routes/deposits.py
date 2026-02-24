"""API routes for deposit providers"""

from typing import Annotated

from app.config import Config, get_config
from app.dependencies.services import (
    get_cryptapi_deposit_provider_service,
    get_deposit_service,
    get_keepz_deposit_provider_service,
)
from app.errors.common import NotFoundError
from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.base import PaginationSchema
from app.schemas.deposit import DepositFiltersSchema, DepositSchema
from app.schemas.deposit_providers.cryptapi import (
    CryptAPICallbackSchema,
    CryptAPIDepositCreateSchema,
)
from app.schemas.deposit_providers.keepz import KeepzDepositCreateSchema
from app.services.deposit import DepositService
from app.services.deposit_providers.cryptapi import CryptAPIDepositProviderService
from app.models.deposit import DepositStatus
from app.services.deposit_providers.keepz import (
    DEV_MODE_PAYMENT_URL,
    KeepzDepositProviderService,
)
from fastapi import APIRouter, Depends, HTTPException, Path, Query

deposits_router = APIRouter(prefix="/deposits", tags=["DepositProviders"])


@deposits_router.get("", response_model=PaginationSchema[DepositSchema])
def read_deposits(
    filters: DepositFiltersSchema = Depends(),
    skip: int = 0,
    limit: int = 100,
    deposit_service: DepositService = Depends(get_deposit_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return deposit_service.get_all(filters, skip, limit)


@deposits_router.get("/{deposit_id}", response_model=DepositSchema)
def read_deposit(
    deposit_id: int,
    deposit_service: DepositService = Depends(get_deposit_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return deposit_service.get(deposit_id)


@deposits_router.post("/providers/cryptapi", response_model=DepositSchema)
def cryptapi_create_deposit(
    schema: CryptAPIDepositCreateSchema = Depends(),
    cryptapi_deposit_provider_service: CryptAPIDepositProviderService = Depends(
        get_cryptapi_deposit_provider_service
    ),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return cryptapi_deposit_provider_service.create_deposit(schema, actor_entity)


@deposits_router.post("/providers/keepz", response_model=DepositSchema)
def keepz_create_deposit(
    schema: KeepzDepositCreateSchema = Depends(),
    keepz_deposit_provider_service: KeepzDepositProviderService = Depends(
        get_keepz_deposit_provider_service
    ),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return keepz_deposit_provider_service.create_deposit(schema, actor_entity)


@deposits_router.post("/{deposit_id}/complete-dev", response_model=DepositSchema)
def complete_deposit_dev(
    deposit_id: int,
    deposit_service: DepositService = Depends(get_deposit_service),
    config: Config = Depends(get_config),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    """Complete a Keepz dev-mode deposit (mock payment URL). Dev only."""
    if not config.keepz_dev_mode:
        raise HTTPException(
            403,
            "Dev mode not enabled. Set REFINANCE_KEEPZ_DEV_MODE=1 and restart the API.",
        )
    deposit = deposit_service.get(deposit_id)
    if deposit.provider != "keepz" or deposit.status != DepositStatus.PENDING:
        raise HTTPException(
            400,
            "Deposit cannot be completed via dev endpoint. Must be a pending Keepz deposit.",
        )
    keepz_details = (deposit.details or {}).get("keepz") or {}
    payment_url = keepz_details.get("payment_url") or keepz_details.get(
        "payment_short_url"
    )
    if payment_url != DEV_MODE_PAYMENT_URL:
        raise HTTPException(
            400,
            "Not a dev-mode deposit. This deposit was created with a real Keepz payment URL.",
        )
    if deposit.to_entity_id != actor_entity.id:
        raise HTTPException(
            403,
            "Deposit belongs to another entity. You can only complete deposits for your own account.",
        )
    deposit_service.complete(deposit_id)
    return deposit_service.get(deposit_id)
