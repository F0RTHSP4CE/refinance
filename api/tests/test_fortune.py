import hashlib
from decimal import Decimal
from fractions import Fraction

import pytest
from app.config import Config
from app.fortune import (
    FortuneRules,
    commitment_source,
    money,
    sha256_hex,
    win_probability,
)
from app.seeding import fortune_entity, fortune_tag
from app.services.balance import BalanceService
from fastapi.testclient import TestClient


class FixedRng:
    def sample(self, population, count):
        assert 7 in population
        return [7][:count]


@pytest.fixture(autouse=True)
def deterministic_fortune(monkeypatch):
    monkeypatch.setattr("app.services.fortune.secrets.SystemRandom", FixedRng)
    monkeypatch.setattr(
        "app.services.fortune.secrets.token_hex", lambda size: "ab" * size
    )


def _start(test_app: TestClient, token: str) -> dict:
    response = test_app.post("/fortune/games", headers={"x-token": token})
    assert response.status_code == 200
    return response.json()


def _play(
    test_app: TestClient,
    token: str,
    game_id: int,
    selected_tiles: list[int],
    stake: str = "10.00",
    currency: str = "usd",
    boosted: bool = False,
):
    return test_app.post(
        f"/fortune/games/{game_id}/play",
        json={
            "stake": stake,
            "currency": currency,
            "boosted": boosted,
            "selected_tiles": selected_tiles,
        },
        headers={"x-token": token},
    )


class TestFortuneMath:
    def test_default_probability_and_relative_boost(self):
        rules = FortuneRules.from_config(Config())

        assert win_probability(100, 1, 10) == Fraction(1, 10)
        assert rules.base_probability == Fraction(1, 10)
        assert rules.boosted_probability == Fraction(3, 25)
        assert rules.relative_probability_increase == Fraction(1, 5)
        assert rules.currencies == ("usd", "gel", "eur")

    def test_general_overlap_probability(self):
        assert win_probability(10, 2, 3) == Fraction(8, 15)
        assert win_probability(10, 8, 3) == 1

    @pytest.mark.parametrize(
        "total,server,player",
        [(0, 1, 1), (100, 0, 10), (100, 101, 10), (100, 1, 0)],
    )
    def test_invalid_probability_configuration(self, total, server, player):
        with pytest.raises(ValueError):
            win_probability(total, server, player)

    def test_invalid_rule_configuration(self):
        with pytest.raises(ValueError, match="selectable tiles"):
            FortuneRules.from_config(
                Config(
                    fortune_player_tile_count=12,
                    fortune_boosted_player_tile_count=10,
                )
            )

        with pytest.raises(ValueError, match="JSON list"):
            FortuneRules.from_config(Config(fortune_stake_presets_raw="not-json"))

        with pytest.raises(ValueError, match="JSON list"):
            FortuneRules.from_config(Config(fortune_currencies_raw='["usd","usd"]'))

    def test_commitment_source_is_canonical_and_verifiable(self):
        source = commitment_source(
            rules={"z": 2, "a": 1}, server_tiles=[9, 2], nonce="nonce"
        )

        assert source == (
            '{"nonce":"nonce","rules":{"a":1,"z":2},"server_tiles":[2,9]}'
        )
        assert sha256_hex(source) == hashlib.sha256(source.encode()).hexdigest()

    def test_single_currency_snapshot_remains_supported(self):
        snapshot = FortuneRules.from_config(Config()).snapshot()
        snapshot.pop("currencies")

        restored = FortuneRules.from_snapshot(snapshot)

        assert restored.currency == "usd"
        assert restored.currencies == ("usd",)

    def test_money_and_settlement_round_half_up(self):
        rules = FortuneRules.from_config(Config())

        assert money(Decimal("1.255")) == Decimal("1.26")
        assert rules.total_cost(Decimal("1.01"), boosted=True) == Decimal("1.26")
        assert rules.gross_prize(Decimal("1.01")) == Decimal("5.05")
        assert Decimal("5.05") - Decimal("1.26") == Decimal("3.79")

    def test_maximum_allowed_stake_is_capped_by_fortune_balance(self):
        rules = FortuneRules.from_config(
            Config(
                fortune_max_stake=Decimal("25.00"),
                fortune_prize_multiplier=Decimal("5"),
                fortune_boost_cost_multiplier=Decimal("1.25"),
            )
        )

        assert rules.maximum_allowed_stake(Decimal("100.00")) == Decimal("20.00")
        assert rules.maximum_allowed_stake(Decimal("40.00")) == Decimal("8.00")
        assert rules.maximum_allowed_stake(Decimal("0.00")) == Decimal("0.00")


class TestFortuneAPI:
    @pytest.fixture(autouse=True)
    def fund_fortune_entity(self, test_app: TestClient, token):
        BalanceService._cache.clear()
        BalanceService._treasury_cache.clear()

        current_balance = test_app.get(
            f"/balances/{fortune_entity.id}", headers={"x-token": token}
        ).json()
        usd_balance = Decimal(str(current_balance.get("completed", {}).get("usd", "0")))
        target_balance = Decimal("100.00")
        delta = usd_balance - target_balance

        if delta > 0:
            response = test_app.post(
                "/transactions",
                json={
                    "from_entity_id": fortune_entity.id,
                    "to_entity_id": 1,
                    "amount": str(delta.quantize(Decimal("0.01"))),
                    "currency": "usd",
                    "status": "completed",
                },
                headers={"x-token": token},
            )
        elif delta < 0:
            response = test_app.post(
                "/transactions",
                json={
                    "from_entity_id": 1,
                    "to_entity_id": fortune_entity.id,
                    "amount": str((-delta).quantize(Decimal("0.01"))),
                    "currency": "usd",
                    "status": "completed",
                },
                headers={"x-token": token},
            )
        else:
            return None

        assert response.status_code == 200
        return response.json()

    def test_seeded_fortune_entity_and_tag(self, test_app: TestClient, token):
        entity = test_app.get(
            f"/entities/{fortune_entity.id}", headers={"x-token": token}
        ).json()
        tag = test_app.get(f"/tags/{fortune_tag.id}", headers={"x-token": token}).json()

        assert entity["name"] == "fortune"
        assert [item["id"] for item in entity["tags"]] == [fortune_tag.id]
        assert tag["name"] == "fortune"

    def test_open_game_publishes_rules_without_reveal(self, test_app, token):
        game = _start(test_app, token)

        assert game["status"] == "open"
        assert len(game["commitment_sha256"]) == 64
        assert game["rules"]["base_win_probability"] == "0.1"
        assert game["rules"]["boosted_win_probability"] == "0.12"
        assert game["rules"]["relative_probability_increase"] == "0.2"
        assert game["rules"]["currencies"] == ["usd", "gel", "eur"]
        assert "server_tiles" not in game
        assert "commitment_source" not in game
        assert "selected_tiles" not in game

        fetched = test_app.get(
            f"/fortune/games/{game['id']}", headers={"x-token": token}
        ).json()
        assert fetched["commitment_sha256"] == game["commitment_sha256"]
        assert "server_tiles" not in fetched

    def test_stake_above_fortune_balance_is_rejected(self, test_app, token):
        game = _start(test_app, token)
        blocked = _play(
            test_app,
            token,
            game["id"],
            list(range(1, 11)),
            stake="21.00",
            currency="usd",
        )

        assert blocked.status_code == 422
        assert "maximum is 20.00 USD" in blocked.json()["error"]

    def test_winning_play_reveals_source_and_creates_net_transaction(
        self, test_app, token
    ):
        game = _start(test_app, token)
        response = _play(test_app, token, game["id"], list(range(1, 11)))

        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "settled"
        assert result["won"] is True
        assert result["server_tiles"] == [7]
        assert result["selected_tiles"] == list(range(1, 11))
        assert result["total_cost"] == "10.00"
        assert result["gross_prize"] == "50.00"
        assert result["currency"] == "usd"
        assert result["settlement_amount"] == "40.00"
        assert result["net_change"] == "40.00"
        assert sha256_hex(result["commitment_source"]) == result["commitment_sha256"]
        transaction = result["transaction"]
        assert transaction["from_entity_id"] == fortune_entity.id
        assert transaction["to_entity_id"] == 1
        assert transaction["actor_entity_id"] == 1
        assert transaction["amount"] == "40.00"
        assert transaction["currency"] == "usd"
        assert transaction["status"] == "completed"
        assert [tag["id"] for tag in transaction["tags"]] == [fortune_tag.id]

    def test_boosted_win_uses_entered_stake_for_prize(self, test_app, token):
        game = _start(test_app, token)
        response = _play(
            test_app,
            token,
            game["id"],
            list(range(1, 13)),
            stake="10.00",
            currency="gel",
            boosted=True,
        )

        assert response.status_code == 200
        result = response.json()
        assert result["won"] is True
        assert result["boosted"] is True
        assert result["total_cost"] == "12.50"
        assert result["gross_prize"] == "50.00"
        assert result["currency"] == "gel"
        assert result["settlement_amount"] == "37.50"
        assert result["transaction"]["amount"] == "37.50"

    def test_loss_charges_user_and_retry_is_idempotent(self, test_app, token):
        game = _start(test_app, token)
        response = _play(
            test_app,
            token,
            game["id"],
            list(range(11, 21)),
            currency="eur",
        )

        assert response.status_code == 200
        result = response.json()
        assert result["won"] is False
        assert result["net_change"] == "-10.00"
        assert result["currency"] == "eur"
        assert result["transaction"]["from_entity_id"] == 1
        assert result["transaction"]["to_entity_id"] == fortune_entity.id
        assert result["transaction"]["currency"] == "eur"
        assert result["transaction"].get("comment") is None
        transaction_id = result["transaction"]["id"]

        retry = _play(test_app, token, game["id"], list(range(1, 11)))
        assert retry.status_code == 200
        assert retry.json()["transaction"]["id"] == transaction_id
        assert retry.json()["transaction"].get("comment") is None

    @pytest.mark.parametrize(
        "stake,boosted,tiles",
        [
            ("0.99", False, list(range(1, 11))),
            ("25.01", False, list(range(1, 11))),
            ("10.00", False, list(range(1, 10))),
            ("10.00", True, list(range(1, 11))),
            ("10.00", False, list(range(92, 102))),
        ],
    )
    def test_invalid_play_is_rejected(self, test_app, token, stake, boosted, tiles):
        game = _start(test_app, token)
        response = _play(test_app, token, game["id"], tiles, stake, boosted=boosted)

        assert response.status_code == 422
        fetched = test_app.get(
            f"/fortune/games/{game['id']}", headers={"x-token": token}
        ).json()
        assert fetched["status"] == "open"

    def test_unsupported_currency_is_rejected(self, test_app, token):
        game = _start(test_app, token)

        response = _play(
            test_app,
            token,
            game["id"],
            list(range(1, 11)),
            currency="gbp",
        )

        assert response.status_code == 422

    def test_duplicate_tiles_and_fractional_cents_are_rejected(self, test_app, token):
        duplicate_game = _start(test_app, token)
        duplicate = _play(
            test_app, token, duplicate_game["id"], [1, 1] + list(range(2, 10))
        )
        assert duplicate.status_code == 422

        cents_game = _start(test_app, token)
        fractional = _play(
            test_app,
            token,
            cents_game["id"],
            list(range(1, 11)),
            stake="1.001",
        )
        assert fractional.status_code == 422

    def test_game_is_private_to_its_owner(self, test_app, token, token_factory):
        game = _start(test_app, token)
        other_token = token_factory(2)

        read = test_app.get(
            f"/fortune/games/{game['id']}", headers={"x-token": other_token}
        )
        play = _play(
            test_app, other_token, game["id"], list(range(1, 11)), stake="10.00"
        )

        assert read.status_code == 404
        assert play.status_code == 404
