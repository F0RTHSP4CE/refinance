"""API routes for Balance observing"""

from app.dependencies.services import get_balance_service
from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.balance import BalanceSchema
from app.services.balance import BalanceService
from fastapi import APIRouter, Depends, Query

balance_router = APIRouter(prefix="/balances", tags=["Balances"])


@balance_router.get("", response_model=dict[int, BalanceSchema])
def get_balances(
    entity_ids: list[int] = Query(default_factory=list),
    balance_service: BalanceService = Depends(get_balance_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return balance_service.get_balances_many(entity_ids=entity_ids)


@balance_router.get("/{entity_id}", response_model=BalanceSchema)
def get_balance(
    entity_id: int,
    balance_service: BalanceService = Depends(get_balance_service),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return balance_service.get_balances(entity_id=entity_id)
