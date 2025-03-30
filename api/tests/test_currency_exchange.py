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
          - Displayed rate = max(3.00/3.50, 3.50/3.00) = 1.16 (round down)
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
        assert Decimal(data["rate"]) == Decimal("1.16")
        # Verify the echoed request data.
        assert data["entity_id"] == entity_one
        assert data["source_currency"].lower() == "usd"
        assert data["target_currency"].lower() == "eur"
        assert Decimal(data["source_amount"]) == Decimal("100.00")

    def test_exchange(self, test_app: TestClient, token, entity_one):
        """
        Test the /currency_exchange/exchange endpoint.
        For a request converting 200.00 USD to EUR:
          - Expected conversion: 200 * (3.00 / 3.50) ≈ 171.42 EUR
          - Displayed rate should be 1.16
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

        # 200 USD → EUR: 200 * (3.00/3.50) ≈ 171.42
        assert Decimal(data["target_amount"]) == Decimal("171.42")
        assert Decimal(data["rate"]) == Decimal("1.16")
        transactions = data.get("transactions", [])
        assert isinstance(transactions, list)
        assert len(transactions) == 2
        # One transaction should be in USD and the other in EUR.
        currencies = {tx["currency"].lower() for tx in transactions}
        assert "usd" in currencies
        assert "eur" in currencies

    def test_preview_with_target(self, test_app: TestClient, token, entity_one):
        """
        Test the /currency_exchange/preview endpoint when only target_amount is provided.
        With fixed rates:
          - Conversion rate from USD to EUR = (3.00 / 3.50) ≈ 0.8571
          - Reverse conversion = 1.1667 so the displayed rate = 1.17
          - To receive 100.00 EUR, required USD = 100.00 / (3.00/3.50) ≈ 116.67 USD.
        """
        payload = {
            "entity_id": entity_one,
            "source_currency": "usd",
            "target_currency": "eur",
            "target_amount": "100.00",
        }
        response = test_app.post(
            "/currency_exchange/preview",
            json=payload,
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        # Expected: source_amount computed as 100.00 / (3.00/3.50) = 116.67
        assert Decimal(data["source_amount"]) == Decimal("116.66")
        assert Decimal(data["target_amount"]) == Decimal("100.00")
        assert Decimal(data["rate"]) == Decimal("1.16")
        assert data["entity_id"] == entity_one
        assert data["source_currency"].lower() == "usd"
        assert data["target_currency"].lower() == "eur"

    def test_exchange_with_target(self, test_app: TestClient, token, entity_one):
        """
        Test the /currency_exchange/exchange endpoint when only target_amount is provided.
        For a request converting to receive 150.00 EUR from USD:
          - Required USD = 150.00 / (3.00/3.50) = 175.00 USD.
          - Displayed rate should be 1.16.
          - The receipt should include two transactions: one debiting USD and one crediting EUR.
        """
        payload = {
            "entity_id": entity_one,
            "source_currency": "usd",
            "target_currency": "eur",
            "target_amount": "150.00",
        }
        response = test_app.post(
            "/currency_exchange/exchange",
            json=payload,
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        # Expected: source_amount computed as 150.00 / (3.00/3.50) = 175.00 USD.
        assert Decimal(data["source_amount"]) == Decimal("175.00")
        assert Decimal(data["target_amount"]) == Decimal("150.00")
        assert Decimal(data["rate"]) == Decimal("1.16")
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

    def test_round_trip_with_subtraction(self, test_app: TestClient, token, entity_one):
        """
        Test a round-trip exchange:
        - Convert 1000 USD to GEL.
        - Subtract 0.01 GEL from the received amount.
        - Convert the adjusted GEL amount back to USD.
        The final amount should be 999.99 USD.
        Even though 0.01 GEL is less than 0.01 USD.
        """
        # Exchange 1000 USD to GEL.
        payload_usd_to_gel = {
            "entity_id": entity_one,
            "source_currency": "usd",
            "source_amount": "1000.00",
            "target_currency": "gel",
        }
        resp = test_app.post(
            "/currency_exchange/exchange",
            json=payload_usd_to_gel,
            headers={"x-token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        received_gel = Decimal(data["target_amount"])

        # Subtract 0.01 GEL from the received amount.
        adjusted_gel = received_gel - Decimal("0.01")

        # Convert the adjusted GEL amount back to USD.
        payload_gel_to_usd = {
            "entity_id": entity_one,
            "source_currency": "gel",
            "source_amount": str(adjusted_gel),
            "target_currency": "usd",
        }
        resp2 = test_app.post(
            "/currency_exchange/exchange",
            json=payload_gel_to_usd,
            headers={"x-token": token},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        final_usd = Decimal(data2["target_amount"])

        # The final USD amount should be 999.99, not 1000.00.
        assert final_usd == Decimal("999.99")
