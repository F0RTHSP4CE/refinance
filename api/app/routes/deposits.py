"""API routes for deposit providers"""

from typing import Annotated

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
from app.services.deposit_providers.keepz import KeepzDepositProviderService
from fastapi import APIRouter, Depends, Path, Query

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
