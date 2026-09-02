"""Commit-reveal game creation and settlement for Fortune."""

import secrets
from collections.abc import Callable
from decimal import Decimal
from random import SystemRandom

from app.config import Config, get_config
from app.dependencies.services import (
    get_balance_service,
    get_currency_exchange_service,
    get_transaction_service,
)
from app.errors.fortune import FortuneGameNotFound, InvalidFortunePlay
from app.fortune import FortuneRules, commitment_source, sha256_hex
from app.models.entity import Entity
from app.models.fortune import FortuneGame, FortuneGameStatus
from app.models.transaction import TransactionStatus
from app.schemas.fortune import FortuneGameSchema, FortunePlaySchema
from app.schemas.transaction import TransactionCreateSchema
from app.seeding import fortune_entity, fortune_tag
from app.services.balance import BalanceService
from app.services.currency_exchange import CurrencyExchangeService
from app.services.transaction import TransactionService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy.orm import Session


class FortuneService:
    def __init__(
        self,
        db: Session = Depends(get_uow),
        transaction_service: TransactionService = Depends(get_transaction_service),
        balance_service: BalanceService = Depends(get_balance_service),
        currency_exchange_service: CurrencyExchangeService = Depends(
            get_currency_exchange_service
        ),
        config: Config = Depends(get_config),
        rng: SystemRandom | None = None,
        nonce_factory: Callable[[int], str] | None = None,
    ):
        self.db = db
        self._transaction_service = transaction_service
        self._balance_service = balance_service
        self._currency_exchange_service = currency_exchange_service
        self._rules = FortuneRules.from_config(config)
        self._rng = rng or secrets.SystemRandom()
        self._nonce_factory = nonce_factory or secrets.token_hex

    def _fortune_balance_in_currency(self, currency: str) -> Decimal:
        target_currency = str(currency or "").lower().strip()
        if not target_currency:
            return Decimal("0")

        self._balance_service.invalidate_cache_entry(fortune_entity.id)
        balances = self._balance_service.get_balances(fortune_entity.id).completed or {}
        total = Decimal("0")
        for code, amount in balances.items():
            source_currency = str(code or "").lower().strip()
            if not source_currency:
                continue
            amount_value = Decimal(
                str(amount.value if hasattr(amount, "value") else amount)
            )
            if source_currency == target_currency:
                total += amount_value
                continue
            try:
                _, converted, _ = self._currency_exchange_service.calculate_conversion(
                    source_amount=amount_value,
                    target_amount=None,
                    source_currency=source_currency,
                    target_currency=target_currency,
                )
            except Exception:
                continue
            total += converted
        return total

    def max_allowed_stake_by_currency(self) -> dict[str, Decimal]:
        return {
            currency: self._rules.maximum_allowed_stake(
                self._fortune_balance_in_currency(currency)
            )
            for currency in self._rules.currencies
        }

    def create_game(self, actor_entity: Entity) -> FortuneGameSchema:
        rules = self._rules.snapshot()
        server_tiles = sorted(
            self._rng.sample(
                range(1, self._rules.total_tiles + 1),
                self._rules.server_tile_count,
            )
        )
        source = commitment_source(
            rules=rules,
            server_tiles=server_tiles,
            nonce=self._nonce_factory(32),
        )
        game = FortuneGame(
            actor_entity_id=actor_entity.id,
            status=FortuneGameStatus.OPEN,
            rules=rules,
            commitment_sha256=sha256_hex(source),
            commitment_source=source,
            server_tiles=server_tiles,
            comment="Fortune commit-reveal game",
        )
        self.db.add(game)
        self.db.flush()
        self.db.refresh(game)
        return self._to_schema(game)

    def get_game(self, game_id: int, actor_entity: Entity) -> FortuneGameSchema:
        game = (
            self.db.query(FortuneGame)
            .filter(
                FortuneGame.id == game_id,
                FortuneGame.actor_entity_id == actor_entity.id,
            )
            .first()
        )
        if game is None:
            raise FortuneGameNotFound
        return self._to_schema(game)

    def play_game(
        self, game_id: int, play: FortunePlaySchema, actor_entity: Entity
    ) -> FortuneGameSchema:
        game = (
            self.db.query(FortuneGame)
            .filter(FortuneGame.id == game_id)
            .with_for_update()
            .first()
        )
        if game is None or game.actor_entity_id != actor_entity.id:
            raise FortuneGameNotFound
        if game.status == FortuneGameStatus.SETTLED:
            return self._to_schema(game)

        rules = FortuneRules.from_snapshot(game.rules)
        selected_tiles = sorted(play.selected_tiles)
        required_count = rules.required_player_tiles(play.boosted)
        if len(selected_tiles) != required_count:
            raise InvalidFortunePlay(f"select exactly {required_count} unique tiles")
        if any(tile < 1 or tile > rules.total_tiles for tile in selected_tiles):
            raise InvalidFortunePlay(f"tiles must be between 1 and {rules.total_tiles}")
        if play.currency not in rules.currencies:
            raise InvalidFortunePlay(
                f"currency must be one of {', '.join(rules.currencies)}"
            )
        fortune_balance = self._fortune_balance_in_currency(play.currency)
        max_allowed_stake = rules.maximum_allowed_stake(fortune_balance)
        if play.stake < rules.min_stake or play.stake > rules.max_stake:
            raise InvalidFortunePlay(
                f"stake must be between {rules.min_stake:.2f} and "
                f"{rules.max_stake:.2f} {play.currency.upper()}"
            )
        if play.stake > max_allowed_stake:
            raise InvalidFortunePlay(
                f"stake exceeds the fortune balance; maximum is "
                f"{max_allowed_stake:.2f} {play.currency.upper()}"
            )

        total_cost = rules.total_cost(play.stake, play.boosted)
        gross_prize = rules.gross_prize(play.stake)
        won = bool(set(selected_tiles).intersection(game.server_tiles))
        settlement_amount = gross_prize - total_cost if won else total_cost

        if won:
            from_entity_id = fortune_entity.id
            to_entity_id = actor_entity.id
        else:
            from_entity_id = actor_entity.id
            to_entity_id = fortune_entity.id

        transaction = self._transaction_service.create(
            TransactionCreateSchema(
                from_entity_id=from_entity_id,
                to_entity_id=to_entity_id,
                amount=settlement_amount,
                currency=play.currency,
                status=TransactionStatus.COMPLETED,
                tag_ids=[fortune_tag.id],
                comment=f"Fortune game #{game.id}: win" if won else None,
            ),
            overrides={"actor_entity_id": actor_entity.id},
        )

        game.selected_tiles = selected_tiles
        game.stake = play.stake
        game.boosted = play.boosted
        game.total_cost = total_cost
        game.gross_prize = gross_prize
        game.won = won
        game.settlement_amount = settlement_amount
        game.transaction = transaction
        game.status = FortuneGameStatus.SETTLED
        self.db.flush()
        self.db.refresh(game)
        return self._to_schema(game)

    def _to_schema(self, game: FortuneGame) -> FortuneGameSchema:
        revealed = game.status == FortuneGameStatus.SETTLED
        net_change: Decimal | None = None
        if revealed and game.settlement_amount is not None:
            net_change = game.settlement_amount if game.won else -game.settlement_amount

        rules = FortuneRules.from_snapshot(game.rules)
        max_allowed_stakes = self.max_allowed_stake_by_currency()
        default_currency = rules.currency.lower()
        max_allowed_stake = max_allowed_stakes.get(default_currency, Decimal("0.00"))

        return FortuneGameSchema(
            id=game.id,
            comment=game.comment,
            created_at=game.created_at,
            modified_at=game.modified_at,
            actor_entity_id=game.actor_entity_id,
            status=game.status,
            commitment_sha256=game.commitment_sha256,
            rules=game.rules,
            max_allowed_stake=max_allowed_stake,
            max_allowed_stakes={
                currency: max_allowed_stakes.get(currency, Decimal("0.00"))
                for currency in rules.currencies
            },
            stake=game.stake if revealed else None,
            currency=(
                game.transaction.currency
                if revealed and game.transaction is not None
                else None
            ),
            boosted=game.boosted if revealed else None,
            total_cost=game.total_cost if revealed else None,
            gross_prize=game.gross_prize if revealed else None,
            won=game.won if revealed else None,
            settlement_amount=game.settlement_amount if revealed else None,
            net_change=net_change,
            selected_tiles=game.selected_tiles if revealed else None,
            server_tiles=game.server_tiles if revealed else None,
            commitment_source=game.commitment_source if revealed else None,
            transaction=game.transaction if revealed else None,
        )
