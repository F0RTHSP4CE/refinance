"""DTO for Token"""

from app.schemas.base import BaseSchema


class TokenSendRequestSchema(BaseSchema):
    entity_name: str


class TokenResponseSchema(BaseSchema):
    token: str


class TokenSendReportSchema(BaseSchema):
    entity_found: bool
    token_generated: bool
    message_sent: bool


class TelegramAuthSchema(BaseSchema):
    id: int
    auth_date: int
    hash: str
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
