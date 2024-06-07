"""Middleware for authentication, checks for avlid token in request headers"""

from fastapi import Depends, Header
from refinance.config import Config, get_config
from refinance.errors.token import TokenInvalid


def get_api_token(
    x_token: str = Header(
        default=None,
        description="API token required for authentication of API client (web-panel, telegram-bot)",
    ),
    config: Config = Depends(get_config),
):
    if x_token in config.api_tokens:
        return x_token
    else:
        raise TokenInvalid
