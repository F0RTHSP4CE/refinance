from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient


def test_entity_money_flow_by_day(test_app: TestClient, token):
    def create_entity(name: str) -> int:
        response = test_app.post(
            "/entities",
            json={"name": name},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        return response.json()["id"]

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

    target = create_entity("Flow Target")
    incoming_source = create_entity("Flow Source")
    outgoing_dest = create_entity("Flow Dest")

    create_transaction(incoming_source, target, "10.00")
    create_transaction(incoming_source, target, "2.50")
    create_transaction(target, outgoing_dest, "7.25")

    today = date.today().isoformat()

    response = test_app.get(
        f"/stats/entity/{target}/money-flow-by-day/",
        params={"timeframe_from": today, "timeframe_to": today},
        headers={"x-token": token},
    )
    assert response.status_code == 200
    rows = response.json()
    assert isinstance(rows, list)
    assert rows

    today_row = next((row for row in rows if row.get("day") == today), None)
    assert today_row is not None
    assert today_row["incoming_total_usd"] == pytest.approx(12.50)
    assert today_row["outgoing_total_usd"] == pytest.approx(7.25)

    bundle = test_app.get(
        f"/stats/entity/{target}",
        params={"months": 1, "limit": 5, "timeframe_to": today},
        headers={"x-token": token},
    )
    assert bundle.status_code == 200
    body = bundle.json()
    assert "money_flow_by_day" in body
    assert isinstance(body["money_flow_by_day"], list)


def test_resident_fee_average_by_month_normalizes_by_invoice_count(
    test_app: TestClient, token
):
    billing_period = date.today().replace(day=1).isoformat()

    def create_entity(name: str) -> int:
        response = test_app.post(
            "/entities",
            json={"name": name},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        return response.json()["id"]

    def fund_entity(entity_id: int, amount: str) -> None:
        response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": 2,
                "to_entity_id": entity_id,
                "amount": amount,
                "currency": "usd",
                "status": "completed",
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200

    def create_fee_invoice(entity_id: int, amount: str) -> dict:
        response = test_app.post(
            "/invoices",
            json={
                "from_entity_id": entity_id,
                "to_entity_id": 1,
                "amounts": [
                    {"currency": "usd", "amount": amount},
                    {"currency": "gel", "amount": "9999.00"},
                ],
                "billing_period": billing_period,
                "tag_ids": [3],
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        return response.json()

    def pay_invoice(entity_id: int, invoice_id: int, amount: str) -> None:
        response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": entity_id,
                "to_entity_id": 1,
                "amount": amount,
                "currency": "usd",
                "status": "completed",
                "invoice_id": invoice_id,
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200

    first_resident = create_entity("Average Fee Resident 1")
    second_resident = create_entity("Average Fee Resident 2")
    third_resident = create_entity("Average Fee Resident 3")

    fund_entity(first_resident, "100.00")
    fund_entity(second_resident, "200.00")

    first_invoice = create_fee_invoice(first_resident, "100.00")
    second_invoice = create_fee_invoice(second_resident, "200.00")
    create_fee_invoice(third_resident, "300.00")

    pay_invoice(first_resident, first_invoice["id"], "100.00")
    pay_invoice(second_resident, second_invoice["id"], "200.00")

    # F0 expenses should not participate in the normalized fee chart.
    expense_response = test_app.post(
        "/transactions",
        json={
            "from_entity_id": 1,
            "to_entity_id": 10,
            "amount": "999.00",
            "currency": "usd",
            "status": "completed",
            "tag_ids": [7],
        },
        headers={"x-token": token},
    )
    assert expense_response.status_code == 200

    response = test_app.get(
        "/stats/resident-fee-average-by-month",
        params={"timeframe_from": billing_period, "timeframe_to": billing_period},
        headers={"x-token": token},
    )
    assert response.status_code == 200

    rows = response.json()
    row = next(
        item
        for item in rows
        if f"{item['year']}-{item['month']:02d}" == billing_period[:7]
    )
    assert row["invoice_count"] == 3
    assert row["paid_invoice_count"] == 2
    assert row["paid_usd_per_invoice"] == pytest.approx(100.0)
    assert row["expected_usd_per_invoice"] == pytest.approx(200.0)


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
