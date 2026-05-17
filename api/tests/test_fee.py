"""Tests for FeeService"""

import json
from datetime import date
from decimal import Decimal

from app.seeding import (
    common_consumables_entity,
    crowdfunding_target_tag,
    fee_tag,
    general_purchase_fund_entity,
    resident_tag,
    safety_cushion_entity,
)
from app.services.notification import NotificationService
from fastapi.testclient import TestClient


class TestFeeService:
    """Test FeeService logic through its API endpoint"""

    def test_get_fees(self, test_app: TestClient, token):
        # The DB is pre-populated with a "resident" tag (id=2) and a hackerspace entity (id=1)
        hackerspace_id = 1

        # Get current date for dynamic testing
        today = date.today()
        current_year, current_month = today.year, today.month

        # Calculate previous and next month for testing boundaries
        prev_year = current_year if current_month > 1 else current_year - 1
        prev_month = current_month - 1 if current_month > 1 else 12

        next_year = current_year if current_month < 12 else current_year + 1
        next_month = current_month + 1 if current_month < 12 else 1

        # Create two residents, with resident tag
        resident1_resp = test_app.post(
            "/entities",
            json={
                "name": "Resident One",
                "comment": "test resident",
                "tag_ids": [resident_tag.id],
            },
            headers={"x-token": token},
        )
        assert resident1_resp.status_code == 200
        resident1 = resident1_resp.json()

        resident2_resp = test_app.post(
            "/entities",
            json={
                "name": "Resident Two",
                "comment": "test resident",
                "tag_ids": [resident_tag.id],
            },
            headers={"x-token": token},
        )
        assert resident2_resp.status_code == 200
        resident2 = resident2_resp.json()

        def create_invoice(from_entity_id: int, year: int, month: int) -> int:
            invoice_resp = test_app.post(
                "/invoices",
                json={
                    "from_entity_id": from_entity_id,
                    "to_entity_id": hackerspace_id,
                    "amounts": [{"currency": "usd", "amount": "100"}],
                    "billing_period": f"{year}-{month:02d}-01",
                    "tag_ids": [fee_tag.id],
                },
                headers={"x-token": token},
            )
            assert invoice_resp.status_code == 200
            return invoice_resp.json()["id"]

        def pay_invoice(invoice_id: int, from_entity_id: int) -> None:
            tx_resp = test_app.post(
                "/transactions",
                json={
                    "from_entity_id": from_entity_id,
                    "to_entity_id": hackerspace_id,
                    "amount": "100",
                    "currency": "usd",
                    "status": "completed",
                    "invoice_id": invoice_id,
                },
                headers={"x-token": token},
            )
            assert tx_resp.status_code == 200

        # Create invoices for Resident One and pay them
        invoice_current = create_invoice(resident1["id"], current_year, current_month)
        pay_invoice(invoice_current, resident1["id"])

        invoice_previous = create_invoice(resident1["id"], prev_year, prev_month)
        pay_invoice(invoice_previous, resident1["id"])

        invoice_future = create_invoice(resident1["id"], next_year, next_month)
        pay_invoice(invoice_future, resident1["id"])

        # Create an unpaid invoice for Resident Two for the current month
        _ = create_invoice(resident2["id"], current_year, current_month)

        # Call the endpoint to get fees for the last 2 months
        response = test_app.get("/fees/?months=2", headers={"x-token": token})
        assert response.status_code == 200
        data = response.json()

        # Find our residents in the response
        resident1_data = next(
            (r for r in data if r["entity"]["id"] == resident1["id"]), None
        )
        resident2_data = next(
            (r for r in data if r["entity"]["id"] == resident2["id"]), None
        )

        assert resident1_data is not None
        assert resident2_data is not None

        # --- Assertions for Resident One ---
        fees1 = sorted(resident1_data["fees"], key=lambda x: (x["year"], x["month"]))
        # Expecting fees for previous, current, and next month
        assert len(fees1) == 3

        # Previous month
        assert fees1[0]["year"] == prev_year
        assert fees1[0]["month"] == prev_month
        assert fees1[0]["amounts"] == {"usd": "100.00"}

        # Current month
        assert fees1[1]["year"] == current_year
        assert fees1[1]["month"] == current_month
        assert fees1[1]["amounts"] == {"usd": "100.00"}

        # Next month (future payment)
        assert fees1[2]["year"] == next_year
        assert fees1[2]["month"] == next_month
        assert fees1[2]["amounts"] == {"usd": "100.00"}

        # --- Assertions for Resident Two ---
        fees2 = sorted(resident2_data["fees"], key=lambda x: (x["year"], x["month"]))
        # Leading empty past months trimmed; only first month with data
        assert len(fees2) == 1
        assert fees2[0]["year"] == current_year
        assert fees2[0]["month"] == current_month
        assert fees2[0]["amounts"] == {}


class TestDirectedFeeAllocations:
    def _create_resident(self, test_app: TestClient, token: str, name: str) -> int:
        response = test_app.post(
            "/entities",
            json={"name": name, "tag_ids": [resident_tag.id]},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        return int(response.json()["id"])

    def _issue_fee_invoice(
        self,
        test_app: TestClient,
        token: str,
        entity_id: int,
    ) -> int:
        period = date.today().replace(day=1).isoformat()
        response = test_app.post(
            "/fees/invoices/bulk",
            json={
                "from_tag_ids": [resident_tag.id],
                "billing_period": period,
                "notify": False,
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        invoices_response = test_app.get(
            "/invoices",
            params={"from_entity_id": entity_id, "billing_period": period},
            headers={"x-token": token},
        )
        assert invoices_response.status_code == 200
        invoices = invoices_response.json()["items"]
        assert len(invoices) == 1
        return int(invoices[0]["id"])

    def _pay_invoice(
        self,
        test_app: TestClient,
        token: str,
        entity_id: int,
        invoice_id: int,
    ) -> list[int]:
        response = test_app.post(
            f"/fees/invoices/{invoice_id}/settlement",
            json={"currency": "usd"},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        transaction_ids = [int(item["id"]) for item in response.json()]
        for transaction_id in transaction_ids:
            confirm_response = test_app.patch(
                f"/transactions/{transaction_id}",
                json={"status": "completed"},
                headers={"x-token": token},
            )
            assert confirm_response.status_code == 200
        return transaction_ids

    def test_standard_invoice_creates_directed_allocation_and_notification(
        self, test_app: TestClient, token: str, monkeypatch
    ):
        sent_messages: list[tuple[str, str | None]] = []

        def fake_send(self, entity, message, *, telegram_reply_markup=None):
            sent_messages.append((message, telegram_reply_markup))
            return {"telegram": True}

        monkeypatch.setattr(NotificationService, "send", fake_send)

        entity_id = self._create_resident(test_app, token, "Directed Fee Resident")
        period = date.today().replace(day=1).isoformat()
        response = test_app.post(
            "/fees/invoices/bulk",
            json={
                "from_tag_ids": [resident_tag.id],
                "billing_period": period,
                "notify": True,
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        report = response.json()
        assert report["notification_count"] >= 1

        invoices_response = test_app.get(
            "/invoices",
            params={"from_entity_id": entity_id, "billing_period": period},
            headers={"x-token": token},
        )
        invoice = invoices_response.json()["items"][0]
        assert invoice["amounts"] == [{"currency": "usd", "amount": "50.00"}]

        payer_token = test_app.get(f"/tokens/{entity_id}").json()
        selection_response = test_app.get(
            f"/fees/invoices/{invoice['id']}/directed-allocation",
            headers={"x-token": payer_token},
        )
        assert selection_response.status_code == 200
        selection = selection_response.json()
        assert selection["has_allocation"] is True
        directed = selection["directed_allocation"]
        assert directed["amounts"] == {"usd": "4.00"}
        assert directed["selected_at"] is None
        assert directed["selection_deadline_at"][:10] > invoice["created_at"][:10]
        fixed = {
            item["component_key"]: item["amounts"]
            for item in selection["fixed_allocations"]
        }
        assert fixed == {
            "base": {"usd": "42.00"},
            "common_consumables": {"usd": "2.00"},
            "safety_cushion": {"usd": "2.00"},
        }
        message, reply_markup = sent_messages[-1]
        assert "goes to a space budget you choose" in message
        assert "/fee/invoices/" not in message
        assert reply_markup is not None
        keyboard = json.loads(reply_markup)
        button = keyboard["inline_keyboard"][0][0]
        assert button["text"] == "Choose contribution target"
        assert button["url"].endswith(f"/fee/invoices/{invoice['id']}/selection")

    def test_manual_selection_settles_directly_after_payment(
        self, test_app: TestClient, token: str, monkeypatch
    ):
        sent_messages: list[str] = []

        def fake_send(self, entity, message, *, telegram_reply_markup=None):
            sent_messages.append(message)
            return {"telegram": True}

        monkeypatch.setattr(NotificationService, "send", fake_send)

        entity_id = self._create_resident(test_app, token, "Manual Selection Resident")
        invoice_id = self._issue_fee_invoice(test_app, token, entity_id)
        payer_token = test_app.get(f"/tokens/{entity_id}").json()

        selection_response = test_app.patch(
            f"/fees/invoices/{invoice_id}/directed-allocation",
            json={
                "target_type": "entity",
                "target_entity_id": general_purchase_fund_entity.id,
            },
            headers={"x-token": payer_token},
        )
        assert selection_response.status_code == 200
        assert (
            selection_response.json()["selected_target_name"] == "general-purchase-fund"
        )
        assert sent_messages == []

        transaction_ids = self._pay_invoice(
            test_app, payer_token, entity_id, invoice_id
        )
        assert len(transaction_ids) == 4

        refreshed = test_app.get(
            f"/fees/invoices/{invoice_id}/directed-allocation",
            headers={"x-token": payer_token},
        ).json()
        assert refreshed["directed_allocation"]["allocation_transaction_id"] is not None

        transactions_response = test_app.get(
            "/transactions",
            params={"invoice_id": invoice_id},
            headers={"x-token": token},
        )
        assert transactions_response.status_code == 200
        transactions = transactions_response.json()["items"]
        assert len(transactions) == 4
        assert all(tx["from_entity_id"] == entity_id for tx in transactions)
        by_target = {tx["to_entity_id"]: Decimal(tx["amount"]) for tx in transactions}
        assert by_target[1] == Decimal("42.00")
        assert by_target[safety_cushion_entity.id] == Decimal("2.00")
        assert by_target[common_consumables_entity.id] == Decimal("2.00")
        assert by_target[general_purchase_fund_entity.id] == Decimal("4.00")

        f0_outgoing = test_app.get(
            "/transactions",
            params={
                "from_entity_id": 1,
                "to_entity_id": general_purchase_fund_entity.id,
            },
            headers={"x-token": token},
        )
        assert f0_outgoing.status_code == 200
        assert f0_outgoing.json()["total"] == 0

        for entity_id_to_check, expected in (
            (1, Decimal("42.00")),
            (safety_cushion_entity.id, Decimal("2.00")),
            (common_consumables_entity.id, Decimal("2.00")),
            (general_purchase_fund_entity.id, Decimal("4.00")),
        ):
            balance_response = test_app.get(
                f"/balances/{entity_id_to_check}",
                headers={"x-token": token},
            )
            assert balance_response.status_code == 200
            balance = balance_response.json()["completed"]
            assert Decimal(balance["usd"]) == expected

    def test_draft_settlement_marks_invoice_paid_after_confirmation(
        self, test_app: TestClient, token: str
    ):
        entity_id = self._create_resident(test_app, token, "Draft Settlement Resident")
        invoice_id = self._issue_fee_invoice(test_app, token, entity_id)
        payer_token = test_app.get(f"/tokens/{entity_id}").json()

        selection_response = test_app.patch(
            f"/fees/invoices/{invoice_id}/directed-allocation",
            json={
                "target_type": "entity",
                "target_entity_id": general_purchase_fund_entity.id,
            },
            headers={"x-token": payer_token},
        )
        assert selection_response.status_code == 200

        settlement_response = test_app.post(
            f"/fees/invoices/{invoice_id}/settlement",
            json={"currency": "usd"},
            headers={"x-token": payer_token},
        )
        assert settlement_response.status_code == 200
        transactions = settlement_response.json()
        assert len(transactions) == 4
        assert {tx["status"] for tx in transactions} == {"draft"}

        invoice_response = test_app.get(
            f"/invoices/{invoice_id}", headers={"x-token": token}
        )
        assert invoice_response.json()["status"] == "pending"

        retry_response = test_app.post(
            f"/fees/invoices/{invoice_id}/settlement",
            json={"currency": "usd"},
            headers={"x-token": payer_token},
        )
        assert retry_response.status_code == 200
        assert {tx["id"] for tx in retry_response.json()} == {
            tx["id"] for tx in transactions
        }

        reselection_response = test_app.patch(
            f"/fees/invoices/{invoice_id}/directed-allocation",
            json={
                "target_type": "entity",
                "target_entity_id": safety_cushion_entity.id,
            },
            headers={"x-token": payer_token},
        )
        assert reselection_response.status_code == 418

        complete_response = test_app.post(
            f"/fees/invoices/{invoice_id}/settlement",
            json={"currency": "usd", "status": "completed"},
            headers={"x-token": payer_token},
        )
        assert complete_response.status_code == 200
        assert {tx["id"] for tx in complete_response.json()} == {
            tx["id"] for tx in transactions
        }
        assert {tx["status"] for tx in complete_response.json()} == {"completed"}

        paid_invoice_response = test_app.get(
            f"/invoices/{invoice_id}", headers={"x-token": token}
        )
        assert paid_invoice_response.json()["status"] == "paid"
        assert len(paid_invoice_response.json()["transaction_ids"]) == 4

    def test_split_target_progress_uses_payer_entity(
        self, test_app: TestClient, token: str
    ):
        entity_id = self._create_resident(test_app, token, "Split Target Resident")
        invoice_id = self._issue_fee_invoice(test_app, token, entity_id)
        split_response = test_app.post(
            "/splits",
            json={
                "recipient_entity_id": general_purchase_fund_entity.id,
                "amount": "20.00",
                "currency": "usd",
                "comment": "Wheel fund",
                "tag_ids": [crowdfunding_target_tag.id],
            },
            headers={"x-token": token},
        )
        assert split_response.status_code == 200
        split_id = split_response.json()["id"]
        payer_token = test_app.get(f"/tokens/{entity_id}").json()

        selection_response = test_app.patch(
            f"/fees/invoices/{invoice_id}/directed-allocation",
            json={"target_type": "split", "target_split_id": split_id},
            headers={"x-token": payer_token},
        )
        assert selection_response.status_code == 200

        completed_transactions = test_app.post(
            f"/fees/invoices/{invoice_id}/settlement",
            json={"currency": "usd"},
            headers={"x-token": payer_token},
        )
        assert completed_transactions.status_code == 200
        for tx in completed_transactions.json():
            confirm_response = test_app.patch(
                f"/transactions/{tx['id']}",
                json={"status": "completed"},
                headers={"x-token": token},
            )
            assert confirm_response.status_code == 200

        split_after = test_app.get(f"/splits/{split_id}", headers={"x-token": token})
        assert split_after.status_code == 200
        participants = split_after.json()["participants"]
        payer_participant = next(
            participant
            for participant in participants
            if participant["entity"]["id"] == entity_id
        )
        assert payer_participant["fixed_amount"] == "4.00"

    def test_auto_pay_settles_direct_fee_invoice(
        self, test_app: TestClient, token: str
    ):
        funding_entity = test_app.post(
            "/entities",
            json={"name": "Directed Fee Funding"},
            headers={"x-token": token},
        ).json()["id"]
        entity_id = self._create_resident(test_app, token, "AutoPay Directed Resident")
        credit_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": funding_entity,
                "to_entity_id": entity_id,
                "amount": "50.00",
                "currency": "usd",
                "status": "completed",
            },
            headers={"x-token": token},
        )
        assert credit_response.status_code == 200

        invoice_id = self._issue_fee_invoice(test_app, token, entity_id)
        payer_token = test_app.get(f"/tokens/{entity_id}").json()
        selection_response = test_app.patch(
            f"/fees/invoices/{invoice_id}/directed-allocation",
            json={
                "target_type": "entity",
                "target_entity_id": general_purchase_fund_entity.id,
            },
            headers={"x-token": payer_token},
        )
        assert selection_response.status_code == 200

        auto_pay_response = test_app.post(
            "/invoices/auto-pay",
            headers={"x-token": token},
        )
        assert auto_pay_response.status_code == 200
        assert auto_pay_response.json()["paid"] >= 1

        invoice_response = test_app.get(
            f"/invoices/{invoice_id}",
            headers={"x-token": token},
        )
        assert invoice_response.status_code == 200
        assert invoice_response.json()["status"] == "paid"
        assert len(invoice_response.json()["transaction_ids"]) == 4

        transactions = test_app.get(
            "/transactions",
            params={"invoice_id": invoice_id},
            headers={"x-token": token},
        ).json()["items"]
        assert {tx["status"] for tx in transactions} == {"completed"}
        assert all(tx["from_entity_id"] == entity_id for tx in transactions)

    def test_random_fallback_selects_once_and_excludes_currency_mismatch(
        self, test_app: TestClient, token: str
    ):
        entity_id = self._create_resident(test_app, token, "Random Fallback Resident")
        invoice_id = self._issue_fee_invoice(test_app, token, entity_id)
        mismatch_split_response = test_app.post(
            "/splits",
            json={
                "recipient_entity_id": general_purchase_fund_entity.id,
                "amount": "10.00",
                "currency": "eur",
                "comment": "EUR target",
                "tag_ids": [crowdfunding_target_tag.id],
            },
            headers={"x-token": token},
        )
        assert mismatch_split_response.status_code == 200
        mismatch_split_id = mismatch_split_response.json()["id"]

        future = date.today().replace(year=date.today().year + 1).isoformat()
        first_run = test_app.post(
            "/tasks/fee-allocation-selection/run",
            params={"now": f"{future}T00:00:00"},
            headers={"x-token": token},
        )
        assert first_run.status_code == 200
        assert first_run.json()["result"] >= 1

        payer_token = test_app.get(f"/tokens/{entity_id}").json()
        selection = test_app.get(
            f"/fees/invoices/{invoice_id}/directed-allocation",
            headers={"x-token": payer_token},
        ).json()
        directed = selection["directed_allocation"]
        assert directed["auto_selected"] is True
        assert directed["selected_at"] is not None
        assert directed["target_split_id"] != mismatch_split_id

        second_run = test_app.post(
            "/tasks/fee-allocation-selection/run",
            params={"now": f"{future}T00:00:00"},
            headers={"x-token": token},
        )
        assert second_run.status_code == 200
        assert second_run.json()["result"] == 0

    def test_legacy_override_creates_no_allocation(
        self, test_app: TestClient, token: str
    ):
        entity_id = self._create_resident(test_app, token, "Legacy Fee Resident")
        policy_response = test_app.put(
            f"/fees/policies/{entity_id}",
            json={"kind": "legacy", "active": True},
            headers={"x-token": token},
        )
        assert policy_response.status_code == 200

        invoice_id = self._issue_fee_invoice(test_app, token, entity_id)
        invoice_response = test_app.get(
            f"/invoices/{invoice_id}",
            headers={"x-token": token},
        )
        assert invoice_response.status_code == 200
        assert invoice_response.json()["amounts"] == [
            {"currency": "usd", "amount": "42.00"}
        ]

        payer_token = test_app.get(f"/tokens/{entity_id}").json()
        selection_response = test_app.get(
            f"/fees/invoices/{invoice_id}/directed-allocation",
            headers={"x-token": payer_token},
        )
        assert selection_response.status_code == 200
        assert selection_response.json()["has_allocation"] is False
