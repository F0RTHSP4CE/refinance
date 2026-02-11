"""DTO for Keepz deposit provider."""

from decimal import Decimal

from pydantic import BaseModel, field_validator


class KeepzDepositCreateSchema(BaseModel):
    to_entity_id: int
    amount: Decimal
    currency: str = "GEL"
    note: str | None = None
    commission_type: str = "SENDER"

    @field_validator("amount")
    def amount_must_be_positive(cls, v):
        if v > 0:
            return v
        raise ValueError("Amount must be greater than 0")

    @field_validator("currency")
    def currency_uppercase(cls, v):
        return v.upper().strip()
