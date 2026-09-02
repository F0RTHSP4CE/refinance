"""API schemas for Fortune games."""

from decimal import Decimal, InvalidOperation

from app.models.fortune import FortuneGameStatus
from app.schemas.base import BaseReadSchema, BaseSchema, CurrencyDecimal
from app.schemas.transaction import TransactionSchema
from pydantic import field_validator


class FortuneRulesSchema(BaseSchema):
    model_version: int
    total_tiles: int
    currency: str
    currencies: list[str] | None = None
    min_stake: CurrencyDecimal
    max_stake: CurrencyDecimal
    stake_presets: list[CurrencyDecimal]
    player_tile_count: int
    boosted_player_tile_count: int
    server_tile_count: int
    prize_multiplier: Decimal
    boost_cost_multiplier: Decimal
    base_win_probability: Decimal
    boosted_win_probability: Decimal
    relative_probability_increase: Decimal


class FortunePlaySchema(BaseSchema):
    stake: Decimal
    currency: str
    boosted: bool = False
    selected_tiles: list[int]

    @field_validator("currency")
    @classmethod
    def currency_must_be_normalized(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("Currency must be a three-letter code")
        return normalized

    @field_validator("stake")
    @classmethod
    def stake_must_have_cent_precision(cls, value: Decimal) -> Decimal:
        try:
            if (
                not value.is_finite()
                or value <= 0
                or value != value.quantize(Decimal("0.01"))
            ):
                raise ValueError
        except InvalidOperation as exc:
            raise ValueError("Stake must be a positive amount in cents") from exc
        return value

    @field_validator("selected_tiles")
    @classmethod
    def selected_tiles_must_be_unique(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Selected tiles must be unique")
        return value


class FortuneGameSchema(BaseReadSchema):
    actor_entity_id: int
    status: FortuneGameStatus
    commitment_sha256: str
    rules: FortuneRulesSchema
    max_allowed_stake: CurrencyDecimal | None = None
    max_allowed_stakes: dict[str, CurrencyDecimal] | None = None
    stake: CurrencyDecimal | None = None
    currency: str | None = None
    boosted: bool | None = None
    total_cost: CurrencyDecimal | None = None
    gross_prize: CurrencyDecimal | None = None
    won: bool | None = None
    settlement_amount: CurrencyDecimal | None = None
    net_change: CurrencyDecimal | None = None
    selected_tiles: list[int] | None = None
    server_tiles: list[int] | None = None
    commitment_source: str | None = None
    transaction: TransactionSchema | None = None
