"""API routes for Token manipulation"""

from app.schemas.token import TokenRequestSchema, TokenSendReportSchema
from app.services.token import TokenService
from fastapi import APIRouter, Depends

token_router = APIRouter(prefix="/tokens", tags=["Tokens"])


@token_router.post("/request", response_model=TokenSendReportSchema)
def generate_and_send_new_token(
    token_request_schema: TokenRequestSchema,
    token_service: TokenService = Depends(),
):
    return token_service.generate_and_send_new_token(
        entity_id=token_request_schema.entity_id,
        entity_name=token_request_schema.entity_name,
        entity_telegram_id=token_request_schema.entity_telegram_id,
    )
