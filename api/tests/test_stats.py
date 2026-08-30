from datetime import date, timedelta
from decimal import Decimal

import pytest
from app.app import app
from app.config import get_config
from app.db import DatabaseConnection
from app.models.transaction import Transaction
from app.services.stats import StatsService
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine


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
    balance_row = next(row for row in body["balance_changes"] if row["day"] == today)
    assert balance_row["balance_changes"]["usd"] == pytest.approx(5.25)
    transaction_row = next(
        row for row in body["transactions_by_day"] if row["day"] == today
    )
    assert transaction_row["transaction_count"] == 3


def test_treasury_history_stats_and_cache_invalidation(test_app: TestClient, token):
    def create_entity(name: str) -> int:
        response = test_app.post(
            "/entities", json={"name": name}, headers={"x-token": token}
        )
        assert response.status_code == 200
        return response.json()["id"]

    treasury_response = test_app.post(
        "/treasuries",
        json={"name": "Stats Test Treasury"},
        headers={"x-token": token},
    )
    assert treasury_response.status_code == 200
    treasury_id = treasury_response.json()["id"]
    source = create_entity("Treasury Stats Source")
    holder = create_entity("Treasury Stats Holder")
    destination = create_entity("Treasury Stats Destination")

    def create_transaction(
        from_id: int, to_id: int, amount: str, *, incoming: bool
    ) -> None:
        treasury_field = "to_treasury_id" if incoming else "from_treasury_id"
        response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": from_id,
                "to_entity_id": to_id,
                "amount": amount,
                "currency": "usd",
                "status": "completed",
                treasury_field: treasury_id,
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200, response.text

    create_transaction(source, holder, "12.50", incoming=True)
    create_transaction(holder, destination, "7.25", incoming=False)
    today = date.today().isoformat()

    bundle_response = test_app.get(
        f"/stats/treasury/{treasury_id}",
        params={"months": 1, "timeframe_to": today},
        headers={"x-token": token},
    )
    assert bundle_response.status_code == 200, bundle_response.text
    bundle = bundle_response.json()
    balance_row = next(row for row in bundle["balance_changes"] if row["day"] == today)
    flow_row = next(row for row in bundle["money_flow_by_day"] if row["day"] == today)
    assert balance_row["balance_changes"]["usd"] == pytest.approx(5.25)
    assert flow_row["incoming_total_usd"] == pytest.approx(12.50)
    assert flow_row["outgoing_total_usd"] == pytest.approx(7.25)

    cached_response = test_app.get(
        f"/stats/treasury/{treasury_id}",
        params={"months": 1, "timeframe_to": today, "cached_only": True},
        headers={"x-token": token},
    )
    assert cached_response.status_code == 200
    assert cached_response.json()["cached"] is True

    create_transaction(source, holder, "1.00", incoming=True)
    invalidated_response = test_app.get(
        f"/stats/treasury/{treasury_id}",
        params={"months": 1, "timeframe_to": today, "cached_only": True},
        headers={"x-token": token},
    )
    assert invalidated_response.status_code == 200
    assert invalidated_response.json()["cached"] is False


def test_system_balance_history_compares_real_and_positive_virtual_balances(
    test_app: TestClient, token
):
    def create_entity(name: str, tag_ids: list[int] | None = None) -> int:
        response = test_app.post(
            "/entities",
            json={"name": name, "tag_ids": tag_ids or []},
            headers={"x-token": token},
        )
        assert response.status_code == 200, response.text
        return response.json()["id"]

    def create_treasury(name: str) -> int:
        response = test_app.post(
            "/treasuries", json={"name": name}, headers={"x-token": token}
        )
        assert response.status_code == 200, response.text
        return response.json()["id"]

    deposit = create_entity("System Balance Deposit", [9])
    withdrawal = create_entity("System Balance Withdrawal", [10])
    exchange = create_entity("System Balance Exchange", [12])
    creditor = create_entity("System Balance Creditor")
    second_creditor = create_entity("System Balance Second Creditor")
    debtor = create_entity("System Balance Debtor")
    first_treasury = create_treasury("System Balance Treasury One")
    second_treasury = create_treasury("System Balance Treasury Two")

    def create_transaction(
        from_entity_id: int,
        to_entity_id: int,
        amount: str,
        to_treasury_id: int | None = None,
    ) -> None:
        response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": from_entity_id,
                "to_entity_id": to_entity_id,
                "amount": amount,
                "currency": "usd",
                "status": "completed",
                "to_treasury_id": to_treasury_id,
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200, response.text

    create_transaction(deposit, creditor, "100.00")
    create_transaction(deposit, second_creditor, "60.00", first_treasury)
    create_transaction(deposit, second_creditor, "10.00", second_treasury)
    create_transaction(debtor, creditor, "25.00")
    # Positive balances on boundary entities must not count as virtual liabilities.
    create_transaction(deposit, withdrawal, "40.00")
    create_transaction(deposit, exchange, "30.00")

    today = date.today().isoformat()
    response = test_app.get(
        "/stats/system-balance-history",
        params={"timeframe_from": today, "timeframe_to": today},
        headers={"x-token": token},
    )
    assert response.status_code == 200, response.text
    latest = response.json()[-1]
    assert latest["day"] == today
    assert latest["real_funds_usd"] == pytest.approx(70.00)
    # creditor=125, second_creditor=70, debtor=-25 (discarded)
    assert latest["positive_entity_balances_usd"] == pytest.approx(195.00)
    assert latest["deficit_usd"] == pytest.approx(125.00)

    today_date = date.today()
    previous_month_end = today_date.replace(day=1) - timedelta(days=1)
    previous_month_start = previous_month_end.replace(day=1)
    monthly_response = test_app.get(
        "/stats/system-balance-history",
        params={
            "timeframe_from": previous_month_start.isoformat(),
            "timeframe_to": today,
        },
        headers={"x-token": token},
    )
    assert monthly_response.status_code == 200, monthly_response.text
    assert [row["day"] for row in monthly_response.json()] == [
        previous_month_end.isoformat(),
        today,
    ]


def test_entity_stats_bundle_has_bounded_query_count(test_app: TestClient, token):
    """A longer chart range must not issue one balance query per day."""

    with StatsService._cache_lock:
        StatsService._cache.clear()
        StatsService._entity_cache_index.clear()
        StatsService._treasury_cache_index.clear()

    select_count = 0

    def count_selects(conn, cursor, statement, parameters, context, executemany):
        nonlocal select_count
        if statement.lstrip().upper().startswith(("SELECT", "WITH")):
            select_count += 1

    event.listen(Engine, "before_cursor_execute", count_selects)
    try:
        response = test_app.get(
            "/stats/entity/1",
            params={"months": 12, "limit": 5},
            headers={"x-token": token},
        )
    finally:
        event.remove(Engine, "before_cursor_execute", count_selects)

    assert response.status_code == 200, response.text
    assert select_count <= 8


def test_monthly_fee_stats_separate_f0_and_room_shares_of_multi_recipient_invoice(
    test_app: TestClient, token
):
    billing_period = date.today().replace(day=1).isoformat()

    def create_entity(name: str, tag_ids: list[int] | None = None) -> int:
        response = test_app.post(
            "/entities",
            json={"name": name, "tag_ids": tag_ids or []},
            headers={"x-token": token},
        )
        assert response.status_code == 200, response.text
        return response.json()["id"]

    resident = create_entity("Multi-recipient stats resident")
    room_recipient = create_entity("Multi-recipient stats room", [19])
    funding_entity = create_entity("Multi-recipient stats funding")

    funding_response = test_app.post(
        "/transactions",
        json={
            "from_entity_id": funding_entity,
            "to_entity_id": resident,
            "amount": "50.00",
            "currency": "usd",
            "status": "completed",
        },
        headers={"x-token": token},
    )
    assert funding_response.status_code == 200, funding_response.text

    invoice_response = test_app.post(
        "/invoices",
        json={
            "from_entity_id": resident,
            "billing_period": billing_period,
            "tag_ids": [3],
            "items": [
                {
                    "to_entity_id": 1,
                    "amounts": [
                        {"currency": "usd", "amount": "40.00"},
                        {"currency": "gel", "amount": "100.00"},
                    ],
                },
                {
                    "to_entity_id": room_recipient,
                    "amounts": [
                        {"currency": "usd", "amount": "10.00"},
                        {"currency": "gel", "amount": "25.00"},
                    ],
                },
            ],
        },
        headers={"x-token": token},
    )
    assert invoice_response.status_code == 200, invoice_response.text
    invoice = invoice_response.json()

    pay_response = test_app.post(
        f"/invoices/{invoice['id']}/pay-items",
        json={
            "items": [
                {
                    "item_id": item["id"],
                    "to_entity_id": item["to_entity_id"],
                    "currency": "usd",
                }
                for item in invoice["items"]
            ]
        },
        headers={"x-token": token},
    )
    assert pay_response.status_code == 200, pay_response.text

    # Historical multi-recipient payments were linked through invoice_item_id
    # only. Stats must follow InvoiceItem.transaction even when invoice_id is null.
    config_provider = app.dependency_overrides.get(get_config, get_config)
    db_conn = DatabaseConnection(config=config_provider())
    session = db_conn.get_session()
    try:
        item_ids = [item["id"] for item in invoice["items"]]
        item_transactions = session.query(Transaction).filter(
            Transaction.invoice_item_id.in_(item_ids)
        )
        for transaction in item_transactions:
            transaction.invoice_id = None
            transaction.tags = []
        session.commit()
    finally:
        session.close()
        db_conn.engine.dispose()

    expense_response = test_app.post(
        "/transactions",
        json={
            "from_entity_id": 1,
            "to_entity_id": room_recipient,
            "amount": "30.00",
            "currency": "usd",
            "status": "completed",
            "tag_ids": [7],
        },
        headers={"x-token": token},
    )
    assert expense_response.status_code == 200, expense_response.text

    params = {
        "timeframe_from": billing_period,
        "timeframe_to": billing_period,
    }
    sum_response = test_app.get(
        "/stats/monthly-fee-sum-by-month",
        params=params,
        headers={"x-token": token},
    )
    assert sum_response.status_code == 200, sum_response.text
    sum_row = next(
        row
        for row in sum_response.json()
        if (row["year"], row["month"]) == (date.today().year, date.today().month)
    )
    assert sum_row["amounts"] == {"usd": 40.0}
    assert sum_row["total_usd"] == pytest.approx(40.0)
    assert sum_row["expected_total_usd"] == pytest.approx(40.0)
    assert "expenses_usd" not in sum_row

    transaction_response = test_app.get(
        "/stats/fee-transactions-by-month",
        params={
            "timeframe_from": billing_period,
            "timeframe_to": date.today().isoformat(),
        },
        headers={"x-token": token},
    )
    assert transaction_response.status_code == 200, transaction_response.text
    assert transaction_response.json() == [
        {
            "year": date.today().year,
            "month": date.today().month,
            "f0_fee_total_usd": 40.0,
            "room_fee_total_usd": 10.0,
            "expenses_usd": 30.0,
        }
    ]


def test_donations_by_month_separates_f0_and_general_transactions(
    test_app: TestClient, token
):
    def create_entity(name: str) -> int:
        response = test_app.post(
            "/entities",
            json={"name": name},
            headers={"x-token": token},
        )
        assert response.status_code == 200, response.text
        return response.json()["id"]

    donor = create_entity("Monthly donation donor")
    other_recipient = create_entity("Monthly donation other recipient")

    def create_transaction(
        from_entity_id: int,
        to_entity_id: int,
        amount: str,
        tag_ids: list[int] | None = None,
    ) -> None:
        response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": from_entity_id,
                "to_entity_id": to_entity_id,
                "amount": amount,
                "currency": "usd",
                "status": "completed",
                "tag_ids": tag_ids or [],
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200, response.text

    create_transaction(2, donor, "40.00")
    create_transaction(donor, 1, "25.00", [5])
    create_transaction(donor, other_recipient, "7.00", [5])
    create_transaction(donor, 1, "8.00")

    today = date.today()
    response = test_app.get(
        "/stats/donations-by-month",
        params={
            "timeframe_from": today.replace(day=1).isoformat(),
            "timeframe_to": today.isoformat(),
        },
        headers={"x-token": token},
    )
    assert response.status_code == 200, response.text
    assert response.json() == [
        {
            "year": today.year,
            "month": today.month,
            "f0_donation_total_usd": 25.0,
            "general_donation_total_usd": 7.0,
        }
    ]


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
