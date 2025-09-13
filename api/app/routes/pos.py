"""POS route for processing point-of-sale card payments."""

from decimal import Decimal

from app.schemas.pos import POSChargeRequest, POSChargeResponse
from app.services.pos import POSService
from fastapi import APIRouter, Depends

pos_router = APIRouter(prefix="/pos", tags=["POS"])


@pos_router.post("/charge/by-card", response_model=POSChargeResponse)
def pos_charge(
    payload: POSChargeRequest,
    pos_service: POSService = Depends(),
):
    entity, balance = pos_service.pos(
        card_hash=payload.card_hash,
        amount=payload.amount,
        currency=payload.currency,
        to_entity_id=payload.to_entity_id,
        comment=payload.comment,
    )
    return POSChargeResponse(entity=entity, balance=balance)
