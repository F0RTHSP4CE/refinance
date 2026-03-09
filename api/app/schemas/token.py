"""DTO for Token"""

from typing import Literal

from app.schemas.base import BaseSchema
from pydantic import ConfigDict


class TokenSendRequestSchema(BaseSchema):
    entity_name: str


class TokenResponseSchema(BaseSchema):
    token: str


class TokenSendReportSchema(BaseSchema):
    entity_found: bool
    token_generated: bool
    message_sent: bool


class TelegramAuthPayloadSchema(BaseSchema):
    id: int
    first_name: str
    auth_date: int
    hash: str
    username: str | None = None
    last_name: str | None = None
    photo_url: str | None = None
    link_to_current_entity: bool = False

    model_config = ConfigDict(extra="allow")


class TelegramLoginResponseSchema(TokenResponseSchema):
    entity_id: int
    linked: bool = False


class TelegramAuthConfigResponseSchema(BaseSchema):
    enabled: bool
    bot_username: str | None = None
    reason: Literal["missing_bot_username", "missing_bot_token"] | None = None
