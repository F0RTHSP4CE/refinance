import enum
from dataclasses import dataclass, field, fields
from datetime import datetime
from decimal import Decimal
from typing import Optional, Tuple


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
    from_treasury_id: int | None = None
    to_treasury_id: int | None = None
    from_treasury: Treasury | None = None
    to_treasury: Treasury | None = None


class DepositProvider(enum.Enum):
    CRYPTAPI = "cryptapi"


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
class MonthlyFee:
    year: int
    month: int
    amounts: dict[str, Decimal]
    total_usd: Decimal
    paid: bool


@dataclass
class ResidentFee:
    entity: Entity
    fees: list[MonthlyFee]
    total_usd_series: list[Decimal] = field(default_factory=list)
    sparkline_points: str = ""
    sparkline_segments: list[str] = field(default_factory=list)
    sparkline_dots: list[Tuple[float, float]] = field(default_factory=list)
    sparkline_last_point: Optional[Tuple[float, float]] = None
    max_total_usd: Decimal = Decimal("0")


@dataclass
class ResidentFeeFilters:
    months: int = 12
