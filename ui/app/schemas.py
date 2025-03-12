from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class Entity:
    id: int
    name: str
    comment: str
    created_at: datetime
    modified_at: datetime | None
    telegram_id: int
    tags: list[dict]
    active: bool


@dataclass
class Balance:
    confirmed: dict[str, Decimal]
    non_confirmed: dict[str, Decimal]


@dataclass
class Transaction:
    id: int
    amount: Decimal
    actor_entity_id: int
    actor_entity: Entity
    from_entity_id: int
    from_entity: Entity
    to_entity_id: int
    to_entity: Entity
    created_at: datetime
    modified_at: datetime | None
    currency: str
    confirmed: bool
    tags: list[dict]
    comment: str
