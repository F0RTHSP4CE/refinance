"""Middleware for Entity authentication"""

from app.services.token import TokenService
from fastapi import Depends, Header


def get_entity_from_token(
    x_token: str = Header(
        description="API token for Entity authentication",
    ),
    token_service: TokenService = Depends(),
):
    return token_service.get_entity_from_token(x_token)
