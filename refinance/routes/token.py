"""API routes for Token manipulation"""

from fastapi import APIRouter, Depends

from refinance.schemas.token import TokenSendReportSchema
from refinance.services.token import TokenService

token_router = APIRouter(prefix="/tokens", tags=["Tokens"])


@token_router.post("/send", response_model=TokenSendReportSchema)
def generate_and_send_new_token(
    token_service: TokenService = Depends(),
    entity_id: int | None = None,
    entity_name: str | None = None,
    entity_telegram_id: int | None = None,
):
    return token_service.generate_and_send_new_token(
        entity_id=entity_id,
        entity_name=entity_name,
        entity_telegram_id=entity_telegram_id,
    )
