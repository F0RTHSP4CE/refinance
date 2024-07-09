from dataclasses import dataclass
from datetime import datetime


@dataclass
class Entity:
    id: int
    name: str
    comment: str
    created_at: datetime
    telegram_id: int
    tags: list[dict]
    active: bool


@dataclass
class Balance:
    confirmed: dict[str, float]
    non_confirmed: dict[str, float]


@dataclass
class Transaction:
    id: int
    amount: float
    actor_entity_id: int
    actor_entity: Entity
    from_entity_id: int
    from_entity: Entity
    to_entity_id: int
    to_entity: Entity
    created_at: datetime
    currency: str
    confirmed: bool
    tags: list[dict]
    comment: str
