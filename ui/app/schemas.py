import enum
from dataclasses import dataclass
from datetime import datetime
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


class TransactionStatus(enum.Enum):
    DRAFT = "draft"
    COMPLETED = "completed"


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
    actor_entity_id: int
    actor_entity: Entity
    recipient_entity_id: int
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
