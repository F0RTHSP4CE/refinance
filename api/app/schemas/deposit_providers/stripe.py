"""DTO for Stripe deposit provider."""

from decimal import Decimal

from pydantic import BaseModel, field_validator


class StripeDepositCreateSchema(BaseModel):
    to_entity_id: int
    amount: Decimal
    currency: str = "GEL"
    success_url: str | None = None
    cancel_url: str | None = None

    @field_validator("amount")
    def amount_must_be_positive(cls, v):
        if v > 0:
            return v
        raise ValueError("Amount must be greater than 0")

    @field_validator("currency")
    def currency_uppercase(cls, v):
        return v.upper().strip()
