"""DTOs for the public guest donation endpoint."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator


class DonationCreateSchema(BaseModel):
    amount: Decimal
    currency: str
    comment: str = ""

    @field_validator("amount")
    def amount_must_be_positive(cls, v):
        if v > 0:
            return v
        raise ValueError("Amount must be greater than 0")

    @field_validator("currency")
    def currency_uppercase(cls, v):
        return v.strip().upper()


class DonationResponseSchema(BaseModel):
    deposit_uuid: UUID
    status: str
    payment_url: str | None
    amount: str
    currency: str
