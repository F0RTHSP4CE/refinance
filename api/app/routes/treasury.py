"""API routes for Treasury manipulation"""

from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.base import PaginationSchema
from app.schemas.treasury import (
    TreasuryCreateSchema,
    TreasuryFiltersSchema,
    TreasurySchema,
    TreasuryUpdateSchema,
)
from app.services.treasury import TreasuryService
from fastapi import APIRouter, Depends

treasury_router = APIRouter(prefix="/treasuries", tags=["Treasuries"])


@treasury_router.post("", response_model=TreasurySchema)
def create_treasury(
    treasury: TreasuryCreateSchema,
    service: TreasuryService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return service.create(treasury)


@treasury_router.get("/{treasury_id}", response_model=TreasurySchema)
def read_treasury(
    treasury_id: int,
    service: TreasuryService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return service.get(treasury_id)


@treasury_router.get("", response_model=PaginationSchema[TreasurySchema])
def read_treasuries(
    filters: TreasuryFiltersSchema = Depends(),
    skip: int = 0,
    limit: int = 100,
    service: TreasuryService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return service.get_all(filters, skip, limit)


@treasury_router.patch("/{treasury_id}", response_model=TreasurySchema)
def update_treasury(
    treasury_id: int,
    treasury_update: TreasuryUpdateSchema,
    service: TreasuryService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return service.update(treasury_id, treasury_update)


@treasury_router.delete("/{treasury_id}")
def delete_treasury(
    treasury_id: int,
    service: TreasuryService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
) -> int:
    return service.delete(treasury_id)


@treasury_router.get("/overdraft/{transaction_id}", response_model=bool)
def check_overdraft(
    transaction_id: int,
    service: TreasuryService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return service.transaction_will_overdraft_treasury(transaction_id)
