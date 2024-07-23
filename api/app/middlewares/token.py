"""Middleware for Entity authentication"""

from fastapi import Depends, Header

from app.services.token import TokenService


def get_entity_from_token(
    x_token: str = Header(
        description="API token for Entity authentication",
    ),
    token_service: TokenService = Depends(),
):
    return token_service.get_entity_from_token(x_token)
