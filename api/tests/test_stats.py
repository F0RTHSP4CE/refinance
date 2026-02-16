from decimal import Decimal

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="class")
def top_entities_data(test_app: TestClient, token):
    """Prepare entities and transactions for top incoming/outgoing stats."""

    def create_entity(name: str) -> int:
        response = test_app.post(
            "/entities",
            json={"name": name},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        return response.json()["id"]

    income_a = create_entity("Income Source A")
    income_b = create_entity("Income Source B")
    income_c = create_entity("Income Source C")

    expense_a = create_entity("Expense Target A")
    expense_b = create_entity("Expense Target B")
    expense_c = create_entity("Expense Target C")

    def create_transaction(from_id: int, to_id: int, amount: str) -> None:
        response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": from_id,
                "to_entity_id": to_id,
                "amount": amount,
                "currency": "usd",
                "status": "completed",
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200

    hackerspace_id = 1

    # Incoming transactions (to hackerspace)
    create_transaction(income_a, hackerspace_id, "300.00")
    create_transaction(income_a, hackerspace_id, "50.00")
    create_transaction(income_b, hackerspace_id, "200.00")
    create_transaction(income_c, hackerspace_id, "100.00")

    # Outgoing transactions (from hackerspace)
    create_transaction(hackerspace_id, expense_a, "400.00")
    create_transaction(hackerspace_id, expense_b, "250.00")
    create_transaction(hackerspace_id, expense_b, "50.00")
    create_transaction(hackerspace_id, expense_c, "150.00")

    return {
        "income_totals": {
            income_a: Decimal("350.00"),
            income_b: Decimal("200.00"),
            income_c: Decimal("100.00"),
        },
        "expense_totals": {
            expense_a: Decimal("400.00"),
            expense_b: Decimal("300.00"),
            expense_c: Decimal("150.00"),
        },
        "target_entity_id": hackerspace_id,
    }


@pytest.fixture(scope="class")
def top_tags_data(test_app: TestClient, token):
    """Prepare tags, entities, and transactions for tag-based stats."""

    def create_tag(name: str) -> int:
        response = test_app.post(
            "/tags", json={"name": name}, headers={"x-token": token}
        )
        assert response.status_code == 200
        return response.json()["id"]

    def create_entity(name: str, tag_ids: list[int] | None = None) -> int:
        payload: dict[str, object] = {"name": name}
        if tag_ids is not None:
            payload["tag_ids"] = tag_ids
        response = test_app.post(
            "/entities",
            json=payload,
            headers={"x-token": token},
        )
        assert response.status_code == 200
        return response.json()["id"]

    def create_transaction(
        from_id: int,
        to_id: int,
        amount: str,
        tag_ids: list[int] | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "from_entity_id": from_id,
            "to_entity_id": to_id,
            "amount": amount,
            "currency": "usd",
            "status": "completed",
        }
        if tag_ids is not None:
            payload["tag_ids"] = tag_ids
        response = test_app.post(
            "/transactions",
            json=payload,
            headers={"x-token": token},
        )
        assert response.status_code == 200

    exchange_tag = create_tag("Exchange Operations")
    resident_tag = create_tag("Resident Contributions")
    maintenance_tag = create_tag("Maintenance Expenses")

    tag_names = {
        exchange_tag: "Exchange Operations",
        resident_tag: "Resident Contributions",
        maintenance_tag: "Maintenance Expenses",
    }

    target_entity = create_entity("Stats Tag Target")

    incoming_resident = create_entity("Resident Donor", tag_ids=[resident_tag])
    incoming_exchange = create_entity("Exchange Donor", tag_ids=[resident_tag])
    incoming_maintenance = create_entity("Maintenance Donor", tag_ids=[maintenance_tag])

    outgoing_maintenance = create_entity(
        "Maintenance Vendor", tag_ids=[maintenance_tag]
    )
    outgoing_exchange = create_entity("Exchange Vendor", tag_ids=[exchange_tag])
    outgoing_resident = create_entity("Resident Support", tag_ids=[resident_tag])

    # Incoming transactions (to target)
    create_transaction(
        incoming_exchange,
        target_entity,
        "150.00",
        tag_ids=[exchange_tag],
    )
    create_transaction(
        incoming_resident,
        target_entity,
        "200.00",
    )
    create_transaction(
        incoming_maintenance,
        target_entity,
        "80.00",
    )

    # Outgoing transactions (from target)
    create_transaction(
        target_entity,
        outgoing_maintenance,
        "300.00",
    )
    create_transaction(
        target_entity,
        outgoing_exchange,
        "120.00",
        tag_ids=[exchange_tag],
    )
    create_transaction(
        target_entity,
        outgoing_resident,
        "90.00",
    )

    incoming_totals = {
        resident_tag: Decimal("200.00"),
        exchange_tag: Decimal("150.00"),
        maintenance_tag: Decimal("80.00"),
    }
    outgoing_totals = {
        maintenance_tag: Decimal("300.00"),
        exchange_tag: Decimal("120.00"),
        resident_tag: Decimal("90.00"),
    }

    return {
        "target_entity_id": target_entity,
        "incoming_totals": incoming_totals,
        "outgoing_totals": outgoing_totals,
        "tag_names": tag_names,
    }


class TestTopEntityStats:
    def test_top_incoming_entities(
        self, test_app: TestClient, token, top_entities_data
    ):
        response = test_app.get(
            "/stats/top-incoming-entities",
            params={
                "limit": 2,
                "months": 12,
                "entity_id": top_entities_data["target_entity_id"],
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        income_totals = top_entities_data["income_totals"]
        sorted_income_ids = sorted(
            income_totals.keys(),
            key=lambda eid: income_totals[eid],
            reverse=True,
        )

        assert [item["entity_id"] for item in data] == sorted_income_ids[:2]
        assert data[0]["amounts"]["usd"] == pytest.approx(
            float(income_totals[sorted_income_ids[0]])
        )
        assert data[0]["total_usd"] == pytest.approx(
            float(income_totals[sorted_income_ids[0]])
        )
        assert data[1]["amounts"]["usd"] == pytest.approx(
            float(income_totals[sorted_income_ids[1]])
        )
        assert data[1]["total_usd"] == pytest.approx(
            float(income_totals[sorted_income_ids[1]])
        )

    def test_top_outgoing_entities(
        self, test_app: TestClient, token, top_entities_data
    ):
        response = test_app.get(
            "/stats/top-outgoing-entities",
            params={
                "limit": 2,
                "months": 12,
                "entity_id": top_entities_data["target_entity_id"],
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        expense_totals = top_entities_data["expense_totals"]
        sorted_expense_ids = sorted(
            expense_totals.keys(),
            key=lambda eid: expense_totals[eid],
            reverse=True,
        )

        assert [item["entity_id"] for item in data] == sorted_expense_ids[:2]
        assert data[0]["amounts"]["usd"] == pytest.approx(
            float(expense_totals[sorted_expense_ids[0]])
        )
        assert data[0]["total_usd"] == pytest.approx(
            float(expense_totals[sorted_expense_ids[0]])
        )
        assert data[1]["amounts"]["usd"] == pytest.approx(
            float(expense_totals[sorted_expense_ids[1]])
        )
        assert data[1]["total_usd"] == pytest.approx(
            float(expense_totals[sorted_expense_ids[1]])
        )


class TestTopTagStats:
    def test_top_incoming_tags(self, test_app: TestClient, token, top_tags_data):
        response = test_app.get(
            "/stats/top-incoming-tags",
            params={
                "limit": 2,
                "months": 12,
                "entity_id": top_tags_data["target_entity_id"],
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        incoming_totals = top_tags_data["incoming_totals"]
        expected_order = sorted(
            incoming_totals.items(), key=lambda item: item[1], reverse=True
        )[:2]

        assert [item["tag_id"] for item in data] == [tag for tag, _ in expected_order]
        for idx, (tag_id, expected_total) in enumerate(expected_order):
            assert data[idx]["tag_name"] == top_tags_data["tag_names"][tag_id]
            assert data[idx]["amounts"]["usd"] == pytest.approx(float(expected_total))
            assert data[idx]["total_usd"] == pytest.approx(float(expected_total))

    def test_top_outgoing_tags(self, test_app: TestClient, token, top_tags_data):
        response = test_app.get(
            "/stats/top-outgoing-tags",
            params={
                "limit": 2,
                "months": 12,
                "entity_id": top_tags_data["target_entity_id"],
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        outgoing_totals = top_tags_data["outgoing_totals"]
        expected_order = sorted(
            outgoing_totals.items(), key=lambda item: item[1], reverse=True
        )[:2]

        assert [item["tag_id"] for item in data] == [tag for tag, _ in expected_order]
        for idx, (tag_id, expected_total) in enumerate(expected_order):
            assert data[idx]["tag_name"] == top_tags_data["tag_names"][tag_id]
            assert data[idx]["amounts"]["usd"] == pytest.approx(float(expected_total))
            assert data[idx]["total_usd"] == pytest.approx(float(expected_total))
