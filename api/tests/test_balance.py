"""Tests for Balance API and Transaction confirmation"""

from decimal import Decimal

import pytest
import requests
from app.services.currency_exchange import CurrencyExchangeService
from fastapi import status
from fastapi.testclient import TestClient


class TestBalanceEndpoints:
    """Test API endpoints for Balance"""

    def test_entity_transactions_balance_batch(
        self, test_app: TestClient, token_factory, token
    ):
        response = test_app.post(
            "/entities", json={"name": "Batch Entity A"}, headers={"x-token": token}
        )
        entity_a_id = response.json()["id"]
        token_a = token_factory(entity_a_id)

        response = test_app.post(
            "/entities", json={"name": "Batch Entity B"}, headers={"x-token": token}
        )
        entity_b_id = response.json()["id"]

        response = test_app.post(
            "/transactions/",
            json={
                "from_entity_id": entity_a_id,
                "to_entity_id": entity_b_id,
                "amount": "15.00",
                "currency": "eur",
                "status": "completed",
            },
            headers={"x-token": token_a},
        )
        assert response.status_code == status.HTTP_200_OK

        response = test_app.get(
            "/balances",
            params=[("entity_ids", entity_a_id), ("entity_ids", entity_b_id)],
            headers={"x-token": token},
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data[str(entity_a_id)]["completed"]["eur"] == "-15.00"
        assert data[str(entity_b_id)]["completed"]["eur"] == "15.00"

    def test_entity_transactions_balance(
        self, test_app: TestClient, token_factory, token
    ):
        # Create entities
        response = test_app.post(
            "/entities", json={"name": "Entity A"}, headers={"x-token": token}
        )
        entity_a_id = response.json()["id"]
        token_a = token_factory(entity_a_id)

        response = test_app.post(
            "/entities", json={"name": "Entity B"}, headers={"x-token": token}
        )
        entity_b_id = response.json()["id"]
        token_b = token_factory(entity_b_id)

        # Create a transaction from Entity A to Entity B
        transaction_data = {
            "from_entity_id": entity_a_id,
            "to_entity_id": entity_b_id,
            "amount": "100.00",
            "currency": "usd",
        }
        response = test_app.post(
            "/transactions/", json=transaction_data, headers={"x-token": token_a}
        )
        transaction_id = response.json()["id"]

        # Check initial balance for Entity A and Entity B
        response = test_app.get(
            f"/balances/{entity_a_id}", headers={"x-token": token_a}
        )
        assert response.json()["completed"] == {}
        assert Decimal(response.json()["draft"]["usd"]) == Decimal("-100")
        response = test_app.get(
            f"/balances/{entity_b_id}", headers={"x-token": token_b}
        )
        assert response.json()["completed"] == {}
        assert Decimal(response.json()["draft"]["usd"]) == Decimal("100")

        # Confirm the transaction
        response = test_app.patch(
            f"/transactions/{transaction_id}",
            json={"status": "completed"},
            headers={"x-token": token_a},
        )
        assert response.status_code == status.HTTP_200_OK

        # Check balance after confirming the transaction
        response = test_app.get(
            f"/balances/{entity_a_id}", headers={"x-token": token_a}
        )
        balance_a = Decimal(response.json()["completed"]["usd"])
        assert balance_a == Decimal("-100")
        response = test_app.get(
            f"/balances/{entity_b_id}", headers={"x-token": token_b}
        )
        balance_b = Decimal(response.json()["completed"]["usd"])
        assert balance_b == Decimal("100")

    def test_recommended_deposit_includes_multi_recipient_invoice_items(
        self, test_app: TestClient, token
    ):
        payer = test_app.post(
            "/entities",
            json={"name": "Recommended Deposit Payer"},
            headers={"x-token": token},
        ).json()
        fixed_recipient = test_app.post(
            "/entities",
            json={"name": "Recommended Deposit Fixed Recipient"},
            headers={"x-token": token},
        ).json()
        room_recipient = test_app.post(
            "/entities",
            json={"name": "Recommended Deposit Room Recipient"},
            headers={"x-token": token},
        ).json()
        invoice_response = test_app.post(
            "/invoices",
            json={
                "from_entity_id": payer["id"],
                "items": [
                    {
                        "to_entity_id": fixed_recipient["id"],
                        "amounts": [{"currency": "usd", "amount": "42.00"}],
                    },
                    {
                        "to_entity_id": room_recipient["id"],
                        "amounts": [{"currency": "usd", "amount": "8.00"}],
                    },
                ],
            },
            headers={"x-token": token},
        )
        assert invoice_response.status_code == status.HTTP_200_OK

        response = test_app.get(
            f"/balances/{payer['id']}/recommended-deposit",
            headers={"x-token": token},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "entity_id": payer["id"],
            "currency": "usd",
            "amount": "50.00",
        }

    def test_recommended_deposit_is_empty_when_entity_owes_nothing(
        self, test_app: TestClient, token
    ):
        entity = test_app.post(
            "/entities",
            json={"name": "No Recommended Deposit"},
            headers={"x-token": token},
        ).json()

        response = test_app.get(
            f"/balances/{entity['id']}/recommended-deposit",
            headers={"x-token": token},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "entity_id": entity["id"],
            "currency": None,
            "amount": None,
        }

    def test_recommended_deposit_falls_back_when_rates_are_unavailable(
        self, test_app: TestClient, token, monkeypatch: pytest.MonkeyPatch
    ):
        payer = test_app.post(
            "/entities",
            json={"name": "Offline Rates Payer"},
            headers={"x-token": token},
        ).json()
        recipient = test_app.post(
            "/entities",
            json={"name": "Offline Rates Recipient"},
            headers={"x-token": token},
        ).json()
        invoice_response = test_app.post(
            "/invoices",
            json={
                "from_entity_id": payer["id"],
                "to_entity_id": recipient["id"],
                "amounts": [
                    {"currency": "usd", "amount": "50.00"},
                    {"currency": "gel", "amount": "135.00"},
                ],
            },
            headers={"x-token": token},
        )
        assert invoice_response.status_code == status.HTTP_200_OK

        for transaction in (
            {
                "from_entity_id": 1,
                "to_entity_id": payer["id"],
                "amount": "39.69",
                "currency": "usd",
                "status": "completed",
            },
            {
                "from_entity_id": payer["id"],
                "to_entity_id": recipient["id"],
                "amount": "319.25",
                "currency": "gel",
                "status": "completed",
            },
        ):
            transaction_response = test_app.post(
                "/transactions/", json=transaction, headers={"x-token": token}
            )
            assert transaction_response.status_code == status.HTTP_200_OK

        def unavailable_rates(*args, **kwargs):
            raise requests.ConnectionError("NBG DNS unavailable")

        monkeypatch.setattr(
            CurrencyExchangeService,
            "calculate_conversion",
            unavailable_rates,
        )

        response = test_app.get(
            f"/balances/{payer['id']}/recommended-deposit",
            headers={"x-token": token},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "entity_id": payer["id"],
            "currency": "usd",
            "amount": "11.00",
        }

        gel_only_payer = test_app.post(
            "/entities",
            json={"name": "Offline Rates GEL-only Payer"},
            headers={"x-token": token},
        ).json()
        gel_invoice_response = test_app.post(
            "/invoices",
            json={
                "from_entity_id": gel_only_payer["id"],
                "to_entity_id": recipient["id"],
                "amounts": [{"currency": "gel", "amount": "135.00"}],
            },
            headers={"x-token": token},
        )
        assert gel_invoice_response.status_code == status.HTTP_200_OK

        gel_response = test_app.get(
            f"/balances/{gel_only_payer['id']}/recommended-deposit",
            headers={"x-token": token},
        )
        assert gel_response.status_code == status.HTTP_200_OK
        assert gel_response.json() == {
            "entity_id": gel_only_payer["id"],
            "currency": "gel",
            "amount": "135.00",
        }
