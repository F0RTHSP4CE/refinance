"""API routes for Token manipulation"""

from app.dependencies.services import get_token_service
from app.schemas.token import (
    TokenResponseSchema,
    TokenSendReportSchema,
    TokenSendRequestSchema,
)
from app.services.token import TokenService
from fastapi import APIRouter, Depends

token_router = APIRouter(prefix="/tokens", tags=["Tokens"])


@token_router.post("/send", response_model=TokenSendReportSchema)
def generate_and_send_new_token(
    request: TokenSendRequestSchema,
    token_service: TokenService = Depends(get_token_service),
):
    return token_service.generate_and_send_new_token(
        entity_name=request.entity_name,
    )
