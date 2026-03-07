"""Middleware/dependency for POS endpoint protection."""

from app.config import Config, get_config
from fastapi import Depends, Header, HTTPException


def require_pos_secret(
    x_pos_secret: str = Header(description="Secret key for POS endpoint access"),
    config: Config = Depends(get_config),
):
    if not config.pos_secret or x_pos_secret != config.pos_secret:
        raise HTTPException(status_code=403, detail="Forbidden")
