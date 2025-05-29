"""API routes for deposit providers"""

from typing import Annotated

from app.errors.common import NotFoundError
from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.deposit_providers.cryptapi import (
    CryptAPICallbackSchema,
    CryptAPIDepositCreateSchema,
)
from app.services.deposit_providers.cryptapi import CryptAPIDepositProviderService
from fastapi import APIRouter, Depends, Path, Query

from app.schemas.base import PaginationSchema
from app.schemas.deposit import DepositCreateSchema, DepositFiltersSchema, DepositSchema, DepositUpdateSchema
from app.services.deposit import DepositService

deposits_router = APIRouter(prefix="/deposits", tags=["Deposits"])


@deposits_router.post("/providers/cryptapi")
def cryptapi_create_deposit(
    schema: CryptAPIDepositCreateSchema = Depends(),
    cryptapi_deposit_provider_service: CryptAPIDepositProviderService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return cryptapi_deposit_provider_service.create_deposit(schema, actor_entity)


@deposits_router.post("", response_model=DepositSchema)
def create_deposit(
    deposit: DepositCreateSchema,
    deposit_service: DepositService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return deposit_service.create(
        deposit, overrides={"actor_entity_id": actor_entity.id}
    )


@deposits_router.get("/{deposit_id}", response_model=DepositSchema)
def read_deposit(
    deposit_id: int,
    deposit_service: DepositService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return deposit_service.get(deposit_id)


@deposits_router.get("", response_model=PaginationSchema[DepositSchema])
def read_deposits(
    filters: DepositFiltersSchema = Depends(),
    skip: int = 0,
    limit: int = 100,
    deposit_service: DepositService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return deposit_service.get_all(filters, skip, limit)


@deposits_router.patch("/{deposit_id}", response_model=DepositSchema)
def update_deposit(
    deposit_id: int,
    deposit_update: DepositUpdateSchema,
    deposit_service: DepositService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return deposit_service.update(deposit_id, deposit_update)


@deposits_router.delete("/{deposit_id}")
def delete_deposit(
    deposit_id: int,
    deposit_service: DepositService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
) -> int:
    return deposit_service.delete(deposit_id)
