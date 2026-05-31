"""DTOs for the public guest donation endpoint."""

from decimal import Decimal
from uuid import UUID

from app.config import Config, get_config
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field, field_validator


class DonationCreateSchema(BaseModel):
    amount: Decimal
    currency: str = Field(min_length=1, max_length=10)
    comment: str = Field(default="", max_length=500)

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


class DonationSubscribeSchema(BaseModel):
    amount: Decimal
    currency: str = Field(min_length=1, max_length=10)
    comment: str = Field(default="", max_length=500)
    success_url: str = Field(min_length=1)
    cancel_url: str = Field(min_length=1)

    @field_validator("amount")
    def amount_must_be_positive(cls, v):
        if v > 0:
            return v
        raise ValueError("Amount must be greater than 0")

    @field_validator("currency")
    def currency_uppercase(cls, v):
        return v.strip().upper()


class DonationSubscribeResponseSchema(BaseModel):
    checkout_session_url: str


class DonationPortalResponseSchema(BaseModel):
    portal_url: str


def get_validated_donation(
    schema: DonationCreateSchema,
    config: Config = Depends(get_config),
) -> DonationCreateSchema:
    """Dependency that applies config-driven amount bounds to DonationCreateSchema."""
    if schema.amount < config.donation_min_amount:
        raise HTTPException(
            status_code=422,
            detail=f"Amount must be at least {config.donation_min_amount}",
        )
    if schema.amount > config.donation_max_amount:
        raise HTTPException(
            status_code=422,
            detail=f"Amount must be at most {config.donation_max_amount}",
        )
    return schema


def get_validated_subscribe(
    schema: DonationSubscribeSchema,
    config: Config = Depends(get_config),
) -> DonationSubscribeSchema:
    """Dependency that applies config-driven amount bounds to DonationSubscribeSchema."""
    if schema.amount < config.donation_min_amount:
        raise HTTPException(
            status_code=422,
            detail=f"Amount must be at least {config.donation_min_amount}",
        )
    if schema.amount > config.donation_max_amount:
        raise HTTPException(
            status_code=422,
            detail=f"Amount must be at most {config.donation_max_amount}",
        )
    return schema
