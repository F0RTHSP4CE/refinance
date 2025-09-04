"""Tests for ResidentFeeService"""

from datetime import date

from app.seeding import resident_tag
from fastapi.testclient import TestClient


class TestResidentFeeService:
    """Test ResidentFeeService logic through its API endpoint"""

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

        # Create transactions for Resident One
        # Fee for current month
        test_app.post(
            "/transactions",
            json={
                "from_entity_id": resident1["id"],
                "to_entity_id": hackerspace_id,
                "amount": "100",
                "currency": "USD",
                "comment": f"Fee for {current_year}-{current_month:02d}",
            },
            headers={"x-token": token},
        )
        # Fee for previous month
        test_app.post(
            "/transactions",
            json={
                "from_entity_id": resident1["id"],
                "to_entity_id": hackerspace_id,
                "amount": "100",
                "currency": "USD",
                "comment": f"Fee for {prev_year}-{prev_month:02d}",
            },
            headers={"x-token": token},
        )
        # Fee for a future month
        test_app.post(
            "/transactions",
            json={
                "from_entity_id": resident1["id"],
                "to_entity_id": hackerspace_id,
                "amount": "100",
                "currency": "USD",
                "comment": f"Fee for {next_year}-{next_month:02d}",
            },
            headers={"x-token": token},
        )

        # Create transaction for Resident Two for the current month
        # This one has no date in the comment, so created_at will be used
        test_app.post(
            "/transactions",
            json={
                "from_entity_id": resident2["id"],
                "to_entity_id": hackerspace_id,
                "amount": "50",
                "currency": "EUR",
            },
            headers={"x-token": token},
        )

        # Call the endpoint to get resident fees for the last 2 months
        response = test_app.get("/resident_fees/?months=2", headers={"x-token": token})
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
        assert fees2[0]["amounts"] == {"eur": "50.00"}
