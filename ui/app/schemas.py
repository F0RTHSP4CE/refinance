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
    confirmed: dict[str, Decimal]
    non_confirmed: dict[str, Decimal]


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
    confirmed: bool
    tags: list[Tag]


@dataclass
class Split(Base):
    amount: Decimal
    actor_entity_id: int
    actor_entity: Entity
    recipient_entity_id: int
    recipient_entity: Entity
    participants: list[Entity]
    performed: bool
    share_preview: Decimal
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
