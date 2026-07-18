import enum
from dataclasses import dataclass, field, fields
from datetime import date, datetime
from decimal import Decimal


@dataclass
class Base:
    id: int
    comment: str
    created_at: datetime
    modified_at: datetime | None


@dataclass
class Tag(Base):
    name: str


@dataclass
class Entity(Base):
    name: str
    auth: dict | None
    tags: list[Tag]
    active: bool


@dataclass
class Balance:
    draft: dict[str, Decimal]
    completed: dict[str, Decimal]


@dataclass
class Treasury(Base):
    name: str
    active: bool
    balances: Balance


class TransactionStatus(enum.Enum):
    DRAFT = "draft"
    COMPLETED = "completed"


class DepositStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Transaction(Base):
    amount: Decimal
    actor_entity_id: int
    actor_entity: Entity
    from_entity_id: int
    from_entity: Entity
    to_entity_id: int
    to_entity: Entity
    currency: str
    status: str
    tags: list[Tag]
    invoice_id: int | None = None
    invoice_item_id: int | None = None
    from_treasury_id: int | None = None
    to_treasury_id: int | None = None
    from_treasury: Treasury | None = None
    to_treasury: Treasury | None = None


class InvoiceStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


@dataclass
class InvoiceAmount:
    currency: str
    amount: Decimal


@dataclass
class InvoiceItem(Base):
    invoice_id: int
    amounts: list[InvoiceAmount]
    to_entity_id: int | None = None
    to_entity: "Entity | None" = None
    to_tag_id: int | None = None
    to_tag: "Tag | None" = None
    transaction_id: int | None = None

    def __post_init__(self):
        self.amounts = [
            InvoiceAmount(**a) if isinstance(a, dict) else a for a in self.amounts
        ]
        if isinstance(self.to_entity, dict):
            self.to_entity = Entity(**self.to_entity)
        if isinstance(self.to_tag, dict):
            self.to_tag = Tag(**self.to_tag)


@dataclass
class Invoice(Base):
    actor_entity_id: int
    actor_entity: Entity
    from_entity_id: int
    from_entity: Entity
    amounts: list[InvoiceAmount]
    status: InvoiceStatus
    tags: list[Tag]
    items: list[InvoiceItem] = field(default_factory=list)
    to_entity_id: int | None = None
    to_entity: Entity | None = None
    transaction_id: int | None = None
    billing_period: date | None = None
    paid_amount: Decimal | None = None
    paid_currency: str | None = None
    display_amounts: list[tuple[str, Decimal]] = field(default_factory=list, init=False)

    def __post_init__(self):
        self.items = [
            InvoiceItem(**i) if isinstance(i, dict) else i for i in self.items
        ]


class DepositProvider(enum.Enum):
    CRYPTAPI = "cryptapi"
    KEEPZ = "keepz"
    STRIPE = "stripe"


@dataclass
class Deposit(Base):
    amount: Decimal
    actor_entity_id: int
    actor_entity: Entity
    from_entity_id: int
    from_entity: Entity
    to_entity_id: int
    to_entity: Entity
    to_treasury_id: int | None
    to_treasury: Treasury | None
    currency: str
    status: DepositStatus
    provider: DepositProvider
    details: dict | None
    tags: list[Tag]


@dataclass
class StripeAuthorization(Base):
    entity_id: int
    stripe_customer_id: str
    stripe_payment_method_id: str
    mode: str
    static_amount: Decimal
    static_currency: str | None
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


@dataclass
class SplitParticipant(Base):
    entity: Entity
    fixed_amount: Decimal | None


@dataclass
class SplitSharePreview(Base):
    current_share: Decimal
    next_share: Decimal


@dataclass
class Split(Base):
    amount: Decimal
    actor_entity: Entity
    recipient_entity: Entity
    participants: list[SplitParticipant]
    performed: bool
    share_preview: SplitSharePreview
    performed_transactions: list[Transaction]
    collected_amount: Decimal
    currency: str
    tags: list[Tag]


@dataclass
class CurrencyExchangePreviewResponse:
    entity_id: int
    source_currency: str
    source_amount: Decimal
    target_currency: str
    target_amount: Decimal
    rate: Decimal


@dataclass
class CurrencyExchangeReceipt:
    source_currency: str
    source_amount: Decimal
    target_currency: str
    target_amount: Decimal
    rate: Decimal
    transactions: list[Transaction]


@dataclass
class AutoBalanceExchangeItem:
    source_currency: str
    source_amount: Decimal
    target_currency: str
    target_amount: Decimal
    rate: Decimal


@dataclass
class AutoBalanceEntityPlan:
    entity_id: int
    entity_name: str
    exchanges: list[AutoBalanceExchangeItem]


@dataclass
class AutoBalancePreview:
    plans: list[AutoBalanceEntityPlan]


@dataclass
class AutoBalanceEntityReceipt:
    entity_id: int
    entity_name: str
    receipts: list[CurrencyExchangeReceipt]


@dataclass
class AutoBalanceRunResult:
    results: list[AutoBalanceEntityReceipt]


@dataclass
class MonthlyFee:
    year: int
    month: int
    amounts: dict[str, Decimal]
    unpaid_invoice_id: int | None = None
    paid_invoice_id: int | None = None
    unpaid_invoice_amounts: dict[str, Decimal] | None = None


@dataclass
class Fee:
    entity: Entity
    fees: list[MonthlyFee]


@dataclass
class FeeFilters:
    months: int = 12
