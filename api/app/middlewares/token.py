"""Middleware for Entity authentication"""

from app.dependencies.services import get_token_service
from app.services.token import TokenService
from fastapi import Depends, Header


def get_entity_from_token(
    x_token: str = Header(
        description="API token for Entity authentication",
    ),
    token_service: TokenService = Depends(get_token_service),
):
    return token_service.get_entity_from_token(x_token)
