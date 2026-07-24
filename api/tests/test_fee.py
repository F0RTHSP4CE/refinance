"""Tests for FeeService"""

import warnings
from datetime import date

from app.seeding import fee_tag, resident_tag
from fastapi.testclient import TestClient
from sqlalchemy.exc import SAWarning


class TestFeeService:
    """Test FeeService logic through its API endpoint"""

    def test_get_fees_includes_multi_recipient_invoices(
        self, test_app: TestClient, token
    ):
        today = date.today()
        period = today.replace(day=1).isoformat()

        def create_resident(name: str) -> int:
            response = test_app.post(
                "/entities",
                json={"name": name, "tag_ids": [resident_tag.id]},
                headers={"x-token": token},
            )
            assert response.status_code == 200, response.text
            return response.json()["id"]

        recipient = test_app.post(
            "/entities",
            json={"name": "Multi-fee recipient"},
            headers={"x-token": token},
        ).json()["id"]
        pending_resident = create_resident("Pending multi-fee resident")
        paid_resident = create_resident("Paid multi-fee resident")

        def create_invoice(from_entity_id: int) -> dict:
            response = test_app.post(
                "/invoices",
                json={
                    "from_entity_id": from_entity_id,
                    "billing_period": period,
                    "tag_ids": [fee_tag.id],
                    "items": [
                        {
                            "to_entity_id": 1,
                            "amounts": [
                                {"currency": "usd", "amount": "40"},
                                {"currency": "gel", "amount": "100"},
                            ],
                        },
                        {
                            "to_entity_id": recipient,
                            "amounts": [
                                {"currency": "usd", "amount": "10"},
                                {"currency": "gel", "amount": "25"},
                            ],
                        },
                    ],
                },
                headers={"x-token": token},
            )
            assert response.status_code == 200, response.text
            return response.json()

        pending_invoice = create_invoice(pending_resident)
        paid_invoice = create_invoice(paid_resident)

        funding_entity = test_app.post(
            "/entities",
            json={"name": "Multi-fee funding"},
            headers={"x-token": token},
        ).json()["id"]
        funding_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": funding_entity,
                "to_entity_id": paid_resident,
                "amount": "50",
                "currency": "usd",
                "status": "completed",
            },
            headers={"x-token": token},
        )
        assert funding_response.status_code == 200, funding_response.text

        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always", SAWarning)
            pay_response = test_app.post(
                f"/invoices/{paid_invoice['id']}/pay-items",
                json={
                    "items": [
                        {
                            "item_id": item["id"],
                            "to_entity_id": item["to_entity_id"],
                            "currency": "usd",
                        }
                        for item in paid_invoice["items"]
                    ]
                },
                headers={"x-token": token},
            )
        assert pay_response.status_code == 200, pay_response.text
        assert not any(
            "Multiple rows returned with uselist=False" in str(warning.message)
            for warning in caught_warnings
        )

        response = test_app.get("/fees/?months=1", headers={"x-token": token})
        assert response.status_code == 200, response.text
        fees_by_resident = {
            record["entity"]["id"]: record["fees"][0] for record in response.json()
        }

        pending_fee = fees_by_resident[pending_resident]
        assert pending_fee["unpaid_invoice_id"] == pending_invoice["id"]
        assert pending_fee["unpaid_invoice_amounts"] == {
            "usd": "50.00",
            "gel": "125.00",
        }

        paid_fee = fees_by_resident[paid_resident]
        assert paid_fee["paid_invoice_id"] == paid_invoice["id"]
        assert paid_fee["amounts"] == {"usd": "50.00"}

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
            import uuid

            bank = test_app.post(
                "/entities",
                json={"name": f"fee-bank-{uuid.uuid4().hex[:8]}"},
                headers={"x-token": token},
            ).json()["id"]
            fund_resp = test_app.post(
                "/transactions",
                json={
                    "from_entity_id": bank,
                    "to_entity_id": from_entity_id,
                    "amount": "100",
                    "currency": "usd",
                    "status": "completed",
                },
                headers={"x-token": token},
            )
            assert fund_resp.status_code == 200, fund_resp.text
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
