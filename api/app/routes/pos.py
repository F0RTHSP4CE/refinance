"""POS route for processing point-of-sale payments."""

from app.dependencies.services import get_pos_service
from app.middlewares.pos import require_pos_secret
from app.schemas.pos import POSChargeRequest, POSChargeResponse
from app.services.pos import POSService
from fastapi import APIRouter, Depends

pos_router = APIRouter(prefix="/pos", tags=["POS"])


@pos_router.post("/charge", response_model=POSChargeResponse)
def pos_charge(
    payload: POSChargeRequest,
    _: None = Depends(require_pos_secret),
    pos_service: POSService = Depends(get_pos_service),
):
    entity, balance = pos_service.pos(
        entity_name=payload.entity_name,
        amount=payload.amount,
        currency=payload.currency,
        to_entity_id=payload.to_entity_id,
        comment=payload.comment,
    )
    return POSChargeResponse(entity=entity, balance=balance)
