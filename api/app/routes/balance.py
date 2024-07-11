"""API routes for Balance observing"""

from datetime import datetime

from app.middlewares.token import get_entity_from_token
from app.models.entity import Entity
from app.schemas.balance import BalanceSchema
from app.services.balance import BalanceService
from fastapi import APIRouter, Depends

balance_router = APIRouter(prefix="/balances", tags=["Balances"])


@balance_router.get("/{entity_id}", response_model=BalanceSchema)
def get_balance(
    entity_id: int,
    specific_date: datetime | None = None,
    balance_service: BalanceService = Depends(),
    actor_entity: Entity = Depends(get_entity_from_token),
):
    return balance_service.get_balances(
        entity_id=entity_id, specific_date=specific_date
    )
