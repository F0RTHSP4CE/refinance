"""DTOs for Stripe authorization management."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from app.models.stripe_authorization import StripeAuthorizationMode
from app.schemas.base import (
    BaseReadSchema,
    BaseSchema,
    BaseUpdateSchema,
    CurrencyDecimal,
)
from pydantic import field_validator, model_validator


class StripeAuthorizationSchema(BaseReadSchema):
    entity_id: int
    stripe_customer_id: str
    stripe_payment_method_id: str
    mode: StripeAuthorizationMode
    static_amount: CurrencyDecimal
    static_currency: str | None = None
    donation_recipient_entity_id: int | None = None
    active: bool
    priority: int
    consecutive_error_count: int
    last_error: str | None = None
    last_attempt_at: datetime | None = None
    last_success_at: datetime | None = None
    card_brand: str | None = None
    card_last4: str | None = None
    card_exp_month: int | None = None
    card_exp_year: int | None = None


class StripeAuthorizationSetupSchema(BaseSchema):
    mode: Literal["entity_dynamic", "guest_static"] = "entity_dynamic"
    static_amount: Decimal | None = None
    static_currency: str | None = None
    entity_id: int | None = None
    success_url: str | None = None
    cancel_url: str | None = None
    donation_comment: str | None = None
    donation_recipient_entity_id: int | None = None

    @field_validator("static_currency")
    def normalize_currency(cls, v):
        return v.upper().strip() if v else v

    @model_validator(mode="after")
    def validate_mode_fields(self):
        if self.mode == "guest_static":
            if self.static_amount is None or self.static_amount <= 0:
                raise ValueError("guest_static mode requires static_amount > 0")
            if not self.static_currency:
                raise ValueError("guest_static mode requires static_currency")
        else:
            self.static_amount = Decimal("0")
            self.static_currency = None
        return self


class StripeAuthorizationSessionSchema(BaseSchema):
    checkout_session_id: str
    checkout_session_url: str | None = None


class StripeAuthorizationToggleSchema(BaseUpdateSchema):
    active: bool


class StripeAuthorizationPrioritySchema(BaseUpdateSchema):
    priority: int


class StripeAuthorizationListSchema(BaseSchema):
    items: list[StripeAuthorizationSchema]


class StripeAuthorizationChargeSchema(BaseSchema):
    entity_id: int | None = None
    amount: Decimal
    currency: str

    @field_validator("currency")
    def normalize_currency(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("amount")
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v
