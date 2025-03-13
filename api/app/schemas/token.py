"""DTO for Token"""

from app.schemas.base import BaseSchema


class TokenRequestSchema(BaseSchema):
    entity_id: int | None = None
    entity_name: str | None = None
    entity_telegram_id: int | None = None


class TokenSendReportSchema(BaseSchema):
    entity_found: bool
    token_generated: bool
    message_sent: bool
