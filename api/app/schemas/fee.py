"""DTOs for fees"""

from datetime import date, datetime
from decimal import Decimal

from app.models.fee import FeePolicyOverrideKind, FeeTargetType
from app.models.transaction import TransactionStatus
from app.schemas.base import BaseSchema, CurrencyDecimal
from app.schemas.entity import EntitySchema
from pydantic import Field, field_validator


class MonthlyFeeSchema(BaseSchema):
    year: int
    month: int
    amounts: dict[str, CurrencyDecimal]
    unpaid_invoice_id: int | None = None
    paid_invoice_id: int | None = None
    unpaid_invoice_amounts: dict[str, CurrencyDecimal] | None = None


class FeeSchema(BaseSchema):
    entity: EntitySchema
    fees: list[MonthlyFeeSchema]


class FeeFiltersSchema(BaseSchema):
    months: int = 12


class FeeAmountSchema(BaseSchema):
    tag_id: int
    currency: str
    amount: CurrencyDecimal


class FeeRuleSchema(BaseSchema):
    membership_tag_id: int
    label: str
    invoice_amounts: dict[str, CurrencyDecimal]
    legacy_invoice_amounts: dict[str, CurrencyDecimal]
    directed_amounts: dict[str, CurrencyDecimal]


class FeeTargetSchema(BaseSchema):
    target_type: FeeTargetType
    id: int
    name: str
    currency: str | None = None


class FeeConfigSchema(BaseSchema):
    rules: list[FeeRuleSchema]
    budget_targets: list[FeeTargetSchema]
    split_targets: list[FeeTargetSchema]
    selection_deadline_days: int


class FeeAllocationSchema(BaseSchema):
    id: int
    invoice_id: int
    component_key: str
    amounts: dict[str, CurrencyDecimal]
    extra_amounts: dict[str, CurrencyDecimal] | None = None
    target_type: FeeTargetType | None = None
    target_entity_id: int | None = None
    target_split_id: int | None = None
    selected_by_entity_id: int | None = None
    selected_at: datetime | None = None
    auto_selected: bool
    selection_deadline_at: datetime
    allocation_transaction_id: int | None = None


class FeeAllocationSelectionSchema(BaseSchema):
    has_allocation: bool
    invoice_id: int
    directed_allocation: FeeAllocationSchema | None = None
    fixed_allocations: list[FeeAllocationSchema] = Field(default_factory=list)
    budget_targets: list[FeeTargetSchema] = Field(default_factory=list)
    split_targets: list[FeeTargetSchema] = Field(default_factory=list)
    selected_target_name: str | None = None


class FeeDirectedAllocationUpdateSchema(BaseSchema):
    target_type: FeeTargetType
    target_entity_id: int | None = None
    target_split_id: int | None = None
    extra_amount: Decimal | None = None
    extra_currency: str | None = None


class FeeInvoiceBulkCreateSchema(BaseSchema):
    from_tag_ids: list[int] = Field(default_factory=list)
    billing_period: date | None = None
    notify: bool = True


class FeeInvoiceBulkCreateReportSchema(BaseSchema):
    billing_period: date
    created_count: int
    skipped_count: int
    legacy_count: int
    invoice_ids: list[int]
    notification_count: int


class FeeInvoiceSettlementCreateSchema(BaseSchema):
    currency: str
    status: TransactionStatus = TransactionStatus.DRAFT

    @field_validator("currency")
    def currency_must_be_lowercase(cls, value: str) -> str:
        return value.lower()


class FeeInvoiceSettlementSchema(BaseSchema):
    transaction_ids: list[int]
    status: TransactionStatus


class FeePolicyOverrideSchema(BaseSchema):
    id: int
    entity_id: int
    kind: FeePolicyOverrideKind
    active: bool


class FeePolicyOverrideUpdateSchema(BaseSchema):
    kind: FeePolicyOverrideKind = FeePolicyOverrideKind.LEGACY
    active: bool = True
