"""API routes for Balance observing"""

from fastapi import APIRouter, Depends

from refinance.schemas.balance import BalanceSchema
from refinance.services.balance import BalanceService

balance_router = APIRouter(prefix="/balances", tags=["Balances"])


@balance_router.get("/{entity_id}", response_model=BalanceSchema)
def get_balances(entity_id: int, balance_service: BalanceService = Depends()):
    return balance_service.get_balances(entity_id)
