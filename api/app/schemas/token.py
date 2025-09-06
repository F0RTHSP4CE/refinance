"""DTO for Token"""

from app.schemas.base import BaseSchema


class TokenSendRequestSchema(BaseSchema):
    entity_name: str


class TokenByCardHashRequestSchema(BaseSchema):
    card_hash: str


class TokenResponseSchema(BaseSchema):
    token: str


class TokenSendReportSchema(BaseSchema):
    entity_found: bool
    token_generated: bool
    message_sent: bool
