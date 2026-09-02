"""Pure rule, probability, and commitment helpers for Fortune."""

import hashlib
import json
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from math import comb

from app.config import Config

MONEY_QUANTUM = Decimal("0.01")
FORTUNE_TOTAL_TILES = 100
FORTUNE_MODEL_VERSION = 1


def win_probability(total_tiles: int, server_tiles: int, player_tiles: int) -> Fraction:
    """Exact chance that two samples overlap at least once."""
    if total_tiles < 1:
        raise ValueError("total_tiles must be positive")
    if not 1 <= server_tiles <= total_tiles:
        raise ValueError("server_tiles must be between 1 and total_tiles")
    if not 1 <= player_tiles <= total_tiles:
        raise ValueError("player_tiles must be between 1 and total_tiles")
    if player_tiles > total_tiles - server_tiles:
        return Fraction(1, 1)
    return Fraction(1, 1) - Fraction(
        comb(total_tiles - server_tiles, player_tiles),
        comb(total_tiles, player_tiles),
    )


def fraction_decimal(value: Fraction) -> Decimal:
    return Decimal(value.numerator) / Decimal(value.denominator)


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class FortuneRules:
    currency: str
    currencies: tuple[str, ...]
    min_stake: Decimal
    max_stake: Decimal
    stake_presets: tuple[Decimal, ...]
    player_tile_count: int
    boosted_player_tile_count: int
    server_tile_count: int
    prize_multiplier: Decimal
    boost_cost_multiplier: Decimal
    total_tiles: int = FORTUNE_TOTAL_TILES
    model_version: int = FORTUNE_MODEL_VERSION

    def __post_init__(self) -> None:
        if self.model_version != FORTUNE_MODEL_VERSION:
            raise ValueError("Unsupported Fortune model version")
        if self.total_tiles != FORTUNE_TOTAL_TILES:
            raise ValueError("Fortune uses a fixed 10x10 grid")
        if not self.currency.isalpha() or len(self.currency) != 3:
            raise ValueError("Fortune currency must be a three-letter code")
        if (
            not self.currencies
            or len(self.currencies) != len(set(self.currencies))
            or any(len(value) != 3 or not value.isalpha() for value in self.currencies)
        ):
            raise ValueError("Fortune currencies must be unique three-letter codes")
        if self.currency not in self.currencies:
            raise ValueError("Fortune default currency must be selectable")
        if not self.min_stake.is_finite() or not self.max_stake.is_finite():
            raise ValueError("Fortune stake limits must be finite")
        if self.min_stake <= 0 or self.max_stake < self.min_stake:
            raise ValueError("Fortune stake limits are invalid")
        if self.min_stake != money(self.min_stake) or self.max_stake != money(
            self.max_stake
        ):
            raise ValueError("Fortune stake limits must use cent precision")
        if not self.stake_presets:
            raise ValueError("Fortune needs at least one stake preset")
        if any(
            not value.is_finite()
            or value != money(value)
            or value < self.min_stake
            or value > self.max_stake
            for value in self.stake_presets
        ):
            raise ValueError("Fortune stake presets must be cents within the limits")
        win_probability(
            self.total_tiles, self.server_tile_count, self.player_tile_count
        )
        win_probability(
            self.total_tiles,
            self.server_tile_count,
            self.boosted_player_tile_count,
        )
        if self.boosted_player_tile_count <= self.player_tile_count:
            raise ValueError("Fortune boost must add selectable tiles")
        if self.boosted_probability <= self.base_probability:
            raise ValueError("Fortune boost must increase the win probability")
        if (
            not self.prize_multiplier.is_finite()
            or not self.boost_cost_multiplier.is_finite()
        ):
            raise ValueError("Fortune multipliers must be finite")
        if self.prize_multiplier <= self.boost_cost_multiplier:
            raise ValueError("Fortune prize must exceed the boosted play cost")
        if self.boost_cost_multiplier <= Decimal("1"):
            raise ValueError("Fortune boost cost multiplier must exceed one")

    @classmethod
    def from_config(cls, config: Config) -> "FortuneRules":
        return cls(
            currency=config.fortune_currency.strip().lower(),
            currencies=tuple(config.fortune_currencies),
            min_stake=config.fortune_min_stake,
            max_stake=config.fortune_max_stake,
            stake_presets=tuple(config.fortune_stake_presets),
            player_tile_count=config.fortune_player_tile_count,
            boosted_player_tile_count=config.fortune_boosted_player_tile_count,
            server_tile_count=config.fortune_server_tile_count,
            prize_multiplier=config.fortune_prize_multiplier,
            boost_cost_multiplier=config.fortune_boost_cost_multiplier,
        )

    @classmethod
    def from_snapshot(cls, snapshot: dict) -> "FortuneRules":
        currency = str(snapshot["currency"]).lower()
        return cls(
            currency=currency,
            currencies=tuple(
                str(value).lower() for value in snapshot.get("currencies", [currency])
            ),
            min_stake=Decimal(snapshot["min_stake"]),
            max_stake=Decimal(snapshot["max_stake"]),
            stake_presets=tuple(Decimal(value) for value in snapshot["stake_presets"]),
            player_tile_count=int(snapshot["player_tile_count"]),
            boosted_player_tile_count=int(snapshot["boosted_player_tile_count"]),
            server_tile_count=int(snapshot["server_tile_count"]),
            prize_multiplier=Decimal(snapshot["prize_multiplier"]),
            boost_cost_multiplier=Decimal(snapshot["boost_cost_multiplier"]),
            total_tiles=int(snapshot["total_tiles"]),
            model_version=int(snapshot["model_version"]),
        )

    @property
    def base_probability(self) -> Fraction:
        return win_probability(
            self.total_tiles, self.server_tile_count, self.player_tile_count
        )

    @property
    def boosted_probability(self) -> Fraction:
        return win_probability(
            self.total_tiles,
            self.server_tile_count,
            self.boosted_player_tile_count,
        )

    @property
    def relative_probability_increase(self) -> Fraction:
        return (
            self.boosted_probability - self.base_probability
        ) / self.base_probability

    def snapshot(self) -> dict:
        return {
            "model_version": self.model_version,
            "total_tiles": self.total_tiles,
            "currency": self.currency,
            "currencies": list(self.currencies),
            "min_stake": format(self.min_stake, ".2f"),
            "max_stake": format(self.max_stake, ".2f"),
            "stake_presets": [format(value, ".2f") for value in self.stake_presets],
            "player_tile_count": self.player_tile_count,
            "boosted_player_tile_count": self.boosted_player_tile_count,
            "server_tile_count": self.server_tile_count,
            "prize_multiplier": str(self.prize_multiplier),
            "boost_cost_multiplier": str(self.boost_cost_multiplier),
            "base_win_probability": str(fraction_decimal(self.base_probability)),
            "boosted_win_probability": str(fraction_decimal(self.boosted_probability)),
            "relative_probability_increase": str(
                fraction_decimal(self.relative_probability_increase)
            ),
        }

    def required_player_tiles(self, boosted: bool) -> int:
        return self.boosted_player_tile_count if boosted else self.player_tile_count

    def total_cost(self, stake: Decimal, boosted: bool) -> Decimal:
        return money(stake * (self.boost_cost_multiplier if boosted else Decimal(1)))

    def maximum_allowed_stake(self, fortune_balance: Decimal) -> Decimal:
        balance = Decimal(str(fortune_balance or "0"))
        if not balance.is_finite() or balance <= 0:
            return Decimal("0.00")
        max_allowed = min(self.max_stake, balance / self.prize_multiplier)
        limit = money(max_allowed)
        if limit < self.min_stake:
            return Decimal("0.00")
        return limit

    def gross_prize(self, stake: Decimal) -> Decimal:
        return money(stake * self.prize_multiplier)


def commitment_source(rules: dict, server_tiles: list[int], nonce: str) -> str:
    return json.dumps(
        {"nonce": nonce, "rules": rules, "server_tiles": sorted(server_tiles)},
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_hex(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()
