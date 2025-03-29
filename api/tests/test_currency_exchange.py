from decimal import Decimal

import pytest

# Import bootstrap data to use pre-existing tags and entities.
from app.bootstrap import BOOTSTRAP, Entity
from fastapi.testclient import TestClient


@pytest.fixture
def entity_one():
    """
    Use one of the pre-existing entities from BOOTSTRAP.
    We deliberately skip the currency_exchange_entity (id=11) since it's used internally.
    """
    for e in BOOTSTRAP[Entity]:
        if e.id != 11:
            return e.id


class TestCurrencyExchangeEndpoints:
    @pytest.fixture(autouse=True)
    def patch_rates(self, monkeypatch):
        """
        Override the _raw_rates property of CurrencyExchangeService so that
        tests run against fixed conversion rates.
        Fixed rates:
          - 1 USD = 3.00 GEL
          - 1 EUR = 3.50 GEL
          - GEL is the base (1 GEL = 1 GEL)
        """
        from app.services.currency_exchange import CurrencyExchangeService

        monkeypatch.setattr(
            CurrencyExchangeService,
            "_raw_rates",
            property(
                lambda self: [
                    {
                        "currencies": [
                            {"code": "usd", "rate": "3.00", "quantity": "1"},
                            {"code": "eur", "rate": "3.50", "quantity": "1"},
                            {"code": "gel", "rate": "1", "quantity": "1"},
                        ]
                    }
                ]
            ),
        )

    def test_preview(self, test_app: TestClient, token, entity_one):
        """
        Test the /currency_exchange/preview endpoint.
        With fixed rates:
          - Conversion rate from USD to EUR = (3.00 / 3.50) ≈ 0.8571
          - Converted amount for 100.00 USD ≈ 85.71 EUR
          - Displayed rate = max(3.00/3.50, 3.50/3.00) = 1.17
        """
        payload = {
            "entity_id": entity_one,
            "source_currency": "usd",
            "source_amount": "100.00",
            "target_currency": "eur",
        }
        response = test_app.post(
            "/currency_exchange/preview",
            json=payload,
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()

        # 100 USD → EUR: 100 * (3.00/3.50) = 85.714... rounded to 85.71
        assert Decimal(data["target_amount"]) == Decimal("85.71")
        assert Decimal(data["rate"]) == Decimal("1.17")
        # Verify the echoed request data.
        assert data["entity_id"] == entity_one
        assert data["source_currency"].lower() == "usd"
        assert data["target_currency"].lower() == "eur"
        assert Decimal(data["source_amount"]) == Decimal("100.00")

    def test_exchange(self, test_app: TestClient, token, entity_one):
        """
        Test the /currency_exchange/exchange endpoint.
        For a request converting 200.00 USD to EUR:
          - Expected conversion: 200 * (3.00 / 3.50) ≈ 171.43 EUR
          - Displayed rate should be 1.17
          - The receipt should include two transactions:
            one debiting USD and one crediting EUR.
        """
        payload = {
            "entity_id": entity_one,
            "source_currency": "usd",
            "source_amount": "200.00",
            "target_currency": "eur",
        }
        response = test_app.post(
            "/currency_exchange/exchange",
            json=payload,
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()

        # 200 USD → EUR: 200 * (3.00/3.50) ≈ 171.43
        assert Decimal(data["target_amount"]) == Decimal("171.43")
        assert Decimal(data["rate"]) == Decimal("1.17")
        transactions = data.get("transactions", [])
        assert isinstance(transactions, list)
        assert len(transactions) == 2
        # One transaction should be in USD and the other in EUR.
        currencies = {tx["currency"].lower() for tx in transactions}
        assert "usd" in currencies
        assert "eur" in currencies

    def test_rates(self, test_app: TestClient, token):
        """
        Test the /currency_exchange/rates endpoint.
        It should return the fixed rates we set via monkeypatch.
        """
        response = test_app.get(
            "/currency_exchange/rates",
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        expected = [
            {
                "currencies": [
                    {"code": "usd", "rate": "3.00", "quantity": "1"},
                    {"code": "eur", "rate": "3.50", "quantity": "1"},
                    {"code": "gel", "rate": "1", "quantity": "1"},
                ]
            }
        ]
        assert data == expected

    def test_many_exchanges_no_gain(self, test_app: TestClient, token, entity_one):
        """
        Simulate many consecutive exchanges in a round-trip:
          USD → EUR, then EUR → USD.
        The final USD amount should never exceed the initial amount,
        ensuring that rounding errors do not lead to a net gain.
        """
        initial_usd = Decimal("100.00")
        current_usd = initial_usd
        iterations = 10
        for _ in range(iterations):
            # Exchange USD → EUR.
            payload_usd_to_eur = {
                "entity_id": entity_one,
                "source_currency": "usd",
                "source_amount": str(current_usd),
                "target_currency": "eur",
            }
            resp = test_app.post(
                "/currency_exchange/exchange",
                json=payload_usd_to_eur,
                headers={"x-token": token},
            )
            assert resp.status_code == 200
            data = resp.json()
            current_eur = Decimal(data["target_amount"])

            # Exchange EUR → USD.
            payload_eur_to_usd = {
                "entity_id": entity_one,
                "source_currency": "eur",
                "source_amount": str(current_eur),
                "target_currency": "usd",
            }
            resp = test_app.post(
                "/currency_exchange/exchange",
                json=payload_eur_to_usd,
                headers={"x-token": token},
            )
            assert resp.status_code == 200
            data = resp.json()
            current_usd = Decimal(data["target_amount"])

        # Ensure that the final USD amount is not greater than the initial amount.
        # It may be slightly lower due to rounding, but never a net gain.
        assert current_usd <= initial_usd
