"""Schemas for EntityCard operations"""

from app.schemas.base import BaseReadSchema
from pydantic import BaseModel


class EntityCardCreateSchema(BaseModel):
    card_hash: str
    comment: str | None = None


class EntityCardReadSchema(BaseReadSchema):
    pass
    # card_hash deliberately omitted from read schema
