"""API routes for Token manipulation"""

from app.errors.token import TokenInvalid
from app.dependencies.services import get_token_service
from app.models.entity import Entity
from app.schemas.token import (
    TelegramAuthConfigResponseSchema,
    TelegramAuthPayloadSchema,
    TelegramLoginResponseSchema,
    TokenSendReportSchema,
    TokenSendRequestSchema,
)
from app.services.token import TokenService
from fastapi import APIRouter, Depends, Header, HTTPException, status

token_router = APIRouter(prefix="/tokens", tags=["Tokens"])


@token_router.post("/send", response_model=TokenSendReportSchema)
def generate_and_send_new_token(
    request: TokenSendRequestSchema,
    token_service: TokenService = Depends(get_token_service),
):
    return token_service.generate_and_send_new_token(
        entity_name=request.entity_name,
    )


@token_router.get("/telegram-config", response_model=TelegramAuthConfigResponseSchema)
def get_telegram_auth_config(
    token_service: TokenService = Depends(get_token_service),
):
    return token_service.get_telegram_auth_config()


@token_router.post("/telegram-login", response_model=TelegramLoginResponseSchema)
def login_or_link_via_telegram(
    payload: TelegramAuthPayloadSchema,
    token_service: TokenService = Depends(get_token_service),
    x_token: str | None = Header(default=None),
):
    actor_entity: Entity | None = None
    if x_token:
        try:
            actor_entity = token_service.get_entity_from_token(x_token)
        except TokenInvalid as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid current session token.",
            ) from exc

    return token_service.login_or_link_with_telegram(
        payload=payload,
        actor_entity=actor_entity,
    )
